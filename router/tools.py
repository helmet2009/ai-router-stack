import abc
import json
from typing import Any, Dict, List, Optional, Type

class Tool(abc.ABC):
    """Base class for all tools."""
    
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Name of the tool."""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Description of the tool for the LLM."""
        pass

    @property
    @abc.abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema of the tool parameters."""
        pass

    @abc.abstractmethod
    async def run(self, **kwargs) -> Any:
        """Execute the tool."""
        pass

    def to_openai_tool(self) -> Dict[str, Any]:
        """Convert to OpenAI tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

class ToolRegistry:
    """Registry to manage and execute tools."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a new tool."""
        self.tools[tool.name] = tool

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all registered tools."""
        return [tool.to_openai_tool() for tool in self.tools.values()]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name with arguments."""
        if name not in self.tools:
            return f"Error: Tool '{name}' not found."
        
        try:
            return await self.tools[name].run(**arguments)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

# Global registry
registry = ToolRegistry()
