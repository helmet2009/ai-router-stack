"""
crew/memory.py — Lightweight Redis-backed result cache for crew runs.

Keys: crew:result:<sha256(topic)>  TTL: 3600s
"""
from __future__ import annotations

import hashlib
import json
import logging
import os

import redis

logger = logging.getLogger("crew.memory")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
RESULT_TTL = int(os.getenv("CREW_RESULT_TTL", "3600"))

# Use a synchronous Redis client inside the executor thread
_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL, decode_responses=True)
    return _client


def _topic_key(topic: str) -> str:
    digest = hashlib.sha256(topic.encode()).hexdigest()
    return f"crew:result:{digest}"


def save_crew_result(topic: str, result: dict) -> None:
    """Persist crew run result to Redis."""
    try:
        r = _get_client()
        r.set(_topic_key(topic), json.dumps(result), ex=RESULT_TTL)
        logger.info(f"Crew result cached for topic: {topic[:60]}")
    except Exception as e:
        logger.warning(f"Failed to save crew result to Redis: {e}")


def get_crew_result(topic: str) -> dict | None:
    """Retrieve cached crew result. Returns None on miss or error."""
    try:
        r = _get_client()
        raw = r.get(_topic_key(topic))
        if raw:
            logger.info(f"Crew result cache HIT for topic: {topic[:60]}")
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"Failed to get crew result from Redis: {e}")
    return None
