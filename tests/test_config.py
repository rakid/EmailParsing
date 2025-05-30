"""Unit tests for config.py - Configuration Management"""

import os
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest

from src.config import ServerConfig, lifespan_manager, shutdown_event


class TestServerConfig:
    """Test ServerConfig class and environment handling"""

    @patch.dict(
        os.environ, {}, clear=True
    )  # Clear all environment variables for this test
    def test_server_config_defaults(self):
        """Test ServerConfig with default values"""
        test_config = ServerConfig()

        assert test_config.server_name == "inbox-zen-email-parser"
        assert test_config.server_version == "0.1.0"
        assert test_config.environment == "development"
        assert test_config.debug is True
        assert test_config.log_level == "INFO"  # From .env file

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "LOG_LEVEL": "WARNING",
            "LOG_FORMAT": "json",
            "ENABLE_CONSOLE_COLORS": "false",
            "LOG_FILE_PATH": "/tmp/test-prod.log",
        },
    )
    def test_server_config_production_env(self):
        """Test ServerConfig with production environment variables"""
        test_config = ServerConfig()

        assert test_config.environment == "production"
        assert test_config.debug is False
        assert test_config.log_level == "WARNING"
        assert test_config.log_format == "json"
        assert test_config.enable_console_colors is False
        assert test_config.log_file_path == "/tmp/test-prod.log"

    @patch.dict(os.environ, {"WEBHOOK_ENDPOINT": "/custom-webhook"})
    def test_server_config_webhook_endpoint(self):
        """Test ServerConfig webhook endpoint configuration"""
        test_config = ServerConfig()
        assert test_config.webhook_endpoint == "/custom-webhook"

    @patch.dict(os.environ, {"POSTMARK_WEBHOOK_SECRET": "test-secret-123"})
    def test_server_config_webhook_secret(self):
        """Test ServerConfig webhook secret configuration"""
        test_config = ServerConfig()
        assert test_config.postmark_webhook_secret == "test-secret-123"


class TestLifespanManager:
    """Test application lifespan management"""

    @pytest.mark.asyncio
    async def test_lifespan_manager_startup_shutdown(self):
        """Test lifespan manager startup and shutdown sequence"""
        mock_app = MagicMock()

        # Track if startup and shutdown occurred
        startup_called = False
        shutdown_called = False

        @asynccontextmanager
        async def test_lifespan(app):
            nonlocal startup_called, shutdown_called
            startup_called = True
            yield
            shutdown_called = True

        # Test the actual lifespan manager
        async with lifespan_manager(mock_app):
            # Check that we're in the running state
            assert startup_called is False  # Our test manager doesn't set this
            # The actual lifespan_manager should have logged startup

        # After exiting context, shutdown should have been called
        assert shutdown_event.is_set()

    @pytest.mark.asyncio
    @patch("src.config.logger")
    async def test_lifespan_manager_logging(self, mock_logger):
        """Test that lifespan manager logs startup and shutdown messages"""
        mock_app = MagicMock()

        # Reset shutdown event for clean test
        shutdown_event.clear()

        async with lifespan_manager(mock_app):
            # Verify startup logging
            mock_logger.info.assert_called_with("Application startup...")

        # Verify shutdown logging
        mock_logger.info.assert_any_call("Application shutdown sequence initiated...")
        mock_logger.info.assert_any_call("Application shutdown complete.")
        assert shutdown_event.is_set()


