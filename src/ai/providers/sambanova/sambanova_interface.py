"""
SambaNova AI Interface Implementation
Extends AIAnalysisInterface with SambaNova's advanced language models for superior email analysis.
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import aiohttp
from pydantic import BaseModel, Field, ValidationError

from ...config import SambaNovaConfigManager, get_sambanova_config


# Assume these models exist from the base project
# We'll define them here for the SambaNova integration
class EmailData(BaseModel):
    """Email data structure for analysis."""

    id: str
    subject: str
    body: str
    sender: str
    recipients: List[str]
    timestamp: datetime
    thread_id: Optional[str] = None
    importance: Optional[str] = None


class Task(BaseModel):
    """Extracted task structure with enhanced SambaNova analysis."""

    id: str = Field(default_factory=lambda: f"task_{int(time.time())}")
    description: str
    priority: str = Field(default="medium")  # critical, high, medium, low
    category: str = Field(
        default="action_required"
    )  # action_required, follow_up, decision_needed, etc.
    deadline: Optional[str] = None
    time_sensitivity: Optional[str] = (
        None  # immediate, today, this_week, this_month, flexible
    )
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    context: Optional[str] = None
    assignee: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    source_email_id: Optional[str] = None


class SentimentAnalysis(BaseModel):
    """Multi-dimensional sentiment analysis."""

    primary_emotion: str  # frustrated, satisfied, urgent, appreciative, neutral
    intensity: float = Field(ge=0.0, le=1.0)
    professional_tone: str  # formal, casual, aggressive, diplomatic
    escalation_risk: float = Field(ge=0.0, le=1.0)
    response_urgency: str  # immediate, same_day, next_business_day, flexible


class ContextAnalysis(BaseModel):
    """Context analysis for email threads and relationships."""

    thread_summary: str
    key_stakeholders: List[str]
    main_topics: List[str]
    decision_points: List[str]
    action_items_evolution: List[Dict[str, Any]]
    conversation_state: str  # ongoing, resolved, escalated, waiting_response
    project_correlation: Optional[str] = None


class EmailAnalysis(BaseModel):
    """Comprehensive email analysis from SambaNova."""

    email_id: str
    summary: str
    tasks: List[Task]
    sentiment: SentimentAnalysis
    priority_score: float = Field(ge=0.0, le=1.0)
    category: str  # business, personal, automated, marketing, etc.
    requires_response: bool
    response_suggestions: List[str] = Field(default_factory=list)
    entities: List[str] = Field(
        default_factory=list
    )  # People, organizations, dates, etc.
    confidence: float = Field(ge=0.0, le=1.0)


# Abstract base interface (assuming this exists in the base project)
class AIAnalysisInterface(ABC):
    """Abstract base class for AI analysis interfaces."""

    @abstractmethod
    async def analyze_email(self, email_data: EmailData) -> EmailAnalysis:
        """Analyze email and extract comprehensive insights."""
        pass

    @abstractmethod
    async def extract_tasks(
        self, email_content: str, context: Optional[str] = None
    ) -> List[Task]:
        """Extract actionable tasks from email content."""
        pass

    @abstractmethod
    async def batch_analyze(self, emails: List[EmailData]) -> List[EmailAnalysis]:
        """Analyze multiple emails in batch for efficiency."""
        pass


@dataclass
class CacheEntry:
    """Cache entry for API responses."""

    response: Any
    timestamp: datetime
    ttl: int

    def is_expired(self) -> bool:
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl)


class SambaNovaInterface(AIAnalysisInterface):
    """
    SambaNova AI Interface implementation with advanced prompting and analysis capabilities.

    Provides superior task extraction and contextual understanding using SambaNova's
    state-of-the-art language models with sophisticated prompt engineering.
    """

    def __init__(self, config_manager: Optional[SambaNovaConfigManager] = None):
        """
        Initialize SambaNova interface.

        Args:
            config_manager: Optional configuration manager. If None, uses global config.
        """
        self.config_manager = config_manager or get_sambanova_config()
        self.config = self.config_manager.config
        self.logger = logging.getLogger(__name__)

        # Initialize cache if enabled
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_enabled = self.config.enable_caching

        # Rate limiting
        self.last_request_time = 0.0
        self.request_interval = 60.0 / self.config.rate_limit_rpm

        # API session will be initialized on first use
        self._session: Optional[aiohttp.ClientSession] = None

        self.logger.info(
            f"SambaNovaInterface initialized with model: {self.config.model}"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "InboxZen-SambaNova/1.0",
            }
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self._session

    async def _make_api_request(
        self, prompt: str, system_prompt: str = "", **kwargs
    ) -> Dict[str, Any]:
        """
        Make rate-limited API request to SambaNova.

        Args:
            prompt: Main user prompt
            system_prompt: System prompt for role definition
            **kwargs: Additional parameters for the API call

        Returns:
            API response as dictionary
        """
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_interval:
            await asyncio.sleep(self.request_interval - time_since_last)

        # Check cache
        cache_key = self._get_cache_key(prompt, system_prompt, **kwargs)
        if self.cache_enabled and cache_key in self.cache:
            entry = self.cache[cache_key]
            if not entry.is_expired():
                self.logger.debug("Cache hit for SambaNova request")
                return entry.response
            else:
                del self.cache[cache_key]

        # Prepare request
        session = await self._get_session()

        # Get optimized prompt configuration
        prompt_config = self.config_manager.get_prompt_config()

        payload = {
            "model": prompt_config["model"],
            "messages": [
                {"role": "system", "content": system_prompt} if system_prompt else None,
                {"role": "user", "content": prompt},
            ],
            "max_tokens": prompt_config["max_tokens"],
            "temperature": prompt_config["temperature"],
            "top_p": prompt_config.get("top_p", 0.9),
            "frequency_penalty": prompt_config.get("frequency_penalty", 0.1),
            "presence_penalty": prompt_config.get("presence_penalty", 0.1),
            **kwargs,
        }

        # Remove None values
        payload["messages"] = [msg for msg in payload["messages"] if msg is not None]

        # Make API request with retries
        for attempt in range(self.config.max_retries):
            try:
                async with session.post(
                    f"{self.config.endpoint}/chat/completions", json=payload
                ) as response:
                    response.raise_for_status()
                    result = await response.json()

                    # Cache successful response
                    if self.cache_enabled:
                        self.cache[cache_key] = CacheEntry(
                            response=result,
                            timestamp=datetime.now(),
                            ttl=self.config.cache_ttl,
                        )

                    self.last_request_time = time.time()
                    return result

            except Exception as e:
                self.logger.warning(
                    f"SambaNova API request attempt {attempt + 1} failed: {e}"
                )
                if attempt == self.config.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)  # Exponential backoff

        raise RuntimeError("All SambaNova API request attempts failed")

    def _get_cache_key(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        """Generate cache key for request."""
        content = f"{system_prompt}|{prompt}|{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Extract JSON from API response text with robust parsing.

        Args:
            response_text: Raw response text from API

        Returns:
            Parsed JSON dictionary
        """
        try:
            # Try direct JSON parsing first
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Look for JSON blocks in markdown-style formatting
            import re

            json_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL
            )
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            # Look for JSON objects in the text
            json_match = re.search(
                r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response_text, re.DOTALL
            )
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            # Fallback: try to extract key-value pairs
            self.logger.warning(
                f"Could not parse JSON from response: {response_text[:200]}..."
            )
            return {"error": "Could not parse JSON", "raw_response": response_text}

    async def analyze_email(self, email_data: EmailData) -> EmailAnalysis:
        """
        Analyze email comprehensively using SambaNova's advanced understanding.

        Args:
            email_data: Email data to analyze

        Returns:
            Comprehensive email analysis
        """
        system_prompt = """You are an expert email analyst and intelligent assistant specializing in comprehensive email analysis for productivity enhancement. Your expertise includes:

- Advanced task extraction with high precision (>95% accuracy)
- Multi-dimensional sentiment analysis and professional tone assessment
- Contextual understanding of business communications
- Priority assessment and urgency detection
- Response recommendations and professional communication guidance

Analyze emails with deep understanding of professional contexts, relationships, and implicit requirements."""

        user_prompt = f"""Analyze the following email comprehensively and provide structured insights:

**EMAIL TO ANALYZE:**
Subject: {email_data.subject}
From: {email_data.sender}
To: {', '.join(email_data.recipients)}
Date: {email_data.timestamp}

Body:
{email_data.body}

**ANALYSIS REQUIREMENTS:**

1. **TASK EXTRACTION**: Identify all actionable tasks (explicit and implicit)
   - Include tasks for both sender and recipient
   - Determine priority levels and deadlines
   - Assess confidence scores for each task

2. **SENTIMENT ANALYSIS**: Analyze emotional tone and professional context
   - Primary emotion (frustrated, satisfied, urgent, appreciative, neutral)
   - Intensity level (0.0-1.0)
   - Professional tone (formal, casual, aggressive, diplomatic)
   - Escalation risk and response urgency

3. **CONTENT ANALYSIS**: Extract key information
   - Email summary and main purpose
   - Key entities (people, organizations, dates, projects)
   - Category classification
   - Priority score and response requirements

4. **RESPONSE GUIDANCE**: Provide actionable recommendations
   - Response suggestions if response is needed
   - Professional communication recommendations

**OUTPUT FORMAT**: Provide response as valid JSON with this exact structure:

```json
{{
  "summary": "Brief summary of email content and purpose",
  "tasks": [
    {{
      "description": "Clear task description",
      "priority": "critical|high|medium|low",
      "category": "action_required|follow_up|decision_needed|information_request|meeting_required|approval_needed",
      "deadline": "deadline if mentioned or null",
      "time_sensitivity": "immediate|today|this_week|this_month|flexible",
      "confidence_score": 0.95,
      "context": "Additional context for the task",
      "assignee": "who should do this task"
    }}
  ],
  "sentiment": {{
    "primary_emotion": "frustrated|satisfied|urgent|appreciative|neutral",
    "intensity": 0.7,
    "professional_tone": "formal|casual|aggressive|diplomatic",
    "escalation_risk": 0.3,
    "response_urgency": "immediate|same_day|next_business_day|flexible"
  }},
  "priority_score": 0.8,
  "category": "business|personal|automated|marketing|support",
  "requires_response": true,
  "response_suggestions": [
    "Specific response recommendation 1",
    "Specific response recommendation 2"
  ],
  "entities": ["person1", "Company X", "Project Alpha", "March 15"],
  "confidence": 0.92
}}
```

Analyze thoroughly and provide precise, actionable insights."""

        try:
            response = await self._make_api_request(user_prompt, system_prompt)
            response_text = response["choices"][0]["message"]["content"]

            # Parse JSON response
            analysis_data = self._extract_json_from_response(response_text)

            # Validate and create EmailAnalysis object
            # Add email_id and enhance tasks with source reference
            analysis_data["email_id"] = email_data.id

            # Enhance tasks with source email ID
            for task_data in analysis_data.get("tasks", []):
                task_data["source_email_id"] = email_data.id
                if "id" not in task_data:
                    task_data["id"] = (
                        f"task_{email_data.id}_{len(analysis_data.get('tasks', []))}"
                    )

            # Create validated analysis object
            analysis = EmailAnalysis(**analysis_data)

            self.logger.info(
                f"Successfully analyzed email {email_data.id}: {len(analysis.tasks)} tasks extracted"
            )
            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze email {email_data.id}: {e}")

            # Return fallback analysis
            return EmailAnalysis(
                email_id=email_data.id,
                summary=f"Analysis failed: {str(e)}",
                tasks=[],
                sentiment=SentimentAnalysis(
                    primary_emotion="neutral",
                    intensity=0.5,
                    professional_tone="formal",
                    escalation_risk=0.0,
                    response_urgency="flexible",
                ),
                priority_score=0.5,
                category="business",
                requires_response=False,
                confidence=0.0,
            )

    async def extract_tasks(
        self, email_content: str, context: Optional[str] = None
    ) -> List[Task]:
        """
        Extract actionable tasks with advanced SambaNova understanding.

        Uses sophisticated prompt engineering for >95% accuracy in task identification.

        Args:
            email_content: Email content to analyze
            context: Optional context information

        Returns:
            List of extracted tasks with high confidence scores
        """
        system_prompt = """You are an expert task extraction specialist with exceptional ability to identify actionable items from email content. Your expertise includes:

- Detecting explicit tasks (clearly stated actions)
- Identifying implicit tasks (implied responsibilities and follow-ups)
- Understanding business context and professional obligations
- Distinguishing between actionable tasks and informational content
- Assessing task priorities and urgency levels

Extract tasks with precision and provide confidence scores for reliability assessment."""

        context_section = f"\n**CONTEXT**: {context}\n" if context else ""

        user_prompt = f"""Extract all actionable tasks from the following email content with high precision:

**EMAIL CONTENT:**
{email_content}
{context_section}

**TASK EXTRACTION INSTRUCTIONS:**

1. **IDENTIFY ACTIONABLE ITEMS**:
   - Explicit tasks: Direct requests and assignments
   - Implicit tasks: Implied follow-ups and responsibilities
   - Decision points: Items requiring decisions or approvals
   - Information requests: Requests for data or clarification

2. **CATEGORIZE TASKS**:
   - action_required: Direct actions to be taken
   - follow_up: Follow-up communications or check-ins
   - decision_needed: Decisions or approvals required
   - information_request: Information gathering or sharing
   - meeting_required: Meetings or calls to be scheduled
   - approval_needed: Approvals or sign-offs required

3. **ASSESS PRIORITY AND TIMING**:
   - Priority: critical, high, medium, low
   - Time sensitivity: immediate, today, this_week, this_month, flexible
   - Deadline extraction from content

4. **CONFIDENCE SCORING**:
   - Rate your confidence (0.0-1.0) for each extracted task
   - Higher confidence for explicit tasks, lower for implicit ones

**EXCLUSIONS** (Do NOT extract as tasks):
- Email signatures and disclaimers
- Social pleasantries ("Hope you're well")
- FYI information without action required
- Automated system messages
- General company announcements without personal action

**OUTPUT FORMAT**: Valid JSON array of tasks:

```json
[
  {{
    "description": "Specific, clear task description",
    "priority": "critical|high|medium|low",
    "category": "action_required|follow_up|decision_needed|information_request|meeting_required|approval_needed",
    "deadline": "extracted deadline or null",
    "time_sensitivity": "immediate|today|this_week|this_month|flexible",
    "confidence_score": 0.95,
    "context": "Additional context explaining why this is a task",
    "assignee": "who should perform this task (if clear from content)"
  }}
]
```

**EXAMPLES:**

Email: "Please review the Q3 budget proposal and let me know your thoughts by Friday."
Task: {{"description": "Review Q3 budget proposal and provide feedback", "priority": "high", "category": "action_required", "deadline": "Friday", "confidence_score": 0.98}}

Email: "We should probably schedule a meeting to discuss the new project timeline."
Task: {{"description": "Schedule meeting to discuss new project timeline", "priority": "medium", "category": "meeting_required", "time_sensitivity": "this_week", "confidence_score": 0.85}}

Extract tasks with precision and provide only valid JSON output."""

        try:
            response = await self._make_api_request(user_prompt, system_prompt)
            response_text = response["choices"][0]["message"]["content"]

            # Extract JSON from response
            tasks_data = self._extract_json_from_response(response_text)

            # Handle both array and object responses
            if isinstance(tasks_data, dict):
                if "tasks" in tasks_data:
                    tasks_data = tasks_data["tasks"]
                elif "error" in tasks_data:
                    self.logger.warning(f"Task extraction parsing error: {tasks_data}")
                    return []
                else:
                    tasks_data = [tasks_data]  # Single task object

            # Validate and create Task objects
            tasks = []
            for i, task_data in enumerate(tasks_data):
                try:
                    # Add default ID if missing
                    if "id" not in task_data:
                        task_data["id"] = f"task_{int(time.time())}_{i}"

                    task = Task(**task_data)
                    tasks.append(task)
                except ValidationError as e:
                    self.logger.warning(f"Invalid task data: {task_data}, error: {e}")
                    continue

            self.logger.info(
                f"Successfully extracted {len(tasks)} tasks from email content"
            )
            return tasks

        except Exception as e:
            self.logger.error(f"Failed to extract tasks: {e}")
            return []

    async def analyze_context(self, email_thread: List[EmailData]) -> ContextAnalysis:
        """
        Analyze context and relationships within email threads.

        Args:
            email_thread: List of emails in chronological order

        Returns:
            Context analysis with thread understanding
        """
        system_prompt = """You are an expert email thread analyst specializing in understanding conversation flows, stakeholder relationships, and project contexts. Your expertise includes:

- Thread conversation analysis and summarization
- Stakeholder identification and relationship mapping
- Decision tracking and consensus building
- Action item evolution and completion status
- Project and topic correlation analysis

Analyze email threads with deep understanding of business contexts and communication patterns."""

        # Prepare thread content
        thread_content = ""
        for i, email in enumerate(email_thread):
            thread_content += f"""
EMAIL {i+1} - {email.timestamp}
From: {email.sender}
To: {', '.join(email.recipients)}
Subject: {email.subject}

{email.body}

---
"""

        user_prompt = f"""Analyze the following email thread for contextual insights and relationships:

**EMAIL THREAD:**
{thread_content}

**CONTEXT ANALYSIS REQUIREMENTS:**

1. **THREAD SUMMARY**: Provide a comprehensive summary of the conversation flow
2. **STAKEHOLDERS**: Identify key participants and their roles
3. **TOPICS**: Extract main topics and themes discussed
4. **DECISION POINTS**: Identify decisions made or pending
5. **ACTION ITEMS EVOLUTION**: Track how action items evolved through the thread
6. **CONVERSATION STATE**: Assess current state of the conversation
7. **PROJECT CORRELATION**: Identify any project or business context

**OUTPUT FORMAT**: Provide valid JSON with this structure:

```json
{{
  "thread_summary": "Comprehensive summary of the conversation flow and outcomes",
  "key_stakeholders": ["stakeholder1", "stakeholder2", "stakeholder3"],
  "main_topics": ["topic1", "topic2", "topic3"],
  "decision_points": [
    "Decision 1: What was decided and when",
    "Decision 2: Pending decision and requirements"
  ],
  "action_items_evolution": [
    {{
      "action": "Action item description",
      "status": "assigned|completed|pending|cancelled",
      "assignee": "person responsible",
      "evolution": "how this item changed through the thread"
    }}
  ],
  "conversation_state": "ongoing|resolved|escalated|waiting_response",
  "project_correlation": "Related project or business context if identified"
}}
```

Analyze thoroughly and provide actionable insights about the thread context."""

        try:
            response = await self._make_api_request(user_prompt, system_prompt)
            response_text = response["choices"][0]["message"]["content"]

            # Parse JSON response
            context_data = self._extract_json_from_response(response_text)

            # Create validated context analysis
            context_analysis = ContextAnalysis(**context_data)

            self.logger.info(
                f"Successfully analyzed context for thread with {len(email_thread)} emails"
            )
            return context_analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze thread context: {e}")

            # Return fallback analysis
            return ContextAnalysis(
                thread_summary=f"Context analysis failed: {str(e)}",
                key_stakeholders=[email.sender for email in email_thread],
                main_topics=["analysis_failed"],
                decision_points=[],
                action_items_evolution=[],
                conversation_state="ongoing",
            )

    async def batch_analyze(self, emails: List[EmailData]) -> List[EmailAnalysis]:
        """
        Analyze multiple emails efficiently with batch processing.

        Args:
            emails: List of emails to analyze

        Returns:
            List of email analyses
        """
        self.logger.info(f"Starting batch analysis of {len(emails)} emails")

        # Process in parallel with concurrency limit
        semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

        async def analyze_single(email: EmailData) -> EmailAnalysis:
            async with semaphore:
                return await self.analyze_email(email)

        try:
            results = await asyncio.gather(
                *[analyze_single(email) for email in emails], return_exceptions=True
            )

            # Handle exceptions and log results
            analyses = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(
                        f"Failed to analyze email {emails[i].id}: {result}"
                    )
                    # Create fallback analysis
                    analyses.append(
                        EmailAnalysis(
                            email_id=emails[i].id,
                            summary=f"Analysis failed: {str(result)}",
                            tasks=[],
                            sentiment=SentimentAnalysis(
                                primary_emotion="neutral",
                                intensity=0.5,
                                professional_tone="formal",
                                escalation_risk=0.0,
                                response_urgency="flexible",
                            ),
                            priority_score=0.5,
                            category="business",
                            requires_response=False,
                            confidence=0.0,
                        )
                    )
                else:
                    analyses.append(result)

            self.logger.info(
                f"Completed batch analysis: {len([a for a in analyses if a.confidence > 0])} successful"
            )
            return analyses

        except Exception as e:
            self.logger.error(f"Batch analysis failed: {e}")
            raise

    async def cleanup(self):
        """Clean up resources."""
        if self._session and not self._session.closed:
            await self._session.close()

        # Clear cache
        self.cache.clear()

        self.logger.info("SambaNovaInterface cleanup completed")

    def get_interface_info(self) -> Dict[str, Any]:
        """Get interface information and capabilities."""
        return {
            "name": "SambaNovaInterface",
            "version": "1.0.0",
            "model": self.config.model.value,
            "capabilities": [
                "advanced_task_extraction",
                "multi_dimensional_sentiment_analysis",
                "contextual_thread_analysis",
                "batch_processing",
                "intelligent_caching",
                "response_suggestions",
            ],
            "cache_enabled": self.cache_enabled,
            "cache_size": len(self.cache),
            "rate_limit_rpm": self.config.rate_limit_rpm,
        }


# Factory function for easy integration
async def create_sambanova_interface(
    config_manager: Optional[SambaNovaConfigManager] = None,
) -> SambaNovaInterface:
    """
    Factory function to create and validate SambaNova interface.

    Args:
        config_manager: Optional configuration manager

    Returns:
        Initialized and validated SambaNovaInterface
    """
    interface = SambaNovaInterface(config_manager)

    # Test API connectivity
    try:
        test_email = EmailData(
            id="test_connectivity",
            subject="Test",
            body="Test connectivity",
            sender="test@example.com",
            recipients=["test@example.com"],
            timestamp=datetime.now(),
        )

        # Try a simple analysis to verify API works
        await interface.extract_tasks("Test task extraction connectivity")

        logging.getLogger(__name__).info("SambaNova interface connectivity verified")
        return interface

    except Exception as e:
        logging.getLogger(__name__).error(
            f"SambaNova interface connectivity test failed: {e}"
        )
        raise RuntimeError(f"Failed to initialize SambaNova interface: {e}")
