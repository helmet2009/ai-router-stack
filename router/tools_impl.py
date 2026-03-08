import math
import simpleeval
from tools import Tool, registry

class CalculatorTool(Tool):
    """Tool to evaluate mathematical expressions."""
    
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluate a mathematical expression. Supports basic arithmetic, trig functions, etc."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression to evaluate, e.g., '123 * 456' or 'math.sqrt(16)'",
                }
            },
            "required": ["expression"],
        }

    async def run(self, expression: str) -> str:
        try:
            # Use simpleeval for safer evaluation
            result = simpleeval.simple_eval(expression)
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"

# Register the tool
registry.register(CalculatorTool())


class WebSearchTool(Tool):
    """(Mock) Tool to simulate web search."""
    
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                }
            },
            "required": ["query"],
        }

    async def run(self, query: str) -> str:
        # Mocking search results
        responses = {
            "today weather in bangkok": "Today in Bangkok: 32°C, mostly sunny.",
            "who is the ceo of apple": "The CEO of Apple is Tim Cook.",
            "what is the price of bitcoin": "Bitcoin is currently trading at approximately $95,000.",
        }
        return responses.get(query.lower(), f"No results found for '{query}'. (Mock search)")

# Register the search tool
registry.register(WebSearchTool())
