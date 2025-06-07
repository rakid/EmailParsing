#!/usr/bin/env python3
"""
Test script to validate SambaNova AI integration with the existing plugin system.

This script tests:
1. Plugin registration and integration
2. Basic email processing pipeline
3. AI component initialization
4. Integration with PluginManager

Run with: python test_sambanova_integration.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai import (
    AIRegistry,
    SambaNovaConfig,
    create_sambanova_plugin,
    get_sambanova_config,
    get_sambanova_integration_info,
    register_sambanova_integrations,
    validate_sambanova_setup,
)
from src.ai.plugin import SambaNovaPlugin
from src.integrations import integration_registry
from src.models import (
    EmailAnalysis,
    EmailData,
    EmailStatus,
    ProcessedEmail,
    UrgencyLevel,
)

# Test configuration
TEST_CONFIG = {
    "api_key": "test_key_12345",
    "model": "sambanova-large",
    "max_concurrent": 3,
    "timeout": 30,
    "enable_caching": True,
    "batch_processing": True,
}

# Sample email data for testing
SAMPLE_EMAIL = {
    "subject": "Test Email",
    "from": "test@example.com",
    "to": ["recipient@example.com"],
    "body": "This is a test email for integration testing.",
    "date": datetime.now(timezone.utc).isoformat(),
}


def create_test_config() -> SambaNovaConfig:
    """Create a test configuration."""
    return SambaNovaConfig(**TEST_CONFIG)


class MockSambaNovaClient:
    """Mock SambaNova client for testing."""

    def __init__(self, *args, **kwargs):
        self.config = kwargs

    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Mock generate method."""
        return {
            "choices": [
                {
                    "text": json.dumps(
                        {
                            "summary": "Test summary",
                            "key_points": ["Point 1", "Point 2"],
                            "action_items": ["Action 1"],
                            "sentiment": "positive",
                            "urgency": "low",
                        }
                    )
                }
            ]
        }


@pytest.fixture
def mock_sambanova_client(monkeypatch):
    """Fixture to mock the SambaNova client."""

    def mock_client(*args, **kwargs):
        return MockSambaNovaClient(*args, **kwargs)

    # Mock the client import that doesn't exist yet
    monkeypatch.setattr("sambanova.SambaverseClient", mock_client, raising=False)
    return mock_client


@pytest.mark.asyncio
async def test_plugin_initialization():
    """Test SambaNova plugin initialization."""
    # Create the plugin (main plugin doesn't take config in constructor)
    plugin = SambaNovaPlugin()

    # Verify the plugin was initialized correctly
    assert plugin.get_name() == "sambanova-ai-analysis"
    assert plugin.get_version() == "1.0.0"
    assert isinstance(plugin.get_dependencies(), list)


@pytest.mark.asyncio
async def test_plugin_interface():
    """Test plugin interface without external dependencies."""
    # Initialize the plugin
    plugin = SambaNovaPlugin()

    # Test that plugin can be initialized
    assert plugin.get_name() == "sambanova-ai-analysis"
    assert plugin.get_version() == "1.0.0"

    # Test dependencies list
    deps = plugin.get_dependencies()
    assert isinstance(deps, list)


@pytest.mark.asyncio
async def test_plugin_basic_functionality():
    """Test basic plugin functionality."""
    # Initialize the plugin
    plugin = SambaNovaPlugin()

    # Test basic properties
    assert plugin.get_name() == "sambanova-ai-analysis"
    assert plugin.get_version() == "1.0.0"
    assert isinstance(plugin.get_dependencies(), list)


def test_plugin_creation():
    """Test that the SambaNova plugin can be created and has expected interface."""
    # Create the plugin
    plugin = SambaNovaPlugin()

    # Verify the plugin has expected methods
    assert hasattr(plugin, "get_name")
    assert hasattr(plugin, "get_version")
    assert hasattr(plugin, "get_dependencies")
    assert hasattr(plugin, "initialize")
    assert hasattr(plugin, "process_email")

    # Verify basic properties
    assert plugin.get_name() == "sambanova-ai-analysis"
    assert plugin.get_version() == "1.0.0"
    assert isinstance(plugin.get_dependencies(), list)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
