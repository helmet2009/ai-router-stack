# TOOLS.md

AI Router Stack – Agent Tool Catalog

This document defines the **tool ecosystem available to all agents** in the system.

Tools allow agents to interact with the environment safely.

All tools must follow:

* allowlisted commands
* sandbox execution
* limited filesystem access
* audit logging

---

# 1. Tool Architecture

Tool invocation flow

User Goal
↓
Agent reasoning
↓
Tool selection
↓
Tool execution sandbox
↓
Result returned to agent

---

# 2. Tool Categories

The system groups tools into 5 major domains.

| Category    | Purpose                |
| ----------- | ---------------------- |
| System      | system inspection      |
| DevOps      | infrastructure control |
| Development | code interaction       |
| Research    | data collection        |
| Data        | parsing and analysis   |

---

# 3. System Tools

Used for inspecting the environment.

### filesystem_tool

Capabilities

* read files
* list directories
* inspect workspace

Allowed commands

ls
cat
pwd

Example

```
ls workspace
cat workspace/report.md
```

---

### shell_tool

Restricted shell execution.

Allowed commands

ls
pwd
cat
git

Example

```
git status
ls -la
```

Unsafe commands are rejected.

---

# 4. DevOps Tools

Infrastructure control tools.

### docker_tool

Capabilities

* inspect containers
* read container logs
* restart services

Allowed commands

docker ps
docker logs
docker restart

Example

```
docker logs router
docker restart redis
```

---

### container_health_tool

Checks health of containers.

Output includes

* container state
* restart count
* uptime

---

# 5. Development Tools

### git_tool

Capabilities

clone repositories
inspect commits
read repository structure

Example

```
git clone repo_url
git log
git status
```

---

### repo_analysis_tool

Scans project codebases.

Capabilities

* directory mapping
* dependency discovery
* architecture overview

Useful for coding agents.

---

# 6. Research Tools

### search_tool

Web search capability.

Engine

DuckDuckGo

Example

```
search EV market Thailand
```

---

### scrape_tool

Extract structured data from web pages.

Capabilities

HTML parsing
text extraction

---

# 7. Data Tools

### parser_tool

Transforms data formats.

Supported

JSON
CSV
Markdown

---

### calculator_tool

Performs numeric calculations.

Used for

analysis
statistics
financial modeling

---

# 8. Workspace Tools

Agents may interact with:

crew/workspace/

Capabilities

* create files
* write reports
* generate scripts

Example

workspace/report.md
workspace/analysis.py

---

# 9. Tool Safety Rules

All tools must follow these constraints.

1. allowlist command filtering
2. workspace-only filesystem access
3. execution timeout
4. audit logging
5. no root-level system modification

---

# 10. Future Tools

Planned tool extensions

browser automation
database connectors
API connectors
scheduler tools
CI/CD pipeline control

---

END OF FILE
