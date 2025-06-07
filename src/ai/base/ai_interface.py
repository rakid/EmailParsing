"""
Base interface for AI providers.

This module defines the abstract base class that all AI providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AIInterface(ABC):
    """Abstract base class defining the interface for AI providers."""

    @abstractmethod
    async def analyze_email(
        self, email_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze an email and extract structured information.

        Args:
            email_data: Raw email data including headers, body, etc.
            context: Optional context information for the analysis.

        Returns:
            Dictionary containing the analysis results.
        """
        pass

    @abstractmethod
    async def extract_tasks(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract tasks from the given text.

        Args:
            text: Input text to extract tasks from.
            context: Optional context information for task extraction.

        Returns:
            List of extracted tasks with their details.
        """
        pass

    @abstractmethod
    async def analyze_sentiment(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze the sentiment of the given text.

        Args:
            text: Input text to analyze.
            context: Optional context information for sentiment analysis.

        Returns:
            Dictionary containing sentiment analysis results.
        """
        pass

    @abstractmethod
    async def analyze_thread(
        self, messages: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a thread of messages.

        Args:
            messages: List of message dictionaries in the thread.
            context: Optional context information for thread analysis.


        Returns:
            Dictionary containing thread analysis results.
        """
        pass
