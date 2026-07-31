"""Runs the graph for the API layer and shapes the result into `IntakeResponse`."""
from __future__ import annotations

import time
import uuid

from sqlalchemy.orm import Session

from app.agents.graph import complaint_graph
from app.schemas import (
    Assessment, ComplaintDraft, CompletenessReport, IntakeResponse, RiskAssessment,
)
from app.services.llm import llm_router


def _invoke(payload: dict, thread_id: str, db: Session) -> tuple[dict, int]:
    started = time.perf_counter()
    final = complaint_graph.invoke(
        {**payload, "thread_id": thread_id, "trace": [], "errors": [], "models_used": []},
        config={"configurable": {"thread_id": thread_id, "db": db}},
    )
    return final, int((time.perf_counter() - started) * 1000)


def run_intake(*, text: str, source_type: str, db: Session, thread_id: str | None = None) -> IntakeResponse:
    thread_id = thread_id or f"intake-{uuid.uuid4().hex[:12]}"
    final, latency_ms = _invoke(
        {"mode": "intake", "raw_text": text, "source_type": source_type}, thread_id, db
    )
    return _shape(final, thread_id, latency_ms)


def _shape(final: dict, thread_id: str, latency_ms: int) -> IntakeResponse:
    draft = ComplaintDraft.model_validate(final.get("draft") or {})

    assessment = Assessment(
        risk=RiskAssessment.model_validate(final.get("risk") or {}),
        completeness=CompletenessReport.model_validate(final.get("completeness") or {}),
        duplicates=final.get("duplicates") or [],
        root_causes=final.get("root_causes") or [],
        capa=final.get("capa") or {},
        summary=final.get("summary"),
        trace=final.get("trace") or [],
        engine="groq" if llm_router.enabled else "fallback",
        models_used=sorted(set(final.get("models_used") or [])),
        latency_ms=latency_ms,
        errors=final.get("errors") or [],
    )

    return IntakeResponse(
        thread_id=thread_id,
        is_valid_complaint=final.get("is_valid_complaint", True),
        rejection_reason=final.get("rejection_reason"),
        source_type=final.get("source_type") or "text",
        raw_text=final.get("raw_text") or "",
        draft=draft,
        field_confidence=final.get("field_confidence") or {},
        assessment=assessment,
    )


def run_correction(*, thread_id: str, message: str, db: Session) -> IntakeResponse:
    """Follow-up turn.

    Nothing about the source document is passed in again: `MemorySaver` restores
    the draft, raw text and confidences recorded against this thread_id, the patch
    is merged, and the downstream analysis re-runs against the corrected record.
    """
    final, latency_ms = _invoke({"mode": "correction", "user_message": message}, thread_id, db)
    response = _shape(final, thread_id, latency_ms)
    response.patch_confirmation = final.get("patch_confirmation")
    response.applied_fields = final.get("applied_fields") or []
    return response
