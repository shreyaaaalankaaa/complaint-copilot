"""Intake endpoints: text in or file in, populated complaint form + copilot out."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.agents.runner import run_correction, run_intake
from app.config import get_settings
from app.database import get_db
from app.schemas import CorrectionRequest, IntakeRequest, IntakeResponse
from app.services.extraction import extract_text

router = APIRouter(prefix="/intake", tags=["intake"])
settings = get_settings()


@router.post("/analyze", response_model=IntakeResponse)
def analyze_text(payload: IntakeRequest, db: Session = Depends(get_db)) -> IntakeResponse:
    """Free-text or pasted-email intake. Nothing is persisted here -- a reviewer
    reviews the populated form first and then saves it."""
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="Provide complaint text to analyze.")
    return run_intake(text=text, source_type=payload.source_type, db=db)


@router.post("/upload", response_model=IntakeResponse)
async def analyze_upload(
    file: UploadFile = File(...),
    note: str | None = Form(None),
    db: Session = Depends(get_db),
) -> IntakeResponse:
    """PDF / .eml / .txt / image intake."""
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB.")

    source_type, text = extract_text(file.filename or "upload", data)
    if note:
        text = f"{text}\n\n--- reviewer note ---\n{note}"
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No text could be read from this file. If it is a scan, type the complaint text instead.",
        )
    return run_intake(text=text, source_type=source_type, db=db)


@router.post("/correct", response_model=IntakeResponse)
def correct(payload: CorrectionRequest, db: Session = Depends(get_db)) -> IntakeResponse:
    """Conversational correction of an in-progress form.

    The reviewer types "sorry, the batch number is BMX240602 and the affected
    quantity is 48 capsules" and the copilot patches those two fields, confirms
    what it changed, and re-runs the assessment against the corrected record.
    """
    if not payload.message.strip():
        raise HTTPException(status_code=422, detail="Type a correction, for example: the batch number is AMX240602.")
    return run_correction(thread_id=payload.thread_id, message=payload.message, db=db)
