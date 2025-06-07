"""
Registry for AI providers.

This module provides a central registry for managing AI provider plugins.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar

from .base.ai_plugin import AIPlugin

T = TypeVar("T", bound=AIPlugin)


class AIRegistry:
    """
    A registry for AI provider plugins.
    """

    def __init__(self):
        """Initialize the registry."""
        self._plugins: Dict[str, Type[AIPlugin]] = {}
        self._instances: Dict[str, AIPlugin] = {}

    def register_plugin(self, plugin_cls: Type[T]) -> None:
        """
        Register an AI plugin class.

        Args:
            plugin_cls: The plugin class to register.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        # Create a temporary instance to get the name
        try:
            # Try to get the name without validation
            temp_instance = plugin_cls.__new__(plugin_cls)
            temp_instance._initialized = True  # Skip initialization
            name = temp_instance.name.lower()
        except Exception:
            # Fall back to class name if getting the name fails
            name = plugin_cls.__name__.lower()

        if name in self._plugins:
            raise ValueError(f"Plugin with name '{name}' is already registered.")

        self._plugins[name] = plugin_cls

    def get_plugin_class(self, name: str) -> Optional[Type[AIPlugin]]:
        """
        Get a plugin class by name.

        Args:
            name: The name of the plugin to get.

        Returns:
            The plugin class, or None if not found.
        """
        return self._plugins.get(name.lower())

    async def get_plugin(
        self, name: str, config: Optional[Dict[str, Any]] = None
    ) -> Optional[AIPlugin]:
        """
        Get or create an instance of a plugin.

        Args:
            name: The name of the plugin to get.
            config: Optional configuration for the plugin.

        Returns:
            An initialized plugin instance, or None if not found.
        """
        name = name.lower()

        # Return existing instance if available
        if name in self._instances:
            instance = self._instances[name]
            # Update config if provided
            if config is not None:
                instance.config.update(config)
                await instance.initialize()
            return instance

        # Create new instance if plugin class exists
        plugin_cls = self.get_plugin_class(name)
        if plugin_cls is None:
            return None

        instance = plugin_cls(config or {})
        await instance.initialize()
        self._instances[name] = instance
        return instance

    def list_plugins(self) -> List[str]:
        """
        List all registered plugin names.

        Returns:
            A list of registered plugin names.
        """
        return list(self._plugins.keys())

    def clear(self) -> None:
        """Clear all registered plugins and instances."""
        self._plugins.clear()
        self._instances.clear()


# Create a default registry instance
default_registry = AIRegistry()


# Convenience functions
def register_plugin(plugin_cls: Type[T]) -> None:
    """Register a plugin with the default registry."""
    default_registry.register_plugin(plugin_cls)


def get_plugin(
    name: str, config: Optional[Dict[str, Any]] = None
) -> Optional[AIPlugin]:
    """Get a plugin instance from the default registry."""
    import asyncio

    return asyncio.get_event_loop().run_until_complete(
        default_registry.get_plugin(name, config)
    )


def list_plugins() -> List[str]:
    """List all plugins in the default registry."""
    return default_registry.list_plugins()
