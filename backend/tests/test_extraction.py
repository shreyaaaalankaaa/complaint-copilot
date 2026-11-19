"""Rule-engine extraction on the bundled sample artefacts (no Groq key needed)."""
from datetime import date
from pathlib import Path

from app.services.extraction import extract_text
from app.services.rules import heuristic_extract

SAMPLES = Path(__file__).resolve().parents[2] / "sample_data"


def _extract(name: str) -> dict:
    path = SAMPLES / name
    _, text = extract_text(path.name, path.read_bytes())
    draft, _ = heuristic_extract(text)
    return draft


def test_pdf_letterhead_gives_customer_name_not_form_label():
    draft = _extract("complaint_01_particulate.pdf")
    # Used to be "Date", read from the "Date raised:" label.
    assert draft["customer_name"] == "Northbridge Healthcare Ltd"


def test_month_year_pack_dates_are_parsed():
    draft = _extract("complaint_01_particulate.pdf")
    assert draft["mfg_date"] == date(2026, 2, 1)
    assert draft["expiry_date"] == date(2028, 1, 31)  # expiry runs to month end


def test_form_label_is_never_a_customer():
    draft, _ = heuristic_extract("Date raised: 12/07/2026\nBatch No: ABC-1234\nTablets were cracked.")
    assert draft.get("customer_name") != "Date"


def test_prose_reporter_still_works():
    draft, _ = heuristic_extract("Apollo Pharmacy reported discoloured capsules in Amoxicillin Capsules 500 mg.")
    assert draft["customer_name"] == "Apollo Pharmacy"
