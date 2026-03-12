# AGENTS.md

AI Router Stack – Multi-Agent Architecture Specification (v2)

---

# 1. System Purpose

This repository implements a **local-first multi-agent AI system** designed to operate as a personal AI assistant similar to:

* autonomous coding assistants
* DevOps automation agents
* research copilots
* personal AI operating systems

The system runs entirely on a **local infrastructure stack** using containerized services and open-source models.

Primary goals:

* autonomous task execution
* multi-agent collaboration
* local model inference
* persistent memory
* tool-enabled actions
* secure execution environment

---

# 2. Core Architecture

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
  ├── Redis Memory
  ├── Qdrant Vector Memory
  └── Ollama LLM Runtime
```

---

# 3. Infrastructure Services

The system runs via Docker Compose.

Services include:

| Service    | Role                    |
| ---------- | ----------------------- |
| router     | API gateway + LLM proxy |
| open-webui | chat interface          |
| redis      | short-term memory       |
| qdrant     | vector memory           |
| prometheus | metrics                 |
| grafana    | monitoring              |

LLM inference is executed through:

Ollama (running on host)

---

# 4. Router Responsibilities

The Router acts as the **control plane**.

Responsibilities:

* LLM proxy
* cache layer
* agent gateway
* tool execution interface
* telemetry endpoint

Main endpoints:

```
POST /api/generate
POST /api/agent/run
```

---

# 5. Agent Architecture

Agents are implemented using CrewAI.

There are two types:

### Control Agents

| Agent   | Purpose                  |
| ------- | ------------------------ |
| Planner | Break goals into tasks   |
| Manager | Coordinate worker agents |

### Worker Agents

| Agent      | Role                          |
| ---------- | ----------------------------- |
| Researcher | data collection               |
| Engineer   | coding and automation         |
| Reviewer   | validation and output quality |

Agents collaborate through **task orchestration**.

---

# 6. Task Execution Model

Execution pipeline:

```
Goal
 ↓
Planner
 ↓
Task List
 ↓
Manager
 ↓
Crew Workers
 ↓
Tool Execution
 ↓
Memory Storage
 ↓
Final Result
```

Example:

User goal:

```
Analyze EV market Thailand
```

Planner output:

```
1 research EV adoption data
2 analyze policy incentives
3 create investment model
4 produce report
```

---

# 7. Tool Execution System

Agents can interact with tools through a controlled sandbox.

Available tool categories:

### System Tools

* filesystem
* shell
* process management

### Development Tools

* git
* docker
* repository analysis

### Research Tools

* web search
* web scraping

### Data Tools

* parsing
* transformation
* analytics

All commands are validated through **allowlists** before execution.

Example:

```
docker ps
docker logs
git clone
ls
cat
```

Unsafe commands are rejected.

---

# 8. Workspace

Agents operate within a dedicated workspace directory.

```
crew/workspace/
```

This directory allows agents to:

* generate reports
* write scripts
* store intermediate files
* run analysis

Example outputs:

```
workspace/report.md
workspace/analysis.py
workspace/data.json
```

---

# 9. Memory Architecture

Two memory layers exist.

### L1 Memory — Redis

Purpose:

* conversation context
* agent state
* task outputs
* cache

Characteristics:

* low latency
* ephemeral

---

### L2 Memory — Qdrant

Purpose:

* long-term knowledge
* semantic retrieval
* solution history

Flow:

```
prompt
↓
embedding
↓
vector search
↓
context injection
```

---

# 10. Autonomous Execution

Agents may run multiple reasoning cycles.

Loop pattern:

```
plan
execute
observe
reflect
repeat
```

This allows the system to solve multi-step tasks.

Maximum iterations are configurable per request.

---

# 11. Monitoring

System metrics are exported to:

Prometheus

Dashboards are visualized via:

Grafana

Recommended metrics:

```
agent_tasks_total
agent_tool_calls_total
agent_failures_total
router_requests_total
cache_hit_ratio
```

---

# 12. Security Model

Security is enforced through:

* container isolation
* command allowlists
* tool sandboxing
* filesystem restrictions

Agents cannot execute arbitrary system commands.

Workspace scope is limited.

---

# 13. Scaling Strategy

Current mode:

single node deployment

Future horizontal scaling:

```
multiple routers
shared redis
shared qdrant
load balancer
distributed inference nodes
```

---

# 14. Performance Expectations

Typical resource usage:

| Component     | Memory  |
| ------------- | ------- |
| Open WebUI    | ~400 MB |
| Router        | ~50 MB  |
| Redis         | ~10 MB  |
| Qdrant        | ~150 MB |
| CrewAI Agents | ~200 MB |

Total base footprint:

~800 MB (excluding LLM models)

---

# 15. Development Workflow

Recommended development process:

1. implement tool
2. register tool with agent
3. test agent behavior
4. observe telemetry
5. refine prompts and roles

---

# 16. Repository Layout

```
ai-router-stack/

docker-compose.production.yml
AGENTS.md

router/

crew/
  agents/
  tools/
  planner/
  memory/
  workspace/

monitoring/
```

---

# 17. Design Philosophy

System principles:

* local-first AI
* deterministic execution
* tool-augmented reasoning
* transparent orchestration
* secure automation

Agents should assist with:

* development
* research
* operations
* automation

---

END OF FILE
