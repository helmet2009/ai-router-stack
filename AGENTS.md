# AGENTS.md
AI Router Stack – Production Architecture Specification (v1.1 – March 2026)

---

## 1. System Overview (Current Production)

Local-first AI routing stack บน Arch Linux (Phatthalung, TH)  
ใช้งานจริงกับสแตกต่อไปนี้:

- Open WebUI (Frontend + RAG + Tools) – พอร์ต 8080
- FastAPI Router (Control Plane + Proxy) – พอร์ต 8000
- Ollama (LLM Runtime บน host systemd) – พอร์ต 11434 (127.0.0.1)
- Redis (L1 Cache)
- Qdrant (L2 Semantic Cache)
- Prometheus + Grafana (Observability)
- Tailscale (Secure access จากทุกอุปกรณ์)

**เป้าหมายหลัก**
- Local-first inference เป็นหลัก (Ollama host)
- Deterministic routing + caching
- ควบคุมค่าใช้จ่าย (Gemini เป็น fallback เท่านั้น)
- Latency ต่ำ + observable
- พร้อมขยายไป agentic workflows

---

## 2. High-Level Architecture (Current)

```
User (Tailscale IP)
    ↓
Open WebUI (8080) ── OLLAMA_BASE_URL = http://router:8000
    ↓
Router (8000) ── host.docker.internal:11434
    ├─ Redis (L1 Cache) ── sha256(prompt + model)
    ├─ Qdrant (L2 Semantic Cache) ── nomic-embed-text
    └─ Ollama Host (11434) ── models: qwen2.5-coder, llama3.2:1b, glm-4-flash, ...
          └─ Gemini Fallback (free tier, low confidence only)
```

Router เป็น control plane หลักทุก request ต้องผ่านที่นี่

---

## 3. Agent Model (Current)

**Single-step Deterministic Proxy Agent**  
Capabilities ที่ใช้งานจริง:
- Streaming / non-streaming
- Request hashing + L1 Redis cache
- Semantic cache via Qdrant
- RAG integration (ผ่าน Open WebUI)
- Tool calling (ผ่าน Open WebUI)
- Gemini fallback (เมื่อ confidence ต่ำ)

**ยังไม่มี**
- Autonomous planning
- Multi-step reasoning
- Auto model pull / syntax fix

---

## 4. Router Responsibilities

1. Protocol Adapter (Open WebUI ↔ Ollama)
2. Cache Coordinator (L1 + L2)
3. Model Discovery & Probe (/api/tags)
4. Future Policy Engine + Confidence Scoring
5. Observability Endpoint (/health, /debug/models)

**Current Endpoints**
- POST /api/generate (passthrough + cache)
- GET /health
- GET /debug/models (list Ollama models จาก container)

---

## 5. Caching Strategy

**L1 – Redis**  
Key: `sha256(prompt + system_prompt + model_version)`  
TTL: 3600s  
Rules: cache เฉพาะ non-streaming, binary-safe (orjson)

**L2 – Qdrant**  
Purpose: semantic prompt similarity  
Embedding: nomic-embed-text  
Threshold dynamic (0.89–0.94 ตาม prompt length)

---

## 6. Streaming Policy

- stream=true → passthrough chunks, no cache  
- stream=false → await full response → cache → return JSON

---

## 7. Environment Variables (สำคัญ)

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash
ROUTER_API_KEY=...
```

---

## 8. Production Constraints

- Ollama รันบน host (systemd) ไม่ใช่ container
- Router ใช้ bridge network + extra_hosts: host.docker.internal:host-gateway
- Open WebUI ต่อผ่าน router เท่านั้น
- Tailscale-only access (no public port)

---

## 9. Observability

- Prometheus scrape router:8000/metrics (future)
- Grafana พอร์ต 3001 (admin / admin123)
- Planned metrics: request_total, cache_hit_ratio, gemini_fallback_rate, model_probe_success

---

## 10. Known Issues & Mitigations (Current)

| Issue                        | Status     | Mitigation / Next Step                     |
|------------------------------|------------|--------------------------------------------|
| Router probe Ollama model ไม่เจอ (แต่ host มี) | Active     | เพิ่ม debug probe + fuzzy match ใน ollama_client.py |
| Ollama เป็น host ไม่ใช่ container | By design  | ใช้ extra_hosts + healthcheck ตรง Ollama   |
| Model name syntax mismatch   | Frequent   | ใช้ exact tag จาก ollama list + auto-try fallback tag |
| Container ไม่มี curl/jq      | Temporary  | อัปเดต Dockerfile เพิ่ม debug tools        |

---

## 11. Security Model

- Tailscale overlay network
- Router bind to 0.0.0.0:8000 (แต่เข้าผ่าน Tailscale เท่านั้น)
- Future: rate limiting, API key, prompt injection guard

---

## 12. Scaling Strategy

**Current**: Single GPU node  
**Horizontal Plan**:
- Router replicas + shared Redis/Qdrant
- Ollama sharding (model เฉพาะต่อ node)

---

## 13. Extension Roadmap

**Phase 0 – Current (Deployed)**  
Open WebUI → Router → Ollama + Redis/Qdrant + monitoring

**Phase 1 – Short-term**  
- Model probe & auto-fix syntax  
- Intent classifier (lightweight local)  
- Pre-confidence estimation  
- Gemini fallback logic

**Phase 2 – Mid-term**  
- Policy engine เต็มรูปแบบ  
- Tool execution layer (local-first)  
- Memory / RAG enhancement

**Phase 3 – Long-term**  
- Planner + self-reflection  
- Multi-model arbitration  
- Auto model management (pull/unload)

---

## 14. Design Philosophy

- Deterministic over magic  
- Cache before compute  
- Local before cloud  
- Explicit routing over implicit orchestration  
- Extendable, not over-engineered

---
# Agent Rules

- Always create a plan first
- Show diff before modifying files
- Run tests after changes
- Use bash commands, not fish
- If tool fails (e.g., multi_edit invalid): Retry with fixed params. Remove duplicate edits.
- Max retries per step: 3

**END OF FILE – v1.1 – March 2026**
