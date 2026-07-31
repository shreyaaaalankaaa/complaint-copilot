"""Complaint record CRUD. Every write goes to the audit trail."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AIAssessment, AuditLog, Complaint
from app.schemas import ComplaintCreate, ComplaintOut, ComplaintStatusUpdate
from app.services import audit
from app.services.numbering import next_complaint_no

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintOut, status_code=201)
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db)) -> Complaint:
    fields = payload.draft.model_dump(exclude_none=True)
    risk = payload.assessment.risk if payload.assessment else None

    complaint = Complaint(
        complaint_no=next_complaint_no(db),
        source_type=payload.source_type,
        raw_text=payload.raw_text,
        status="Draft",
        regulatory_reportable=bool(
            risk and risk.regulatory_flags.get("requires_regulatory_reporting_review")
        ),
        **fields,
    )
    db.add(complaint)
    db.flush()

    if payload.assessment:
        a = payload.assessment
        db.add(
            AIAssessment(
                complaint_id=complaint.id,
                risk_level=a.risk.risk_level,
                risk_score=a.risk.risk_score,
                risk_rationale=a.risk.rationale,
                regulatory_flags=a.risk.regulatory_flags,
                completeness=a.completeness.model_dump(),
                duplicates=[d.model_dump() for d in a.duplicates],
                root_causes=[r.model_dump() for r in a.root_causes],
                capa=a.capa.model_dump(),
                summary=a.summary,
                trace=[s.model_dump() for s in a.trace],
                engine=a.engine,
                models_used=a.models_used,
                latency_ms=a.latency_ms,
            )
        )

    audit.record(
        db, entity="complaint", entity_id=complaint.id, action="create",
        actor=payload.actor, after=audit.snapshot(complaint),
        reason=f"Logged from {payload.source_type} intake",
    )
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("", response_model=list[ComplaintOut])
def list_complaints(
    db: Session = Depends(get_db),
    status: str | None = None,
    severity: str | None = None,
    q: str | None = Query(None, description="Matches product, batch or customer"),
    limit: int = Query(50, le=200),
) -> list[Complaint]:
    stmt = select(Complaint).order_by(Complaint.id.desc())
    if status:
        stmt = stmt.where(Complaint.status == status)
    if severity:
        stmt = stmt.where(Complaint.severity == severity)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            Complaint.product_name.ilike(like)
            | Complaint.batch_no.ilike(like)
            | Complaint.customer_name.ilike(like)
        )
    return list(db.execute(stmt.limit(limit)).scalars().all())


@router.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    rows = db.execute(select(Complaint)).scalars().all()
    by = lambda key: {  # noqa: E731
        value: sum(1 for r in rows if getattr(r, key) == value)
        for value in sorted({getattr(r, key) for r in rows if getattr(r, key)})
    }
    return {
        "total": len(rows),
        "open": sum(1 for r in rows if r.status not in ("Closed", "Rejected")),
        "by_severity": by("severity"),
        "by_status": by("status"),
        "by_category": by("complaint_category"),
    }


@router.get("/{complaint_id}")
def get_complaint(complaint_id: int, db: Session = Depends(get_db)) -> dict:
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    assessment = complaint.latest_assessment
    trail = db.execute(
        select(AuditLog)
        .where(AuditLog.entity == "complaint", AuditLog.entity_id == complaint_id)
        .order_by(AuditLog.id.desc())
    ).scalars().all()

    return {
        "complaint": ComplaintOut.model_validate(complaint).model_dump(),
        "detail": {
            c.name: getattr(complaint, c.name)
            for c in Complaint.__table__.columns
            if c.name != "raw_text"
        },
        "raw_text": complaint.raw_text,
        "assessment": None if not assessment else {
            "risk_level": assessment.risk_level,
            "risk_score": assessment.risk_score,
            "rationale": assessment.risk_rationale,
            "regulatory_flags": assessment.regulatory_flags,
            "completeness": assessment.completeness,
            "duplicates": assessment.duplicates,
            "root_causes": assessment.root_causes,
            "capa": assessment.capa,
            "summary": assessment.summary,
            "trace": assessment.trace,
            "engine": assessment.engine,
            "models_used": assessment.models_used,
            "latency_ms": assessment.latency_ms,
        },
        "audit_trail": [
            {"id": a.id, "action": a.action, "actor": a.actor, "reason": a.reason,
             "at": a.at, "before": a.before, "after": a.after}
            for a in trail
        ],
    }


@router.patch("/{complaint_id}/status", response_model=ComplaintOut)
def update_status(
    complaint_id: int, payload: ComplaintStatusUpdate, db: Session = Depends(get_db)
) -> Complaint:
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    before = audit.snapshot(complaint)
    complaint.status = payload.status
    db.flush()
    audit.record(
        db, entity="complaint", entity_id=complaint.id, action="status_change",
        actor=payload.actor, reason=payload.reason, before=before, after=audit.snapshot(complaint),
    )
    db.commit()
    db.refresh(complaint)
    return complaint
