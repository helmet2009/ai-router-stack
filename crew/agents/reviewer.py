from crewai import Agent
from langchain_ollama import ChatOllama

def create_reviewer(llm: ChatOllama) -> Agent:
    return Agent(
        role="Technical Reviewer & Quality Controller",
        goal="Verify the output of the researcher and engineer to ensure accuracy and completeness.",
        backstory=(
            "You are a meticulous reviewer who formats final reports clearly "
            "and confirms that the user's initial goal was completely solved."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm,
        tools=[],
        max_iter=3,
    )
