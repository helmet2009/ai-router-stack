import os
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Ensure we only operate within the Workspace Dir
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "/tmp/crew_workspace")

def _safe_path(filename: str) -> str:
    """Ensure the path is within the workspace directory."""
    # Strip any directory traversal attempts
    basename = os.path.basename(filename)
    return os.path.join(WORKSPACE_DIR, basename)

class FileWriterSchema(BaseModel):
    filename: str = Field(..., description="The name of the file to write (e.g., 'report.md'). Path will be automatically resolved to the workspace.")
    content: str = Field(..., description="The content to write into the file.")

class FileWriterTool(BaseTool):
    name: str = "File Writer Tool"
    description: str = "Write content to a file in the agent workspace. If the file exists, it will be overwritten."
    args_schema: Type[BaseModel] = FileWriterSchema
    
    def _run(self, filename: str, content: str) -> str:
        try:
            os.makedirs(WORKSPACE_DIR, exist_ok=True)
            safe_file = _safe_path(filename)
            with open(safe_file, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {safe_file}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

class FileReaderSchema(BaseModel):
    filename: str = Field(..., description="The name of the file to read from the workspace.")

class FileReaderTool(BaseTool):
    name: str = "File Reader Tool"
    description: str = "Read the contents of a file from the agent workspace."
    args_schema: Type[BaseModel] = FileReaderSchema
    
    def _run(self, filename: str) -> str:
        try:
            safe_file = _safe_path(filename)
            if not os.path.exists(safe_file):
                return f"Error: File {filename} does not exist in workspace."
            with open(safe_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
