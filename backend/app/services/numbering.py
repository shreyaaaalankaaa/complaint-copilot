"""Complaint numbering: CMP-<year>-<sequence>, unique and gapless per year."""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Complaint


def next_complaint_no(db: Session) -> str:
    year = datetime.now().year
    prefix = f"CMP-{year}-"
    latest = db.execute(
        select(func.max(Complaint.complaint_no)).where(Complaint.complaint_no.like(f"{prefix}%"))
    ).scalar()
    sequence = int(latest.split("-")[-1]) + 1 if latest else 1
    return f"{prefix}{sequence:04d}"
