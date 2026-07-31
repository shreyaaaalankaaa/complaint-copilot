"""ORM models.

Field set mirrors the customer-complaint record of a pharmaceutical QMS for an
API / FDF manufacturer (see docs/QMS_NOTES.md). Two things are deliberate:

* `AuditLog` is append-only -- every write to a complaint is recorded with the
  before/after image. Under 21 CFR Part 11 a quality record without an
  attributable, contemporaneous audit trail is not a quality record.
* Every AI-produced value lands in `AIAssessment`, never silently inside the
  complaint row. A human still owns the complaint record; the agent advises it.
"""
from datetime import date, datetime

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

SEVERITIES = ("Critical", "Major", "Minor")
STATUSES = ("Draft", "Under Investigation", "Pending CAPA", "Closed", "Rejected")
COMPLAINT_SOURCES = ("Pharmacy", "Email", "Phone", "Distributor", "Customer Portal", "Field Force")
SITE_BLOCKS = ("Block A - OSD", "Block B - Sterile", "Block C - API", "Block D - Packaging", "Contract Site")
NPM_OPTIONS = ("Primary packaging", "Secondary packaging", "Shipper / carton", "Label / leaflet", "Desiccant", "None")

CATEGORIES = (
    "Product Quality - Physical",
    "Product Quality - Chemical",
    "Packaging / Labelling",
    "Documentation (CoA / COC)",
    "Shipping & Transit Damage",
    "Cold Chain Excursion",
    "Adverse Event / Medical",
    "Shortage / Quantity",
    "Foreign Matter Contamination",
    "Product Defect - Discoloration",
)


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    # Intake
    source_type: Mapped[str] = mapped_column(String(24), default="manual")  # email|pdf|text|manual
    received_date: Mapped[date | None] = mapped_column(Date)
    reported_by: Mapped[str | None] = mapped_column(String(160))
    complaint_source: Mapped[str | None] = mapped_column(String(48))

    # Customer
    customer_name: Mapped[str | None] = mapped_column(String(200), index=True)
    customer_site: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(80))
    contact_email: Mapped[str | None] = mapped_column(String(160))

    # Product
    product_name: Mapped[str | None] = mapped_column(String(200), index=True)
    generic_name: Mapped[str | None] = mapped_column(String(200))
    product_type: Mapped[str | None] = mapped_column(String(16))  # API | FDF
    dosage_form: Mapped[str | None] = mapped_column(String(80))
    strength: Mapped[str | None] = mapped_column(String(80))
    batch_no: Mapped[str | None] = mapped_column(String(64), index=True)
    mfg_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    quantity_supplied: Mapped[str | None] = mapped_column(String(80))
    quantity_affected: Mapped[str | None] = mapped_column(String(80))

    # Facility & material impact
    originating_site_block: Mapped[str | None] = mapped_column(String(120))
    impacted_npm: Mapped[str | None] = mapped_column(String(200))

    # Complaint body
    complaint_category: Mapped[str | None] = mapped_column(String(64), index=True)
    complaint_description: Mapped[str | None] = mapped_column(Text)
    sample_available: Mapped[bool | None] = mapped_column(Boolean)
    adverse_event: Mapped[bool | None] = mapped_column(Boolean, default=False)
    regulatory_reportable: Mapped[bool | None] = mapped_column(Boolean, default=False)

    # Disposition
    severity: Mapped[str | None] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(32), default="Draft", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(120))
    due_date: Mapped[date | None] = mapped_column(Date)

    raw_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    assessments: Mapped[list["AIAssessment"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan", order_by="AIAssessment.id.desc()"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan"
    )

    @property
    def latest_assessment(self) -> "AIAssessment | None":
        return self.assessments[0] if self.assessments else None


class AIAssessment(Base):
    """One run of the LangGraph agent against one complaint."""

    __tablename__ = "ai_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id", ondelete="CASCADE"))

    risk_level: Mapped[str | None] = mapped_column(String(16))
    risk_score: Mapped[float | None] = mapped_column(Float)
    risk_rationale: Mapped[str | None] = mapped_column(Text)
    regulatory_flags: Mapped[dict | None] = mapped_column(JSON)

    completeness: Mapped[dict | None] = mapped_column(JSON)
    duplicates: Mapped[list | None] = mapped_column(JSON)
    root_causes: Mapped[list | None] = mapped_column(JSON)
    capa: Mapped[dict | None] = mapped_column(JSON)
    summary: Mapped[str | None] = mapped_column(Text)

    field_confidence: Mapped[dict | None] = mapped_column(JSON)
    trace: Mapped[list | None] = mapped_column(JSON)
    engine: Mapped[str | None] = mapped_column(String(24))  # groq | fallback
    models_used: Mapped[list | None] = mapped_column(JSON)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    complaint: Mapped[Complaint] = relationship(back_populates="assessments")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    extracted_chars: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    complaint: Mapped[Complaint] = relationship(back_populates="attachments")


class AuditLog(Base):
    """Append-only. Never updated, never deleted."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(120), default="qa.reviewer")
    reason: Mapped[str | None] = mapped_column(String(255))
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
