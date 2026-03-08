from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, Response
import httpx
import os
import asyncio
import hashlib
import time
import uuid
import logging
import ipaddress
import redis.asyncio as redis
import orjson
import json
from prometheus_client import (
    Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
)
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    SearchParams,
    Filter,
    FieldCondition,
    MatchValue,
    Range,
)
from policy import PolicyContext, RouteDecision, decide_route
from gemini_client import generate_with_gemini, GeminiNotConfigured
from tools import registry
import tools_impl  # Ensure tools are registered

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("router")

# ===============================
# CONFIG
# ===============================

OLLAMA_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://host.docker.internal:11434"
)

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://redis:6379"
)

QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://qdrant:6333"
)

EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

SEMANTIC_THRESHOLD = float(os.getenv("SEMANTIC_THRESHOLD", "0.92"))

# Maximum logical age (in seconds) for a semantic cache entry to be considered.
# Defaults to 24h; set to 0 or a negative value to disable age-based filtering.
SEMANTIC_MAX_AGE_SECONDS = float(os.getenv("SEMANTIC_MAX_AGE_SECONDS", "86400"))

CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

OLLAMA_MAX_CONCURRENT = int(os.getenv("OLLAMA_MAX_CONCURRENT", "4"))

OLLAMA_RETRIES = int(os.getenv("OLLAMA_RETRIES", "2"))

# Optional API key required for /api/generate. If empty, auth is disabled.
ROUTER_API_KEY = os.getenv("ROUTER_API_KEY", "").strip()

# Simple per-identifier rate limit (requests per minute). Set to 0 to disable.
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

# IPs or hosts that can bypass API key authentication (comma-separated).
AUTH_BYPASS_IPS = [
    ip.strip() for ip in os.getenv("AUTH_BYPASS_IPS", "127.0.0.1,localhost,open-webui").split(",")
    if ip.strip()
]

# CIDR ranges that can bypass API key authentication (comma-separated).
# Example: "127.0.0.1/32,172.18.0.0/16"
AUTH_BYPASS_CIDRS = []
for cidr in os.getenv("AUTH_BYPASS_CIDRS", "").split(","):
    cidr = cidr.strip()
    if not cidr:
        continue
    try:
        AUTH_BYPASS_CIDRS.append(ipaddress.ip_network(cidr, strict=False))
    except ValueError:
        logger.warning(f"Ignoring invalid AUTH_BYPASS_CIDRS entry: {cidr}")

# If true, retry with Gemini when the local model fails (non-stream only).
FALLBACK_TO_GEMINI_ON_ERROR = os.getenv("FALLBACK_TO_GEMINI_ON_ERROR", "0").strip().lower() in {
    "1",
    "true",
    "yes",
}

# Embedding vector dimension; must match the configured EMBED_MODEL.
# `nomic-embed-text` produces 768-dimensional vectors.
VECTOR_DIM = 768

COLLECTION_NAME = "semantic_cache"

# ===============================
# CLIENTS
# ===============================

r = redis.from_url(REDIS_URL, decode_responses=False)

ollama_semaphore = asyncio.Semaphore(OLLAMA_MAX_CONCURRENT)

qdrant = AsyncQdrantClient(url=QDRANT_URL)

# ===============================
# PROMETHEUS METRICS
# ===============================

REQUEST_TOTAL = Counter(
    "request_total",
    "Total requests to /api/generate",
    ["stream"]
)

CACHE_HIT = Counter(
    "cache_hit_total",
    "Total Redis L1 cache hits"
)

CACHE_MISS = Counter(
    "cache_miss_total",
    "Total Redis L1 cache misses"
)

SEMANTIC_HIT = Counter(
    "semantic_hit_total",
    "Total Qdrant L2 semantic cache hits"
)

SEMANTIC_MISS = Counter(
    "semantic_miss_total",
    "Total Qdrant L2 semantic cache misses"
)

POLICY_ROUTE_CACHE = Counter(
    "policy_route_cache_total",
    "Total requests served from cache (L1 or L2)"
)

POLICY_ROUTE_LOCAL = Counter(
    "policy_route_local_total",
    "Total requests served by local model (Ollama)"
)

POLICY_ROUTE_GEMINI = Counter(
    "policy_route_gemini_total",
    "Total requests served by Gemini fallback"
)

