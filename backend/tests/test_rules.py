"""Tests for the deterministic layer.

These are the rules that must not drift: negation handling, mandatory-field
gating and the risk ratchet. They are also the parts that run identically with
and without an API key, so they are the parts worth pinning in CI.
"""
from app.services import rules


class TestNegation:
    def test_denied_adverse_event_is_not_an_adverse_event(self):
        text = "The pharmacist confirmed no adverse reaction has been reported by the patient."
        assert rules.mentions(text, "adverse") is False

    def test_reported_adverse_event_is_detected(self):
        text = "The patient developed a rash and an adverse reaction was reported to the pharmacy."
        assert rules.mentions(text, "adverse reaction") is True

    def test_negation_does_not_leak_across_sentences(self):
        text = "No stock was dispensed. An adverse reaction was later reported by the clinic."
        assert rules.mentions(text, "adverse reaction") is True


class TestClassification:
    def test_particulate_complaint_is_physical_quality(self):
        text = "Black particulate matter was found embedded in the tablets in three cartons."
        assert rules.classify_category(text) == "Product Quality - Physical"

    def test_purchase_order_is_not_a_complaint(self):
        text = "Please find our purchase order for 200,000 tablets. Confirm Q4 pricing and lead time."
        accepted, _ = rules.looks_like_complaint(text)
        assert accepted is False

    def test_defect_report_is_a_complaint(self):
        text = "We are raising a complaint: the tablets show discolouration and we have quarantined the batch."
        accepted, _ = rules.looks_like_complaint(text)
        assert accepted is True


class TestRisk:
    def test_adverse_event_scores_critical(self):
        level, score, _, flags = rules.score_risk(
            {"adverse_event": True}, "The patient was hospitalised after taking the product."
        )
        assert level == "Critical"
        assert score >= 60
        assert flags["potential_field_alert_report"] is True

    def test_cosmetic_defect_stays_minor(self):
        level, _, _, flags = rules.score_risk({}, "One carton was slightly dented in transit.")
        assert level == "Minor"
        assert flags["potential_recall_evaluation"] is False


class TestCompleteness:
    def test_missing_batch_blocks_investigation(self):
        report = rules.completeness(
            {"customer_name": "Acme", "product_name": "X", "complaint_description": "y",
             "received_date": "2026-07-01"}
        )
        assert "Batch / lot number" in report["missing_mandatory"]
        assert report["investigation_ready"] is False
        assert any("batch" in q.lower() for q in report["follow_up_questions"])

    def test_full_record_is_investigation_ready(self):
        report = rules.completeness(
            {field: "value" for field in rules.MANDATORY_FIELDS}
        )
        assert report["investigation_ready"] is True


class TestExtraction:
    def test_labelled_fields_beat_regex_guesses(self):
        text = "Product: Cefixime Tablets 100 mg\nBatch No: CFX-4472\nQuantity affected: 27 tablets"
        draft, confidence = rules.heuristic_extract(text)
        assert draft["batch_no"] == "CFX-4472"
        assert draft["product_name"] == "Cefixime Tablets 100 mg"
        assert draft["quantity_affected"] == "27 tablets"
        assert confidence["batch_no"] >= 0.7
