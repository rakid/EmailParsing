"""
SambaNova AI Configuration Module
Handles API credentials, model parameters, and integration settings.
"""

import logging
import os
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


class SambaNovaModel(str, Enum):
    """Available SambaNova models for different use cases."""

    E5_MISTRAL_7B = "e5-mistral-7b-instruct"
    SAMBANOVA_LARGE = "sambanova-large"
    DEFAULT = "e5-mistral-7b-instruct"


class SambaNovaConfig(BaseModel):
    """
    SambaNova API configuration with validation and defaults.
    Integrates with existing config system via environment variables.
    """

    api_key: str = Field(..., description="SambaNova API key", min_length=10)

    model: SambaNovaModel = Field(
        default=SambaNovaModel.DEFAULT, description="SambaNova model identifier"
    )

    endpoint: str = Field(
        default="https://api.sambanova.ai/v1", description="SambaNova API endpoint URL"
    )

    max_tokens: int = Field(
        default=2048, ge=100, le=8192, description="Maximum tokens for model responses"
    )

    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Model temperature for response randomness",
    )

    timeout: int = Field(
        default=30, ge=5, le=120, description="API request timeout in seconds"
    )

    max_retries: int = Field(
        default=3, ge=1, le=10, description="Maximum number of API retry attempts"
    )

    rate_limit_rpm: int = Field(
        default=60, ge=1, le=1000, description="Rate limit in requests per minute"
    )

    enable_caching: bool = Field(
        default=True, description="Enable intelligent response caching"
    )

    cache_ttl: int = Field(
        default=3600, ge=300, le=86400, description="Cache TTL in seconds"
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key format."""
        if not v or v.strip() == "":
            raise ValueError("SambaNova API key cannot be empty")
        if v.startswith("your_api_key") or v == "placeholder":
            raise ValueError("Please provide a valid SambaNova API key")
        return v.strip()

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v):
        """Validate API endpoint URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint must be a valid HTTP/HTTPS URL")
        return v.rstrip("/")

    model_config = ConfigDict(env_prefix="SAMBANOVA_", case_sensitive=False)


class SambaNovaConfigManager:
    """
    Configuration manager for SambaNova integration.
    Handles loading from environment, validation, and integration with existing config system.
    """

    def __init__(self):
        self._config: Optional[SambaNovaConfig] = None
        self._logger = logging.getLogger(__name__)

    @classmethod
    def from_environment(cls) -> "SambaNovaConfigManager":
        """
        Create configuration manager loading from environment variables.

        Expected environment variables:
        - SAMBANOVA_API_KEY: Required SambaNova API key
        - SAMBANOVA_MODEL: Model identifier (optional, defaults to e5-mistral-7b-instruct)
        - SAMBANOVA_ENDPOINT: API endpoint (optional, defaults to https://api.sambanova.ai/v1)
        - SAMBANOVA_MAX_TOKENS: Maximum tokens (optional, defaults to 2048)
        - SAMBANOVA_TEMPERATURE: Model temperature (optional, defaults to 0.1)
        - SAMBANOVA_TIMEOUT: Request timeout (optional, defaults to 30)
        - SAMBANOVA_MAX_RETRIES: Max retry attempts (optional, defaults to 3)
        - SAMBANOVA_RATE_LIMIT_RPM: Rate limit RPM (optional, defaults to 60)
        - SAMBANOVA_ENABLE_CACHING: Enable caching (optional, defaults to True)
        - SAMBANOVA_CACHE_TTL: Cache TTL seconds (optional, defaults to 3600)
        """
        manager = cls()

        try:
            # Load configuration from environment with defaults
            config_data = {
                "api_key": os.getenv("SAMBANOVA_API_KEY", ""),
                "model": os.getenv("SAMBANOVA_MODEL", SambaNovaModel.DEFAULT.value),
                "endpoint": os.getenv(
                    "SAMBANOVA_ENDPOINT", "https://api.sambanova.ai/v1"
                ),
                "max_tokens": int(os.getenv("SAMBANOVA_MAX_TOKENS", "2048")),
                "temperature": float(os.getenv("SAMBANOVA_TEMPERATURE", "0.1")),
                "timeout": int(os.getenv("SAMBANOVA_TIMEOUT", "30")),
                "max_retries": int(os.getenv("SAMBANOVA_MAX_RETRIES", "3")),
                "rate_limit_rpm": int(os.getenv("SAMBANOVA_RATE_LIMIT_RPM", "60")),
                "enable_caching": os.getenv("SAMBANOVA_ENABLE_CACHING", "true").lower()
                == "true",
                "cache_ttl": int(os.getenv("SAMBANOVA_CACHE_TTL", "3600")),
            }

            manager._config = SambaNovaConfig(**config_data)
            manager._logger.info(
                f"SambaNova configuration loaded successfully with model: {manager._config.model}"
            )

        except Exception as e:
            manager._logger.error(f"Failed to load SambaNova configuration: {e}")
            raise ValueError(f"Invalid SambaNova configuration: {e}")

        return manager

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "SambaNovaConfigManager":
        """Create configuration manager from dictionary (for integration with existing config system)."""
        manager = cls()
        try:
            manager._config = SambaNovaConfig(**config_dict)
            manager._logger.info("SambaNova configuration loaded from dictionary")
        except Exception as e:
            manager._logger.error(
                f"Failed to create SambaNova configuration from dict: {e}"
            )
            raise ValueError(f"Invalid SambaNova configuration: {e}")

        return manager

    @property
    def config(self) -> SambaNovaConfig:
        """Get validated configuration."""
        if self._config is None:
            raise RuntimeError(
                "Configuration not loaded. Call from_environment() or from_dict() first."
            )
        return self._config

    def validate_api_connectivity(self) -> bool:
        """
        Validate API connectivity and credentials.
        This will be implemented in the SambaNovaInterface.
        """
        # Placeholder for API connectivity test
        # Will be implemented in Task #AI002
        return True

    def get_prompt_config(self) -> Dict[str, Any]:
        """Get configuration optimized for prompt engineering."""
        return {
            "model": self.config.model.value,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": 0.9,  # For consistent task extraction
            "frequency_penalty": 0.1,  # Reduce repetition
            "presence_penalty": 0.1,  # Encourage diverse analysis
        }

    def get_api_config(self) -> Dict[str, Any]:
        """Get configuration for API client initialization."""
        return {
            "api_key": self.config.api_key,
            "endpoint": self.config.endpoint,
            "timeout": self.config.timeout,
            "max_retries": self.config.max_retries,
            "rate_limit_rpm": self.config.rate_limit_rpm,
        }

    def get_cache_config(self) -> Dict[str, Any]:
        """Get configuration for caching system."""
        return {
            "enabled": self.config.enable_caching,
            "ttl": self.config.cache_ttl,
            "max_size": 1000,  # Maximum cached responses
        }


# Global configuration instance
_config_manager: Optional[SambaNovaConfigManager] = None


def get_sambanova_config() -> SambaNovaConfigManager:
    """
    Get global SambaNova configuration manager.
    Initializes from environment on first call.
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = SambaNovaConfigManager.from_environment()
    return _config_manager


def initialize_sambanova_config(
    config_dict: Optional[Dict[str, Any]] = None,
) -> SambaNovaConfigManager:
    """
    Initialize SambaNova configuration.

    Args:
        config_dict: Optional configuration dictionary. If None, loads from environment.

    Returns:
        Initialized configuration manager.
    """
    global _config_manager

    if config_dict:
        _config_manager = SambaNovaConfigManager.from_dict(config_dict)
    else:
        _config_manager = SambaNovaConfigManager.from_environment()

    return _config_manager


# Configuration validation utilities
def validate_sambanova_setup() -> bool:
    """
    Validate that SambaNova is properly configured.

    Returns:
        True if configuration is valid and API is accessible.
    """
    try:
        config_manager = get_sambanova_config()
        return config_manager.validate_api_connectivity()
    except Exception as e:
        logger.error(f"SambaNova setup validation failed: {e}")
        return False


# Example usage and configuration template
EXAMPLE_ENV_CONFIG = """
# SambaNova AI Configuration
SAMBANOVA_API_KEY=your_actual_api_key_here
SAMBANOVA_MODEL=e5-mistral-7b-instruct
SAMBANOVA_ENDPOINT=https://api.sambanova.ai/v1
SAMBANOVA_MAX_TOKENS=2048
SAMBANOVA_TEMPERATURE=0.1
SAMBANOVA_TIMEOUT=30
SAMBANOVA_MAX_RETRIES=3
SAMBANOVA_RATE_LIMIT_RPM=60
SAMBANOVA_ENABLE_CACHING=true
SAMBANOVA_CACHE_TTL=3600
"""

if __name__ == "__main__":
    # Test configuration loading
    try:
        config = get_sambanova_config()
        print(f"✅ SambaNova configuration loaded successfully")
        print(f"   Model: {config.config.model}")
        print(f"   Endpoint: {config.config.endpoint}")
        print(
            f"   Caching: {'Enabled' if config.config.enable_caching else 'Disabled'}"
        )
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("\nExample .env configuration:")
        print(EXAMPLE_ENV_CONFIG)