SEMANTIC_SCORE_USED = Histogram(
    "semantic_score_used",
    "Semantic similarity score for L2 cache hits",
    buckets=[0.7, 0.8, 0.85, 0.9, 0.95, 1.0],
)

MODEL_LATENCY = Histogram(
    "model_latency_seconds",
    "Ollama response latency",
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300]
)


# ===============================
# STARTUP — Ensure Qdrant Collection
# ===============================

@app.on_event("startup")
async def startup():
    try:
        collections = await qdrant.get_collections()
        names = [c.name for c in collections.collections]
        if COLLECTION_NAME not in names:
            await qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_DIM,
                    distance=Distance.COSINE
                ),
            )
            logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")
        else:
            logger.info(f"Qdrant collection exists: {COLLECTION_NAME}")
    except Exception as e:
        logger.warning(f"Qdrant startup failed (graceful fallback): {e}")


# ===============================
# L1 CACHE — Redis
# ===============================

def cache_key(body: dict) -> str:
    raw = orjson.dumps(body)
    return "llm:" + hashlib.sha256(raw).hexdigest()


async def get_cache(key: str):
    try:
        return await r.get(key)
    except Exception as e:
        logger.warning(f"Redis GET failed (graceful fallback): {e}")
        return None


async def set_cache(key: str, value: bytes):
    try:
        await r.set(key, value, ex=CACHE_TTL)
    except Exception as e:
        logger.warning(f"Redis SET failed (graceful fallback): {e}")


# ===============================
# L2 CACHE — Qdrant Semantic
# ===============================

