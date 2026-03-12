docs/index.md
```

```markdown src=docs/index.md
# AI Router Stack – Local-First Multi-Agent AI System

> **A secure, containerized, local-first AI agent platform** — powered by FastAPI, Ollama, Redis, and Qdrant.

[![CI](https://github.com/helmet2009/ai-router-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/helmet2009/ai-router-stack/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Compose](https://img.shields.io/badge/Docker--Compose-24.0+-blue?logo=docker)](https://docs.docker.com/compose/)

---

## 🎯 Overview

`ai-router-stack` is a **local-first AI orchestration platform** for building autonomous agents that:

- ✅ Run entirely on your hardware (no cloud dependency)
- ✅ Use open LLMs via **Ollama**
- ✅ Coordinate tasks using **CrewAI**
- ✅ Store memory in **Redis (L1)** + **Qdrant (L2)**
- ✅ Securely execute tools via allowlist sandbox

Designed for DevOps automation, coding assistants, research agents, and personal AI OS.

---

## 🧱 Architecture

```mermaid
graph TD
    A[User] --> B[Open WebUI]
    B --> C[AI Router (FastAPI)]
    C --> D[Planner Agent]
    D --> E[Manager Agent]
    E --> F[CrewAI Workers]
    F --> G[Tool Sandbox]
    F --> H[Redis Memory]
    F --> I[Qdrant Vector DB]
    F --> J[Ollama LLM]
```

See full architecture in [Architecture Guide →](./architecture.md)

---

## 🚀 Quick Start

```bash
# Clone & deploy in one command
git clone https://github.com/helmet2009/ai-router-stack.git
cd ai-router-stack
docker compose -f docker-compose.production.yml up -d
```

Full guide: [Getting Started →](./getting-started.md)

---

## 🛠️ Stack Overview

| Layer          | Technology                      |
|----------------|---------------------------------|
| Frontend       | Open WebUI                      |
| Router         | FastAPI + Custom Proxy          |
| Agent System   | CrewAI + Planner/Manager/Workers|
| LLM Runtime    | Ollama (host-resident models)   |
| L1 Memory      | Redis (short-term state)        |
| L2 Memory      | Qdrant (semantic vector store)  |
| Tool Execution | Sandbox + Allowlist             |

Full stack details: [Stack Overview →](./agents.md)

---

## 🔒 Security

- ❌ No secrets in code (`.env` excluded via `.gitignore`)
- ✅ All commands go through allowlist validation
- ✅ Container isolation via Docker Compose
- ✅ Read-only workspace scope

Read more in [Security Model →](./AGENTS.md#12-security-model)

---

## 🤝 Contributing

We welcome contributors! See:
- [Contributing Guide →](https://github.com/helmet2009/ai-router-stack/blob/main/CONTRIBUTING.md)
- [Coding Standards →](./SKILLS.md)

---

## 📜 License

MIT License — see [LICENSE](https://github.com/helmet2009/ai-router-stack/blob/main/LICENSE) for details.
```

---

#### ✅ **Step 3: สร้าง `docs/architecture.md` (อ้างอิงจาก `AGENTS.md` §2)**

```bash
cat > docs/architecture.md << 'EOF'
# System Architecture

## High-Level Flow

```
User
  │
  ▼
Open WebUI
  │
  ▼
AI Router (FastAPI)
  │
  ▼
Agent Gateway
  │
  ▼
Planner Agent
  │
  ▼
Manager Agent
  │
  ▼
CrewAI Workers
  │
  ├── Tool Sandbox
  ├── Redis Memory (L1)
  ├── Qdrant Memory (L2)
  └── Ollama LLM Runtime
```

## Core Components

### 1. AI Router (`router/`)

A FastAPI-based gateway that:

- Proxies LLM calls to Ollama or external providers
- Caches responses via Redis
- Routes agent requests to the correct worker pool
- Enforces tool execution policy (see [`policy.py`](../router/policy.py))

Key endpoints:

| Endpoint               | Method | Purpose                          |
|------------------------|--------|----------------------------------|
| `/api/generate`        | POST   | LLM inference (unified interface)|
| `/api/agent/run`       | POST   | Trigger agent execution          |

### 2. Agent System

Agents are defined in [`crew/agents/`](../crew/agents/) and use **CrewAI** for task orchestration.

| Agent Type   | Role                                | File                           |
|--------------|-------------------------------------|--------------------------------|
| Planner      | Breaks high-level goals into tasks  | `planner.py`                   |
| Manager      | Coordinates workers & delegates     | `manager.py`                   |
| Researcher   | Collects data / scrapes web         | `crew/agents/researcher.py`    |
| Engineer     | Generates code / runs automation    | `crew/agents/engineer.py`      |
| Reviewer     | Validates outputs / quality gate    | `crew/agents/reviewer.py`      |

### 3. Memory Layers

| Layer | Tech | Purpose | Latency |
|-------|------|---------|---------|
| L1 (Short-term) | Redis | Conversation state, task outputs | < 5ms |
| L2 (Long-term)  | Qdrant | Semantic retrieval, solution history | ~20–50ms |

Embeddings are generated on the fly (e.g., `text-embedding-ada-002` or local `nomic-embed-text`).

### 4. Tool Execution Sandbox

All tools run inside a restricted shell:

- Commands validated against [`policy.py`](../router/policy.py) allowlist
- Filesystem limited to `crew/workspace/`
- No network outside docker (unless explicitly allowed)

Example allowed commands:

```bash
ls, cat, git clone, docker ps, python script.py, wget
```

Forbidden:

```bash
rm, sudo, ssh, curl (unless in allowlist)
```

## Data Flow Example

Goal: `Analyze EV market in Thailand`

1. **User Input** → `POST /api/agent/run`
2. **Planner** decomposes into:
   - `Researcher`: collect adoption stats, policy docs
   - `Engineer`: build Python analysis script
   - `Reviewer`: verify outputs
3. **Manager** assigns tasks & monitors progress
4. **Tool Sandbox** executes `python analysis.py`
5. **Redis** stores intermediate steps
6. **Qdrant** stores final insights for future reuse
7. **Router** returns structured result to user

## Scaling Strategy

Current: single-node Docker Compose  
Future: Horizontal scaling with:

- Multi-router load balancer
- Shared Redis + Qdrant
- Distributed Ollama inference nodes

See [AGENTS.md §13](../AGENTS.md#13-scaling-strategy).
EOF
```

---

#### ✅ **Step 4: สร้าง `docs/getting-started.md`**

```markdown
docs/getting-started.md
```

```markdown src=docs/getting-started.md
# Getting Started

## ✅ Prerequisites

| Tool        | Version |
|-------------|---------|
| Docker      | ≥24.0   |
| Docker Compose | ≥2.20 |
| Git         | ≥2.39   |
| Ollama      | ≥0.1.0  |
| Python (dev) | ≥3.10  |

> 💡 Ollama must be running on your host (not in Docker) — see [Ollama docs](https://ollama.com/docs).

---

## 🚀 Quick Deploy (Local)

### 1. Clone the Repo

```bash
git clone https://github.com/helmet2009/ai-router-stack.git
cd ai-router-stack
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY (optional, for fallback)
# ROUTER_API_KEY auto-generated if empty — but safer to set manually
```

> 🛑 **Never commit `.env`** — it’s ignored in `.gitignore`.

### 3. Pull Required Docker Images

```bash
docker pull ghcr.io/otwrd/openwebui:latest
docker pull redis:7-alpine
docker pull qdrant/qdrant:latest
```

### 4. Deploy Stack

```bash
docker compose -f docker-compose.production.yml up -d
```

✅ Services up:

| Service      | URL                          | Port |
|--------------|------------------------------|------|
| Open WebUI   | http://localhost:3000        | 3000 |
| Router API   | http://localhost:8000        | 8000 |
| Redis        | `redis://localhost:6379`     | 6379 |
| Qdrant       | http://localhost:6333        | 6333 |

### 5. Test the Router

```bash
curl -X POST http://localhost:8000/api/health \
     -H "Authorization: Bearer $ROUTER_API_KEY"
```

Expected response:

```json
{"status":"ok","ollama_connected":true,"redis_connected":true,"qdrant_connected":true}
```

---

## 🛠 Developer Setup (Optional)

```bash
# Install Python deps
python -m venv venv
source venv/bin/activate
pip install -r router/requirements.txt

# Lint & test
ruff check router/
black --check router/
mypy router/
```

To run router locally (outside Docker):

```bash
uvicorn router.main:app --reload --host 0.0.0.0 --port 8000
```

> ⚠️ Local dev mode bypasses Docker isolation — only for testing.

---

## 🧪 First Agent Task

Use Open WebUI (http://localhost:3000):

1. Log in
2. Go to **Agent Mode** (top-right menu)
3. Type:

   ```
   Analyze Thai EV market trends (2020–2024)
   ```

4. Watch logs in router:

   ```bash
   docker compose logs -f router
   ```

You’ll see:
- Planner → task breakdown
- Manager → delegation
- Tools → `researcher.py`, `engineer.py`, `python analyze.py`

---

## 📦 Clean Up

```bash
docker compose -f docker-compose.production.yml down -v
# Deletes volumes: Redis, Qdrant, workspace
```

---

## ❓ Troubleshooting

| Issue | Solution |
|-------|----------|
| Ollama not reachable | `ollama serve` must be running on host |
| Redis connection error | `docker compose ps` → verify redis is up |
| Vector DB slow | Increase Qdrant RAM (`docker-compose.yml` env vars) |
| Permission denied | Ensure user is in `docker` group: `sudo usermod -aG docker $USER` |

Full FAQ: [troubleshooting.md](./troubleshooting.md)
```

---

#### ✅ **Step 5: สร้าง `docs/tools.md`**

```markdown
docs/tools.md
```

```markdown src=docs/tools.md
# Tool Execution System

Agents interact with the outside world via **sandboxed tools**, governed by strict allowlists in [`router/policy.py`](../router/policy.py).

---

## 🧪 Allowed Categories

### 1. System Tools

| Command | Example | Use Case |
|---------|---------|----------|
| `ls` | `ls -la` | List workspace files |
| `cat` | `cat report.md` | Read text files |
| `mkdir` | `mkdir analysis` | Create directories |
| `python` | `python script.py` | Execute Python code |
| `docker ps` | `docker ps` | List containers (host) |

### 2. Development Tools

| Command | Example | Use Case |
|---------|---------|----------|
| `git` | `git clone https://...` | Clone repos |
| `npm` | `npm install` | Install JS deps |
| `chmod` | `chmod +x script.sh` | Make scripts executable |

### 3. Research Tools

| Command | Example | Use Case |
|---------|---------|----------|
| `wget` | `wget https://...` | Download docs |
| `curl` | `curl -s https://...` | Fetch JSON (if allowed) |

> ⚠️ `curl` must be whitelisted in `policy.py` before use.

### 4. Data Tools

| Command | Example | Use Case |
|---------|---------|----------|
| `jq` | `cat data.json \| jq '.items[]'` | Parse JSON |
| `python -c` | `python -c 'import pandas as pd'` | Inline analytics |

---

## 🔒 Security Rules

1. **No arbitrary commands**
   ```bash
   ❌ rm -rf /   # Blocked by policy
   ❌ sudo su    # Blocked
   ❌ ssh user@host # Blocked unless whitelisted
   ```

2. **Filesystem scope**
   - Only `crew/workspace/` and subdirs are writable
   - Host paths (`/etc`, `/var`) are read-only → blocked

3. **Timeout enforcement**
   - Commands timeout after 60s (configurable per task)
   - Long-running scripts use `&` + PID tracking

4. **Audit logging**
   - All tool calls logged to `logs/tools.log`
   - Includes: timestamp, agent, command, exit code

---

## 🔧 How to Add a New Tool

1. Edit [`router/policy.py`](../router/policy.py)
2. Add command to `ALLOWED_COMMANDS`
3. Optionally add args whitelist:
   ```python
   "docker": {
       "allowed_args": ["ps", "logs", "exec"],
       "block_all_others": True,
   }
   ```
4. Restart router: `docker compose restart router`

Example PR: See [tools.md#adding-a-new-tool](https://github.com/helmet2009/ai-router-stack/blob/main/docs/tools.md#adding-a-new-tool).

---

## 🧰 Example Tool Calls in CrewAI

```python
# In agent’s tools list
[
    {
        "name": "list_files",
        "description": "List files in workspace",
        "func": lambda: run_command("ls -la"),
    },
    {
        "name": "run_python",
        "description": "Execute Python script in workspace",
        "func": lambda script: run_command(f"python {script}"),
    },
]
```

> 🔒 `run_command()` uses sandbox — never uses `subprocess.run(cmd, shell=True)`.
```

---

#### ✅ **Step 6: สร้าง `docs/troubleshooting.md`**

```markdown
docs/troubleshooting.md
```

```markdown src=docs/troubleshooting.md
# Troubleshooting

---

## 🚨 Critical Failures

### Ollama Connection Lost

```bash
# Check if Ollama is running
curl http://localhost:11434

# Should return {"models":[...]}
```

**Fix:**
- Start Ollama: `ollama serve`
- Or pull model: `ollama pull llama3`

---

### Redis Connection Error

```bash
docker compose logs redis
```

Look for:

```
WARNING: Memory overcommit must be enabled!
```

**Fix (Linux):**
```bash
echo "vm.overcommit_memory=1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

### Qdrant Index Out of Memory

```bash
docker compose logs qdrant | grep "oom"
```

**Fix:**
- Increase RAM in `docker-compose.production.yml`:
  ```yaml
  qdrant:
    environment:
      - QDRANT_MEM_LOCK=true
    mem_limit: 2g
  ```

---

## 📝 Common Issues

### 1. `Permission denied` when running tools

**Cause:** User not in `docker` group.

**Fix:**
```bash
sudo usermod -aG docker $USER
# Logout & login to refresh groups
```

### 2. Agent stuck in loop (no progress)

**Diagnose:**
```bash
docker compose logs router | grep "Retry"
```

**Fix:**
- Reduce `max_iterations` in planner prompt
- Check tool timeouts (default: 60s)

### 3. Git clone fails in agent

**Cause:** SSH key not mounted, or HTTP blocked.

**Fix:**
- Use HTTPS + token in `.env`
- Or add `git` to `ALLOWED_COMMANDS` with args in `policy.py`

---

## 🐛 Debugging Agent Flow

Enable verbose logging:

```bash
export AGENT_DEBUG=true
docker compose up router
```

Logs now include:
- `🧩 Planner → task breakdown`
- `🤖 Manager → assigned worker`
- `🛠 Tool Sandbox → executed: ls -la`

---

## 📊 Monitoring Checklist

Use Grafana (http://localhost:3001):

1. Log in (`admin/admin`)
2. Dashboards → `router_dashboard`
3. Check:
   - ✅ `agent_tasks_total` increasing
   - ✅ `cache_hit_ratio` > 0.7
   - ❌ `agent_failures_total` flat or low

Prometheus metrics: http://localhost:9090

---

## 🆘 Still stuck?

1. Check logs: `docker compose logs -f router`
2. Run health check:

   ```bash
   docker compose exec router curl -s http://localhost:8000/api/health | jq

