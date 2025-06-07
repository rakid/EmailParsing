"""
AI Integration Framework

This package provides a modular AI integration framework for the Inbox Zen
Email Parsing MCP Server, supporting multiple AI providers with a common interface.

Architecture:
- base/: Abstract base classes and interfaces
- providers/: Provider-specific implementations (SambaNova, OpenAI, etc.)

Key Components:
- AIInterface: Base interface for all AI providers
- AIPlugin: Base plugin class for AI providers
- Registry: Central registry for AI providers
"""

# Set up AI components availability
_AI_COMPONENTS_AVAILABLE = False

try:
    from .base.ai_interface import AIInterface
    from .base.ai_plugin import AIPlugin
    from .registry import AIRegistry

    _AI_COMPONENTS_AVAILABLE = True
except ImportError:
    # Fall back to dummy implementations if components are not available
    from .base.dummy import DummyAIInterface as AIInterface
    from .base.dummy import DummyAIPlugin as AIPlugin
    from .registry import AIRegistry

# Initialize the registry
registry = AIRegistry()

# Export common types and functions
__all__ = ["AIInterface", "AIPlugin", "registry"]

# Try to import optional components
if _AI_COMPONENTS_AVAILABLE:
    try:
        from .providers.sambanova.sentiment_analysis import SentimentAnalysisEngine
        from .providers.sambanova.task_extraction import TaskExtractionEngine
        from .providers.sambanova.thread_intelligence import ThreadIntelligenceEngine

        __all__.extend(
            [
                "SentimentAnalysisEngine",
                "TaskExtractionEngine",
                "ThreadIntelligenceEngine",
            ]
        )
    except ImportError:
        pass

# Import main plugin for backward compatibility
try:
    from .plugin import SambaNovaPlugin

    __all__.extend(["SambaNovaPlugin"])
except ImportError:
    pass

# Add integration functions
try:
    from .integration import (
        create_sambanova_plugin,
        get_sambanova_integration_info,
        register_sambanova_integrations,
        unregister_sambanova_integrations,
    )

    __all__.extend(
        [
            "create_sambanova_plugin",
            "register_sambanova_integrations",
            "get_sambanova_integration_info",
            "unregister_sambanova_integrations",
        ]
    )
except ImportError:
    pass

__version__ = "1.0.0"
__author__ = "Inbox Zen Team"
__description__ = "AI Integration Framework for the Inbox Zen Email Parsing MCP Server"

# Add SambaNova specific exports if available
try:
    from .config import (
        SambaNovaConfig,
        SambaNovaConfigManager,
        SambaNovaModel,
        get_sambanova_config,
        initialize_sambanova_config,
        validate_sambanova_setup,
    )

    __all__.extend(
        [
            "SambaNovaConfig",
            "SambaNovaConfigManager",
            "SambaNovaModel",
            "get_sambanova_config",
            "initialize_sambanova_config",
            "validate_sambanova_setup",
        ]
    )
except ImportError:
    pass

# Module metadata
AI_MODULE_INFO = {
    "name": "sambanova-ai-integration",
    "version": __version__,
    "description": __description__,
    "capabilities": [
        "advanced_task_extraction",
        "contextual_email_analysis",
        "intelligent_sentiment_analysis",
        "multi_email_thread_intelligence",
        "ai_powered_response_suggestions",
    ],
    "models_supported": (
        [model.value for model in SambaNovaModel]
        if "SambaNovaModel" in locals()
        else []
    ),
    "integration_type": "ai_plugin_extension",
}
