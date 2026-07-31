# Demo video scripts

The brief asks for two videos, 5–10 minutes total. Script them separately, record separately.
Set `GROQ_API_KEY` in `backend/.env` before recording so the traces show the real models,
and run `python -m app.seed` first so duplicate detection has history to hit.

---

## Video 1 — Working demonstration (~4 min)

**0:00 – 0:25 · Frame it**
"This is a customer complaint intake console for a pharmaceutical manufacturer handling both
API and finished dosage products. The job it does: turn an unstructured complaint into a
validated QMS record, with AI assistance the reviewer stays in control of."

Show the empty state — form on the left with *Awaiting AI extraction…* placeholders, the
copilot on the right, badge reading **Pending Triage**.

**0:25 – 1:20 · Free text intake**
Paste: *"Apollo Pharmacy reported discolored capsules in Amoxicillin Capsules 500 mg. Batch
number AMX240602. Manufacturing date March 2026. Expiry date February 2028. Please log this
complaint"*

Point at: fields populating with **AI** tags and per-field confidence; the badge moving to
**Ready to Commit**; and section 5, the AI copilot risk assessment — severity Major, next
action, and the rationale citing the specific facts that drove it.

**1:20 – 2:10 · Conversational correction — the important one**
Type: *"ah sorry the batch number is BMX240602 and affected quantity is 48 capcules"*

"The copilot confirms exactly what it changed, the two fields pulse on the form, and they
flip from AI provenance to human — because I stated them, so the model's confidence in them
is no longer meaningful. Note I did not re-send the complaint. LangGraph's checkpointer is
holding the form state against this thread."

**2:10 – 3:00 · PDF intake, API-side complaint**
Drop `sample_data/complaint_01_particulate.pdf` into the copilot. Show extraction, the
Critical classification, and the regulatory flags.

**3:00 – 3:40 · The bonus features**
Open *Additional AI analysis*: completeness with the follow-up questions to ask the
complainant, duplicate detection, root cause with verification steps, CAPA split three ways,
and the agent trace with real per-node latency and model.

**3:40 – 4:00 · Commit and audit**
Commit the complaint, switch to the register, open the record and show the audit trail.
Also show `sample_data/complaint_04_not_a_complaint.eml` being rejected at triage.

---

## Video 2 — Code walkthrough (~5 min)

Follow one request end to end. Do not tour the repo; follow the data.

**0:00 – 0:40 · Frontend origin**
`CopilotChat.jsx` — one input does both jobs, and the presence of a thread decides which.
`intakeSlice.js` — `analyzeText` vs `correctForm` thunks, and `provenance` being rebuilt on
every result.

**0:40 – 1:15 · The API boundary**
`api/intake.py` — `/intake/analyze`, `/intake/upload`, `/intake/correct`. Nothing is
persisted at intake: the reviewer reviews before anything becomes a record.

**1:15 – 2:45 · The graph — spend your time here**
`agents/graph.py`. Walk the diagram. Explain, in this order:
1. the **conditional entry point** and why a correction skips triage and extraction;
2. why both paths converge on `completeness` — a corrected batch number changes duplicates
   and risk, so the analysis re-runs;
3. the **fan-out** and therefore why `trace`, `errors` and `models_used` need `operator.add`
   reducers in `state.py`, and why nothing else does;
4. the `MemorySaver` checkpointer and what `thread_id` buys.

**2:45 – 3:40 · Inside a node**
`nodes.py` → `extract_node`. The Pydantic validation through `_clean_draft` so a bad date
never reaches the form; the merge order (LLM wins, regex fills gaps); the `LLMUnavailable`
catch and what it degrades to. Then `risk_node` and the **safety ratchet** — rules can
escalate, never de-escalate.

**3:40 – 4:20 · What is deliberately not AI**
`services/rules.py`. Mandatory fields, reportability, the negation handling. Tell the story:
"no adverse reaction has been reported" is in almost every complaint letter, a naive keyword
match read it as an adverse event and escalated everything to Critical, and my test then
caught that the negation window ran past a full stop. `services/llm.py` — the tier argument
and why two models.

**4:20 – 5:00 · Back to the screen**
`ComplaintForm.jsx` and `Field.jsx` — provenance tags, and `RiskAssessmentSection.jsx` as
section 5 of the record rather than a sidebar. Close on `pytest -q`: 18 tests, and name the
two real bugs they caught.

---

## Have an answer ready for

- Why a conditional entry point rather than two graphs? *(Shared downstream analysis, one
  state schema, one checkpointer — and a correction genuinely must re-run risk.)*
- What breaks at 10,000 complaints? *(`find_duplicates` scans 300 recent rows; needs an
  index on batch_no and a blocking key.)*
- Why is completeness not an LLM call? *(Procedural, inspectable, must be deterministic.)*
- How would you add a human approval gate? *(`interrupt_before` on a node, plus the
  existing audit trail for the sign-off.)*
