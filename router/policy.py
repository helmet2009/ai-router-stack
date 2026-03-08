from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RouteDecision(str, Enum):
    """High-level routing decision for a request."""

    USE_CACHE = "cache"
    USE_LOCAL_MODEL = "local"
    USE_GEMINI_FALLBACK = "gemini_fallback"


@dataclass
class PolicyContext:
    """Inputs to the routing policy."""

    cache_hit_l1: bool
    cache_hit_l2: bool
    semantic_score: Optional[float] = None
    prompt_length: int = 0
    model: Optional[str] = None
    retry_with_gemini: bool = False
    intent: Optional[str] = None


def decide_route(context: PolicyContext) -> RouteDecision:
    """
    Simple routing policy:

    - If any cache hit occurred (L1 or L2), use cache.
    - If the requested model looks like a Gemini model, route to Gemini.
    - If the caller explicitly requests a retry with Gemini, route to Gemini.
    - Otherwise, use the local model (Ollama).
    """
    if context.cache_hit_l1 or context.cache_hit_l2:
        return RouteDecision.USE_CACHE

    if context.model and context.model.startswith("gemini"):
        return RouteDecision.USE_GEMINI_FALLBACK

    if context.retry_with_gemini:
        return RouteDecision.USE_GEMINI_FALLBACK

    return RouteDecision.USE_LOCAL_MODEL

