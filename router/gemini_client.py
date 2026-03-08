from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx


GEMINI_API_ENDPOINT = os.getenv("GEMINI_API_ENDPOINT", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


class GeminiNotConfigured(RuntimeError):
    pass


def _ensure_configured() -> None:
    if not GEMINI_API_ENDPOINT or not GEMINI_API_KEY:
        raise GeminiNotConfigured("Gemini fallback is not configured")


async def generate_with_gemini(prompt: str, extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Minimal Gemini client.

    Phase 2 will adapt the exact request/response shape to match the
    deployed Gemini endpoint, but this keeps all Gemini-specific concerns
    isolated behind a single function.
    """
    _ensure_configured()

    # Google Generative Language API: generateContent
    # https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
    payload: Dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ]
    }

    if extra_params:
        payload.update(extra_params)

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(GEMINI_API_ENDPOINT, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Normalize Gemini response into the router's JSON shape.
    text_chunks: list[str] = []
    for candidate in data.get("candidates", [])[:1]:
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            if "text" in part:
                text_chunks.append(part["text"])

    combined_text = "\n".join(text_chunks).strip()

    return {
        "model": GEMINI_MODEL,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "response": combined_text,
    }

