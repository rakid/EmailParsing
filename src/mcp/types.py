"""
MCP Types - Common data types and models for the Model Context Protocol.
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, field_validator


class TextContent(BaseModel):
    """Represents text content with optional metadata."""

    text: str
    metadata: Dict[str, Any] = {}
    content_type: str = "text/plain"


class AnalysisResult(BaseModel):
    """Represents the result of an analysis operation."""

    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class Task(BaseModel):
    """Represents a task extracted from content."""

    id: str
    description: str
    status: str = "pending"
    priority: int = 0
    metadata: Dict[str, Any] = {}


class EmailAnalysis(AnalysisResult):
    """Represents the result of an email analysis."""

    tasks: List[Task] = []
    sentiment: Optional[Dict[str, float]] = None
    categories: List[str] = []
    entities: List[Dict[str, Any]] = []


class PromptMessage(BaseModel):
    """A message in a prompt conversation."""

    role: Literal["system", "user", "assistant", "function"]
    content: str
    name: Optional[str] = None


class PromptArgument(BaseModel):
    """An argument for a prompt template."""

    name: str
    type: str
    description: str
    required: bool = True


class Prompt(BaseModel):
    """A prompt template for generating AI responses."""

    name: str
    description: str
    messages: List[PromptMessage]
    arguments: List[PromptArgument] = []
    metadata: Dict[str, Any] = {}


class Resource(BaseModel):
    """A resource that can be used by tools or prompts."""

    uri: str
    name: str
    description: str
    mimeType: Optional[str] = None
    metadata: Dict[str, Any] = {}

    @field_validator('uri', mode='before')
    @classmethod
    def convert_uri_to_string(cls, v):
        """Convert AnyUrl to string if needed."""
        if hasattr(v, '__str__'):
            return str(v)
        return v


class Tool(BaseModel):
    """A tool that can be called by the AI."""

    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str] = []
    returns: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


# Common types for MCP
Content = Union[str, TextContent, Dict[str, Any]]
AnalysisRequest = Dict[str, Any]
AnalysisResponse = Dict[str, Any]
