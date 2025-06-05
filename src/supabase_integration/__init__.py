"""
Supabase Integration Package

This package provides comprehensive Supabase integration for the Inbox Zen
Email Parsing MCP Server, including multi-user database capabilities,
real-time features, authentication, and dashboard functionality.

Components:
- SupabaseConfig: Configuration management
- SupabaseDatabaseInterface: Database interface implementation
- SupabaseAuthInterface: Authentication and user management
- SupabaseRealtimeInterface: Real-time subscriptions and notifications
- SupabasePlugin: Plugin implementation
"""

from .auth_interface import SupabaseAuthInterface
from .config import SupabaseConfig
from .database_interface import SupabaseDatabaseInterface
from .plugin import SupabasePlugin
from .realtime import SupabaseRealtimeInterface

__version__ = "1.0.0"
__author__ = "Inbox Zen Team"

__all__ = [
    "SupabaseConfig",
    "SupabaseDatabaseInterface",
    "SupabaseAuthInterface",
    "SupabaseRealtimeInterface",
    "SupabasePlugin",
]
