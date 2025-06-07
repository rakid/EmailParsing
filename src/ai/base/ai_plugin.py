"""
Base plugin class for AI providers.

This module defines the abstract base class for AI provider plugins.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, TypeVar

# Use string literals for type hints to avoid circular imports
if TYPE_CHECKING:
    from ..registry import AIRegistry


class AIPlugin(ABC):
    """Abstract base class for AI provider plugins."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AI plugin.

        Args:
            config: Configuration dictionary for the plugin.
        """
        self.config = config or {}
        self._initialized = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the AI provider."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version of the AI provider."""
        pass

    @property
    def is_initialized(self) -> bool:
        """Return whether the plugin has been initialized."""
        return self._initialized

    async def initialize(self) -> None:
        """
        Initialize the plugin.

        This method should be called before using the plugin.
        """
        if not self._initialized:
            await self._initialize()
            self._initialized = True

    @abstractmethod
    async def _initialize(self) -> None:
        """
        Perform provider-specific initialization.

        This method should be implemented by subclasses to perform any
        necessary setup, such as establishing connections or loading models.
        """
        pass

    @abstractmethod
    def get_interface(self) -> Any:
        """
        Get the AI interface instance for this provider.

        Returns:
            An instance of a class implementing AIInterface.
        """
        pass

    @classmethod
    def register(cls, registry: Optional["AIRegistry"] = None) -> None:
        """Register this plugin with the AI registry.

        Args:
            registry: The registry to register with. If None, uses the default registry.
        """
        if registry is None:
            from .. import registry as default_registry

            registry = default_registry
        registry.register_plugin(cls)

    @classmethod
    @abstractmethod
    def validate_config(cls, config: Dict[str, Any]) -> bool:
        """Validate the configuration for this plugin.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            bool: True if the configuration is valid, False otherwise.
        """
        pass
