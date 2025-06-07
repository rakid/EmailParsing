"""Configuration management for the SambaNova AI provider."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class SambaNovaConfig:
    """Configuration for the SambaNova AI provider."""

    # API Configuration
    api_key: str = ""
    base_url: str = "https://api.sambanova.com/v1"

    # Model Configuration
    model_name: str = "sambanova/llama-2-70b-chat"
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9

    # Performance Settings
    timeout: int = 30
    max_retries: int = 3

    # Caching
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour

    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.api_key:
            raise ValueError("API key is required")
        if not self.base_url:
            raise ValueError("Base URL is required")
        return True


class SambaNovaConfigManager:
    """Manages loading and saving SambaNova configuration."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize the config manager.

        Args:
            config_path: Path to the configuration file. If None, uses default path.
        """
        if config_path is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".config", "sambanova")
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, "config.yaml")

        self.config_path = Path(config_path)
        self._config: Optional[SambaNovaConfig] = None

    def load(self) -> SambaNovaConfig:
        """Load configuration from file.

        Returns:
            Loaded configuration.

        Raises:
            FileNotFoundError: If the config file doesn't exist.
            yaml.YAMLError: If the config file is invalid YAML.
        """
        if not self.config_path.exists():
            config = SambaNovaConfig()
            self.save(config)
            return config

        with open(self.config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

        # Create config from dictionary
        config = SambaNovaConfig(**config_data)
        self._config = config
        return config

    def save(self, config: SambaNovaConfig) -> None:
        """Save configuration to file.

        Args:
            config: Configuration to save.
        """
        config.validate()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert dataclass to dict, skipping None values
        config_dict = {
            k: v
            for k, v in config.__dict__.items()
            if v is not None and not k.startswith("_")
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False)

        self._config = config

    @property
    def config(self) -> SambaNovaConfig:
        """Get the current configuration."""
        if self._config is None:
            return self.load()
        return self._config
