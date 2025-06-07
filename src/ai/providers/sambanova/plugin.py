"""
SambaNova AI Plugin implementation.

This module provides the plugin implementation for SambaNova's AI services.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from ...base import AIPlugin
from .config import SambaNovaConfig, SambaNovaConfigManager
from .interface import SambaNovaInterface


class SambaNovaPlugin(AIPlugin):
    """SambaNova AI Plugin for the Inbox Zen Email Parsing MCP Server."""

    # Plugin metadata
    description = "SambaNova AI integration for email parsing and analysis"

    @property
    def name(self) -> str:
        """Return the name of the AI provider."""
        return "sambanova"

    @property
    def version(self) -> str:
        """Return the version of the AI provider."""
        return "1.0.0"

    # Default configuration
    default_config = {
        "api_key": "",
        "base_url": "https://api.sambanova.com/v1",
        "model_name": "sambanova/llama-2-70b-chat",
        "max_tokens": 2048,
        "temperature": 0.7,
        "top_p": 0.9,
        "timeout": 30,
        "max_retries": 3,
        "enable_caching": True,
        "cache_ttl": 3600,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the SambaNova plugin.

        Args:
            config: Optional configuration dictionary or SambaNovaConfig instance.
                   If not provided, will be loaded from default location.
        """
        super().__init__(config)
        self._config_manager = SambaNovaConfigManager()
        self._config: Optional[SambaNovaConfig] = None
        self._interface: Optional[SambaNovaInterface] = None
        self._client = None  # Initialize _client as None

        try:
            # For testing, skip config file loading if TESTING env var is set
            if os.environ.get("TESTING") == "1":
                self._config = (
                    config
                    if isinstance(config, SambaNovaConfig)
                    else SambaNovaConfig(**(config or {}))
                )
            else:
                # In non-testing mode, load config from file if not provided
                if config is None:
                    try:
                        self._config = self._config_manager.load_config()
                    except FileNotFoundError:
                        # Create default config if none exists
                        self._config = SambaNovaConfig()
                        self._config_manager.save(self._config)
                elif isinstance(config, SambaNovaConfig):
                    self._config = config
                else:
                    self._config = SambaNovaConfig(**config)
                    self._config.validate()
                    self._config_manager.save(self._config)

                # Override with any config provided at runtime
                if config and isinstance(config, dict):
                    for key, value in config.items():
                        if hasattr(self._config, key):
                            setattr(self._config, key, value)
        except Exception as e:
            logging.error(f"Error initializing SambaNova plugin: {e}")
            raise

        # Always validate the final config
        if self._config is not None:
            self._config.validate()

    async def _initialize(self) -> None:
        """Initialize the plugin and its dependencies."""
        if self._config is None:
            raise RuntimeError("Configuration not loaded")

        # Lazy initialization of the interface
        if self._interface is None:
            self._interface = SambaNovaInterface(self._config)

        # Just set the initialized flag, don't call super().initialize()
        # to avoid recursion
        self._initialized = True
        logging.info("SambaNova plugin initialized")

    async def analyze_email(
        self, email_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze an email and extract structured information.

        Args:
            email_data: Dictionary containing email data (subject, body, etc.)
            context: Optional context for the analysis

        Returns:
            Dictionary containing the analysis results
        """
        if not self._initialized:
            await self.initialize()
        return await self.interface.analyze_email(email_data, context)

    async def extract_tasks(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract tasks from the given text.

        Args:
            text: Input text to extract tasks from.
            context: Optional context information for task extraction.

        Returns:
            List of extracted tasks with their details.
        """
        if not self._initialized:
            await self.initialize()
        return await self.interface.extract_tasks(text, context)

    async def analyze_sentiment(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze the sentiment of the given text.

        Args:
            text: Text to analyze.
            context: Optional context for the analysis.

        Returns:
            Dictionary containing sentiment analysis results.
        """
        if not self._initialized:
            await self.initialize()
        return await self.interface.analyze_sentiment(text, context)

    async def analyze_thread(
        self, thread: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze a thread of messages.

        Args:
            thread: List of message dictionaries forming the thread.
            context: Optional context for the analysis.

        Returns:
            Dictionary containing thread analysis results.
        """
        if not self._initialized:
            await self.initialize()
        return await self.interface.analyze_thread(thread, context)

    def get_interface(self) -> SambaNovaInterface:
        """Get the AI interface instance.

        Returns:
            SambaNovaInterface: The initialized interface instance.

        Raises:
            RuntimeError: If the plugin is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("Plugin not initialized. Call initialize() first.")
        if self._interface is None:
            raise RuntimeError("Interface not created. Call initialize() first.")
        return self._interface

    @property
    def interface(self) -> SambaNovaInterface:
        """Get the interface instance.

        Returns:
            The SambaNovaInterface instance.

        Raises:
            RuntimeError: If the plugin is not initialized.
        """
        if self._interface is None:
            raise RuntimeError("Plugin not initialized. Call initialize() first.")
        return self._interface

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> bool:
        """Validate the configuration for this plugin.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            bool: True if the configuration is valid.

        Raises:
            ValueError: If the configuration is invalid.
        """
        required_fields = ["api_key", "base_url"]

        for field in required_fields:
            if not config.get(field):
                raise ValueError(f"Missing required configuration field: {field}")

        # Validate URL format if provided
        base_url = config.get("base_url", "")
        if base_url and not (
            base_url.startswith("http://") or base_url.startswith("https://")
        ):
            raise ValueError("base_url must start with 'http://' or 'https://'")

        # Validate numeric fields
        numeric_fields = ["max_tokens", "timeout", "max_retries", "cache_ttl"]
        for field in numeric_fields:
            if field in config and not isinstance(config[field], (int, float)):
                raise ValueError(f"{field} must be a number")

        # Validate temperature and top_p
        if "temperature" in config and not 0 <= config["temperature"] <= 2:
            raise ValueError("temperature must be between 0 and 2")

        if "top_p" in config and not 0 < config["top_p"] <= 1:
            raise ValueError("top_p must be between 0 and 1")

        return True


# Plugin registration is now handled by the test environment or application code
# SambaNovaPlugin.register()  # Commented out to prevent auto-registration
