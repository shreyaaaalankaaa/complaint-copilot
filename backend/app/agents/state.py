"""Shared state for the complaint intake graph.

`trace`, `errors` and `models_used` carry an `operator.add` reducer because the
root-cause / CAPA / summary branch runs as a fan-out: three nodes write to the
same state object in the same super-step, and LangGraph needs to be told how to
merge them. Every other key is written by exactly one node, so last-write-wins
is correct and no reducer is needed.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class GraphState(TypedDict, total=False):
    # input
    thread_id: str
    source_type: str
    raw_text: str
    mode: str            # "intake" on the first turn, "correction" on follow-ups
    user_message: str    # the reviewer's plain-language correction

    # correction turn output
    patch: dict[str, Any]
    applied_fields: list[str]
    patch_confirmation: str

    # triage
    is_valid_complaint: bool
    rejection_reason: str | None

    # extraction
    draft: dict[str, Any]
    field_confidence: dict[str, float]

    # analysis
    completeness: dict[str, Any]
    duplicates: list[dict[str, Any]]
    risk: dict[str, Any]
    root_causes: list[dict[str, Any]]
    capa: dict[str, Any]
    summary: str

    # observability (fan-out safe)
    trace: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]
    models_used: Annotated[list[str], operator.add]
