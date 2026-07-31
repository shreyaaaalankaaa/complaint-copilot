"""Pydantic contracts shared by the API and the agent."""
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["Critical", "Major", "Minor"]


class ComplaintDraft(BaseModel):
    """What the agent extracts and what the 'Log Customer Complaint' form binds to.

    Everything is optional by design: the extractor must be allowed to return
    nothing rather than hallucinate a batch number.
    """

    received_date: date | None = None
    reported_by: str | None = None
    complaint_source: str | None = None   # Pharmacy | Email | Phone | Distributor | Portal
    customer_name: str | None = None
    customer_site: str | None = None
    country: str | None = None
    contact_email: str | None = None

    product_name: str | None = None
    generic_name: str | None = None
    product_type: Literal["API", "FDF"] | None = None
    dosage_form: str | None = None
    strength: str | None = None
    batch_no: str | None = None
    mfg_date: date | None = None
    expiry_date: date | None = None
    quantity_supplied: str | None = None
    quantity_affected: str | None = None

    # Facility & material impact (section 3 of the form)
    originating_site_block: str | None = None
    impacted_npm: str | None = None       # impacted non-product materials

    complaint_category: str | None = None
    complaint_description: str | None = None
    sample_available: bool | None = None
    adverse_event: bool | None = None
    severity: Severity | None = None


class RiskAssessment(BaseModel):
    risk_level: Severity | None = None
    risk_score: float | None = Field(None, ge=0, le=100)
    rationale: str | None = None
    suggested_next_action: str | None = None
    patient_safety_impact: str | None = None
    regulatory_flags: dict[str, Any] = Field(default_factory=dict)


class CompletenessReport(BaseModel):
    score: int = 0
    missing_mandatory: list[str] = Field(default_factory=list)
    missing_recommended: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    investigation_ready: bool = False


class DuplicateHit(BaseModel):
    complaint_id: int
    complaint_no: str
    similarity: float
    matched_on: list[str] = Field(default_factory=list)
    product_name: str | None = None
    batch_no: str | None = None
    status: str | None = None


class RootCause(BaseModel):
    category: str  # Ishikawa 6M
    hypothesis: str
    confidence: float = 0.0
    evidence: str | None = None
    verification_step: str | None = None


class CAPAProposal(BaseModel):
    immediate_correction: list[str] = Field(default_factory=list)
    corrective_actions: list[str] = Field(default_factory=list)
    preventive_actions: list[str] = Field(default_factory=list)
    effectiveness_checks: list[str] = Field(default_factory=list)
    target_closure_days: int | None = None


class AgentStep(BaseModel):
    node: str
    label: str
    status: Literal["ok", "skipped", "error"] = "ok"
    model: str | None = None
    latency_ms: int | None = None
    note: str | None = None


class Assessment(BaseModel):
    """The whole right-hand 'AI Copilot' panel in one object."""

    risk: RiskAssessment = Field(default_factory=RiskAssessment)
    completeness: CompletenessReport = Field(default_factory=CompletenessReport)
    duplicates: list[DuplicateHit] = Field(default_factory=list)
    root_causes: list[RootCause] = Field(default_factory=list)
    capa: CAPAProposal = Field(default_factory=CAPAProposal)
    summary: str | None = None
    trace: list[AgentStep] = Field(default_factory=list)
    engine: str = "fallback"
    models_used: list[str] = Field(default_factory=list)
    latency_ms: int = 0
    errors: list[str] = Field(default_factory=list)


class IntakeRequest(BaseModel):
    text: str | None = None
    source_type: Literal["text", "email", "pdf", "manual"] = "text"


class CorrectionRequest(BaseModel):
    """A follow-up turn: the reviewer corrects the form in plain language."""

    thread_id: str
    message: str


class IntakeResponse(BaseModel):
    thread_id: str
    is_valid_complaint: bool = True
    rejection_reason: str | None = None
    source_type: str = "text"
    raw_text: str = ""
    draft: ComplaintDraft = Field(default_factory=ComplaintDraft)
    field_confidence: dict[str, float] = Field(default_factory=dict)
    assessment: Assessment = Field(default_factory=Assessment)

    # Set only on a correction turn: what the copilot changed and what it said.
    patch_confirmation: str | None = None
    applied_fields: list[str] = Field(default_factory=list)


class ComplaintCreate(BaseModel):
    draft: ComplaintDraft
    source_type: str = "manual"
    raw_text: str | None = None
    assessment: Assessment | None = None
    actor: str = "qa.reviewer"


class ComplaintStatusUpdate(BaseModel):
    status: str
    reason: str | None = None
    actor: str = "qa.reviewer"


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_no: str
    source_type: str
    received_date: date | None
    customer_name: str | None
    product_name: str | None
    batch_no: str | None
    complaint_category: str | None
    complaint_description: str | None
    severity: str | None
    status: str
    adverse_event: bool | None
    regulatory_reportable: bool | None
    created_at: datetime


class CopilotQuestion(BaseModel):
    complaint_id: int | None = None
    thread_id: str | None = None
    question: str
