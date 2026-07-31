"""End-to-end tests over the real graph, on SQLite, with no API key.

This is the contract a reviewer cares about: the product works, and works
without Groq credentials, because the deterministic engine covers every node.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["GROQ_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

EMAIL = """From: Northbridge QA <quality@northbridge.example>
Date: Thu, 23 Jul 2026 16:02:10 +0100
Subject: Particulate matter complaint

Customer: Northbridge Healthcare Ltd
Product: Amoxicillin Trihydrate Capsules 250 mg
Batch No: AMX-8817
Quantity affected: 95 capsules

Black particulate matter was found inside capsule shells in three cartons during
goods-in inspection. Stock has been quarantined and complaint samples retained.
No adverse reactions have been reported.
"""


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_engine(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["fast_model"] == "gemma2-9b-it"


def test_graph_runs_every_node(client):
    body = client.post("/api/v1/intake/analyze", json={"text": EMAIL}).json()
    nodes = [step["node"] for step in body["assessment"]["trace"]]
    for expected in ("triage", "extract", "check_completeness", "scan_duplicates",
                     "classify_risk", "assemble"):
        assert expected in nodes


def test_extraction_populates_the_form(client):
    draft = client.post("/api/v1/intake/analyze", json={"text": EMAIL}).json()["draft"]
    assert draft["batch_no"] == "AMX-8817"
    assert draft["product_name"].startswith("Amoxicillin")
    assert draft["received_date"] == "2026-07-23"
    assert draft["adverse_event"] is False  # "no adverse reactions" must not flip this


def test_completeness_and_risk_are_returned(client):
    assessment = client.post("/api/v1/intake/analyze", json={"text": EMAIL}).json()["assessment"]
    assert assessment["risk"]["risk_level"] in ("Critical", "Major", "Minor")
    assert assessment["completeness"]["score"] > 0
    assert len(assessment["root_causes"]) >= 1
    assert assessment["capa"]["corrective_actions"]


def test_non_complaint_is_rejected(client):
    body = client.post(
        "/api/v1/intake/analyze",
        json={"text": "Please find our purchase order HP-2026-8841 for 200,000 tablets. "
                      "Confirm indicative Q4 pricing and whether the lead time has improved."},
    ).json()
    assert body["is_valid_complaint"] is False
    assert body["rejection_reason"]


def test_save_then_duplicate_is_detected(client):
    first = client.post("/api/v1/intake/analyze", json={"text": EMAIL}).json()
    saved = client.post(
        "/api/v1/complaints",
        json={"draft": first["draft"], "source_type": "email", "raw_text": EMAIL,
              "assessment": first["assessment"]},
    )
    assert saved.status_code == 201
    assert saved.json()["complaint_no"].startswith("CMP-")

    again = client.post("/api/v1/intake/analyze", json={"text": EMAIL}).json()
    matches = again["assessment"]["duplicates"]
    assert matches and matches[0]["batch_no"] == "AMX-8817"


def test_status_change_is_audited(client):
    listing = client.get("/api/v1/complaints").json()
    complaint_id = listing[0]["id"]
    client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status": "Under Investigation", "reason": "QA head approved"},
    )
    detail = client.get(f"/api/v1/complaints/{complaint_id}").json()
    actions = [entry["action"] for entry in detail["audit_trail"]]
    assert "status_change" in actions and "create" in actions
