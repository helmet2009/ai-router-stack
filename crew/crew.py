"""
crew/crew.py — Production-ready CrewAI multi-agent core with dynamic planning.

Agents:  Dynamic planner → researcher → engineer → reviewer
LLM:     ChatOllama via host.docker.internal:11434
Memory:  Redis result cache (crew/memory.py)
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from crewai import Crew, Process, Task
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from crew.memory import get_crew_result, save_crew_result
from crew.planner.planner import PlannerAgent
from crew.agents import create_researcher, create_engineer, create_reviewer

logger = logging.getLogger("crew.crew")

# ──────────────────────────────────────────
# Config (from env)
# ──────────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_OLLAMA_MODEL", "qwen2.5-coder:7b")
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "/tmp/crew_workspace")

os.makedirs(WORKSPACE_DIR, exist_ok=True)


# ──────────────────────────────────────────
# Request schema (used by FastAPI endpoint)
# ──────────────────────────────────────────
class AgentRequest(BaseModel):
    topic: str = Field(..., description="หัวข้อหลักที่ต้องการให้ multi-agent วิเคราะห์")
    goal: str = Field(
        default="วิเคราะห์และให้คำแนะนำเชิงลึก",
        description="เป้าหมายสุดท้ายของ crew นี้",
    )
    max_iterations: int = Field(default=5, ge=1, le=10)
    use_cache: bool = Field(default=True, description="ใช้ Redis cache สำหรับ topic เดิม")
    model: str = Field(default="", description="Ollama model override (ว่างเปล่า = ใช้ default)")


# ──────────────────────────────────────────
# LLM factory (cached per model name)
# ──────────────────────────────────────────
@lru_cache(maxsize=4)
def _get_llm(model_name: str) -> ChatOllama:
    timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    return ChatOllama(
        model=model_name,
        base_url=OLLAMA_URL,
        temperature=0.65,
        num_ctx=8192,  # คงที่ 8k เพื่อประหยัด VRAM
        timeout=timeout,
    )


# ──────────────────────────────────────────
# Task factory (dynamic per request)
# ──────────────────────────────────────────
def _generate_dynamic_tasks(
    request: AgentRequest,
    researcher,
    engineer,
    reviewer,
    model_name: str
) -> list[Task]:

    # 1. Use PlannerAgent to dynamically break the goal down
    planner = PlannerAgent(model_name=model_name)
    plan = planner.generate_plan(request.topic, request.goal)

    crew_tasks = []
    agent_map = {
        "researcher": researcher,
        "engineer": engineer,
    }

    # 2. Map planner JSON into CrewAI Tasks
    previous_task = None
    for step in plan:
        agent_name = step.get("agent", "researcher")
        assigned_agent = agent_map.get(agent_name, researcher) # fallback to researcher

        t = Task(
            description=step.get("description", f"Process: {request.topic}"),
            expected_output=step.get("expected_output", "Task results"),
            agent=assigned_agent,
            context=[previous_task] if previous_task else []
        )
        crew_tasks.append(t)
        previous_task = t

    # 3. Always append the generic reviewer task at the end to finalize
    review_task = Task(
        description=(
            "ตรวจสอบและสรุปผลการทำงานที่ผ่านมาอย่างละเอียด "
            "แก้ไขข้อผิดพลาด เติมเต็มส่วนที่ขาด และสร้าง final deliverable ให้ตรงกับเป้าหมายของผู้ใช้\n"
            f"Topic: {request.topic}\n"
            f"Goal: {request.goal}"
        ),
        expected_output=(
            "รายงานฉบับสุดท้าย (Markdown format) ประกอบด้วย:\n"
            "1. Executive Summary\n"
            "2. รายละเอียดวิเคราะห์และข้อมูลเชิงลึก\n"
            "3. โค้ดหรือแผนงาน (ถ้ามี)\n"
            "4. บทสรุปและ Next Steps"
        ),
        agent=reviewer,
        context=crew_tasks,
    )
    
    crew_tasks.append(review_task)
    return crew_tasks


# ──────────────────────────────────────────
# Public API
# ──────────────────────────────────────────
def run_crew(request: AgentRequest) -> dict:
    """
    Run the multi-agent crew synchronously.
    Intended to be called from asyncio.run_in_executor() to avoid blocking the event loop.
    """
    # Check Redis cache first
    if request.use_cache:
        cached = get_crew_result(request.topic)
        if cached:
            logger.info(f"Returning cached crew result for: {request.topic[:60]}")
            cached["cache_hit"] = True
            return cached

    model_name = request.model or DEFAULT_MODEL
    logger.info(f"Starting crew run | topic={request.topic[:60]} | model={model_name}")

    llm = _get_llm(model_name)
    
    researcher = create_researcher(llm)
    engineer = create_engineer(llm)
    reviewer = create_reviewer(llm)
    
    tasks = _generate_dynamic_tasks(request, researcher, engineer, reviewer, model_name=model_name)

    crew = Crew(
        agents=[researcher, engineer, reviewer],
        tasks=tasks,
        process=Process.sequential,
        memory=True, # Note: this sets crew internal memory
        cache=True,
        verbose=True,
        planning=False, # We use our own PlannerAgent
        max_rpm=None,  # No rate limit for local Ollama
    )

    result_obj = crew.kickoff(inputs={"topic": request.topic, "goal": request.goal})

    output = {
        "final_output": str(result_obj),
        "topic": request.topic,
        "goal": request.goal,
        "model": model_name,
        "agents_used": [a.role for a in crew.agents],
        "tasks_completed": len(crew.tasks),
        "status": "completed",
        "cache_hit": False,
    }

    # Persist to Redis for future cache hits
    if request.use_cache:
        save_crew_result(request.topic, output)

    return output
