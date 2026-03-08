# AI Router Stack – Local-First Intelligent Proxy

Production-grade AI inference router with deterministic routing, semantic caching, policy enforcement, and smart fallback to free-tier Gemini.

**Local-first** → ใช้ Ollama เป็นหลัก  
**Zero-cost fallback** → Gemini 1.5 Flash เฉพาะกรณี confidence ต่ำ  
**Secure by design** → Tailscale-only access

## ✨ Features

- Multi-model routing (Ollama local + Gemini fallback)
- L1 Redis exact cache + L2 Qdrant semantic cache
- Intent classification & policy engine (coding → qwen, sensitive → local, etc.)
- Heuristic pre-confidence scoring → ลด cloud call 20–30%
- Streaming support + async FastAPI
- Observability-ready (Prometheus + Grafana planned)
- Tailscale overlay network → no public ports
- Agentic-ready architecture (memory, tools, planner ใน roadmap)

## 🏗 Architecture

```mermaid
flowchart TD
    User[User / Open WebUI] -->|Tailscale| Router[FastAPI Router]
    Router --> Redis[Redis L1 Cache]
    Router --> Qdrant[Qdrant L2 Semantic Cache]
    Qdrant --> Embed[Embedding Model<br>nomic-embed-text]
    Router --> Intent[Intent Classifier]
    Intent --> Policy[Policy Engine]
    Policy --> Ollama[Ollama Local Models]
    Policy -->|low conf + quota ok| Gemini[Gemini 1.5 Flash Free]
    Ollama --> Response[Stream Response]
    Gemini --> Response# ai-router-stack
