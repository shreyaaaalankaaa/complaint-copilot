"""Generate the demo intake artefacts in sample_data/.

Four files, each exercising a different path through the graph:

  complaint_01_particulate.pdf     PDF -> pypdf -> full extraction, Critical/Major risk
  complaint_02_label_mixup.eml     email -> header + body parse, labelling defect
  complaint_03_repeat_batch.eml    duplicate of seeded CMP-2026-0002 (batch AMX-8817)
  complaint_04_not_a_complaint.eml purchase order -> triage rejects it
  complaint_05_incomplete.txt      missing batch/date -> completeness checker fires

Run:  python scripts/make_sample_data.py
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "sample_data"
OUT.mkdir(exist_ok=True)

PDF_BODY = [
    ("CUSTOMER COMPLAINT NOTIFICATION", 16, True),
    ("Northbridge Healthcare Ltd  |  Quality Assurance Department", 9, False),
    ("", 6, False),
    ("Complaint reference: NBH/QA/2026/0442", 10, False),
    ("Date raised: 12/07/2026", 10, False),
    ("Raised by: Dr. Helena Vasquez, Head of Quality Assurance", 10, False),
    ("Contact: quality@northbridge.example  |  +44 161 496 0117", 10, False),
    ("", 8, False),
    ("PRODUCT DETAILS", 12, True),
    ("Product: Cefixime Dispersible Tablets IP 100 mg", 10, False),
    ("Generic name: Cefixime Trihydrate", 10, False),
    ("Batch No: CFX-4472", 10, False),
    ("Mfg date: 02/2026        Exp date: 01/2028", 10, False),
    ("Quantity supplied: 84,000 tablets (2,800 packs)", 10, False),
    ("Quantity affected: 27 tablets across 9 blister strips", 10, False),
    ("Country of distribution: United Kingdom", 10, False),
    ("", 8, False),
    ("COMPLAINT DESCRIPTION", 12, True),
    ("During routine goods-in inspection at our Manchester depot on 11 July 2026,", 10, False),
    ("our warehouse QA technician identified visible black particulate matter", 10, False),
    ("embedded in the surface of dispersible tablets in nine separate blister", 10, False),
    ("strips drawn from three different cartons of batch CFX-4472. The particles", 10, False),
    ("measure approximately 0.5 to 1.5 mm and are firmly embedded rather than", 10, False),
    ("surface deposits. Two of the affected strips also show slight brown", 10, False),
    ("discolouration at the tablet edge.", 10, False),
    ("", 6, False),
    ("This product is dispensed to a paediatric population. One community", 10, False),
    ("pharmacy has reported that a parent returned an opened pack after noticing", 10, False),
    ("dark specks; no adverse reaction has been reported by the patient and no", 10, False),
    ("medical attention was sought. The remaining stock of batch CFX-4472 at our", 10, False),
    ("depot (2,640 packs) has been placed on quarantine hold pending your", 10, False),
    ("response. Complaint samples have been retained and are available for", 10, False),
    ("return under controlled conditions.", 10, False),
    ("", 6, False),
    ("We note that batch CFX-4471 supplied in the same shipment has not shown", 10, False),
    ("the defect on inspection of 40 packs.", 10, False),
    ("", 8, False),
    ("REQUESTED ACTION", 12, True),
    ("Acknowledgement within 2 working days and a written investigation", 10, False),
    ("response within 30 calendar days per the Quality Agreement, Annexure 4.", 10, False),
]


def build_pdf() -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    path = OUT / "complaint_01_particulate.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 60
    for text, size, bold in PDF_BODY:
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(56, y, text)
        y -= size + 5
        if y < 60:
            c.showPage()
            y = height - 60
    c.save()
    print("wrote", path.name)


EMAILS = {
    "complaint_02_label_mixup.eml": """From: Priya Raghunathan <priya.raghunathan@vitalisdistribution.example>
To: complaints@aivoa-pharma.example
Date: Mon, 20 Jul 2026 09:14:22 +0530
Subject: URGENT - Carton labelling discrepancy, Losartan Potassium 50 mg, batch LST-7719

