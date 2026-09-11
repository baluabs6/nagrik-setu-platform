"""
Optional AI-triage agent for newly submitted issues.

Feature-flagged (ENABLE_AI_TRIAGE, default False) and entirely best-effort:
any failure here (missing API key, network error, malformed response) is
logged and swallowed, exactly like the existing `_log_to_dynamodb` pattern
in apps/issues/views.py — a citizen's report must never be blocked or lost
because an AI call failed.

What it does, given an Issue's `category` (as picked by the citizen) and
`description` (free text):
  - suggests the category the text actually seems to describe
  - estimates urgency (low/medium/high) from cues in the text
  - returns a 0-1 confidence score

This is intentionally a thin, swappable wrapper: swap `_call_model` for a
different provider without touching the calling code in views.py.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TriageResult:
    suggested_category: str
    urgency: str
    confidence: float


_ALLOWED_URGENCY = {"low", "medium", "high"}


def triage_issue(category_choices: list[str], category: str, description: str) -> Optional[TriageResult]:
    """Returns a TriageResult, or None if triage is disabled/unavailable.

    Never raises — callers can invoke this fire-and-forget.
    """
    from django.conf import settings

    if not getattr(settings, "ENABLE_AI_TRIAGE", False):
        return None

    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    if not api_key:
        logger.info("AI triage skipped: ENABLE_AI_TRIAGE is on but no ANTHROPIC_API_KEY is configured.")
        return None

    try:
        raw = _call_model(api_key, category_choices, category, description)
        data = json.loads(raw)
        suggested = data.get("suggested_category", category)
        urgency = data.get("urgency", "medium")
        confidence = float(data.get("confidence", 0.0))

        if suggested not in category_choices:
            suggested = category
        if urgency not in _ALLOWED_URGENCY:
            urgency = "medium"
        confidence = max(0.0, min(1.0, confidence))

        return TriageResult(suggested_category=suggested, urgency=urgency, confidence=confidence)
    except Exception:  # noqa: BLE001 - triage is a nice-to-have, never fatal
        logger.exception("AI triage call failed; continuing without it.")
        return None


def _call_model(api_key: str, category_choices: list[str], category: str, description: str) -> str:
    """Calls the Anthropic Messages API and returns the raw JSON string the
    model produced. Kept as a separate function so tests can monkeypatch it
    without needing real network access or an API key."""
    import urllib.request

    prompt = (
        "You triage civic-issue reports for a municipal dashboard. "
        f"Allowed categories: {', '.join(category_choices)}.\n"
        f"Citizen-picked category: {category}\n"
        f"Description: {description}\n\n"
        "Respond with ONLY a JSON object, no prose, no markdown fences: "
        '{"suggested_category": "<one of the allowed categories>", '
        '"urgency": "low|medium|high", "confidence": <0-1 float>}'
    )

    body = json.dumps(
        {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        payload = json.loads(response.read())

    text_blocks = [block["text"] for block in payload.get("content", []) if block.get("type") == "text"]
    return "".join(text_blocks) or "{}"
