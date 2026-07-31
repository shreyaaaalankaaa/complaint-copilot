# Customer complaints in a pharmaceutical QMS

Background research for the assignment. The brief asked for curiosity rather than domain
expertise, so this records what I read and what of it I actually built in.

## Where the complaint module sits

A pharmaceutical Quality Management System is the set of processes that keep a licensed
manufacturer in a validated state. Its elements — deviations, change control, CAPA, OOS
investigation, product quality review, and complaint handling — are interlocked: a complaint
that turns out to be real usually opens a deviation, which opens an investigation, which
closes through CAPA, which is then reviewed in the annual Product Quality Review.

The customer complaint module is the system's **outward-facing sensor**. Everything else
detects problems inside the plant; complaints are how the plant hears about problems that
have already reached the market. That is why complaint handling is explicitly required by
EU GMP Chapter 8 and by 21 CFR 211.198, and why the record has to be reviewable years later.

## API vs FDF changes the shape of a complaint

The assignment specifies manufacturers of both, and they are genuinely different intakes.

| | API (bulk active) | FDF (finished dosage form) |
| --- | --- | --- |
| Complainant | another manufacturer's QA/QC function | distributor, pharmacy, hospital, sometimes a patient |
| Typical defect | assay or impurity out of trend, colour, particle count, moisture, packaging drum integrity | discolouration, chipped or capped tablets, foreign particles, labelling error, cold chain excursion |
| Quantity unit | kg, drums, containers | tablets, capsules, vials, packs, cartons |
| Evidence | CoA, joint OOS investigation, retained sample | photographs, complaint sample return, pharmacy record |
| Escalation | supply interruption, customer's own batch rejection | Field Alert Report, recall evaluation, adverse event reporting |

This is why the form labels the strength field **Product Strength/Grade** when the product
type is API (grades like IP/BP matter more than a strength), and why `quantity_affected` is
a free-text string rather than a number: "50 kg (2 HDPE Drum)" and "48 capsules" are both
correct answers and normalising them would lose information the investigator needs.

## What a complaint record must capture

Working from the intake fields a QA reviewer cannot proceed without:

- **Traceability** — product, batch/lot, manufacturing and expiry date. Without a batch
  number nothing can be traced, no retention sample can be pulled, and no scope can be
  drawn around other affected batches. This is why `batch_no` is mandatory in the code.
- **Complainant identity and channel** — who reported it and how it arrived, because the
  response has to go back to them within the period set in the Quality Agreement.
- **The observation, stated factually** — what was seen, how much, when, by whom. The form
  calls this the *Structured Defect Summary* and the agent synthesises it rather than
  pasting the customer's email, because a QMS record is not correspondence.
- **Sample availability** — an investigation without the complaint sample is largely
  theoretical, so this drives what the investigation can actually conclude.
- **Adverse event flag** — this is the branch that changes everything downstream.

## Classification, and why it drives the workflow

Complaints are triaged by severity, and the severity determines the timeline and who gets
told. The scheme implemented here:

- **Critical** — potential patient harm, adverse event, product mix-up, wrong strength,
  contamination or sterility concern, counterfeit suspicion. Candidate for a Field Alert
  Report and a recall evaluation. Target closure 30 days.
- **Major** — confirmed or suspected out-of-specification attribute, labelling defect with
  mis-dosing potential, cold chain excursion affecting stability. Target closure 60 days.
- **Minor** — cosmetic or isolated defect with no impact on identity, strength, quality,
  purity or safety. Trended rather than investigated individually. Target closure 90 days.

The rule engine implements this as a weighted score with a stated reason per signal, so the
classification is explainable rather than asserted. Anything a language model returns can be
escalated by the rules but never de-escalated — a model having a bad day must not be able to
turn a suspected adverse event into a Minor.

## Root cause and CAPA

Investigations are structured with Ishikawa categories (Man, Machine, Material, Method,
Measurement, Environment), so the agent produces hypotheses in those terms — and, more
importantly, pairs each with the **specific record a site would check to confirm or rule it
out**: the tooling inspection log, the line clearance record, the data logger profile, the
impurity trend for the input lot. A hypothesis without a verification step is not useful to
an investigator.

CAPA is deliberately split three ways because auditors read it that way, and conflating them
is one of the most common audit findings:

- **Correction** — contains the problem now (stock hold, sample retrieval, quarantine).
- **Corrective action** — removes the cause of the occurrence that happened.
- **Preventive action** — stops the same cause producing a recurrence elsewhere.
- **Effectiveness check** — how the site will later prove the CAPA worked.

## Data integrity

Complaint records are GxP records, so ALCOA+ applies: attributable, legible, contemporaneous,
original, accurate, plus complete, consistent, enduring and available. Two consequences are
built in:

1. **The audit trail is append-only.** Every write records actor, timestamp, reason, and the
   before/after image. `AuditLog` rows are never updated or deleted.
2. **AI output is never silently merged into the record.** Every agent-produced value lands
   in `AIAssessment`, and every form field carries a provenance tag showing whether a human
   or the model put it there. A reviewer owns the record; the agent advises it.

## Sources consulted

EU GMP Part I Chapter 8 (Complaints, Quality Defects and Product Recalls); 21 CFR 211.198
(Complaint files) and 21 CFR Part 11 (Electronic records and signatures); ICH Q9 (Quality
Risk Management) and Q10 (Pharmaceutical Quality System); WHO TRS 986 Annex 2; FDA guidance
on Field Alert Reports. Read for structure and vocabulary, not quoted — no text from any of
these is reproduced in the code or this document.
