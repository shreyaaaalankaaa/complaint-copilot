"""Groq LLM access for the LangGraph nodes.

Model routing
-------------
`gemma2-9b-it`            -> extraction, classification, completeness. High volume,
                             schema-constrained, latency-sensitive. Cheap and fast.
`llama-3.3-70b-versatile` -> root cause, CAPA, copilot Q&A. Low volume, needs actual
                             reasoning over pharmaceutical context.

Every call goes through `complete_json`, which pins the model to a JSON contract,
repairs fenced output, retries once on a parse failure, and raises `LLMUnavailable`
so the calling node can degrade to the deterministic engine instead of failing the
whole request. A QA reviewer would rather see a partially filled form than a 500.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from app.config import get_settings

log = logging.getLogger(__name__)
_FENCE = re.compile(r"```(?:json)?(.*?)```", re.S)


class LLMUnavailable(RuntimeError):
    pass


@dataclass
class LLMResult:
    data: dict[str, Any]
    model: str
    latency_ms: int


class LLMRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._clients: dict[str, Any] = {}

    @property
    def enabled(self) -> bool:
        return self.settings.llm_enabled

    def model_for(self, tier: str) -> str:
        return self.settings.reasoning_model if tier == "reasoning" else self.settings.fast_model

    def _client(self, model: str):
        if model in self._clients:
            return self._clients[model]
        if not self.enabled:
            raise LLMUnavailable("GROQ_API_KEY is not set")
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:  # pragma: no cover
            raise LLMUnavailable(f"langchain-groq not installed: {exc}") from exc

        client = ChatGroq(
            model=model,
            api_key=self.settings.groq_api_key,
            temperature=self.settings.llm_temperature,
            timeout=self.settings.llm_timeout_s,
            max_retries=0,  # we own the retry loop
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        self._clients[model] = client
        return client

    @staticmethod
    def _parse(raw: str) -> dict[str, Any]:
        text = raw.strip()
        fenced = _FENCE.search(text)
        if fenced:
            text = fenced.group(1).strip()
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("expected a JSON object")
        return parsed

    def complete_json(
        self, *, system: str, user: str, tier: str = "fast", node: str = "?"
    ) -> LLMResult:
        model = self.model_for(tier)
        client = self._client(model)
        messages = [("system", system), ("human", user)]
        last_error: Exception | None = None

        for attempt in range(self.settings.llm_max_retries + 1):
            started = time.perf_counter()
            try:
                response = client.invoke(messages)
                data = self._parse(response.content)
                return LLMResult(
                    data=data, model=model, latency_ms=int((time.perf_counter() - started) * 1000)
                )
            except Exception as exc:  # noqa: BLE001 - any failure degrades the same way
                last_error = exc
                log.warning("[%s] %s attempt %s failed: %s", node, model, attempt + 1, exc)
                messages = [
                    ("system", system),
                    ("human", user),
                    ("human", "Your last reply was not valid JSON. Reply with the JSON object only."),
                ]
        raise LLMUnavailable(f"{model} failed after retries: {last_error}")


llm_router = LLMRouter()
