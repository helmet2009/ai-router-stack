import os
from typing import Any, Dict, List
import json
import logging
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_OLLAMA_MODEL", "qwen2.5-coder:7b")

logger = logging.getLogger("crew.planner")

PLANNER_PROMPT = """You are the Senior AI Planner Agent for an autonomous agent system.
Your job is to break down a user's objective into a step-by-step Execution Plan.

The system has two worker agents:
1. "researcher": Can search the web for information or read files.
2. "engineer": Can write code, create files, write reports, or analyze data.

Given the TOPIC and GOAL below, output a strict JSON list of tasks.
Each task must be a JSON object with:
- "description": Detailed instruction of what to do
- "expected_output": What exactly needs to be produced by this task
- "agent": Either "researcher" or "engineer"

Rules:
1. ONLY return valid JSON array. Do not include markdown formatting like ```json or any other text before or after.
2. The final task must produce the exact deliverable requested in the GOAL.
3. Keep the plan to 2 or 3 tasks maximum.

TOPIC: {topic}
GOAL: {goal}

JSON PLAN:"""

class PlannerAgent:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.llm = ChatOllama(
            model=model_name,
            base_url=OLLAMA_URL,
            temperature=0.1,  # Low temperature for structured output
            timeout=60,      # Prevent indefinite hangs
        )
        self.prompt = PromptTemplate.from_template(PLANNER_PROMPT)
        self.chain = self.prompt | self.llm
        
    def generate_plan(self, topic: str, goal: str) -> List[Dict[str, Any]]:
        """Generate a dynamic execution plan based on the topic and goal."""
        logger.info(f"Generating plan for topic: {topic[:50]}")
        response = self.chain.invoke({"topic": topic, "goal": goal})
        content = response.content.strip()
        
        # Clean up possible markdown fences
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        try:
            plan = json.loads(content.strip())
            if isinstance(plan, list):
                logger.info(f"Planner generated {len(plan)} tasks.")
                return plan
            else:
                logger.warning("Planner output is not a list. Falling back to default tasks.")
        except json.JSONDecodeError as e:
            logger.error(f"Planner failed to output valid JSON: {str(e)}\nOutput was: {content}")
        
        # Default fallback plan if the LLM fails to output valid JSON
        return [
            {
                "description": f"Research information about: {topic}",
                "expected_output": "Key findings summarized",
                "agent": "researcher"
            },
            {
                "description": f"Complete the goal based on the research: {goal}",
                "expected_output": "The final requested deliverable",
                "agent": "engineer"
            }
        ]
