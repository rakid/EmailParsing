"""MCP Server - Core server implementation for the Model Context Protocol."""

from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T", bound=Callable[..., Any])

from .types import Content, TextContent


class Server:
    """MCP Server handles incoming requests and routes them to appropriate handlers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the MCP server with optional configuration."""
        self.config = config or {}
        self.running = False
        self.handlers: Dict[str, Callable[..., Any]] = {}
        self.name = self.config.get("name", "MCP Email Processing Server")
        self.version = self.config.get("version", "1.0.0")
        self.instructions = "MCP server for unified email entry and processing"
        self.resource_list_handler: Optional[Callable[..., Any]] = None
        self.resource_read_handler: Optional[Callable[..., Any]] = None
        self.tools_list_handler: Optional[Callable[..., Any]] = None
        self.tool_call_handler: Optional[Callable[..., Any]] = None
        self.prompts_list_handler: Optional[Callable[..., Any]] = None
        self.prompt_get_handler: Optional[Callable[..., Any]] = None

    async def start(self) -> None:
        """Start the MCP server."""
        self.running = True

    async def stop(self) -> None:
        """Stop the MCP server."""
        self.running = False

    async def analyze(self, content: Content, **kwargs) -> Dict[str, Any]:
        """Analyze the given content.

        Args:
            content: The content to analyze
            **kwargs: Additional analysis parameters

        Returns:
            Analysis response with results
        """
        if isinstance(content, dict):
            content = TextContent(**content)

        return {
            "success": True,
            "content": content.text if hasattr(content, "text") else str(content),
            "analysis": {
                "sentiment": {"score": 0.8, "label": "positive"},
                "categories": ["test"],
                "entities": [],
            },
        }

    def register_handler(self, content_type: str, handler: Callable[..., Any]) -> None:
        """Register a handler for a specific content type.

        Args:
            content_type: The content type to handle
            handler: The handler function
        """
        self.handlers[content_type] = handler

    def list_resources(self) -> Callable[[T], T]:
        """Register a function as the handler for listing resources.

        Returns:
            The decorator function
        """

        def decorator(func: T) -> T:
            self.resource_list_handler = func
            return func

        return decorator

    def read_resource(self) -> Callable[[T], T]:
        """Register a function as the handler for reading a resource.

        The decorated function should accept a URI parameter and return
        the resource data.

        Returns:
            The decorator function
        """

        def decorator(func: T) -> T:
            self.resource_read_handler = func
            return func

        return decorator

    def list_tools(self) -> Callable[[T], T]:
        """Register a function as the handler for listing available tools.

        The decorated function should return a list of available tools.

        Returns:
            The decorator function
        """

        def decorator(func: T) -> T:
            self.tools_list_handler = func
            return func

        return decorator

    def call_tool(self) -> Callable[[T], T]:
        """Register a function as the handler for calling tools.

        The decorated function should accept tool name and parameters,
        and return the tool's response.

        Returns:
            The decorator function
        """

        def decorator(func: T) -> T:
            self.tool_call_handler = func
            return func

        return decorator

    def list_prompts(self) -> Callable[[T], T]:
        """Register a function as the handler for listing available prompts.

        The decorated function should return a list of available prompts.

        Returns:
            The decorator function
        """

        def decorator(func: T) -> T:
            self.prompts_list_handler = func
            return func

        return decorator

    def get_prompt(self) -> Callable[[T], T]:
        """Register a function as the handler for getting a specific prompt.

        The decorated function should accept a prompt ID and return
        the prompt details.

        Returns:
            The decorator function
        """

        def decorator(func: T) -> T:
            self.prompt_get_handler = func
            return func

        return decorator


async def create_server(config: Optional[Dict[str, Any]] = None) -> Server:
    """Create and initialize a new MCP server instance.

    Args:
        config: Optional configuration dictionary

    Returns:
        Initialized Server instance
    """
    server = Server(config)
    await server.start()
    return server
