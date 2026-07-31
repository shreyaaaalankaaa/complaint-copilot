"""Seed historical complaints.

These exist so duplicate detection has real history to hit: sample_data/
complaint_03_repeat_batch.eml deliberately repeats the product, batch and defect
of CMP-2026-0002 below, so the Copilot flags it during the demo.

Run:  python -m app.seed
"""
from __future__ import annotations

from datetime import date, timedelta

from app.database import Base, SessionLocal, engine
from app.models import Complaint
from app.services import audit

TODAY = date.today()

SEED = [
    dict(
        complaint_no="CMP-2026-0001",
        source_type="email",
        received_date=TODAY - timedelta(days=46),
        customer_name="Meridian Pharma Distribution",
        customer_site="Rotterdam DC",
        country="Netherlands",
        contact_email="qa@meridianpharma.example",
        product_name="Metformin Hydrochloride Tablets IP 500 mg",
        generic_name="Metformin Hydrochloride",
        product_type="FDF",
        dosage_form="Tablets",
        strength="500 mg",
        batch_no="MET-2451",
        mfg_date=TODAY - timedelta(days=300),
        expiry_date=TODAY + timedelta(days=430),
        quantity_supplied="120,000 tablets",
        quantity_affected="18 tablets",
        complaint_category="Product Quality - Physical",
        complaint_description="Chipped and capped tablets observed in 6 blister strips on visual inspection at goods-in.",
        sample_available=True,
        adverse_event=False,
        regulatory_reportable=False,
        severity="Minor",
        status="Closed",
    ),
    dict(
        complaint_no="CMP-2026-0002",
        source_type="email",
        received_date=TODAY - timedelta(days=21),
        customer_name="Northbridge Healthcare Ltd",
        customer_site="Manchester",
        country="United Kingdom",
        contact_email="quality@northbridge.example",
        product_name="Amoxicillin Trihydrate Capsules 250 mg",
        generic_name="Amoxicillin Trihydrate",
        product_type="FDF",
        dosage_form="Capsules",
        strength="250 mg",
        batch_no="AMX-8817",
        mfg_date=TODAY - timedelta(days=210),
        expiry_date=TODAY + timedelta(days=520),
        quantity_supplied="60,000 capsules",
        quantity_affected="approximately 40 capsules",
        complaint_category="Product Quality - Physical",
        complaint_description="Black particulate matter visible inside capsule shells in two cartons. Pharmacist withheld stock from dispensing.",
        sample_available=True,
        adverse_event=False,
        regulatory_reportable=True,
        severity="Major",
        status="Under Investigation",
    ),
    dict(
        complaint_no="CMP-2026-0003",
        source_type="pdf",
        received_date=TODAY - timedelta(days=14),
        customer_name="Sanjivani Formulations Pvt Ltd",
        customer_site="Ahmedabad Plant",
        country="India",
        contact_email="qc@sanjivaniformulations.example",
        product_name="Paracetamol API",
        generic_name="Paracetamol",
        product_type="API",
        dosage_form="Powder",
        batch_no="PCM-API-3390",
        mfg_date=TODAY - timedelta(days=120),
        expiry_date=TODAY + timedelta(days=700),
        quantity_supplied="500 kg",
        quantity_affected="1 drum (25 kg)",
        complaint_category="Product Quality - Chemical",
        complaint_description="Assay result of 98.2% on receipt against the CoA value of 99.8%. Customer requests joint OOS investigation.",
        sample_available=True,
        adverse_event=False,
        regulatory_reportable=True,
        severity="Major",
        status="Pending CAPA",
    ),
    dict(
        complaint_no="CMP-2026-0004",
        source_type="email",
        received_date=TODAY - timedelta(days=9),
        customer_name="Cascade Medical Supply",
        customer_site="Portland OR",
        country="United States",
        contact_email="qa@cascademedical.example",
        product_name="Insulin Glargine Injection 100 IU/mL",
        generic_name="Insulin Glargine",
        product_type="FDF",
        dosage_form="Injection",
        strength="100 IU/mL",
        batch_no="INS-1207",
        mfg_date=TODAY - timedelta(days=95),
        expiry_date=TODAY + timedelta(days=280),
        quantity_supplied="4,800 vials",
        quantity_affected="1 pallet (600 vials)",
        complaint_category="Cold Chain Excursion",
        complaint_description="Data logger recorded 11 hours at 14 to 19 degrees C during transit. Pallet quarantined on arrival.",
        sample_available=True,
        adverse_event=False,
        regulatory_reportable=True,
        severity="Major",
        status="Under Investigation",
    ),
    dict(
        complaint_no="CMP-2026-0005",
        source_type="manual",
        received_date=TODAY - timedelta(days=4),
        customer_name="Meridian Pharma Distribution",
        customer_site="Rotterdam DC",
        country="Netherlands",
        contact_email="qa@meridianpharma.example",
        product_name="Atorvastatin Tablets 20 mg",
        generic_name="Atorvastatin Calcium",
        product_type="FDF",
        dosage_form="Tablets",
        strength="20 mg",
        batch_no="ATV-5540",
        expiry_date=TODAY + timedelta(days=600),
        quantity_supplied="90,000 tablets",
        quantity_affected="3 cartons",
        complaint_category="Packaging / Labelling",
        complaint_description="Carton overprint shows an expiry date that does not match the blister foil on three cartons.",
        sample_available=False,
        adverse_event=False,
        regulatory_reportable=True,
        severity="Major",
        status="Under Investigation",
    ),
]


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = {c.complaint_no for c in db.query(Complaint).all()}
        added = 0
        for row in SEED:
            if row["complaint_no"] in existing:
                continue
            complaint = Complaint(**row)
            db.add(complaint)
            db.flush()
            audit.record(
                db, entity="complaint", entity_id=complaint.id, action="create",
                actor="system.seed", reason="Historical record loaded for demonstration",
                after=audit.snapshot(complaint),
            )
            added += 1
        db.commit()
        print(f"Seeded {added} complaint(s); {len(existing)} already present.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
