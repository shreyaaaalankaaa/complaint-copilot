"""Duplicate complaint detection.

Cheap and explainable on purpose: a QA reviewer has to be able to say *why* two
complaints were linked. Weighted field agreement plus a text similarity ratio
beats an opaque embedding score when the output goes into a regulated record.
"""
from __future__ import annotations

from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Complaint

# An exact batch-number match is on its own enough to put a record in front of the
# reviewer: in complaint handling, two reports against one lot is the pattern that
# turns an isolated defect into a recurring one, and missing it is the expensive error.
WEIGHTS = {"batch_no": 0.50, "product_name": 0.25, "complaint_category": 0.15, "narrative": 0.20}
THRESHOLD = 0.40


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a[:1500], b[:1500]).ratio()


def find_duplicates(
    db: Session, draft: dict, *, exclude_id: int | None = None, limit: int = 5
) -> list[dict]:
    stmt = select(Complaint).order_by(Complaint.id.desc()).limit(300)
    candidates = db.execute(stmt).scalars().all()

    results: list[dict] = []
    draft_narrative = _norm(draft.get("complaint_description"))

    for candidate in candidates:
        if exclude_id and candidate.id == exclude_id:
            continue
        score, matched = 0.0, []

        if draft.get("batch_no") and _norm(draft["batch_no"]) == _norm(candidate.batch_no):
            score += WEIGHTS["batch_no"]
            matched.append("batch number")
        if draft.get("product_name") and candidate.product_name:
            product_ratio = _ratio(_norm(draft["product_name"]), _norm(candidate.product_name))
            if product_ratio > 0.75:
                score += WEIGHTS["product_name"] * product_ratio
                matched.append("product")
        if draft.get("complaint_category") and draft["complaint_category"] == candidate.complaint_category:
            score += WEIGHTS["complaint_category"]
            matched.append("category")

        narrative_ratio = _ratio(draft_narrative, _norm(candidate.complaint_description))
        if narrative_ratio > 0.35:
            score += WEIGHTS["narrative"] * narrative_ratio
            matched.append("narrative")

        if score >= THRESHOLD:
            results.append(
                {
                    "complaint_id": candidate.id,
                    "complaint_no": candidate.complaint_no,
                    "similarity": round(min(score, 1.0), 3),
                    "matched_on": matched,
                    "product_name": candidate.product_name,
                    "batch_no": candidate.batch_no,
                    "status": candidate.status,
                }
            )

    results.sort(key=lambda item: item["similarity"], reverse=True)
    return results[:limit]
