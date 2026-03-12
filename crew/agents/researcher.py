from crewai import Agent
from langchain_ollama import ChatOllama
from crew.tools import SearchTool

def create_researcher(llm: ChatOllama) -> Agent:
    return Agent(
        role="Senior Researcher",
        goal="Search and quickly gather the most accurate information from multiple sources.",
        backstory=(
            "You are a Senior Researcher with a decade of experience in discovering and "
            "analyzing data. You use the Search Tool to find recent and relevant facts."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm,
        tools=[SearchTool()],
        max_iter=5,
    )
