# RUNBOOK.md

AI Router Stack – Operations and Debugging Guide

This document defines operational procedures for diagnosing system issues.

---

# 1. System Overview

The platform consists of:

Open WebUI
Router API
CrewAI agents
Redis memory
Qdrant vector memory
Ollama LLM runtime

All components run via Docker.

---

# 2. Basic Health Check

Check running services.

```
docker compose ps
```

Expected containers

router
open-webui
redis
qdrant
prometheus
grafana

---

# 3. Router Failure

Symptoms

API returns 500 errors
Agent execution fails

Diagnosis

```
docker logs ai-router
```

Common causes

missing dependency
memory error
tool execution failure

Restart

```
docker restart ai-router
```

---

# 4. Ollama Connectivity Failure

Symptoms

LLM responses fail.

Error example

connection refused

Diagnosis

```
curl http://localhost:11434/api/tags
```

Expected output

list of installed models

---

# 5. Redis Failure

Symptoms

agent memory unavailable.

Diagnosis

```
docker logs redis
```

Test connection

```
redis-cli ping
```

Expected

```
PONG
```

---

# 6. Qdrant Failure

Symptoms

vector memory retrieval fails.

Check container

```
docker logs qdrant
```

Test API

```
curl http://localhost:6333/collections
```

---

# 7. Agent Execution Failure

Symptoms

agent stops mid-task.

Check router logs.

Look for

tool execution errors
memory failures
LLM timeout

---

# 8. Tool Execution Errors

Symptoms

agent tool invocation fails.

Common causes

command not in allowlist
filesystem permission error

Check logs for:

tool validation failure

---

# 9. Workspace Issues

Agents use

crew/workspace/

Verify directory exists.

```
ls crew/workspace
```

Ensure write permissions.

---

# 10. Monitoring

Metrics available via Prometheus.

Important metrics

agent_tasks_total
agent_failures_total
router_requests_total

Dashboards available in Grafana.

---

# 11. Performance Issues

Common causes

LLM model too large
memory exhaustion
long agent loops

Solutions

reduce iterations
optimize prompts
use smaller models

---

# 12. Recovery Procedure

If the system becomes unstable

restart stack

```
docker compose down
docker compose up -d
```

---

# 13. Backup Strategy

Backup recommended for

Redis snapshot
Qdrant collections
workspace outputs

---

# 14. Incident Reporting

When reporting an issue include:

timestamp
goal input
router logs
container status

---

END OF FILE
