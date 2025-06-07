"""SambaNova AI Interface implementation.

This module implements the AIInterface for SambaNova's AI services.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ...base import AIInterface
from .config import SambaNovaConfig

logger = logging.getLogger(__name__)


class SambaNovaInterface(AIInterface):
    """Implementation of AIInterface for SambaNova AI services."""

    def __init__(self, config: SambaNovaConfig):
        """Initialize the SambaNova interface.

        Args:
            config: Configuration for the SambaNova service.
        """
        self.config = config
        self._client = None

    async def _get_client(self):
        """Lazily initialize and return the SambaNova client."""
        if self._client is None:
            # Import here to avoid circular imports
            from sambanova import SambaverseClient  # type: ignore

            self._client = SambaverseClient(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
        return self._client

    async def analyze_email(
        self, email_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze an email and extract structured information.

        Args:
            email_data: Dictionary containing email data (subject, body, etc.)
            context: Optional context for the analysis

        Returns:
            Dictionary containing the analysis results
        """
        client = await self._get_client()

        # Prepare the prompt
        prompt = self._prepare_email_prompt(email_data, context)

        # Call the API
        response = await client.generate(
            prompt=prompt,
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
        )

        # Process and return the response
        return self._process_email_response(response, email_data)

    async def extract_tasks(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract tasks from the given text.

        Args:
            text: Input text to extract tasks from.
            context: Optional context information for task extraction.

        Returns:
            List of extracted tasks with their details.
        """
        client = await self._get_client()

        # Prepare the prompt
        prompt = self._prepare_task_extraction_prompt(text, context)

        # Call the API
        response = await client.generate(
            prompt=prompt,
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            temperature=0.3,  # Lower temperature for more deterministic task extraction
            top_p=0.9,
        )

        # Process and return the response
        return self._process_task_extraction_response(response, text)

    async def analyze_sentiment(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze the sentiment of the given text.

        Args:
            text: Input text to analyze.
            context: Optional context information for sentiment analysis.

        Returns:
            Dictionary containing sentiment analysis results.
        """
        client = await self._get_client()

        # Prepare the prompt
        prompt = self._prepare_sentiment_prompt(text, context)

        # Call the API
        response = await client.generate(
            prompt=prompt,
            model=self.config.model_name,
            max_tokens=100,  # Sentiment analysis doesn't need many tokens
            temperature=0.1,  # Very low temperature for sentiment analysis
            top_p=0.9,
        )

        # Process and return the response
        return self._process_sentiment_response(response, text)

    async def analyze_thread(
        self, messages: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze a thread of messages.

        Args:
            messages: List of message dictionaries in the thread.
            context: Optional context information for thread analysis.

        Returns:
            Dictionary containing thread analysis results.
        """
        client = await self._get_client()

        # Prepare the prompt
        prompt = self._prepare_thread_prompt(messages, context)

        # Call the API
        response = await client.generate(
            prompt=prompt,
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            temperature=0.5,  # Moderate temperature for balanced analysis
            top_p=0.9,
        )

        # Process and return the response
        return self._process_thread_response(response, messages)

    # Helper methods for prompt preparation and response processing

    def _prepare_email_prompt(
        self, email_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare the prompt for email analysis.

        Args:
            email_data: Dictionary containing email data
            context: Optional context for the analysis

        Returns:
            Formatted prompt string
        """
        prompt = """Analyze the following email and extract the following information:

Subject: {subject}
From: {from_}
To: {to}
Body:
{body}

Extract the following information in JSON format:
- intent: The main purpose of the email (e.g., question, request, information, etc.)
- entities: List of important entities (people, organizations, dates, etc.)
- action_items: Any action items or tasks mentioned
- sentiment: Overall sentiment (positive, negative, neutral)
- categories: List of relevant categories or topics
"""
        return prompt.strip()

    def _process_email_response(
        self, response: Dict[str, Any], email_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process the email analysis response.

        Args:
            response: Raw response from the AI service
            email_data: Original email data for reference

        Returns:
            Processed response as a dictionary
        """
        try:
            # Extract the text from the response
            if "choices" in response and response["choices"]:
                content = response["choices"][0]["text"]
                # Try to parse the JSON content
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse JSON response: %s", content)
                    return {"error": f"Failed to parse AI response: {str(e)}"}
            else:
                logger.warning("Unexpected response format: %s", response)
                return {"error": "Unexpected response format from AI service"}
        except Exception as e:
            logger.exception("Error processing email analysis response")
            return {"error": f"Error processing response: {str(e)}"}

    def _prepare_task_extraction_prompt(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare the prompt for task extraction."""
        return f"""
        Extract tasks from the following text. Return a JSON array of tasks,
        where each task has 'description' and 'priority' (high/medium/low):

        {text}

        JSON Response:
        """.strip()

    def _process_task_extraction_response(
        self, response: Dict[str, Any], original_text: str
    ) -> List[Dict[str, Any]]:
        """Process the task extraction response."""
        try:
            tasks = json.loads(response.get("generated_text", "[]"))
            if isinstance(tasks, list):
                return tasks
            return []
        except json.JSONDecodeError:
            logger.warning("Failed to parse task extraction response")
            return []

    def _prepare_sentiment_prompt(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare the prompt for sentiment analysis."""
        return f"""
        Analyze the sentiment of the following text.
        Return a JSON object with 'sentiment' and 'confidence':

        {text}

        JSON Response:
        """.strip()

    def _process_sentiment_response(
        self, response: Dict[str, Any], original_text: str
    ) -> Dict[str, Any]:
        """Process the sentiment analysis response."""
        try:
            result = json.loads(response.get("generated_text", "{}"))
            if not isinstance(result, dict):
                raise ValueError("Expected a JSON object")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse sentiment response: {e}")
            return {"sentiment": "neutral", "confidence": 0.5, "error": str(e)}

    def _prepare_thread_prompt(
        self, messages: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare the prompt for thread analysis."""
        thread_text = "\n---\n".join(
            f"From: {msg.get('from', 'Unknown')}\n"
            f"Date: {msg.get('date', 'Unknown')}\n"
            f"Subject: {msg.get('subject', 'No Subject')}\n"
            f"\n{msg.get('body', '')}"
            for msg in messages
        )

        return f"""
        Analyze the following email thread and provide a summary of the discussion,
        key decisions made, and any action items mentioned.

        {thread_text}

        Return a JSON object with 'summary', 'key_decisions', and 'action_items'.

        JSON Response:
        """.strip()

    def _process_thread_response(
        self, response: Dict[str, Any], messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process the thread analysis response."""
        try:
            result = json.loads(response.get("generated_text", "{}"))
            if not isinstance(result, dict):
                raise ValueError("Expected a JSON object")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse thread analysis response: %s", e)
            return {
                "summary": "Error analyzing thread",
                "key_decisions": [],
                "action_items": [],
                "error": str(e),
            }
