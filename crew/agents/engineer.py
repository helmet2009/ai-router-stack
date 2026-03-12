from crewai import Agent
from langchain_ollama import ChatOllama
from crew.tools import FileReaderTool, FileWriterTool

def create_engineer(llm: ChatOllama) -> Agent:
    return Agent(
        role="AI Engineer & Solution Architect",
        goal="Convert research and objectives into actionable code, reports, or workflows.",
        backstory=(
            "You are an AI Engineer specializing in writing code, scripts, and Markdown reports. "
            "You use the File Writer Tool to save your work to the workspace."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm,
        tools=[FileReaderTool(), FileWriterTool()],
        max_iter=5,
    )
