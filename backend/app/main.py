"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.graph import mermaid
from app.api import complaints, copilot, intake
from app.config import get_settings
from app.database import Base, engine
from app.models import (  # noqa: F401 - importing registers the tables
    CATEGORIES, COMPLAINT_SOURCES, NPM_OPTIONS, SEVERITIES, SITE_BLOCKS, STATUSES,
)
from app.services.llm import llm_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI-powered customer complaint intake for pharmaceutical manufacturing (AIVOA Round 1).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake.router, prefix=settings.api_prefix)
app.include_router(complaints.router, prefix=settings.api_prefix)
app.include_router(copilot.router, prefix=settings.api_prefix)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    logging.getLogger(__name__).info(
        "AI engine: %s", "groq" if llm_router.enabled else "rule fallback (no GROQ_API_KEY)"
    )


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "ai_engine": "groq" if llm_router.enabled else "fallback",
        "fast_model": settings.fast_model,
        "reasoning_model": settings.reasoning_model,
    }


@app.get(f"{settings.api_prefix}/meta/graph")
def graph_definition() -> dict:
    """Mermaid source for the LangGraph pipeline -- rendered in the UI."""
    return {"mermaid": mermaid()}


@app.get(f"{settings.api_prefix}/meta/reference")
def reference_data() -> dict:
    return {
        "severities": list(SEVERITIES),
        "statuses": list(STATUSES),
        "categories": list(CATEGORIES),
        "complaint_sources": list(COMPLAINT_SOURCES),
        "site_blocks": list(SITE_BLOCKS),
        "npm_options": list(NPM_OPTIONS),
    }
