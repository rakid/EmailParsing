"""
SambaNova AI Integration Registration

This module provides utilities to register SambaNova AI components with the
existing integration registry.
"""

import logging
from typing import Any, Dict, Optional

from src.integrations import integration_registry


# Interface de base pour l'analyse IA
class AIAnalysisInterface:
    """Interface for AI analysis plugins."""

    async def initialize(self) -> None:
        """Initialize the AI interface."""
        pass

    async def cleanup(self) -> None:
        """Clean up resources."""
        pass


# Implémentation de l'interface SambaNova
class SambaNovaInterface(AIAnalysisInterface):
    """SambaNova AI interface implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.initialized = False

    async def initialize(self) -> None:
        """Initialize the SambaNova interface."""
        self.initialized = True

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.initialized = False


def get_sambanova_config() -> Dict[str, Any]:
    """Get SambaNova configuration from environment variables."""
    import os

    return {
        "api_key": os.getenv("SAMBANOVA_API_KEY", ""),
        "model": os.getenv("SAMBANOVA_MODEL", "sambanova-large"),
        "max_concurrent_requests": int(os.getenv("SAMBANOVA_MAX_CONCURRENT", "5")),
        "timeout_seconds": int(os.getenv("SAMBANOVA_TIMEOUT", "30")),
        "enable_caching": os.getenv("SAMBANOVA_ENABLE_CACHE", "true").lower() == "true",
        "batch_processing": os.getenv("SAMBANOVA_BATCH_PROCESSING", "true").lower()
        == "true",
    }


def validate_sambanova_setup() -> bool:
    """Validate that SambaNova is properly configured."""
    config = get_sambanova_config()
    return bool(config.get("api_key"))


# Création d'une instance de plugin factice pour la compatibilité
def create_sambanova_plugin(
    config: Optional[Dict[str, Any]] = None,
) -> SambaNovaInterface:
    """Create a SambaNova plugin instance."""
    return SambaNovaInterface(config or {})


logger = logging.getLogger(__name__)


async def register_sambanova_integrations(
    config: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Register SambaNova AI components with the integration registry.

    Args:
        config: Optional configuration dictionary. If not provided, will attempt
               to load from environment variables.

    Returns:
        True if registration successful, False otherwise
    """
    try:
        logger.info("Registering SambaNova AI integrations...")

        # Get or validate configuration
        if config is None:
            config = get_sambanova_config()
        else:
            # Merge with default config if partial config provided
            default_config = get_sambanova_config()
            default_config.update(config)
            config = default_config

        # Validate setup
        if not validate_sambanova_setup():
            logger.error(
                "SambaNova setup validation failed - missing required configuration"
            )
            return False

        # Create and initialize the interface
        sambanova_interface = SambaNovaInterface(config)
        await sambanova_interface.initialize()

        # Register the AI interface
        integration_registry.register_ai_interface("sambanova", sambanova_interface)
        logger.info("SambaNova AI interface registered successfully")

        # Create and register the plugin
        sambanova_plugin = create_sambanova_plugin(config)

        # Register with high priority (low number = high priority)
        integration_registry.plugin_manager.register_plugin(
            sambanova_plugin, priority=5
        )
        logger.info("SambaNova AI plugin registered successfully with priority 5")

        logger.info("SambaNova AI integrations registered successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to register SambaNova integrations: {e}", exc_info=True)
        return False


def get_sambanova_integration_info() -> Dict[str, Any]:
    """
    Get information about registered SambaNova integrations.

    Returns:
        Dictionary with integration status and details
    """
    try:
        # Check AI interface registration
        ai_interface = integration_registry.get_ai_interface("sambanova")
        ai_registered = ai_interface is not None

        # Check plugin registration
        plugin_info = integration_registry.plugin_manager.get_plugin_info()
        plugin_registered = "sambanova-ai-analysis" in plugin_info

        sambanova_plugin_info = plugin_info.get("sambanova-ai-analysis", {})

        return {
            "ai_interface_registered": ai_registered,
            "plugin_registered": plugin_registered,
            "plugin_info": sambanova_plugin_info,
            "total_plugins": len(plugin_info),
            "total_ai_interfaces": len(integration_registry.ai_interfaces),
            "sambanova_available": ai_registered and plugin_registered,
        }

    except Exception as e:
        logger.error(f"Error getting SambaNova integration info: {e}")
        return {"error": str(e), "sambanova_available": False}


async def unregister_sambanova_integrations() -> bool:
    """
    Unregister SambaNova AI components from the integration registry.

    Returns:
        True if unregistration successful, False otherwise
    """
    try:
        logger.info("Unregistering SambaNova AI integrations...")

        # Unregister plugin
        if "sambanova-ai-analysis" in integration_registry.plugin_manager.plugins:
            plugin = integration_registry.plugin_manager.plugins[
                "sambanova-ai-analysis"
            ]
            await plugin.cleanup()
            integration_registry.plugin_manager.unregister_plugin(
                "sambanova-ai-analysis"
            )
            logger.info("SambaNova plugin unregistered successfully")

        # Unregister AI interface
        if "sambanova" in integration_registry.ai_interfaces:
            ai_interface = integration_registry.ai_interfaces["sambanova"]
            await ai_interface.cleanup()
            del integration_registry.ai_interfaces["sambanova"]
            logger.info("SambaNova AI interface unregistered successfully")

        logger.info("SambaNova AI integrations unregistered successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to unregister SambaNova integrations: {e}", exc_info=True)
        return False


# Auto-registration flag
_AUTO_REGISTER_ON_IMPORT = False


def enable_auto_registration():
    """Enable automatic registration of SambaNova components on import."""
    global _AUTO_REGISTER_ON_IMPORT
    _AUTO_REGISTER_ON_IMPORT = True


async def try_auto_register():
    """Attempt to auto-register SambaNova components if enabled and configured."""
    if not _AUTO_REGISTER_ON_IMPORT:
        return

    try:
        if validate_sambanova_setup():
            await register_sambanova_integrations()
            logger.info("SambaNova components auto-registered successfully")
    except Exception as e:
        logger.debug(
            f"Auto-registration failed (this is normal if not configured): {e}"
        )


# Example usage configuration
EXAMPLE_CONFIG = {
    "sambanova": {
        "api_key": "your_sambanova_api_key_here",
        "model": "sambanova-large",
        "max_concurrent_requests": 5,
        "timeout_seconds": 30,
        "enable_caching": True,
        "batch_processing": True,
        "enable_context_analysis": True,
    }
}
