# Configuration for MCP Email Parsing Server
import os
import asyncio  # Ensure asyncio is imported
from pydantic_settings import BaseSettings
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI  # Import FastAPI
from src.logging_system import logger  # Import logger

# For graceful shutdown
shutdown_event = asyncio.Event()

@asynccontextmanager
async def lifespan_manager(app: "FastAPI") -> AsyncGenerator[None, None]:
    """Manage application lifespan events for graceful shutdown."""
    logger.info("Application startup...")
    # Perform any startup tasks here if needed
    # e.g., initialize database connections, load resources
    
    yield # Application is now running
    
    # --- Shutdown sequence ---
    logger.info("Application shutdown sequence initiated...")
    shutdown_event.set() 
    
    # Give active requests time to complete (e.g., 5 seconds)
    # This is a simple example; more sophisticated handling might be needed
    # depending on the nature of background tasks or long-lived connections.
    await asyncio.sleep(5) 
    logger.info("Application shutdown complete.")


class ServerConfig(BaseSettings):
    """Server configuration settings"""
    
    # Server metadata
    server_name: str = "inbox-zen-email-parser"
    server_version: str = "0.1.0"
    
    # Postmark webhook settings
    postmark_webhook_secret: Optional[str] = None
    webhook_endpoint: str = "/webhook"
    
    # Processing settings
    max_processing_time: float = 2.0  # seconds
    enable_async_processing: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "text"  # "text" or "json"
    enable_console_colors: bool = True
    log_file_path: Optional[str] = None # e.g., "logs/inbox-zen.log"
    log_file_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    log_file_backup_count: int = 5
    
    # Environment: "development" or "production"
    # This can be used to adjust default logging behavior
    environment: str = "development"

    # Add lifespan manager to config to be accessible
    @property
    def lifespan_manager(self):
        return lifespan_manager

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

# Global configuration instance
config = ServerConfig()

# Adjust logging defaults for production environment
if config.environment == "production":
    config.log_level = os.getenv("LOG_LEVEL", "INFO")
    config.log_format = os.getenv("LOG_FORMAT", "json")
    config.enable_console_colors = os.getenv("ENABLE_CONSOLE_COLORS", "False").lower() == "true"
    if not config.log_file_path:
        config.log_file_path = "logs/inbox-zen-prod.log"

# Ensure log directory exists if file logging is enabled
if config.log_file_path:
    log_dir = os.path.dirname(config.log_file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)