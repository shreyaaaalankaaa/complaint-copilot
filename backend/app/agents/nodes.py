"""LangGraph nodes.

Every node follows the same contract:

    (state, config) -> partial state update, including one `trace` entry

The trace is what the AI Copilot panel renders as the agent timeline, so a
reviewer can see which node produced which value, on which model, in how long.
Each node degrades independently: if Groq is unavailable or returns junk, that
single node falls back to `app.services.rules` and marks itself in the trace.
No node is allowed to raise into the request.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.prompts import (
    CAPA_SYSTEM, CORRECTION_SYSTEM, EXTRACT_SYSTEM, RISK_SYSTEM, ROOT_CAUSE_SYSTEM,
    SUMMARY_SYSTEM, TRIAGE_SYSTEM,
)
from app.agents.state import GraphState
from app.schemas import ComplaintDraft
from app.services import rules
from app.services.duplicates import find_duplicates
from app.services.llm import LLMUnavailable, llm_router

log = logging.getLogger(__name__)
MAX_CHARS = 12_000


def _step(node: str, label: str, started: float, *, model=None, status="ok", note=None) -> dict:
    return {
        "node": node,
        "label": label,
        "status": status,
        "model": model,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "note": note,
    }


def _source(state: GraphState) -> str:
    return (state.get("raw_text") or "")[:MAX_CHARS]


def _db(config: RunnableConfig):
    return (config or {}).get("configurable", {}).get("db")


# --------------------------------------------------------------------------- #
# 0. entry router
# --------------------------------------------------------------------------- #
def route_entry(state: GraphState) -> str:
    """First turn re-reads the document; later turns patch the form in place.

    Both paths share everything downstream of the draft, so a correction still
    re-checks completeness, re-scans for duplicates and re-scores risk -- changing
    a batch number can turn an isolated defect into a recurring one, and the
    reviewer should see that immediately rather than after saving.
    """
    return "correction" if state.get("mode") == "correction" else "intake"


def parse_correction_node(state: GraphState, config: RunnableConfig) -> dict:
    """Turn 'sorry, the batch is BMX240602' into a field-level patch."""
    started = time.perf_counter()
    message = (state.get("user_message") or "").strip()
    draft = state.get("draft") or {}

    if llm_router.enabled:
        try:
            result = llm_router.complete_json(
                system=CORRECTION_SYSTEM,
                user=f"CURRENT FORM:\n{draft}\n\nREVIEWER MESSAGE:\n{message}",
                tier="fast",
                node="parse_correction",
            )
            updates = {
                key: value
                for key, value in (result.data.get("updates") or {}).items()
                if key in ComplaintDraft.model_fields and value not in (None, "")
            }
            return {
                "patch": updates,
                "patch_confirmation": result.data.get("confirmation") or rules.describe_patch(updates),
                "models_used": [result.model],
                "trace": [_step("parse_correction", "Read the correction", started,
                                model=result.model, note=f"{len(updates)} field(s)")],
            }
        except LLMUnavailable as exc:
            log.warning("parse_correction fell back: %s", exc)

    updates = rules.parse_correction(message)
    return {
        "patch": updates,
        "patch_confirmation": rules.describe_patch(updates),
        "trace": [_step("parse_correction", "Read the correction", started,
                        note=f"rule engine - {len(updates)} field(s)")],
    }


def apply_patch_node(state: GraphState, config: RunnableConfig) -> dict:
    """Merge the patch into the draft the checkpointer restored for this thread."""
    started = time.perf_counter()
    patch = state.get("patch") or {}
    draft = dict(state.get("draft") or {})
    draft.update(_clean_draft(patch) if patch else {})

    confidence = dict(state.get("field_confidence") or {})
    for field in patch:
        confidence[field] = 1.0  # stated outright by the reviewer

    return {
        "draft": draft,
        "field_confidence": confidence,
        "applied_fields": list(patch.keys()),
        "trace": [_step("apply_patch", "Update the form", started,
                        note=", ".join(patch) or "no change")],
    }


# --------------------------------------------------------------------------- #
# 1. triage
# --------------------------------------------------------------------------- #
def triage_node(state: GraphState, config: RunnableConfig) -> dict:
    started = time.perf_counter()
    text = _source(state)

    if len(text.strip()) < 25:
        return {
            "is_valid_complaint": False,
            "rejection_reason": "The input is too short to log as a complaint. Paste the complaint text or upload the email or PDF.",
            "trace": [_step("triage", "Triage input", started, status="skipped", note="input below minimum length")],
        }

    if llm_router.enabled:
        try:
            result = llm_router.complete_json(
                system=TRIAGE_SYSTEM, user=f"MESSAGE:\n{text}", tier="fast", node="triage"
            )
            is_complaint = bool(result.data.get("is_complaint", True))
            return {
                "is_valid_complaint": is_complaint,
                "rejection_reason": None if is_complaint else (result.data.get("reason") or "This does not read as a product complaint."),
                "models_used": [result.model],
                "trace": [_step("triage", "Triage input", started, model=result.model,
                                note=result.data.get("intent"))],
            }
        except LLMUnavailable as exc:
            log.warning("triage fell back: %s", exc)

    is_complaint, reason = rules.looks_like_complaint(text)
    return {
        "is_valid_complaint": is_complaint,
        "rejection_reason": None if is_complaint else reason,
        "trace": [_step("triage", "Triage input", started,
                        status="ok" if is_complaint else "skipped", note="rule engine")],
    }


def route_after_triage(state: GraphState) -> str:
    return "extract" if state.get("is_valid_complaint", True) else "reject"


def reject_node(state: GraphState, config: RunnableConfig) -> dict:
    started = time.perf_counter()
    return {
        "draft": {},
        "field_confidence": {},
        "trace": [_step("reject", "Not logged as a complaint", started, status="skipped",
                        note=state.get("rejection_reason"))],
    }


# --------------------------------------------------------------------------- #
# 2. extraction
# --------------------------------------------------------------------------- #
def _clean_draft(fields: dict[str, Any]) -> dict[str, Any]:
    """Validate through the Pydantic contract so dates and enums are real."""
    safe = {k: v for k, v in fields.items() if v not in ("", "null", "N/A", "n/a")}
    try:
        return ComplaintDraft.model_validate(safe).model_dump(mode="json", exclude_none=True)
    except Exception:  # noqa: BLE001 - salvage field by field
        salvaged: dict[str, Any] = {}
        for key, value in safe.items():
            try:
                salvaged.update(
                    ComplaintDraft.model_validate({key: value}).model_dump(mode="json", exclude_none=True)
                )
            except Exception:  # noqa: BLE001
                continue
        return salvaged


def extract_node(state: GraphState, config: RunnableConfig) -> dict:
    started = time.perf_counter()
    text = _source(state)

    heuristic_draft, heuristic_conf = rules.heuristic_extract(text)
    heuristic_draft = _clean_draft(heuristic_draft)

    if llm_router.enabled:
        try:
            result = llm_router.complete_json(
                system=EXTRACT_SYSTEM,
                user=f"SOURCE TYPE: {state.get('source_type', 'text')}\n\nSOURCE TEXT:\n{text}",
                tier="fast",
                node="extract",
            )
            llm_draft = _clean_draft(result.data.get("fields") or {})
            confidence = {
                k: float(v) for k, v in (result.data.get("confidence") or {}).items()
                if isinstance(v, (int, float))
            }
            # LLM wins; regex fills only the gaps it left.
            merged = {**heuristic_draft, **llm_draft}
            merged_conf = {**heuristic_conf, **confidence}
            return {
                "draft": merged,
                "field_confidence": {k: round(min(max(v, 0.0), 1.0), 2) for k, v in merged_conf.items() if k in merged},
                "models_used": [result.model],
                "trace": [_step("extract", "Extract complaint fields", started, model=result.model,
                                note=f"{len(merged)} fields populated")],
            }
        except LLMUnavailable as exc:
            return {
                "draft": heuristic_draft,
                "field_confidence": heuristic_conf,
                "errors": [f"extract: {exc}"],
                "trace": [_step("extract", "Extract complaint fields", started, status="error",
                                note="rule engine used - LLM unavailable")],
            }

    return {
        "draft": heuristic_draft,
        "field_confidence": heuristic_conf,
        "trace": [_step("extract", "Extract complaint fields", started, note="rule engine")],
    }


# --------------------------------------------------------------------------- #
# 3. completeness  (deterministic by design - see services/rules.py)
# --------------------------------------------------------------------------- #
def completeness_node(state: GraphState, config: RunnableConfig) -> dict:
    started = time.perf_counter()
    report = rules.completeness(state.get("draft") or {})
    return {
        "completeness": report,
        "trace": [_step("check_completeness", "Check complaint completeness", started,
                        note=f"{report['score']}% complete")],
    }


# --------------------------------------------------------------------------- #
# 4. duplicate scan  (database, no LLM)
# --------------------------------------------------------------------------- #
def duplicate_node(state: GraphState, config: RunnableConfig) -> dict:
    started = time.perf_counter()
    db = _db(config)
    if db is None:
        return {"duplicates": [], "trace": [_step("scan_duplicates", "Scan for duplicates", started,
                                                  status="skipped", note="no database session")]}
    hits = find_duplicates(db, state.get("draft") or {})
    return {
        "duplicates": hits,
        "trace": [_step("scan_duplicates", "Scan for duplicates", started,
                        note=f"{len(hits)} possible match(es)")],
    }


# --------------------------------------------------------------------------- #
# 5. risk classification
# --------------------------------------------------------------------------- #
def risk_node(state: GraphState, config: RunnableConfig) -> dict:
    started = time.perf_counter()
    draft = state.get("draft") or {}
    text = _source(state)
    level, score, rationale, flags = rules.score_risk(draft, text)
    baseline = {
        "risk_level": level, "risk_score": score, "rationale": rationale,
        "suggested_next_action": rules.suggest_next_action(level, draft.get("complaint_category")),
        "patient_safety_impact": None, "regulatory_flags": flags,
    }

    if llm_router.enabled:
        try:
            result = llm_router.complete_json(
                system=RISK_SYSTEM,
                user=(
                    f"COMPLAINT RECORD:\n{draft}\n\n"
                    f"DUPLICATE / RECURRENCE SIGNALS: {state.get('duplicates') or 'none'}\n\n"
                    f"ORIGINAL SOURCE:\n{text[:4000]}"
                ),
                tier="fast",
                node="risk",
            )
            data = result.data
            merged = {
                "risk_level": data.get("risk_level") or level,
                "risk_score": float(data.get("risk_score") or score),
                "rationale": data.get("rationale") or rationale,
                "suggested_next_action": data.get("suggested_next_action")
                or rules.suggest_next_action(level, draft.get("complaint_category")),
                "patient_safety_impact": data.get("patient_safety_impact"),
                "regulatory_flags": {**flags, **(data.get("regulatory_flags") or {})},
            }
            # Safety ratchet: the rule engine may raise the level, never lower it.
            order = {"Minor": 0, "Major": 1, "Critical": 2}
            if order.get(level, 0) > order.get(merged["risk_level"], 0):
                merged["risk_level"] = level
                merged["rationale"] = f"{merged['rationale']} Escalated by the rule engine: {rationale}"
            return {
                "risk": merged,
                "models_used": [result.model],
                "trace": [_step("classify_risk", "Classify risk", started, model=result.model,
                                note=merged["risk_level"])],
            }
        except LLMUnavailable as exc:
            return {"risk": baseline, "errors": [f"risk: {exc}"],
                    "trace": [_step("classify_risk", "Classify risk", started, status="error",
                                    note=f"rule engine used - {level}")]}

    return {"risk": baseline, "trace": [_step("classify_risk", "Classify risk", started, note=f"rule engine - {level}")]}


# --------------------------------------------------------------------------- #
# 6-8. fan-out branch: root cause / CAPA / summary run in one super-step
# --------------------------------------------------------------------------- #
def root_cause_node(state: GraphState, config: RunnableConfig) -> dict:
    started = time.perf_counter()
    draft = state.get("draft") or {}
    if llm_router.enabled:
        try:
            result = llm_router.complete_json(
                system=ROOT_CAUSE_SYSTEM,
                user=f"COMPLAINT RECORD:\n{draft}\n\nRISK: {state.get('risk')}\n\nSOURCE:\n{_source(state)[:3000]}",
                tier="reasoning",
                node="root_cause",
            )
            causes = [c for c in (result.data.get("root_causes") or []) if isinstance(c, dict)]
            if causes:
                return {"root_causes": causes, "models_used": [result.model],
                        "trace": [_step("recommend_root_cause", "Recommend root causes", started,
                                        model=result.model, note=f"{len(causes)} hypotheses")]}
        except LLMUnavailable as exc:
            log.warning("root_cause fell back: %s", exc)
    return {"root_causes": rules.fallback_root_causes(draft),
            "trace": [_step("recommend_root_cause", "Recommend root causes", started, note="rule engine")]}


def capa_node(state: GraphState, config: RunnableConfig) -> dict:
    started = time.perf_counter()
    draft = state.get("draft") or {}
    level = (state.get("risk") or {}).get("risk_level", "Minor")
    if llm_router.enabled:
        try:
            result = llm_router.complete_json(
                system=CAPA_SYSTEM,
                user=f"COMPLAINT RECORD:\n{draft}\n\nRISK: {state.get('risk')}\n\nLIKELY ROOT CAUSES: {state.get('root_causes')}",
                tier="reasoning",
                node="capa",
            )
            if result.data.get("corrective_actions"):
                return {"capa": result.data, "models_used": [result.model],
                        "trace": [_step("draft_capa", "Draft CAPA plan", started, model=result.model)]}
        except LLMUnavailable as exc:
            log.warning("capa fell back: %s", exc)
    return {"capa": rules.fallback_capa(draft, level),
            "trace": [_step("draft_capa", "Draft CAPA plan", started, note="rule engine")]}


def summary_node(state: GraphState, config: RunnableConfig) -> dict:
    started = time.perf_counter()
    draft = state.get("draft") or {}
    level = (state.get("risk") or {}).get("risk_level", "Minor")
    if llm_router.enabled:
        try:
            result = llm_router.complete_json(
                system=SUMMARY_SYSTEM,
                user=f"COMPLAINT RECORD:\n{draft}\n\nRISK LEVEL: {level}",
                tier="fast",
                node="summary",
            )
            if result.data.get("summary"):
                return {"summary": result.data["summary"], "models_used": [result.model],
                        "trace": [_step("write_summary", "Write complaint summary", started, model=result.model)]}
        except LLMUnavailable as exc:
            log.warning("summary fell back: %s", exc)
    return {"summary": rules.fallback_summary(draft, level),
            "trace": [_step("write_summary", "Write complaint summary", started, note="rule engine")]}


# --------------------------------------------------------------------------- #
# 9. assemble (join point for the fan-out)
# --------------------------------------------------------------------------- #
def assemble_node(state: GraphState, config: RunnableConfig) -> dict:
    started = time.perf_counter()
    draft = dict(state.get("draft") or {})
    risk = state.get("risk") or {}

    # The severity shown on the form is the agent's risk level unless extraction
    # found an explicit severity in the source document.
    draft.setdefault("severity", risk.get("risk_level"))
    return {
        "draft": draft,
        "trace": [_step("assemble", "Assemble copilot output", started)],
    }