async def embed_prompt(prompt: str) -> list[float] | None:
    """Get embedding vector from Ollama."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": EMBED_MODEL, "input": prompt}
            )
            data = resp.json()
            return data["embeddings"][0]
    except Exception as e:
        logger.warning(f"Embedding failed (graceful fallback): {e}")
        return None


async def search_semantic_cache(
    vector: list[float],
    model: str | None = None,
    max_age_seconds: float | None = None,
) -> dict | None:
    """Search Qdrant for similar prompt above threshold.

    Returns a dict with keys:
      - "response": cached response payload when a hit is found, else None
      - "score": top similarity score (float) when available
    """
    try:
        # Build an optional filter to scope by model and/or age.
        conditions: list[FieldCondition] = []

        if model:
            conditions.append(
                FieldCondition(
                    key="model",
                    match=MatchValue(value=model),
                )
            )

        if max_age_seconds is not None and max_age_seconds > 0:
            min_timestamp = time.time() - max_age_seconds
            conditions.append(
                FieldCondition(
                    key="timestamp",
                    range=Range(gte=min_timestamp),
                )
            )

        query_filter = Filter(must=conditions) if conditions else None

        results = await qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            query_filter=query_filter,
            limit=1,
        )
        if results.points:
            top = results.points[0]
            score = float(top.score) if top.score is not None else None

            if score is not None and score >= SEMANTIC_THRESHOLD:
                logger.info(
                    "Semantic cache hit",
                    extra={
                        "semantic_score": score,
                        "semantic_model": model,
                    },
                )
                SEMANTIC_HIT.inc()
                return {
                    "response": top.payload.get("response"),
                    "score": score,
                }

            logger.info(
                "Semantic cache below threshold",
                extra={
                    "semantic_score": score,
                    "semantic_model": model,
                },
            )
            SEMANTIC_MISS.inc()
            return {
                "response": None,
                "score": score,
            }

        logger.info(
            "Semantic cache miss",
            extra={
                "semantic_model": model,
            },
        )
        SEMANTIC_MISS.inc()
        return None
    except Exception as e:
        logger.warning(f"Qdrant search failed (graceful fallback): {e}")
        SEMANTIC_MISS.inc()
        return None


async def retrieve_memory(
    vector: list[float],
    model: str | None = None,
    limit: int = 3,
    score_threshold: float = 0.7,
) -> list[str]:
    """Search Qdrant for relevant past contexts to use as RAG."""
    try:
        results = await qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=limit,
            score_threshold=score_threshold,
        )
        snippets = []
        for point in results.points:
            prompt = point.payload.get("prompt", "")
            resp = point.payload.get("response", {})
            # If it's a dict (Ollama response), get the content
            content = ""
            if isinstance(resp, dict):
                content = resp.get("response") or resp.get("message", {}).get("content", "")
            else:
                content = str(resp)
            
            if content:
                snippets.append(f"Q: {prompt}\nA: {content}")
        return snippets
    except Exception as e:
        logger.warning(f"Memory retrieval failed: {e}")
        return []


async def store_semantic_cache(
    vector: list[float], prompt: str, model: str, response_data: dict
):
    """Store prompt embedding + response in Qdrant."""
    try:
        point = PointStruct(
            id=uuid.uuid4().hex,
            vector=vector,
            payload={
                "prompt": prompt,
                "model": model,
                "response": response_data,
                "timestamp": time.time(),
            }
        )
        await qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )
    except Exception as e:
        logger.warning(f"Qdrant upsert failed (graceful fallback): {e}")


# ===============================
# AUTH & RATE LIMITING
# ===============================

API_KEY_HEADER = "x-api-key"


async def check_rate_limit(identifier: str) -> bool:
    """
    Fixed-window rate limit using Redis.

    Returns True if the request is allowed, False if it exceeds the limit.
    """
    if RATE_LIMIT_PER_MINUTE <= 0:
        return True

    try:
        window = int(time.time() // 60)
        key = f"rl:{identifier}:{window}"
        current = await r.incr(key)
        if current == 1:
            # First hit in this window: set expiry.
            await r.expire(key, 60)
        return current <= RATE_LIMIT_PER_MINUTE
    except Exception as e:
        # Fail-open on Redis issues.
        logger.warning(f"Rate limit check failed (graceful fallback): {e}")
        return True


# ===============================
# SAFETY GUARD
# ===============================

class SafetyGuard:
    """Detects and blocks potentially dangerous prompt patterns."""
    
    FORBIDDEN_PATTERNS = [
        r"ignore all previous instructions",
        r"ignore history",
        r"system override",
        r"you are now a", # Common jailbreak prefix
        r"bypass security"
    ]

    @classmethod
    def is_safe(cls, prompt: str) -> tuple[bool, str | None]:
        import re
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                return False, f"Flagged by SafetyGuard: Potential injection pattern detected ('{pattern}')"
        return True, None


async def enforce_auth_and_rate_limit(request: Request) -> JSONResponse | None:
    """
    Enforce optional API key auth and per-identifier rate limiting.

    Returns a JSONResponse on failure, or None to continue processing.
    """
    api_key_header = request.headers.get(API_KEY_HEADER, "").strip()
    client_host = request.client.host if request.client else "unknown"

    # API key auth (if configured).
    if ROUTER_API_KEY:
        # Bypass if client is in the trusted list.
        bypass = False
        if client_host in AUTH_BYPASS_IPS:
            bypass = True
        else:
            try:
                client_ip = ipaddress.ip_address(client_host)
                bypass = any(client_ip in net for net in AUTH_BYPASS_CIDRS)
            except ValueError:
                bypass = False

        if bypass:
            logger.debug(f"Auth bypass for trusted client: {client_host}")
        elif api_key_header != ROUTER_API_KEY:
            logger.warning(f"Unauthorized access attempt from {client_host}")
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "detail": "API key missing or invalid"},
            )

    # Identifier for rate limiting: prefer API key, fall back to client IP.
    identifier = api_key_header or client_host

    allowed = await check_rate_limit(identifier)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"},
        )

    return None


# ===============================
# ENDPOINTS
# ===============================

@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/tags")
async def get_tags():
    """Proxy model list from Ollama."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        logger.error(f"Failed to proxy /api/tags: {e}")
        return JSONResponse(status_code=502, content={"error": "Failed to reach Ollama"})


