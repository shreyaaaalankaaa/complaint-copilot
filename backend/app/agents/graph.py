"""The complaint intake graph.

                        ┌──────────┐
                        │  triage  │
                        └────┬─────┘
              is_complaint?  │
             ┌───────────────┴───────────────┐
             ▼                               ▼
        ┌─────────┐                     ┌─────────┐
        │ reject  │──► END              │ extract │
        └─────────┘                     └────┬────┘
                                             ▼
                                     ┌──────────────┐
                                     │ completeness │
                                     └──────┬───────┘
                                            ▼
                                     ┌──────────────┐
                                     │  duplicates  │
                                     └──────┬───────┘
                                            ▼
                                       ┌────────┐
                                       │  risk  │
                                       └───┬────┘
                        ┌──────────────────┼──────────────────┐
                        ▼                  ▼                  ▼
                 ┌────────────┐      ┌──────────┐      ┌───────────┐
                 │ root_cause │      │   capa   │      │  summary  │
                 └──────┬─────┘      └────┬─────┘      └─────┬─────┘
                        └──────────────────┼──────────────────┘
                                           ▼
                                     ┌───────────┐
                                     │ assemble  │──► END
                                     └───────────┘

Node names are deliberately verbs and deliberately differ from the state keys they
write (`check_completeness` writes `completeness`). LangGraph rejects a node whose
name collides with a state key, and verb names read better in the trace anyway.

Why this shape:

* `triage` gates the graph with a conditional edge so an enquiry or a purchase
  order never becomes a complaint record.
* `completeness` and `duplicates` run before `risk` because both feed it: a
  recurrence across batches raises risk, and a missing batch number changes what
  the assessment can honestly claim.
* root cause / CAPA / summary have no dependency on each other, so they fan out
  and run in a single super-step. On Groq this is roughly a third of the wall
  clock of running them in series.
* A `MemorySaver` checkpointer keeps the state under a thread_id, so the Copilot
  panel can ask follow-up questions and re-run analysis without re-uploading the
  document.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    apply_patch_node, assemble_node, capa_node, completeness_node, duplicate_node,
    extract_node, parse_correction_node, reject_node, risk_node, root_cause_node,
    route_after_triage, route_entry, summary_node, triage_node,
)
from app.agents.state import GraphState

FAN_OUT = ("recommend_root_cause", "draft_capa", "write_summary")


def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("triage", triage_node)
    builder.add_node("reject", reject_node)
    builder.add_node("extract", extract_node)
    builder.add_node("check_completeness", completeness_node)
    builder.add_node("scan_duplicates", duplicate_node)
    builder.add_node("classify_risk", risk_node)
    builder.add_node("recommend_root_cause", root_cause_node)
    builder.add_node("draft_capa", capa_node)
    builder.add_node("write_summary", summary_node)
    builder.add_node("assemble", assemble_node)
    builder.add_node("parse_correction", parse_correction_node)
    builder.add_node("apply_patch", apply_patch_node)

    # Conditional entry: a first turn reads the document, a follow-up patches the
    # form the checkpointer is already holding for this thread.
    builder.add_conditional_edges(
        START, route_entry, {"intake": "triage", "correction": "parse_correction"}
    )
    builder.add_edge("parse_correction", "apply_patch")
    builder.add_edge("apply_patch", "check_completeness")
    builder.add_conditional_edges(
        "triage", route_after_triage, {"extract": "extract", "reject": "reject"}
    )
    builder.add_edge("reject", END)
    builder.add_edge("extract", "check_completeness")
    builder.add_edge("check_completeness", "scan_duplicates")
    builder.add_edge("scan_duplicates", "classify_risk")

    for node in FAN_OUT:
        builder.add_edge("classify_risk", node)
        builder.add_edge(node, "assemble")

    builder.add_edge("assemble", END)
    return builder.compile(checkpointer=MemorySaver())


complaint_graph = build_graph()


def mermaid() -> str:
    """Rendered by GET /api/v1/meta/graph and by the UI's 'View agent graph'."""
    return complaint_graph.get_graph().draw_mermaid()
