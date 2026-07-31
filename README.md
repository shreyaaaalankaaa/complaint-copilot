# AI-Powered Customer Complaint Management System

**AIVOA — Round 1, AI Product Engineer (Intern)**

A complaint intake console for a pharmaceutical manufacturer handling both API and FDF
products. A QA reviewer pastes a customer email or drops a complaint PDF into the copilot;
a LangGraph agent reads it, fills the *Log Customer Complaint* form, and produces a risk
assessment. The reviewer can then correct any field by talking to the copilot in plain
language — *"sorry, the batch number is BMX240602 and affected quantity is 48 capsules"* —
and the form updates in place.

---

## Run it

The application runs **with or without a Groq API key**. Without one, every node falls back
to a deterministic rule engine, so you can clone and see the full product working before
you have credentials. Set a key to exercise the real LangGraph + Groq path.

```bash
# 1. database
docker compose up -d db

# 2. backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: add GROQ_API_KEY
python -m app.seed              # 5 historical complaints, needed for duplicate detection
uvicorn app.main:app --reload --port 8000

# 3. frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open <http://localhost:5173>. API docs at <http://localhost:8000/docs>.

```bash
cd backend && pytest -q        # 18 tests
python scripts/make_sample_data.py   # regenerate the demo PDFs and emails
```

`sample_data/` contains five artefacts, each exercising a different path through the graph:
a complaint PDF, a labelling-defect email, a repeat complaint on an already-logged batch,
a purchase order that must be **rejected** at triage, and an incomplete phone note.

---

## Requirements → implementation

| Requirement | Where |
| --- | --- |
| React UI with Redux | `frontend/src/` — Redux Toolkit, 3 slices (`intakeSlice`, `complaintsSlice`, `copilotSlice`) |
| Python + FastAPI | `backend/app/main.py`, routers in `backend/app/api/` |
| LangGraph agent | `backend/app/agents/graph.py` — 11 nodes, conditional entry, conditional routing, fan-out |
| Groq `gemma2-9b-it` | extraction, triage, risk, summary, corrections — `backend/app/services/llm.py` |
| Groq `llama-3.3-70b-versatile` | root cause, CAPA, copilot Q&A — same router, `tier="reasoning"` |
| Postgres | SQLAlchemy 2.0 models in `backend/app/models.py`, `docker-compose.yml` |
| Google Inter | `frontend/index.html`, `--mono` for identifiers only |
| Workflow from the demo | prompt or PDF/email → form populated → AI copilot risk assessment → conversational correction → commit |
| Complaint Completeness Checker | `rules.completeness()`, node `completeness` |
| Root Cause Recommendation | node `root_cause`, Ishikawa 6M with a verification step per hypothesis |
| Duplicate Complaint Detection | `services/duplicates.py`, node `duplicates` |
| CAPA Recommendation | node `capa` — correction / corrective / preventive / effectiveness split |
| Complaint Summary | node `summary` |
| AI Risk Classification | node `risk` + `services/rules.score_risk()` |
| *(extra)* Non-complaint triage | node `triage` — a purchase order never becomes a QMS record |
| *(extra)* GxP audit trail | `models.AuditLog`, append-only, before/after image on every write |
| *(extra)* Field-level provenance | every field tagged AI or human with a confidence score |

---

## The agent

```
START ──router──> triage ──(is this a complaint?)──> reject ──> END
   │                 │
   │                 └──> extract ──┐
   │                                │
   └──> parse_correction ──> apply_patch ──┤
                                           ▼
                              check_completeness ──> scan_duplicates ──> classify_risk
                                                                              │
                                  ┌───────────────────────────────────────────┼───────────────┐
                                  ▼                                           ▼               ▼
                        recommend_root_cause                             draft_capa    write_summary
                                  └───────────────────────────────────────────┼───────────────┘
                                                                      ▼
                                                                  assemble ──> END