@app.get("/api/version")
async def get_version():
    """Proxy version info from Ollama."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/version")
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        logger.error(f"Failed to proxy /api/version: {e}")
        return JSONResponse(status_code=502, content={"error": "Failed to reach Ollama"})


@app.post("/api/show")
async def post_show(request: Request):
    """Proxy model details from Ollama."""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{OLLAMA_URL}/api/show", json=body)
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        logger.error(f"Failed to proxy /api/show: {e}")
        return JSONResponse(status_code=502, content={"error": "Failed to reach Ollama"})


async def handle_tool_calls(response_dict: dict, messages: list, model_name: str) -> list | None:
    """Execute tools if the LLM requested them and return updated messages list."""
    if "message" not in response_dict:
        return None
    
    message = response_dict["message"]
    tool_calls = message.get("tool_calls", [])
    content = message.get("content", "")

    # Fallback: if no tool_calls but content contains JSON-like tool call
    if not tool_calls and content:
        # Simple heuristic: look for JSON-like block
        import re
        json_matches = re.findall(r'(\{.*\})', content, re.DOTALL)
        for match in reversed(json_matches):
            try:
                data = json.loads(match)
                if "name" in data and ("arguments" in data or "parameters" in data):
                    tool_calls = [{
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": data["name"],
                            "arguments": data.get("arguments") or data.get("parameters")
                        }
                    }]
                    # Remove the JSON block from content to keep message clean
                    message["content"] = content.replace(match, "").strip()
                    break
            except Exception as e:
                continue

    if not tool_calls:
        return None

    new_messages = messages.copy()
    new_messages.append(message)

    for tool_call in tool_calls:
        function = tool_call.get("function", {})
        name = function.get("name")
        arguments = function.get("arguments")
        
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except:
                pass
        
        logger.info(f"Executing tool: {name} with args: {arguments}")
        result = await registry.call_tool(name, arguments)
        
        new_messages.append({
            "role": "tool",
            "content": str(result),
            "tool_call_id": tool_call.get("id")
        })

    return new_messages


@app.post("/api/chat")
async def proxy_chat(request: Request):
    # Security gate
    security_error = await enforce_auth_and_rate_limit(request)
    if security_error is not None:
        return security_error

    body = await request.json()
    messages = body.get("messages", [])
    
    # Safety check on last message
    if messages:
        last_msg = messages[-1].get("content", "")
        is_safe, safety_msg = SafetyGuard.is_safe(last_msg)
        if not is_safe:
            logger.warning(f"Safety violation in chat: {safety_msg}")
            return JSONResponse(status_code=400, content={"error": safety_msg})

    model_name = body.get("model", "")
    tools = body.get("tools")
    stream_mode = body.get("stream", False)

    # Use registered tools if not provided
    if not tools:
        tools = registry.get_tool_schemas()
        if tools:
            body["tools"] = tools

    logger.info(f"Chat request for {model_name} with tools: {[t['function']['name'] for t in tools] if tools else 'none'}")

    # For now, we only support non-streaming for tool-calling/multi-step reasoning
    if stream_mode:
        async def stream():
            async with ollama_semaphore:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST",
                        f"{OLLAMA_URL}/api/chat",
                        json=body,
                    ) as response:
                        async for chunk in response.aiter_bytes():
                            yield chunk
        return StreamingResponse(stream(), media_type="application/json")

    # Non-stream logic with potential tool loop
    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        # RAG — Retrieve relevant context for chat
        if messages:
            last_msg = messages[-1].get("content", "")
            vector = await embed_prompt(last_msg)
            if vector:
                memory_snippets = await retrieve_memory(vector, model=model_name)
                if memory_snippets:
                    context_str = "\n".join(memory_snippets)
                    # Insert as a system message at the beginning or before the last message
                    memory_msg = {
                        "role": "system",
                        "content": f"Relevant context from past interactions:\n{context_str}"
                    }
                    messages.insert(-1, memory_msg)
                    body["messages"] = messages
                    logger.info("Injected RAG context into chat messages")

        # Initial call
        response = await client.post(f"{OLLAMA_URL}/api/chat", json=body)
        response_data = response.json()
        
        logger.debug(f"Initial Ollama response: {response_data}")

        # Check for tool calls
        for i in range(5):  # Max 5 iterations for reasoning
            next_messages = await handle_tool_calls(response_data, messages, model_name)
            if next_messages is None:
                break
            
            logger.info(f"Tool call detected, iteration {i+1}")
            messages = next_messages
            # Call LLM again with tool results
            body["messages"] = messages
            response = await client.post(f"{OLLAMA_URL}/api/chat", json=body)
            response_data = response.json()
            logger.debug(f"Ollama response (iteration {i+1}): {response_data}")

        return JSONResponse(content=response_data)


@app.post("/api/memory")
async def manage_memory(request: Request):
    """Explicitly add or remove facts from the semantic memory."""
    security_error = await enforce_auth_and_rate_limit(request)
    if security_error is not None:
        return security_error

    body = await request.json()
    action = body.get("action", "learn")
    content = body.get("content", "")
    metadata = body.get("metadata", {})

    if not content:
        return JSONResponse(status_code=400, content={"error": "Content is required"})

    vector = await embed_prompt(content)
    if not vector:
        return JSONResponse(status_code=500, content={"error": "Failed to embed content"})

    if action == "learn":
        await store_semantic_cache(
            vector=vector,
            prompt=f"Memory: {content}",
            model=metadata.get("model", "manual"),
            response_data={"response": content, "source": "manual_entry"}
        )
        return {"status": "learned", "content": content}
    elif action == "forget":
        # Qdrant deletion by filter is more complex; for simplicity, we'll just note this is a stub
        # or we could implement it if we had point IDs.
        return {"status": "error", "message": "Forget action not yet implemented (requires point ID search)"}

    return JSONResponse(status_code=400, content={"error": f"Unknown action: {action}"})


# ===============================
# MAIN ROUTE
# ===============================

@app.post("/api/generate")
async def proxy_generate(request: Request):
    # Security gate: API key auth + rate limiting (if configured).
    security_error = await enforce_auth_and_rate_limit(request)
    if security_error is not None:
        return security_error

    body = await request.json()
    prompt = body.get("prompt", "")
    
    # Safety check
    is_safe, safety_msg = SafetyGuard.is_safe(prompt)
    if not is_safe:
        logger.warning(f"Safety violation in generate: {safety_msg}")
        return JSONResponse(status_code=400, content={"error": safety_msg})

    stream_mode = body.get("stream", True)
    REQUEST_TOTAL.labels(stream=str(stream_mode)).inc()

    key = cache_key(body)
    prompt = body.get("prompt", "")
    model_name = body.get("model", "")

    # ---------------------------
    # Streaming requests — always go to local model directly
    # ---------------------------
    if stream_mode:
        async def stream():
            async with ollama_semaphore:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST",
                        f"{OLLAMA_URL}/api/generate",
                        json=body,
                    ) as response:
                        async for chunk in response.aiter_bytes():
                            yield chunk

        return StreamingResponse(
            stream(),
            media_type="application/json"
        )

    # ---------------------------
    # Non-stream: use policy engine (cache / local / Gemini)
    # ---------------------------
    cache_hit_l1 = False
    cache_hit_l2 = False
    semantic_score: float | None = None
    l1_response: dict | None = None
    l2_response: dict | None = None
    vector: list[float] | None = None

    # 1️⃣ L1 — Redis exact match
    cached = await get_cache(key)
    if cached:
        CACHE_HIT.inc()
        l1_response = orjson.loads(cached)
        cache_hit_l1 = True
    else:
        CACHE_MISS.inc()

        # 2️⃣ L2 — Qdrant semantic match
        vector = await embed_prompt(prompt)
        if vector:
            semantic_result = await search_semantic_cache(
                vector=vector,
                model=model_name,
                max_age_seconds=SEMANTIC_MAX_AGE_SECONDS,
            )
            if semantic_result:
                semantic_score = semantic_result.get("score")
                if semantic_result.get("response") is not None:
                    cache_hit_l2 = True
                    l2_response = semantic_result["response"]

    # Intent classification is optional; keep None unless you add a classifier module.
    intent = None

    # Build policy context and decision
    context = PolicyContext(
        cache_hit_l1=cache_hit_l1,
        cache_hit_l2=cache_hit_l2,
        semantic_score=semantic_score,
        prompt_length=len(prompt or ""),
        model=model_name or None,
        retry_with_gemini=bool(body.get("retry_with_gemini", False)),
        intent=intent,
    )
    decision = decide_route(context)
    logger.info(f"Routing decision: {decision} for model: {model_name}")

    # Record semantic score histogram when we actually have an L2 hit
    if cache_hit_l2 and semantic_score is not None:
        SEMANTIC_SCORE_USED.observe(semantic_score)

    # Route: use cache if available
    if decision == RouteDecision.USE_CACHE:
        POLICY_ROUTE_CACHE.inc()
        if cache_hit_l1 and l1_response is not None:
            return JSONResponse(content=l1_response)
        if cache_hit_l2 and l2_response is not None:
            return JSONResponse(content=l2_response)
        # Fallback to local if policy chose cache but nothing is available
        decision = RouteDecision.USE_LOCAL_MODEL

    # Route: Gemini fallback
    if decision == RouteDecision.USE_GEMINI_FALLBACK:
        POLICY_ROUTE_GEMINI.inc()
        try:
            extra_params: dict = {}
            if "temperature" in body:
                extra_params.setdefault("generationConfig", {})["temperature"] = body["temperature"]

            gemini_response = await generate_with_gemini(prompt, extra_params=extra_params)
            # Cache Gemini response in L1
            data_bytes = orjson.dumps(gemini_response)
            await set_cache(key, data_bytes)

            # Optionally store in L2 semantic cache
            if vector is None:
                vector = await embed_prompt(prompt)
            if vector:
                await store_semantic_cache(
                    vector=vector,
                    prompt=prompt,
                    model=model_name or "gemini",
                    response_data=gemini_response,
                )

            return JSONResponse(content=gemini_response)
        except GeminiNotConfigured:
            logger.warning("Gemini requested but not configured; falling back to local model")
            decision = RouteDecision.USE_LOCAL_MODEL
        except Exception as e:
            logger.warning(f"Gemini request failed, falling back to local model: {e}")
            decision = RouteDecision.USE_LOCAL_MODEL

    # Route: Local model (Ollama)
    if decision == RouteDecision.USE_LOCAL_MODEL:
        POLICY_ROUTE_LOCAL.inc()
        
        # 3️⃣ RAG — Retrieve relevant context if no direct match
        if vector is None:
            vector = await embed_prompt(prompt)
        if vector:
            memory_snippets = await retrieve_memory(vector, model=model_name)
            if memory_snippets:
                context_str = "\n".join(memory_snippets)
                # Augment the prompt
                augmented_prompt = f"Context from past interactions:\n{context_str}\n\nCurrent Request: {prompt}"
                body["prompt"] = augmented_prompt
                logger.info("Injected RAG context into prompt")

    timeout = httpx.Timeout(OLLAMA_TIMEOUT)
    last_exc: Exception | None = None

    for attempt in range(1 + OLLAMA_RETRIES):
        try:
            async with ollama_semaphore:
                t0 = time.monotonic()
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{OLLAMA_URL}/api/generate",
                        json=body,
                    )
                latency = time.monotonic() - t0
                MODEL_LATENCY.observe(latency)

            data = response.content
            response_dict = orjson.loads(data)

            # Store L1 cache
            await set_cache(key, data)

            # Store L2 semantic cache if we have an embedding vector
            if vector:
                await store_semantic_cache(
                    vector=vector,
                    prompt=prompt,
                    model=model_name,
                    response_data=response_dict,
                )

            return JSONResponse(content=response_dict)

        except Exception as e:
            last_exc = e
            if attempt < OLLAMA_RETRIES:
                wait = 2 ** attempt
                logger.warning(
                    f"Ollama request failed (attempt {attempt+1}/"
                    f"{1+OLLAMA_RETRIES}), retrying in {wait}s: {e}"
                )
                await asyncio.sleep(wait)

    logger.error(f"Ollama request failed after {1+OLLAMA_RETRIES} attempts: {last_exc}")

    should_fallback = FALLBACK_TO_GEMINI_ON_ERROR or bool(body.get("fallback_to_gemini_on_error", False))
    if should_fallback:
        try:
            POLICY_ROUTE_GEMINI.inc()
            extra_params: dict = {}
            if "temperature" in body:
                extra_params.setdefault("generationConfig", {})["temperature"] = body["temperature"]

            gemini_response = await generate_with_gemini(body.get("prompt", prompt), extra_params=extra_params)

            # Cache Gemini response in L1
            data_bytes = orjson.dumps(gemini_response)
            await set_cache(key, data_bytes)

            # Optionally store in L2 semantic cache
            if vector is None:
                vector = await embed_prompt(prompt)
            if vector:
                await store_semantic_cache(
                    vector=vector,
                    prompt=prompt,
                    model=model_name or "gemini",
                    response_data=gemini_response,
                )

            return JSONResponse(content=gemini_response)
        except GeminiNotConfigured:
            logger.warning("Gemini fallback enabled but not configured")
        except Exception as e:
            logger.warning(f"Gemini fallback failed: {e}")

    return JSONResponse(
        status_code=502,
        content={"error": "Ollama unavailable", "detail": str(last_exc)},
    )
