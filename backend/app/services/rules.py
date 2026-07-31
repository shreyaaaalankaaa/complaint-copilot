"""Deterministic domain rules.

Two jobs:

1. Things that must NOT be left to a language model. Which fields are mandatory
   before an investigation can open, and whether a complaint is potentially
   reportable, are procedural decisions. They belong in code that a QA head can
   read and a regulator can inspect, and they must give the same answer today
   and next Tuesday. The LLM adds judgement on top; it does not own the rule.

2. A working fallback so the whole product still demos with no GROQ_API_KEY set.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from dateutil import parser as dateparser

MANDATORY_FIELDS = {
    "customer_name": "Customer name",
    "product_name": "Product name",
    "batch_no": "Batch / lot number",
    "complaint_description": "Complaint description",
    "received_date": "Date complaint received",
}
RECOMMENDED_FIELDS = {
    "quantity_affected": "Quantity affected",
    "expiry_date": "Expiry date",
    "sample_available": "Retention / complaint sample availability",
    "contact_email": "Complainant contact",
    "complaint_category": "Complaint category",
    "country": "Country of distribution",
}

FOLLOW_UPS = {
    "batch_no": "Which batch / lot number is affected? It is on the label and the CoA.",
    "quantity_affected": "How many units or how much quantity is affected out of the quantity supplied?",
    "sample_available": "Is a complaint sample available for return, and has it been retained?",
    "expiry_date": "What is the expiry date printed on the affected pack?",
    "received_date": "On what date was the complaint received?",
    "customer_name": "Which customer or distributor raised this complaint?",
    "product_name": "Which product is affected, including strength and dosage form?",
    "complaint_description": "What exactly was observed, and when was it first noticed?",
    "country": "In which country was the affected material distributed?",
    "contact_email": "What is the contact email for follow-up with the complainant?",
    "complaint_category": "How should this complaint be categorised?",
}

CATEGORY_KEYWORDS = {
    "Adverse Event / Medical": ["adverse", "hospital", "rash", "nausea", "reaction", "injury", "patient harm", "side effect"],
    "Cold Chain Excursion": ["cold chain", "temperature excursion", "2-8", "reefer", "thermal", "data logger", "frozen"],
    "Packaging / Labelling": ["label", "misprint", "overprint", "leaflet", "artwork", "seal integrity", "barcode", "mislabel", "wrong strength on"],
    "Product Quality - Physical": ["discolor", "discolour", "particle", "particulate", "speck", "black spot", "chipped", "capping", "broken", "crack", "clump", "lump", "foreign matter", "foreign", "odour", "odor", "caking", "crystal"],
    "Product Quality - Chemical": ["assay", "impurity", "out of specification", "oos", "dissolution", "potency", "degradation", "related substance", "moisture", "loss on drying"],
    "Documentation (CoA / COC)": ["coa", "certificate of analysis", "coc", "document", "invoice", "batch record", "annexure"],
    "Shipping & Transit Damage": ["damaged in transit", "pallet", "drum dent", "shipment damage", "wet carton", "torn"],
    "Shortage / Quantity": ["short supply", "shortage", "missing units", "quantity short", "count mismatch"],
}

CRITICAL_SIGNALS = [
    "adverse", "hospital", "patient harm", "injury", "death", "recall", "counterfeit",
    "wrong product", "wrong drug", "cross contamination", "sterility", "mix-up", "mixup",
]
MAJOR_SIGNALS = [
    "out of specification", "oos", "impurity", "foreign particle", "black particle",
    "label", "mislabel", "temperature excursion", "cold chain", "assay", "dissolution",
    "discolor", "discolour", "potency", "particulate", "foreign matter", "black particulate",
]

# Negation matters here. "No adverse reaction has been reported" is the single most
# common sentence in a complaint letter, and a naive keyword match reads it as an
# adverse event and escalates the whole complaint to Critical. Every keyword lookup
# below goes through `mentions()`.
NEGATORS = ("no ", "not ", "never ", "without ", "denies ", "nil ", "none ", "n/a")


def mentions(text: str, term: str) -> bool:
    """True if `term` appears without a negator in the 32 characters before it."""
    lower = text.lower()
    start = 0
    while (index := lower.find(term, start)) != -1:
        window = lower[max(0, index - 32) : index]
        # A negator only binds within its own sentence.
        boundary = max(window.rfind("."), window.rfind(";"), window.rfind("\n"))
        if boundary != -1:
            window = window[boundary + 1 :]
        if not any(neg in window for neg in NEGATORS):
            return True
        start = index + len(term)
    return False


def any_mention(text: str, terms: list[str]) -> bool:
    return any(mentions(text, term) for term in terms)


LABEL_RE_CACHE: dict[str, re.Pattern] = {}


def labeled(text: str, labels: list[str]) -> str | None:
    """Read a 'Label: value' line -- how complaint letters and forms are actually written."""
    for label in labels:
        pattern = LABEL_RE_CACHE.setdefault(
            label, re.compile(rf"^[ \t>*-]*{label}\s*[:\-]\s*(.+)$", re.I | re.M)
        )
        match = pattern.search(text)
        if match:
            value = match.group(1).strip().strip(".,;")
            value = re.split(r"\s{3,}|\s+\|\s+", value)[0].strip()
            if value and value.lower() not in ("", "n/a", "na", "tbc", "unknown", "not known"):
                return value[:200]
    return None


SECTION_RE = re.compile(r"^([A-Z][A-Z \-/&]{6,60})$", re.M)


def section(text: str, *names: str) -> str | None:
    """Pull the body under an ALL-CAPS heading such as 'COMPLAINT DESCRIPTION'."""
    headings = [(m.start(), m.end(), m.group(1).strip()) for m in SECTION_RE.finditer(text)]
    for index, (_, end, title) in enumerate(headings):
        if any(name.upper() in title for name in names):
            stop = headings[index + 1][0] if index + 1 < len(headings) else len(text)
            body = " ".join(text[end:stop].split())
            if len(body) > 40:
                return body
    return None


FROM_RE = re.compile(r"^From:\s*(.+)$", re.M | re.I)
DATE_HDR_RE = re.compile(r"^Date:\s*(.+)$", re.M | re.I)
SUBJECT_RE = re.compile(r"^Subject:\s*(.+)$", re.M | re.I)
# "Batch number AMX240602" used to capture the word "number", because the value
# pattern is case-insensitive and "number" satisfies it. A batch code has to
# contain a digit and must not be one of the words that introduce it.
BATCH_STOPWORDS = {"number", "numbers", "no", "nos", "code", "id", "is", "was", "the", "ref"}
BATCH_RE = re.compile(
    r"(?:batch|lot|b\.?\s?no)\s*(?:number|no\.?|code)?[^A-Za-z0-9]{0,6}"
    r"([A-Za-z0-9][A-Za-z0-9\-/ ]{3,20})", re.I
)
# Prose forms: "Apollo Pharmacy reported ...", "... in Amoxicillin Capsules 500 mg"
REPORTER_RE = re.compile(r"^\s*([A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,4})\s+"
                         r"(?:reported|has reported|raised|complained|notified)", re.M)
PRODUCT_PROSE_RE = re.compile(
    r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s+"
    r"(Capsules?|Tablets?|Injections?|Syrups?|Suspensions?|Ointments?|Creams?|API)\b"
)
MONTH_YEAR_RE = r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})"
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
STRENGTH_RE = re.compile(r"\b(\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|iu|%)(?:\s?/\s?\d+\s?(?:mg|ml))?)\b", re.I)
QTY_RE = re.compile(r"\b(\d[\d,]{0,8}(?:\.\d+)?)\s?(tablets?|capsules?|vials?|bottles?|packs?|units?|kg|g|drums?|cartons?|strips?)\b", re.I)
DOSAGE_FORMS = ["tablet", "capsule", "injection", "syrup", "suspension", "ointment", "cream", "powder", "granule", "sachet", "vial", "ampoule"]


def _find_date(text: str, labels: list[str]) -> date | None:
    for label in labels:
        month_year = re.search(rf"{label}[^A-Za-z0-9]{{0,15}}{MONTH_YEAR_RE}", text, re.I)
        if month_year:
            try:
                return dateparser.parse(month_year.group(1), default=datetime(2000, 1, 1)).date()
            except (ValueError, OverflowError):
                pass
        match = re.search(rf"{label}[^A-Za-z0-9]{{0,15}}([0-9]{{1,4}}[-/\s.][A-Za-z0-9]{{1,9}}[-/\s.][0-9]{{2,4}})", text, re.I)
        if match:
            try:
                return dateparser.parse(match.group(1), dayfirst=True, fuzzy=True).date()
            except (ValueError, OverflowError):
                continue
    return None


def heuristic_extract(text: str) -> tuple[dict, dict[str, float]]:
    """Label-first, regex-second extraction.

    Labelled lines score higher than regex guesses because 'Batch No: CFX-4472'
    is a statement, while a bare token that looks like a batch code is inference.
    Nothing here exceeds 0.7 confidence: this is the no-LLM path and the UI shows
    the reviewer exactly how sure each field is.
    """
    draft: dict = {}
    confidence: dict[str, float] = {}

    def put(field: str, value, score: float) -> None:
        if value not in (None, "", []) and field not in draft:
            draft[field] = value
            confidence[field] = score

    # -- labelled fields (high confidence) --------------------------------- #
    put("customer_name", labeled(text, ["customer", "customer name", "complainant", "distributor", "company"]), 0.7)
    put("customer_site", labeled(text, ["site", "depot", "warehouse", "customer site", "plant"]), 0.6)
    put("country", labeled(text, ["country", "country of distribution", "market"]), 0.7)
    put("reported_by", labeled(text, ["raised by", "reported by", "contact person", "attention"]), 0.7)
    put("product_name", labeled(text, ["product", "product name", "material", "item", "drug product"]), 0.7)
    put("generic_name", labeled(text, ["generic name", "generic", "inn", "api name"]), 0.7)
    put("batch_no", labeled(text, ["batch no", "batch number", "batch", "lot no", "lot number", "lot", "b\\.? ?no"]), 0.7)
    put("quantity_supplied", labeled(text, ["quantity supplied", "qty supplied", "supplied quantity"]), 0.7)
    put("quantity_affected", labeled(text, ["quantity affected", "affected quantity", "qty affected"]), 0.7)
    put("dosage_form", labeled(text, ["dosage form", "form"]), 0.6)
    put("strength", labeled(text, ["strength"]), 0.6)

    # From: header on an email -> who is complaining
    if (sender := FROM_RE.search(text)) and "customer_name" not in draft:
        raw = sender.group(1).strip()
        name = re.sub(r"<[^>]*>", "", raw).strip().strip('"')
        if name and "@" not in name:
            put("reported_by", name, 0.55)
            org = re.search(r"@([\w-]+)\.", raw)
            if org:
                put("customer_name", org.group(1).replace("-", " ").title(), 0.4)

    # -- regex fallbacks (lower confidence) -------------------------------- #
    if "batch_no" not in draft and (batch := BATCH_RE.search(text)):
        candidate = batch.group(1).strip(" .,;:")
        if any(ch.isdigit() for ch in candidate) and candidate.lower() not in BATCH_STOPWORDS:
            put("batch_no", candidate, 0.55)
    if (email := EMAIL_RE.search(text)):
        put("contact_email", email.group(0), 0.65)
    if "strength" not in draft and (strength := STRENGTH_RE.search(text)):
        put("strength", strength.group(1), 0.45)
    if "quantity_affected" not in draft and (qty := QTY_RE.search(text)):
        put("quantity_affected", f"{qty.group(1)} {qty.group(2)}", 0.3)

    # An email always carries a Date header, and "date received" is mandatory on
    # the form, so parse the header before falling back to prose date hunting.
    if (header := DATE_HDR_RE.search(text)):
        try:
            put("received_date", dateparser.parse(header.group(1), fuzzy=True).date(), 0.75)
        except (ValueError, OverflowError, TypeError):
            pass
    put("received_date", _find_date(text, ["date raised", "date received", "received", "date of complaint", "complaint date"]), 0.6)
    put("expiry_date", _find_date(text, ["expiry date", "exp date", "expiry", "expiration", "use before", "exp"]), 0.6)
    put("mfg_date", _find_date(text, ["mfg date", "manufacturing date", "manufactur", "mfd", "mfg"]), 0.6)

    lower = text.lower()
    if "dosage_form" not in draft:
        for form in DOSAGE_FORMS:
            if form in lower:
                put("dosage_form", (form + "s" if form + "s" in lower else form).capitalize(), 0.4)
                break
    if "product_type" not in draft:
        put("product_type", "API" if re.search(r"\bAPI\b|active pharmaceutical ingredient", text) else "FDF", 0.35)

    # -- derived judgements ------------------------------------------------- #
    # Prose intake ("Apollo Pharmacy reported discoloured capsules in Amoxicillin
    # Capsules 500 mg") carries no labels at all, so read the sentence shape.
    if "customer_name" not in draft and (reporter := REPORTER_RE.search(text)):
        put("customer_name", reporter.group(1).strip(), 0.55)
    if "product_name" not in draft and (product := PRODUCT_PROSE_RE.search(text)):
        name = f"{product.group(1)} {product.group(2)}"
        strength_hint = STRENGTH_RE.search(text[product.end() : product.end() + 40])
        put("product_name", f"{name} {strength_hint.group(1)}" if strength_hint else name, 0.5)
    if "complaint_source" not in draft:
        customer = (draft.get("customer_name") or "").lower()
        put("complaint_source",
            "Email" if "From:" in text else
            "Pharmacy" if "pharmacy" in customer else
            "Distributor" if any(w in customer for w in ("distribution", "distributor")) else None,
            0.5)

    put("complaint_category", classify_category(text), 0.5)
    put("adverse_event", any_mention(text, ["adverse", "hospital", "rash", "adverse reaction", "injury", "side effect"]), 0.55)
    put("sample_available", True if any_mention(text, ["sample", "samples are available", "retained"]) else None, 0.45)

    description = section(text, "COMPLAINT DESCRIPTION", "DESCRIPTION", "DETAILS OF COMPLAINT", "OBSERVATION")
    put("complaint_description", description or " ".join(text.split())[:1200], 0.6 if description else 0.3)
    return draft, confidence


def classify_category(text: str) -> str | None:
    best, best_hits = None, 0
    for category, words in CATEGORY_KEYWORDS.items():
        hits = sum(1 for word in words if mentions(text, word))
        # Adverse Event only wins on an un-negated, explicit signal; a letter that
        # says "no adverse reaction reported" must not land in that category.
        if category == "Adverse Event / Medical" and hits < 2:
            continue
        if hits > best_hits:
            best, best_hits = category, hits
    return best


def classify_severity(text: str) -> str:
    if any_mention(text, CRITICAL_SIGNALS):
        return "Critical"
    if any_mention(text, MAJOR_SIGNALS):
        return "Major"
    return "Minor"


def score_risk(draft: dict, text: str) -> tuple[str, float, str, dict]:
    """Weighted score in 0-100 with an explainable rationale."""
    blob = f"{text} {draft.get('complaint_description') or ''}"
    score, reasons = 10.0, []

    if draft.get("adverse_event") or any_mention(blob, ["adverse", "hospital", "injury", "adverse reaction"]):
        score += 55
        reasons.append("possible adverse event reported by the complainant")
    if any_mention(blob, ["wrong product", "mix-up", "mixup", "cross contamination", "counterfeit", "sterility"]):
        score += 40
        reasons.append("signal of product mix-up, contamination or falsification")
    if any_mention(blob, ["out of specification", "oos", "assay", "impurity", "dissolution", "potency"]):
        score += 25
        reasons.append("possible out-of-specification quality attribute")
    if any_mention(blob, ["label", "mislabel", "misprint", "artwork"]):
        score += 20
        reasons.append("labelling defect with mis-dosing potential")
    if any_mention(blob, ["cold chain", "temperature excursion", "excursion"]):
        score += 18
        reasons.append("storage condition excursion affecting stability")
    if any_mention(blob, ["particle", "particulate", "speck", "foreign matter", "black spot", "discolor", "discolour"]):
        score += 22
        reasons.append("visible foreign matter or discolouration in the dosage form")
    if any_mention(blob, ["multiple batches", "several batches", "other batches", "recurring", "again"]):
        score += 12
        reasons.append("indication of more than one batch or a repeat occurrence")

    score = max(0.0, min(100.0, score))
    level = "Critical" if score >= 60 else "Major" if score >= 30 else "Minor"
    rationale = (
        "Scored on " + "; ".join(reasons) + "."
        if reasons
        else "No patient-safety, specification or labelling signal detected in the narrative."
    )
    flags = {
        "potential_field_alert_report": level == "Critical",
        "potential_recall_evaluation": level == "Critical",
        "requires_regulatory_reporting_review": level in ("Critical", "Major"),
        "target_closure_days": 30 if level == "Critical" else 60 if level == "Major" else 90,
    }
    return level, score, rationale, flags


def completeness(draft: dict) -> dict:
    missing_mandatory = [
        label for field, label in MANDATORY_FIELDS.items() if not draft.get(field)
    ]
    missing_recommended = [
        label for field, label in RECOMMENDED_FIELDS.items() if draft.get(field) in (None, "")
    ]
    total = len(MANDATORY_FIELDS) + len(RECOMMENDED_FIELDS)
    filled = total - len(missing_mandatory) - len(missing_recommended)
    questions = [
        FOLLOW_UPS[field]
        for field in list(MANDATORY_FIELDS) + list(RECOMMENDED_FIELDS)
        if not draft.get(field) and field in FOLLOW_UPS
    ][:5]
    return {
        "score": round(filled / total * 100),
        "missing_mandatory": missing_mandatory,
        "missing_recommended": missing_recommended,
        "follow_up_questions": questions,
        "investigation_ready": not missing_mandatory,
    }


def fallback_root_causes(draft: dict) -> list[dict]:
    category = draft.get("complaint_category") or ""
    library = {
        "Product Quality - Physical": [
            ("Material", "Excipient or API lot variability affecting appearance or hardness", "Compare the raw material CoA and vendor lot against adjacent batches"),
            ("Machine", "Punch or die wear on the compression machine causing chipping and capping", "Review the tooling inspection log and preventive maintenance record for the line"),
            ("Environment", "Humidity excursion in the packing area causing caking or discolouration", "Pull area RH/temperature trends for the packing window"),
        ],
        "Packaging / Labelling": [
            ("Method", "Line clearance not effective between two artwork versions", "Review line clearance records and reconciliation for the batch"),
            ("Machine", "Print registration drift on the labeller", "Check inline vision system challenge test results"),
            ("Man", "Operator loaded an obsolete label reel", "Verify label issuance and reconciliation records"),
        ],
        "Cold Chain Excursion": [
            ("Environment", "Reefer or passive shipper failure during transit", "Download and review the data logger profile end to end"),
            ("Method", "Shipper qualification does not cover the lane's ambient profile", "Compare lane ambient data against the shipper qualification envelope"),
        ],
        "Product Quality - Chemical": [
            ("Material", "Input material impurity profile carried into the finished product", "Trend impurity results for the API lot across finished batches"),
            ("Method", "Analytical method or sample handling difference at the customer site", "Request the customer's method and perform a joint OOS investigation"),
            ("Environment", "Storage at the customer site outside the labelled condition", "Request storage records from receipt to test"),
        ],
    }
    entries = library.get(
        category,
        [
            ("Method", "Process step not robust enough to prevent the reported defect", "Review batch record and in-process control data for the batch"),
            ("Material", "Input material variability", "Compare vendor lot data against previously accepted lots"),
            ("Man", "Procedural deviation during manufacture or packing", "Review training records and deviations raised for the batch"),
        ],
    )
    return [
        {
            "category": cat,
            "hypothesis": hypothesis,
            "confidence": round(0.6 - index * 0.12, 2),
            "evidence": f"Pattern typical for the '{category or 'general'}' complaint category",
            "verification_step": step,
        }
        for index, (cat, hypothesis, step) in enumerate(entries)
    ]


def fallback_capa(draft: dict, risk_level: str) -> dict:
    batch = draft.get("batch_no") or "the affected batch"
    return {
        "immediate_correction": [
            f"Place remaining stock of {batch} on hold at the site and at the distributor",
            "Request return of the complaint sample and log it into the complaint sample register",
            "Review the retention sample against the customer's observation",
        ],
        "corrective_actions": [
            "Open an investigation and complete root cause analysis within the target closure period",
            "Extend the review to other batches manufactured on the same line in the same campaign",
            "Update the batch record or SOP step identified as the root cause",
        ],
        "preventive_actions": [
            "Add the failure mode to the risk assessment for the product family",
            "Add an in-process check or an inline detection control for the defect",
            "Retrain the affected operators and record training effectiveness",
        ],
        "effectiveness_checks": [
            "Zero recurrence of the same defect category for the product over the next six batches",
            "Trend complaints for this product quarterly in the Product Quality Review",
        ],
        "target_closure_days": 30 if risk_level == "Critical" else 60 if risk_level == "Major" else 90,
    }


def fallback_summary(draft: dict, risk_level: str) -> str:
    parts = [
        f"{draft.get('customer_name') or 'A customer'} reported",
        f"a {(draft.get('complaint_category') or 'product quality').lower()} complaint",
        f"for {draft.get('product_name') or 'the supplied product'}",
    ]
    if draft.get("batch_no"):
        parts.append(f"batch {draft['batch_no']}")
    if draft.get("quantity_affected"):
        parts.append(f"affecting {draft['quantity_affected']}")
    body = " ".join(parts)
    detail = (draft.get("complaint_description") or "").strip()
    detail = (detail[:220] + "...") if len(detail) > 220 else detail
    return (
        f"{body}. Reported observation: {detail} "
        f"Preliminary risk classification is {risk_level}. "
        "Confirm batch traceability and retention sample review before opening the investigation."
    ).strip()


COMPLAINT_SIGNALS = [
    "complaint", "defect", "out of specification", "discolour", "discolor", "particulate",
    "damaged", "excursion", "mislabel", "wrong", "contaminat", "shortage", "adverse",
    "quarantine", "investigation", "batch record", "recall", "not conform", "deviation",
]
NON_COMPLAINT_SIGNALS = [
    "purchase order", "quotation", "pricing", "price list", "invoice due", "lead time",
    "delivery schedule", "meeting", "webinar", "job application", "resume", "newsletter",
]


def looks_like_complaint(text: str) -> tuple[bool, str]:
    """Fallback triage for the no-API-key path.

    Kept blunt and slightly permissive: wrongly rejecting a real complaint is a
    regulatory failure, wrongly accepting a purchase order costs a reviewer ten
    seconds. The asymmetry decides the tie-break.
    """
    complaint_hits = sum(1 for term in COMPLAINT_SIGNALS if term in text.lower())
    other_hits = sum(1 for term in NON_COMPLAINT_SIGNALS if term in text.lower())
    if other_hits and complaint_hits == 0:
        return False, "Reads as a commercial enquiry or order rather than a product complaint."
    if complaint_hits == 0 and len(text.split()) > 40:
        return False, "No quality defect, deviation or product issue is described."
    return True, "Complaint indicators present."


CORRECTION_TARGETS = {
    "batch_no": ["batch number", "batch no", "batch", "lot number", "lot no", "lot"],
    "quantity_affected": ["affected quantity", "quantity affected", "affected qty", "quantity"],
    "product_name": ["product name", "product"],
    "customer_name": ["customer name", "customer"],
    "strength": ["strength", "grade"],
    "expiry_date": ["expiry date", "expiry"],
    "mfg_date": ["manufacturing date", "mfg date"],
    "complaint_source": ["complaint source", "source"],
    "originating_site_block": ["site block", "originating site", "block"],
    "impacted_npm": ["non-product material", "npm", "impacted material"],
}
FIELD_LABELS = {
    "batch_no": "Batch / Lot Number", "quantity_affected": "Affected Quantity",
    "product_name": "Product Name", "customer_name": "Customer Name",
    "strength": "Product Strength", "expiry_date": "Expiry Date",
    "mfg_date": "Manufacturing Date", "complaint_source": "Complaint Source",
    "originating_site_block": "Originating Site Block",
    "impacted_npm": "Impacted Non-Product Materials",
    "complaint_category": "Complaint Category", "complaint_description": "Complaint Description",
}


def parse_correction(message: str) -> dict[str, str]:
    """Fallback parser for 'the batch number is X and affected quantity is Y'.

    Splits on 'and' so a single sentence can carry several corrections, which is
    how people actually talk. The LLM path handles anything more involved.
    """
    updates: dict[str, str] = {}
    for clause in re.split(r"\band\b", message, flags=re.I):
        matched_here = False  # one correction per clause, but every clause gets a turn
        for field, aliases in CORRECTION_TARGETS.items():
            for alias in aliases:
                match = re.search(
                    rf"{re.escape(alias)}\s*(?:is|should be|=|:|to)\s*(.+?)(?:[.,;]\s*$|$)",
                    clause, re.I,
                )
                if match:
                    value = match.group(1).strip().strip("\"'. ")
                    if value:
                        updates[field] = value
                        matched_here = True
                    break
            if matched_here:
                break
    return updates


def describe_patch(updates: dict[str, str]) -> str:
    if not updates:
        return "I could not tell which field to change. Name the field and the new value."
    parts = [f"the {FIELD_LABELS.get(field, field)} to \"{value}\"" for field, value in updates.items()]
    joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"I have updated {joined} in the form."


def suggest_next_action(risk_level: str, category: str | None) -> str:
    if risk_level == "Critical":
        return "Laboratory investigation & manufacturing record review"
    if (category or "").startswith("Packaging"):
        return "Route to Packaging QA & line clearance review"
    if risk_level == "Major":
        return "Route to QA Investigation & Issue Replacement"
    return "Log for trending & acknowledge to customer"


def today() -> date:
    return datetime.now().date()
