#!/usr/bin/env python3
"""
Comprehensive tests for the logging system
"""
import json
import logging
import logging.handlers
import sys
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.extraction import ExtractedMetadata
from src.logging_system import (
    ColoredFormatter,
    EmailProcessingLogger,
    JSONFormatter,
    log_performance,
)
from src.logging_system import logger as global_logger
from src.models import EmailAnalysis, EmailData, ProcessedEmail


class TestJSONFormatter:
    """Test JSON formatter functionality"""

    def setup_method(self):
        self.formatter = JSONFormatter()

    def test_basic_format(self):
        """Test basic JSON formatting"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert parsed["message"] == "Test message"
        assert parsed["module"] == "test"
        assert parsed["line"] == 10

    def test_format_with_exception(self):
        """Test JSON formatting with exception info"""
        try:
            raise ValueError("Test error")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=20,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        formatted = self.formatter.format(record)
        parsed = json.loads(formatted)

        assert "exception" in parsed
        assert "ValueError: Test error" in parsed["exception"]

    def test_format_with_extra_fields(self):
        """Test JSON formatting with extra fields"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=30,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"user_id": "123", "action": "login"}

        formatted = self.formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["user_id"] == "123"
        assert parsed["action"] == "login"

    def test_format_with_additional_attributes(self):
        """Test JSON formatting with additional custom attributes"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=40,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.custom_field = "custom_value"

        formatted = self.formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["custom_field"] == "custom_value"


class TestColoredFormatter:
    """Test colored formatter functionality"""

    def setup_method(self):
        self.formatter = ColoredFormatter(
            "%(levelname_color)s%(levelname)s - %(message)s"
        )

    def test_format_with_colors(self):
        """Test colored formatting adds color codes"""
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)
        assert "\033[31m" in formatted  # Red color for ERROR
        assert "ERROR" in formatted

    def test_format_unknown_level(self):
        """Test formatting with unknown log level"""
        record = logging.LogRecord(
            name="test",
            level=99,  # Unknown level
            pathname="test.py",
            lineno=10,
            msg="Custom message",
            args=(),
            exc_info=None,
        )
        record.levelname = "CUSTOM"

        formatted = self.formatter.format(record)
        assert "CUSTOM" in formatted


class TestEmailProcessingLogger:
    """Test EmailProcessingLogger functionality"""

    def setup_method(self):
        # Clear any existing handlers
        logging.getLogger("test-logger").handlers.clear()
        self.logger = EmailProcessingLogger("test-logger")

    def test_init_with_default_name(self):
        """Test logger initialization with default name"""
        logger = EmailProcessingLogger()
        assert logger.logger.name == "inbox-zen"

    def test_init_with_custom_name(self):
        """Test logger initialization with custom name"""
        logger = EmailProcessingLogger("custom-logger")
        assert logger.logger.name == "custom-logger"

    @patch("config.config")
    def test_setup_logging_with_config(self, mock_config):
        """Test logging setup with config"""
        mock_config.log_level = "DEBUG"
        mock_config.log_format = "json"
        mock_config.enable_console_colors = False

        logger = EmailProcessingLogger("test-config")
        assert logger.logger.level == logging.DEBUG

    @patch("src.logging_system.sys.modules")
    def test_setup_logging_without_config(self, mock_modules):
        """Test logging setup without config (fallback)"""
        # Mock the config module to not exist
        mock_modules.__contains__.return_value = False
        with patch(
            "src.logging_system.importlib.import_module", side_effect=ImportError
        ):
            logger = EmailProcessingLogger("test-fallback")
            assert logger.logger.level == logging.INFO

    @patch("src.logging_system.sys.modules")
    def test_setup_file_logging_enabled(self, mock_modules):
        """Test file logging setup when enabled"""
        mock_modules.__contains__.return_value = False
        with patch(
            "src.logging_system.importlib.import_module", side_effect=ImportError
        ):
            with tempfile.TemporaryDirectory():
                logger = EmailProcessingLogger("test-file")
                # Just test that it doesn't crash
                logger.setup_file_logging()

    @patch("src.logging_system.sys.modules")
    def test_setup_file_logging_disabled(self, mock_modules):
        """Test file logging setup when disabled"""
        mock_modules.__contains__.return_value = False
        with patch(
            "src.logging_system.importlib.import_module", side_effect=ImportError
        ):
            logger = EmailProcessingLogger("test-no-file")
            logger.setup_file_logging()

    @patch("src.logging_system.sys.modules")
    def test_setup_file_logging_without_config(self, mock_modules):
        """Test file logging setup without config (fallback)"""
        mock_modules.__contains__.return_value = False
        with patch(
            "src.logging_system.importlib.import_module", side_effect=ImportError
        ):
            logger = EmailProcessingLogger("test-no-config")
            logger.setup_file_logging()  # Should not raise exception

    @patch("src.logging_system.sys.modules")
    def test_setup_file_logging_error(self, mock_modules):
        """Test file logging setup with error"""
        mock_modules.__contains__.return_value = False
        with patch(
            "src.logging_system.importlib.import_module", side_effect=ImportError
        ):
            logger = EmailProcessingLogger("test-error")
            # Should handle the error gracefully
            logger.setup_file_logging()

    def test_log_email_received(self):
        """Test email received logging"""
        email_data = EmailData(
            message_id="test-123",
            from_email="sender@example.com",
            subject="Test Subject",
            to_emails=["recipient@example.com"],
            cc_emails=["cc@example.com"],
            attachments=[],
            text_body="Test body",
            html_body="<p>Test body</p>",
            received_at=datetime.now(),
        )

        with patch.object(self.logger.logger, "info") as mock_info:
            self.logger.log_email_received(email_data, {})
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "Email received via webhook" in call_args[0][0]
            assert call_args[1]["extra"]["message_id"] == "test-123"

    def test_log_extraction_start(self):
        """Test extraction start logging"""
        email_data = EmailData(
            message_id="test-456",
            from_email="sender@example.com",
            subject="Test Subject",
            to_emails=["recipient@example.com"],
            text_body="Test content",
            html_body="<p>Test content</p>",
            received_at=datetime.now(),
        )

        with patch.object(self.logger.logger, "info") as mock_info:
            self.logger.log_extraction_start(email_data)
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "Starting content extraction" in call_args[0][0]

    def test_log_extraction_complete(self):
        """Test extraction complete logging"""
        email_data = EmailData(
            message_id="test-789",
            from_email="sender@example.com",
            subject="Test Subject",
            to_emails=["recipient@example.com"],
            received_at=datetime.now(),
        )

        metadata = ExtractedMetadata(
            urgency_indicators=["urgent", "important"],
            temporal_references=["tomorrow", "next week"],
            contact_info={"email": ["contact@example.com"], "phone": [], "url": []},
            links=["http://example.com"],
            action_words=["review", "approve"],
            sentiment_indicators=["positive"],
            priority_keywords=["urgent", "important"],
        )

        with patch.object(self.logger.logger, "info") as mock_info:
            self.logger.log_extraction_complete(email_data, metadata, 8, "positive")
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "Content extraction completed" in call_args[0][0]
            assert call_args[1]["extra"]["urgency_score"] == 8
            assert call_args[1]["extra"]["sentiment"] == "positive"

    def test_log_email_processed(self):
        """Test email processed logging"""
        email_data = EmailData(
            message_id="test-processed",
            from_email="sender@example.com",
            subject="Test Subject",
            to_emails=["recipient@example.com"],
            received_at=datetime.now(),
        )

        analysis = EmailAnalysis(
            urgency_score=7, urgency_level="high", sentiment="neutral", confidence=0.8
        )

        processed_email = ProcessedEmail(
            id="processed-123",
            email_data=email_data,
            analysis=analysis,
            status="analyzed",
        )

        with patch.object(self.logger.logger, "info") as mock_info:
            self.logger.log_email_processed(processed_email, 0.5)
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "Email processing completed successfully" in call_args[0][0]
            assert call_args[1]["extra"]["processing_time_ms"] == 500.0

    def test_log_email_processed_without_analysis(self):
        """Test email processed logging without analysis"""
        email_data = EmailData(
            message_id="test-no-analysis",
            from_email="sender@example.com",
            subject="Test Subject",
            to_emails=["recipient@example.com"],
            received_at=datetime.now(),
        )

        processed_email = ProcessedEmail(
            id="processed-456", email_data=email_data, analysis=None, status="received"
        )

        with patch.object(self.logger.logger, "info") as mock_info:
            self.logger.log_email_processed(processed_email, 0.3)
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert call_args[1]["extra"]["urgency_score"] is None
            assert call_args[1]["extra"]["urgency_level"] is None
            assert call_args[1]["extra"]["sentiment"] is None

    def test_log_processing_error(self):
        """Test processing error logging"""
        error = ValueError("Test processing error")
        context = {"message_id": "error-123", "step": "extraction"}

        with patch.object(self.logger.logger, "error") as mock_error:
            self.logger.log_processing_error(error, context)
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            assert "Processing error: Test processing error" in call_args[0][0]
            assert call_args[1]["extra"]["error_type"] == "ValueError"
            assert call_args[1]["extra"]["message_id"] == "error-123"

    def test_log_webhook_validation_error(self):
        """Test webhook validation error logging"""
        error_msg = "Invalid payload format"
        payload = {"invalid": "data"}

        with patch.object(self.logger.logger, "warning") as mock_warning:
            self.logger.log_webhook_validation_error(error_msg, payload)
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            assert (
                "Webhook validation failed: Invalid payload format" in call_args[0][0]
            )
            assert call_args[1]["extra"]["payload_keys"] == ["invalid"]

    def test_log_webhook_validation_error_empty_payload(self):
        """Test webhook validation error logging with empty payload"""
        error_msg = "Empty payload"

        with patch.object(self.logger.logger, "warning") as mock_warning:
            self.logger.log_webhook_validation_error(error_msg, None)
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            assert call_args[1]["extra"]["payload_keys"] == []
            assert call_args[1]["extra"]["payload_size"] == 0

    def test_log_mcp_request(self):
        """Test MCP request logging"""
        params = {"query": "test search"}

        with patch.object(self.logger.logger, "debug") as mock_debug:
            self.logger.log_mcp_request("search_emails", params)
            mock_debug.assert_called_once()
            call_args = mock_debug.call_args
            assert "MCP request: search_emails" in call_args[0][0]
            assert call_args[1]["extra"]["params"] == params

    def test_log_mcp_request_no_params(self):
        """Test MCP request logging without parameters"""
        with patch.object(self.logger.logger, "debug") as mock_debug:
            self.logger.log_mcp_request("list_emails")
            mock_debug.assert_called_once()
            call_args = mock_debug.call_args
            assert call_args[1]["extra"]["params"] == {}

    def test_log_mcp_response(self):
        """Test MCP response logging"""
        with patch.object(self.logger.logger, "debug") as mock_debug:
            self.logger.log_mcp_response("search_emails", 1024, 0.15)
            mock_debug.assert_called_once()
            call_args = mock_debug.call_args
            assert "MCP response: search_emails" in call_args[0][0]
            assert call_args[1]["extra"]["response_size"] == 1024
            assert call_args[1]["extra"]["execution_time_ms"] == 150.0

    def test_log_performance_metrics(self):
        """Test performance metrics logging"""
        metrics = {"cpu_usage": 45.2, "memory_usage": 67.8}

        with patch.object(self.logger.logger, "info") as mock_info:
            self.logger.log_performance_metrics(metrics)
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "Performance metrics" in call_args[0][0]
            assert call_args[1]["extra"]["cpu_usage"] == 45.2

    def test_log_system_stats(self):
        """Test system statistics logging"""
        mock_stats = Mock()
        mock_stats.total_processed = 100
        mock_stats.total_errors = 5
        mock_stats.avg_urgency_score = 6.5
        mock_stats.last_processed = datetime.now()
        mock_stats.processing_times = [0.1, 0.2, 0.3]

        # Mock the storage import to avoid import errors
        with patch("src.logging_system.storage", create=True):
            with patch.object(self.logger.logger, "info") as mock_info:
                self.logger.log_system_stats(mock_stats)
                mock_info.assert_called_once()
                call_args = mock_info.call_args
                assert "System statistics" in call_args[0][0]
                assert call_args[1]["extra"]["total_processed"] == 100

    def test_log_system_stats_no_last_processed(self):
        """Test system statistics logging without last processed date"""
        mock_stats = Mock()
        mock_stats.total_processed = 50
        mock_stats.total_errors = 2
        mock_stats.avg_urgency_score = 5.0
        mock_stats.last_processed = None
        mock_stats.processing_times = []

        # Mock the storage import to avoid import errors
        with patch("src.logging_system.storage", create=True):
            with patch.object(self.logger.logger, "info") as mock_info:
                self.logger.log_system_stats(mock_stats)
                mock_info.assert_called_once()
                call_args = mock_info.call_args
                assert call_args[1]["extra"]["last_processed"] is None

    def test_delegation_methods(self):
        """Test delegation methods for standard logging interface"""
        with patch.object(self.logger.logger, "warning") as mock_warning:
            self.logger.warning("Test warning")
            mock_warning.assert_called_once_with("Test warning")

        with patch.object(self.logger.logger, "info") as mock_info:
            self.logger.info("Test info")
            mock_info.assert_called_once_with("Test info")

        with patch.object(self.logger.logger, "error") as mock_error:
            self.logger.error("Test error")
            mock_error.assert_called_once_with("Test error")

        with patch.object(self.logger.logger, "debug") as mock_debug:
            self.logger.debug("Test debug")
            mock_debug.assert_called_once_with("Test debug")

        with patch.object(self.logger.logger, "critical") as mock_critical:
            self.logger.critical("Test critical")
            mock_critical.assert_called_once_with("Test critical")


class TestLogPerformanceDecorator:
    """Test performance logging decorator"""

    def setup_method(self):
        self.logger = EmailProcessingLogger("test-perf")

    def test_performance_decorator_success(self):
        """Test performance decorator on successful function"""

        @log_performance(self.logger)
        def test_function(x, y):
            return x + y

        with patch.object(self.logger, "log_performance_metrics") as mock_log:
            result = test_function(1, 2)
            assert result == 3
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert call_args["function"] == "test_function"
            assert call_args["success"] is True
            assert "execution_time_ms" in call_args

    def test_performance_decorator_error(self):
        """Test performance decorator on function that raises exception"""

        @log_performance(self.logger)
        def failing_function():
            raise ValueError("Test error")

        with patch.object(self.logger, "log_performance_metrics") as mock_log:
            with pytest.raises(ValueError):
                failing_function()

            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert call_args["function"] == "failing_function"
            assert call_args["success"] is False
            assert call_args["error"] == "Test error"


class TestGlobalLogger:
    """Test global logger instance"""

    def test_global_logger_instance(self):
        """Test that global logger is properly initialized"""
        assert global_logger is not None
        assert isinstance(global_logger, EmailProcessingLogger)
        assert global_logger.logger.name == "inbox-zen"

    def test_global_logger_functionality(self):
        """Test global logger functionality"""
        with patch.object(global_logger.logger, "info") as mock_info:
            global_logger.info("Test global logging")
            mock_info.assert_called_once_with("Test global logging")
