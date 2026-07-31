"""Append-only audit trail helper (21 CFR Part 11 / ALCOA+ flavour)."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, Complaint

TRACKED = [
    "complaint_no", "customer_name", "product_name", "batch_no", "complaint_category",
    "complaint_description", "severity", "status", "adverse_event", "regulatory_reportable",
]


def snapshot(complaint: Complaint) -> dict[str, Any]:
    return {field: _plain(getattr(complaint, field, None)) for field in TRACKED}


def _plain(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def record(
    db: Session,
    *,
    entity: str,
    entity_id: int | None,
    action: str,
    actor: str = "qa.reviewer",
    reason: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        entity=entity, entity_id=entity_id, action=action, actor=actor,
        reason=reason, before=before, after=after,
    )
    db.add(entry)
    return entry
