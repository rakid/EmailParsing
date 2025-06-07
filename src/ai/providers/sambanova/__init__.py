"""
SambaNova AI Provider

This package provides SambaNova AI integration for the Inbox Zen
Email Parsing MCP Server, implementing the AI provider interface.
"""

from .config import SambaNovaConfig, SambaNovaConfigManager
from .interface import SambaNovaInterface
from .plugin import SambaNovaPlugin

__version__ = "1.0.0"
__author__ = "Inbox Zen Team"

__all__ = [
    "SambaNovaPlugin",
    "SambaNovaInterface",
    "SambaNovaConfig",
    "SambaNovaConfigManager",
]
