from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from langchain_community.tools import DuckDuckGoSearchRun

class SearchToolSchema(BaseModel):
    """Input for SearchTool."""
    query: str = Field(..., description="The search query.")

class SearchTool(BaseTool):
    name: str = "Search Tool"
    description: str = "Search the web for current information. Returns a summary of search results."
    args_schema: Type[BaseModel] = SearchToolSchema
    
    def _run(self, query: str) -> str:
        # We reuse Langchain's DuckDuckGo client for simplicity in this local stack
        search = DuckDuckGoSearchRun()
        try:
            return search.run(query)
        except Exception as e:
            return f"Error executing search: {str(e)}"
