#!/usr/bin/env python3
"""
Comprehensive Logging System for Inbox Zen MCP Server
Provides structured, configurable logging for all components
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""

        # Base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from log call
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        # Add any additional attributes that were passed in extra parameter
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "extra_fields",
                "message",
                "asctime",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


class EmailProcessingLogger:
    """Specialized logger for email processing operations"""

    def __init__(self, name: str = "inbox-zen"):
        self.logger = logging.getLogger(name)
        self.setup_logging()

    def setup_logging(self):
        """Configure logging based on config settings"""
        try:
            from config import config

            log_level = config.log_level.upper()
            log_format = config.log_format.lower()
            enable_colors = config.enable_console_colors
        except ImportError:
            # Fallback configuration for testing
            log_level = "INFO"
            log_format = "standard"
            enable_colors = True

        # Set logging level
        level = getattr(logging, log_level, logging.INFO)
        self.logger.setLevel(level)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)

        if log_format == "json":
            console_handler.setFormatter(JSONFormatter())
        else:
            # Standard format with colors if enabled
            if enable_colors:
                format_string = (
                    "\033[36m%(asctime)s\033[0m - "  # Cyan timestamp
                    "\033[35m%(name)s\033[0m - "  # Magenta logger name
                    # Colored level
                    "%(levelname_color)s%(levelname)s\033[0m - "
                    "%(message)s"
                )
            else:
                format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

            console_handler.setFormatter(ColoredFormatter(format_string))

        self.logger.addHandler(console_handler)

        # File handler (optional)
        self.setup_file_logging()

    def setup_file_logging(self):
        """Setup file logging if configured"""
        try:
            from config import config

            if config.log_file_path:
                # Ensure log directory exists
                log_dir = Path(config.log_file_path).parent
                log_dir.mkdir(parents=True, exist_ok=True)

                file_handler = logging.handlers.RotatingFileHandler(
                    config.log_file_path,
                    maxBytes=config.log_file_max_bytes,
                    backupCount=config.log_file_backup_count,
                )

                # Use JSON formatter for file logs in production, or as
                # configured
                if config.environment == "production" or config.log_format == "json":
                    file_handler.setFormatter(JSONFormatter())
                else:
                    # Standard text format for file logs in dev if not json
                    format_string = (
                        "%(asctime)s - %(name)s - %(levelname)s - "
                        "%(module)s:%(funcName)s:%(lineno)d - %(message)s"
                    )
                    file_handler.setFormatter(logging.Formatter(format_string))

                file_handler.setLevel(self.logger.level)
                self.logger.addHandler(file_handler)
                self.logger.info(
                    f"File logging enabled: {
                        config.log_file_path}"
                )
        except ImportError:
            # Config not available, skip file logging
            pass
        except Exception as e:
            self.logger.error(f"Failed to setup file logging: {e}", exc_info=True)

    def log_email_received(self, email_data, webhook_payload: Dict[str, Any]):
        """Log email reception"""
        self.logger.info(
            "Email received via webhook",
            extra={
                "event_type": "email_received",
                "message_id": email_data.message_id,
                "from_email": email_data.from_email,
                "subject": email_data.subject,
                "to_count": len(email_data.to_emails),
                "cc_count": len(email_data.cc_emails),
                "attachment_count": len(email_data.attachments),
                "text_body_length": len(email_data.text_body or ""),
                "html_body_length": len(email_data.html_body or ""),
                "webhook_source": "postmark",
            },
        )

    def log_extraction_start(self, email_data):
        """Log start of content extraction"""
        self.logger.info(
            "Starting content extraction",
            extra={
                "event_type": "extraction_start",
                "message_id": email_data.message_id,
                "content_length": len(
                    (email_data.text_body or "") + (email_data.html_body or "")
                ),
            },
        )

    def log_extraction_complete(
        self, email_data, extracted_metadata, urgency_score: int, sentiment: str
    ):
        """Log completion of content extraction"""
        self.logger.info(
            "Content extraction completed",
            extra={
                "event_type": "extraction_complete",
                "message_id": email_data.message_id,
                "urgency_score": urgency_score,
                "sentiment": sentiment,
                "keywords_count": len(extracted_metadata.priority_keywords),
                "action_items_count": len(extracted_metadata.action_words),
                "temporal_refs_count": len(extracted_metadata.temporal_references),
                "contact_info": {
                    "emails": len(extracted_metadata.contact_info.get("email", [])),
                    "phones": len(extracted_metadata.contact_info.get("phone", [])),
                    "urls": len(extracted_metadata.contact_info.get("url", [])),
                },
            },
        )

    def log_email_processed(self, processed_email, processing_time: float):
        """Log successful email processing"""
        self.logger.info(
            "Email processing completed successfully",
            extra={
                "event_type": "email_processed",
                "processing_id": processed_email.id,
                "message_id": processed_email.email_data.message_id,
                "processing_time_ms": round(processing_time * 1000, 2),
                "urgency_score": (
                    processed_email.analysis.urgency_score
                    if processed_email.analysis
                    else None
                ),
                "urgency_level": (
                    processed_email.analysis.urgency_level
                    if processed_email.analysis
                    else None
                ),
                "sentiment": (
                    processed_email.analysis.sentiment
                    if processed_email.analysis
                    else None
                ),
                "status": processed_email.status,
            },
        )

    def log_processing_error(self, error: Exception, context: Dict[str, Any]):
        """Log processing errors"""
        self.logger.error(
            f"Processing error: {str(error)}",
            extra={
                "event_type": "processing_error",
                "error_type": type(error).__name__,
                "error_message": str(error),
                **context,
            },
            exc_info=True,
        )

    def log_webhook_validation_error(self, error: str, payload: Dict[str, Any]):
        """Log webhook validation errors"""
        self.logger.warning(
            f"Webhook validation failed: {error}",
            extra={
                "event_type": "webhook_validation_error",
                "error_message": error,
                "payload_keys": list(payload.keys()) if payload else [],
                "payload_size": len(str(payload)) if payload else 0,
            },
        )

    def log_mcp_request(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Log MCP server requests"""
        self.logger.debug(
            f"MCP request: {method}",
            extra={
                "event_type": "mcp_request",
                "method": method,
                "params": params or {},
            },
        )

    def log_mcp_response(self, method: str, response_size: int, execution_time: float):
        """Log MCP server responses"""
        self.logger.debug(
            f"MCP response: {method}",
            extra={
                "event_type": "mcp_response",
                "method": method,
                "response_size": response_size,
                "execution_time_ms": round(execution_time * 1000, 2),
            },
        )

    def log_performance_metrics(self, metrics: Dict[str, Any]):
        """Log performance metrics"""
        self.logger.info(
            "Performance metrics",
            extra={"event_type": "performance_metrics", **metrics},
        )

    def log_system_stats(self, stats=None):
        """Log system statistics"""
        # Use passed stats parameter if provided (for testing), otherwise
        # import from storage
        if stats is not None:
            storage_stats = stats
        else:
            try:
                from src.storage import stats as storage_stats
            except ImportError:
                # Fallback for testing environments
                try:
                    import storage

                    storage_stats = storage.stats
                except ImportError:
                    # Create a default stats object if nothing is available
                    from src.models import EmailStats

                    storage_stats = EmailStats()

        self.logger.info(
            "System statistics",
            extra={
                "event_type": "system_stats",
                "total_processed": storage_stats.total_processed,
                "total_errors": storage_stats.total_errors,
                "avg_urgency_score": storage_stats.avg_urgency_score,
                "last_processed": (
                    storage_stats.last_processed.isoformat()
                    if storage_stats.last_processed
                    else None
                ),
                "processing_times_count": len(storage_stats.processing_times),
            },
        )

    # Delegation methods for standard logging interface
    def warning(self, message: str, *args, **kwargs):
        """Delegate warning to internal logger"""
        self.logger.warning(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """Delegate info to internal logger"""
        self.logger.info(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Delegate error to internal logger"""
        self.logger.error(message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        """Delegate debug to internal logger"""
        self.logger.debug(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Delegate critical to internal logger"""
        self.logger.critical(message, *args, **kwargs)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }

    def format(self, record):
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname_color = self.COLORS[record.levelname]
        else:
            record.levelname_color = ""

        return super().format(record)


# Performance tracking decorator
def log_performance(logger_instance: EmailProcessingLogger):
    """Decorator to log function performance"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            import time

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                logger_instance.log_performance_metrics(
                    {
                        "function": func.__name__,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "success": True,
                    }
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                logger_instance.log_performance_metrics(
                    {
                        "function": func.__name__,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "success": False,
                        "error": str(e),
                    }
                )

                raise

        return wrapper

    return decorator


# Global logger instance
logger = EmailProcessingLogger()