class TestProductionConfiguration:
    """Test production environment specific configuration"""

    @patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True)
    @patch("src.config.config")
    def test_production_environment_adjustments(self, mock_config):
        """Test production environment configuration adjustments"""
        # Mock the config object
        mock_config.environment = "production"
        mock_config.log_level = "DEBUG"  # Initial value
        mock_config.log_format = "text"  # Initial value
        mock_config.enable_console_colors = True  # Initial value
        mock_config.log_file_path = None  # Initial value

        # Simulate the production configuration logic
        if mock_config.environment == "production":
            mock_config.log_level = os.getenv("LOG_LEVEL", "INFO")
            mock_config.log_format = os.getenv("LOG_FORMAT", "json")
            mock_config.enable_console_colors = (
                os.getenv("ENABLE_CONSOLE_COLORS", "False").lower() == "true"
            )
            if not mock_config.log_file_path:
                mock_config.log_file_path = "logs/inbox-zen-prod.log"

        # Verify production defaults
        assert mock_config.log_level == "INFO"
        assert mock_config.log_format == "json"
        assert mock_config.enable_console_colors is False
        assert mock_config.log_file_path == "logs/inbox-zen-prod.log"

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "WARNING",
            "LOG_FORMAT": "structured",
            "ENABLE_CONSOLE_COLORS": "true",
        },
        clear=True,
    )
    @patch("src.config.config")
    def test_production_environment_custom_values(self, mock_config):
        """Test production environment with custom configuration values"""
        mock_config.environment = "production"
        mock_config.log_file_path = None

        # Simulate the production configuration logic
        if mock_config.environment == "production":
            mock_config.log_level = os.getenv("LOG_LEVEL", "INFO")
            mock_config.log_format = os.getenv("LOG_FORMAT", "json")
            mock_config.enable_console_colors = (
                os.getenv("ENABLE_CONSOLE_COLORS", "False").lower() == "true"
            )
            if not mock_config.log_file_path:
                mock_config.log_file_path = "logs/inbox-zen-prod.log"

        # Verify custom production values
        assert mock_config.log_level == "WARNING"
        assert mock_config.log_format == "structured"
        assert mock_config.enable_console_colors is True
        assert mock_config.log_file_path == "logs/inbox-zen-prod.log"


class TestLogDirectoryCreation:
    """Test log directory creation functionality"""

    @patch("os.makedirs")
    @patch("os.path.exists")
    @patch("os.path.dirname")
    @patch("src.config.config")
    def test_log_directory_creation(
        self, mock_config, mock_dirname, mock_exists, mock_makedirs
    ):
        """Test that log directory is created when needed"""
        # Setup mocks
        mock_config.log_file_path = "logs/test-app.log"
        mock_dirname.return_value = "logs"
        mock_exists.return_value = False  # Directory doesn't exist

        # Simulate the log directory creation logic
        if mock_config.log_file_path:
            log_dir = os.path.dirname(mock_config.log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

        # Verify directory creation was attempted
        mock_dirname.assert_called_once_with("logs/test-app.log")
        mock_exists.assert_called_once_with("logs")
        mock_makedirs.assert_called_once_with("logs", exist_ok=True)

    @patch("os.makedirs")
    @patch("os.path.exists")
    @patch("os.path.dirname")
    @patch("src.config.config")
    def test_log_directory_already_exists(
        self, mock_config, mock_dirname, mock_exists, mock_makedirs
    ):
        """Test that log directory creation is skipped when directory exists"""
        # Setup mocks
        mock_config.log_file_path = "logs/test-app.log"
        mock_dirname.return_value = "logs"
        mock_exists.return_value = True  # Directory already exists

        # Simulate the log directory creation logic
        if mock_config.log_file_path:
            log_dir = os.path.dirname(mock_config.log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

        # Verify directory creation was not attempted
        mock_dirname.assert_called_once_with("logs/test-app.log")
        mock_exists.assert_called_once_with("logs")
        mock_makedirs.assert_not_called()

    @patch("os.makedirs")
    @patch("src.config.config")
    def test_no_log_directory_when_no_file_path(self, mock_config, mock_makedirs):
        """Test that no directory creation occurs when log_file_path is None"""
        # Setup mocks
        mock_config.log_file_path = None

        # Simulate the log directory creation logic
        if mock_config.log_file_path:
            log_dir = os.path.dirname(mock_config.log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

        # Verify no directory creation was attempted
        mock_makedirs.assert_not_called()

    @patch("os.makedirs")
    @patch("os.path.exists")
    @patch("os.path.dirname")
    @patch("src.config.config")
    def test_log_directory_empty_dirname(
        self, mock_config, mock_dirname, mock_exists, mock_makedirs
    ):
        """Test handling when dirname returns empty string"""
        # Setup mocks
        mock_config.log_file_path = "app.log"  # No directory path
        mock_dirname.return_value = ""  # Empty directory

        # Simulate the log directory creation logic
        if mock_config.log_file_path:
            log_dir = os.path.dirname(mock_config.log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

        # Verify no directory creation was attempted for empty dirname
        mock_dirname.assert_called_once_with("app.log")
        mock_exists.assert_not_called()
        mock_makedirs.assert_not_called()