Dear Quality Assurance team,

We are writing to raise a formal complaint regarding a labelling discrepancy found in
our Chennai warehouse on 19 July 2026.

Product: Losartan Potassium Tablets IP 50 mg
Batch number: LST-7719
Manufacturing date: March 2026
Expiry date: February 2028
Quantity supplied: 150,000 tablets
Quantity affected: 4 shipper cartons (approximately 2,400 tablets)

On four shipper cartons the outer label states "Losartan Potassium Tablets IP 25 mg"
while the blister foil and the inner carton both correctly state 50 mg. The batch
number and expiry printed on all three levels are identical and match the CoA.

None of the affected cartons have left our warehouse and no product has been supplied
to pharmacies. We have segregated the four cartons in the quarantine cage. Photographs
of all three labelling levels are attached to our internal record and can be shared.

Given the mis-dosing potential if such a carton reached a dispensing pharmacy, we
consider this a serious labelling defect and request an urgent investigation, including
confirmation of whether other cartons of this batch or of batch LST-7718 are affected.

Complaint samples are retained and available for return.

Regards,
Priya Raghunathan
Head - Quality Assurance
Vitalis Distribution Pvt Ltd, Chennai
+91 44 4285 6600
""",
    "complaint_03_repeat_batch.eml": """From: Northbridge QA <quality@northbridge.example>
To: complaints@aivoa-pharma.example
Date: Thu, 23 Jul 2026 16:02:10 +0100
Subject: Further affected cartons - Amoxicillin 250 mg batch AMX-8817

Dear Quality team,

Following our earlier complaint on batch AMX-8817 (Amoxicillin Trihydrate Capsules
250 mg), we have now found black particulate matter inside capsule shells in a further
three cartons held at our Manchester site. This brings the total affected quantity to
approximately 95 capsules.

Batch number: AMX-8817
Expiry date: December 2027
Quantity affected: approximately 95 capsules
Sample availability: yes, retained under quarantine

No adverse reactions have been reported. Stock remains on hold and has not been
dispensed. Please confirm whether the scope of your ongoing investigation now covers
the additional cartons, and whether adjacent batches manufactured on the same
encapsulation line are being reviewed.

Regards,
Northbridge Healthcare Ltd - Quality Assurance
""",
    "complaint_04_not_a_complaint.eml": """From: Procurement <purchasing@harborlinepharma.example>
To: sales@aivoa-pharma.example
Date: Tue, 21 Jul 2026 11:40:05 -0500
Subject: Purchase order HP-2026-8841 and Q4 pricing

Hello,

Please find our purchase order HP-2026-8841 for the following:

  - Metformin Hydrochloride Tablets 500 mg, 200,000 tablets
  - Atorvastatin Tablets 20 mg, 90,000 tablets

Requested delivery: 15 September 2026 to our Dallas DC.

Could you also confirm indicative pricing for Q4 and let us know whether the lead time
on Atorvastatin has improved since last quarter? Happy to set up a call next week.

Best regards,
Marcus Hale
Procurement Manager, Harborline Pharma
""",
}

INCOMPLETE = """Phone complaint logged by customer service, 24 July 2026, 14:20.

Caller: pharmacist from a retail chain, would not give the pharmacy name or a
callback email. Says a bottle of our cough syrup "smells wrong, kind of sour"
and looks slightly cloudier than usual. Says it is the 100 ml bottle. Could not
read out the batch number over the phone and said he would check later. No
patient has taken it as far as he knows. Asked what he should do with the stock.

Told him we would call back once we have the batch details.
"""


def main() -> None:
    build_pdf()
    for name, body in EMAILS.items():
        (OUT / name).write_text(body, encoding="utf-8")
        print("wrote", name)
    (OUT / "complaint_05_incomplete.txt").write_text(INCOMPLETE, encoding="utf-8")
    print("wrote complaint_05_incomplete.txt")


if __name__ == "__main__":
    main()
