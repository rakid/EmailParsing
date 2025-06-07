"""
Base classes and interfaces for AI providers.

This module contains the abstract base classes that define the interface for AI providers.
"""

from .ai_interface import AIInterface
from .ai_plugin import AIPlugin

__all__ = ["AIInterface", "APlugin"]
