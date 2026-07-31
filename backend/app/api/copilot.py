"""AI Copilot: ask questions about a saved complaint, or re-run the assessment."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.prompts import COPILOT_SYSTEM
from app.agents.runner import run_intake
from app.database import get_db
from app.models import Complaint
from app.schemas import CopilotQuestion, IntakeResponse
from app.services.llm import LLMUnavailable, llm_router

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/ask")
def ask(payload: CopilotQuestion, db: Session = Depends(get_db)) -> dict:
    context = ""
    if payload.complaint_id:
        complaint = db.get(Complaint, payload.complaint_id)
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found.")
        assessment = complaint.latest_assessment
        context = (
            f"COMPLAINT {complaint.complaint_no}\n"
            f"Customer: {complaint.customer_name} | Product: {complaint.product_name} "
            f"| Batch: {complaint.batch_no} | Category: {complaint.complaint_category} "
            f"| Severity: {complaint.severity} | Status: {complaint.status}\n"
            f"Description: {complaint.complaint_description}\n"
            f"Risk: {getattr(assessment, 'risk_level', None)} - {getattr(assessment, 'risk_rationale', None)}\n"
            f"Root causes: {getattr(assessment, 'root_causes', None)}\n"
            f"CAPA: {getattr(assessment, 'capa', None)}\n"
        )

    if not llm_router.enabled:
        return {
            "answer": "The copilot Q&A needs a Groq API key. Set GROQ_API_KEY in backend/.env and restart. "
                      "Extraction, risk, CAPA and duplicate detection continue to run on the rule engine.",
            "confidence": 0.0,
            "engine": "fallback",
        }

    try:
        result = llm_router.complete_json(
            system=COPILOT_SYSTEM,
            user=f"{context}\nQUESTION: {payload.question}",
            tier="reasoning",
            node="copilot",
        )
        return {
            "answer": result.data.get("answer", ""),
            "confidence": result.data.get("confidence", 0.0),
            "engine": "groq",
            "model": result.model,
            "latency_ms": result.latency_ms,
        }
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"Copilot unavailable: {exc}") from exc


@router.post("/reassess/{complaint_id}", response_model=IntakeResponse)
def reassess(complaint_id: int, db: Session = Depends(get_db)) -> IntakeResponse:
    """Re-run the full graph against a saved complaint -- used after fields are edited."""
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    text = complaint.raw_text or (
        f"Customer: {complaint.customer_name}\nProduct: {complaint.product_name}\n"
        f"Batch: {complaint.batch_no}\nComplaint: {complaint.complaint_description}"
    )
    return run_intake(
        text=text, source_type=complaint.source_type, db=db, thread_id=f"complaint-{complaint_id}"
    )