```

Four things in this shape are deliberate:

**The conditional entry point** is what makes the conversation work. A first turn reads a
document; every turn after that patches the form the checkpointer is already holding for
that `thread_id`. A correction sends no document — only the message.

**A correction re-runs the analysis.** Both paths converge on `completeness`, so changing a
batch number re-checks completeness, re-scans for duplicates and re-scores risk. Changing a
batch can turn an isolated defect into a recurring one, and the reviewer should see that
before committing, not after.

**The last three nodes fan out** — they have no dependency on each other, so they run in one
super-step. This is why `trace`, `errors` and `models_used` carry `operator.add` reducers in
`agents/state.py`: three nodes write the same keys in the same super-step and LangGraph has
to be told how to merge them. Every other key has exactly one writer.

Node names are verbs and deliberately differ from the state keys they write
(`check_completeness` writes `completeness`) — LangGraph rejects a node whose name collides
with a state key.

**`triage` gates the graph** so a purchase order or a pricing enquiry never becomes a
complaint record. Its fallback is deliberately permissive: wrongly rejecting a real
complaint is a regulatory failure, wrongly accepting an order costs a reviewer ten seconds.

---

## Four engineering decisions

**Model routing, not one model for everything.** `gemma2-9b-it` handles extraction, triage,
risk and corrections — high volume, schema-constrained, latency-sensitive.
`llama-3.3-70b-versatile` handles root cause and CAPA — low volume, needs real reasoning
over pharmaceutical context. `services/llm.py` exposes this as a `tier` argument so a node
declares what kind of thinking it needs rather than naming a model.

**Some decisions must not be an LLM.** Which fields are mandatory before an investigation
can open, and whether a complaint is potentially reportable, are procedural decisions. They
live in `services/rules.py` where a QA head can read them and a regulator can inspect them,
and they give the same answer today and next Tuesday. The model adds judgement on top; it
does not own the rule. There is also a **safety ratchet** in the `risk` node: the rule
engine may escalate the model's risk level, never lower it.

**Every node degrades independently.** If Groq is unavailable or returns malformed JSON,
that one node falls back and marks itself in the trace; the rest of the graph continues. A
reviewer would rather see a partly filled form than a 500.

**Provenance is a first-class concept.** Every field carries an indigo marker if the agent
extracted it, teal if a human typed or corrected it, plus the model's confidence. Under 21
CFR Part 11 a record has to be attributable, so this is a requirement wearing the costume of
a UI flourish. Fields changed by a chat correction flip to human and pulse once so the
change is visible without hunting.

---

## Honest notes

- **OCR is not implemented.** Production-grade document parsing was out of scope per the
  brief. PDFs and `.eml` are parsed properly (`pypdf`, `email`); images return a labelled
  placeholder rather than pretending to have read them.
- **The rule-engine fallback is not as good as the LLM path** on free prose. It is good
  enough to demonstrate every feature without credentials, which is its job.
- **`MemorySaver` is in-process.** Conversation state does not survive a backend restart.
  Production would use `PostgresSaver` against the same database — a one-line swap in
  `agents/graph.py`.
- **Authentication is stubbed.** `actor` defaults to `qa.reviewer` on audit entries. A real
  deployment needs SSO and electronic signatures before the audit trail means anything.

## With more time

Streaming the graph over SSE so nodes appear in the copilot as they complete rather than in
one response; `PostgresSaver` for durable threads; embedding-based duplicate detection as a
second signal alongside the explainable field match; and an effectiveness-check scheduler so
CAPA closure is tracked rather than only proposed.

---

## Layout

```
backend/
  app/
    agents/      graph.py  nodes.py  state.py  prompts.py  runner.py
    api/         intake.py  complaints.py  copilot.py
    services/    llm.py  rules.py  duplicates.py  extraction.py  audit.py  numbering.py
    models.py  schemas.py  database.py  config.py  seed.py
  tests/         test_rules.py  test_api.py
frontend/
  src/
    components/  ComplaintForm.jsx  CopilotChat.jsx  RiskAssessmentSection.jsx  Field.jsx
                 AdditionalAnalysis.jsx  AgentTrace.jsx  copilot/
    store/       intakeSlice.js  complaintsSlice.js  copilotSlice.js
    pages/       LogComplaint.jsx  ComplaintRegister.jsx
sample_data/     demo PDFs and emails
docs/            ARCHITECTURE.md  QMS_NOTES.md  DEMO_SCRIPT.md
```
