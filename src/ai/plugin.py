"""
SambaNova AI Plugin for Email Parsing MCP Server

This plugin integrates SambaNova's advanced language models for:
- Advanced task extraction and analysis
- Multi-dimensional sentiment analysis
- Context-aware email understanding
- Intelligent metadata enhancement

"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.integrations import PluginInterface
from src.models import (
    EmailAnalysis,
    EmailData,
    EmailStatus,
    ProcessedEmail,
    UrgencyLevel,
)

# Import our SambaNova AI components
from .config import SambaNovaConfig
from .performance_optimizer import PerformanceOptimizer, create_performance_optimizer
from .providers.sambanova.context_analysis import ContextAnalysisEngine
from .providers.sambanova.sambanova_interface import SambaNovaInterface
from .providers.sambanova.sentiment_analysis import SentimentAnalysisEngine
from .providers.sambanova.task_extraction import TaskExtractionEngine
from .providers.sambanova.thread_intelligence import ThreadIntelligenceEngine

# Setup logging
logger = logging.getLogger(__name__)


class SambaNovaPlugin:
    """
    Main SambaNova AI plugin that enhances email processing with advanced AI capabilities.

    This plugin acts as the orchestrator for all SambaNova AI components, providing:
    - Intelligent task extraction with context awareness
    - Multi-dimensional sentiment and intent analysis
    - Advanced email relationship detection
    - Enhanced metadata generation
    - Multi-email thread intelligence and analysis
    - Decision tracking and stakeholder profiling
    - Action item consolidation across email threads
    """

    def __init__(self):
        """Initialize the SambaNova plugin."""
        self.config: Optional[SambaNovaConfig] = None
        self.sambanova_interface: Optional[SambaNovaInterface] = None
        self.task_engine: Optional[TaskExtractionEngine] = None
        self.context_engine: Optional[ContextAnalysisEngine] = None
        self.sentiment_engine: Optional[SentimentAnalysisEngine] = None
        self.thread_intelligence: Optional[ThreadIntelligenceEngine] = None
        # Create a basic performance optimizer instance
        self.performance_optimizer = create_performance_optimizer()
        self.is_initialized = False
        self.processing_stats = {
            "emails_processed": 0,
            "total_tasks_extracted": 0,
            "avg_processing_time": 0.0,
            "errors": 0,
            "last_error": None,
        }

    def get_name(self) -> str:
        """Get plugin name."""
        return "sambanova-ai-analysis"

    def get_version(self) -> str:
        """Get plugin version."""
        return "1.0.0"

    def get_dependencies(self) -> List[str]:
        """Get required dependencies."""
        return [
            "httpx>=0.24.0",
            "aiohttp>=3.8.0",
            "pydantic>=2.0.0",
            "python-dateutil>=2.8.0",
        ]

    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the SambaNova plugin with configuration.

        Args:
            config: Plugin configuration dictionary containing:
                - api_key: SambaNova API key
                - model: Model name (default: "sambanova-large")
                - max_concurrent: Max concurrent requests (default: 5)
                - timeout: Request timeout (default: 30)
                - enable_caching: Enable response caching (default: True)
                - batch_processing: Enable batch processing (default: True)
        """
        try:
            logger.info("Initializing SambaNova AI plugin...")

            # Create SambaNova configuration
            self.config = SambaNovaConfig(
                api_key=config.get("api_key", ""),
                model=config.get("model", "sambanova-large"),
                max_concurrent_requests=config.get("max_concurrent", 5),
                timeout_seconds=config.get("timeout", 30),
                enable_caching=config.get("enable_caching", True),
                batch_processing=config.get("batch_processing", True),
            )

            # Initialize main SambaNova interface
            self.sambanova_interface = SambaNovaInterface(self.config)
            await self.sambanova_interface.initialize()

            # Initialize AI engines
            self.task_engine = TaskExtractionEngine(self.sambanova_interface)
            self.context_engine = ContextAnalysisEngine(self.sambanova_interface)
            self.sentiment_engine = SentimentAnalysisEngine(self.sambanova_interface)
            self.thread_intelligence = ThreadIntelligenceEngine(
                self.sambanova_interface
            )

            # Initialize performance optimizer if not already created or update with config
            cache_dir = config.get("cache_dir", None)
            if cache_dir:
                # Re-initialize with specific cache directory if provided
                self.performance_optimizer = create_performance_optimizer(cache_dir)

            # Configure performance optimizer
            if config.get("daily_budget"):
                self.performance_optimizer.daily_budget = config["daily_budget"]
            if config.get("cost_per_token"):
                self.performance_optimizer.cost_per_token = config["cost_per_token"]

            # Initialize all engines
            await self.task_engine.initialize()
            await self.context_engine.initialize()
            await self.sentiment_engine.initialize()
            await self.thread_intelligence.initialize()

            self.is_initialized = True
            logger.info("SambaNova AI plugin initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize SambaNova plugin: {e}", exc_info=True)
            self.processing_stats["errors"] += 1
            self.processing_stats["last_error"] = str(e)
            raise

    async def process_email(self, email: ProcessedEmail) -> ProcessedEmail:
        """
        Process email through SambaNova AI analysis pipeline.

        This method orchestrates the complete AI analysis workflow:
        1. Advanced task extraction with context awareness
        2. Multi-dimensional sentiment and intent analysis
        3. Context analysis and relationship detection
        4. Enhanced metadata generation

        Args:
            email: The processed email to enhance

        Returns:
            Enhanced ProcessedEmail with AI-generated insights
        """
        if not self.is_initialized:
            logger.warning("SambaNova plugin not initialized, returning original email")
            return email

        start_time = datetime.now()
        processing_id = f"{email.id}_ai_{int(start_time.timestamp())}"

        try:
            logger.info(f"Starting SambaNova AI analysis for email {email.id}")

            # Create enhanced copy of the email
            enhanced_email = ProcessedEmail(
                id=email.id,
                email_data=email.email_data,
                analysis=email.analysis,
                status=email.status,
                processed_at=email.processed_at,
                error_message=email.error_message,
                webhook_payload=email.webhook_payload,
            )

            # Ensure we have basic analysis structure
            if not enhanced_email.analysis:
                enhanced_email.analysis = EmailAnalysis(
                    urgency_score=0,
                    urgency_level=UrgencyLevel.LOW,
                    sentiment="neutral",
                    confidence=0.0,
                    keywords=[],
                    action_items=[],
                    tags=[],
                )

            # Stage 1: Advanced Task Extraction
            await self._extract_tasks(enhanced_email, processing_id)

            # Stage 2: Multi-dimensional Sentiment Analysis
            await self._analyze_sentiment(enhanced_email, processing_id)

            # Stage 3: Context Analysis (if enabled)
            if self.config.enable_context_analysis:
                await self._analyze_context(enhanced_email, processing_id)

            # Stage 4: Final Enhancement and Metadata
            await self._enhance_metadata(enhanced_email, processing_id)

            # Update processing statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(processing_time)

            # Add AI processing metadata
            enhanced_email.analysis.tags.append("ai:sambanova-processed")
            enhanced_email.analysis.tags.append(
                f"ai:processing-time-{processing_time:.2f}s"
            )

            enhanced_email.status = EmailStatus.ANALYZED
            if not enhanced_email.processed_at:
                enhanced_email.processed_at = datetime.now()

            logger.info(
                f"SambaNova AI analysis completed for email {email.id} in {processing_time:.2f}s"
            )
            return enhanced_email

        except Exception as e:
            logger.error(
                f"SambaNova AI processing failed for email {email.id}: {e}",
                exc_info=True,
            )
            self.processing_stats["errors"] += 1
            self.processing_stats["last_error"] = str(e)

            # Return original email with error indication
            if email.analysis:
                email.analysis.tags.append("ai:sambanova-error")

            return email

    async def _extract_tasks(self, email: ProcessedEmail, processing_id: str) -> None:
        """Extract advanced tasks using SambaNova task extraction engine."""
        try:
            logger.debug(f"Extracting tasks for {processing_id}")

            # Use advanced task extraction
            task_analysis = await self.task_engine.extract_tasks_advanced(
                email_data=email.email_data, existing_analysis=email.analysis
            )

            if task_analysis.tasks:
                # Convert to action items format and merge
                new_action_items = [task.description for task in task_analysis.tasks]

                # Merge with existing action items, avoiding duplicates
                existing_items = set(email.analysis.action_items or [])
                for item in new_action_items:
                    if item not in existing_items:
                        email.analysis.action_items.append(item)

                # Update urgency based on task analysis
                if task_analysis.overall_urgency > email.analysis.urgency_score:
                    email.analysis.urgency_score = task_analysis.overall_urgency

                    # Update urgency level
                    if task_analysis.overall_urgency >= 80:
                        email.analysis.urgency_level = UrgencyLevel.HIGH
                    elif task_analysis.overall_urgency >= 50:
                        email.analysis.urgency_level = UrgencyLevel.MEDIUM
                    else:
                        email.analysis.urgency_level = UrgencyLevel.LOW

                # Add task-related tags
                email.analysis.tags.append(
                    f"ai:tasks-extracted-{len(task_analysis.tasks)}"
                )

                if task_analysis.has_deadlines:
                    email.analysis.tags.append("ai:has-deadlines")

                if task_analysis.requires_followup:
                    email.analysis.tags.append("ai:requires-followup")

                # Update stats
                self.processing_stats["total_tasks_extracted"] += len(
                    task_analysis.tasks
                )

            logger.debug(
                f"Task extraction completed for {processing_id}: {len(task_analysis.tasks)} tasks found"
            )

        except Exception as e:
            logger.error(f"Task extraction failed for {processing_id}: {e}")
            email.analysis.tags.append("ai:task-extraction-error")

    async def _analyze_sentiment(
        self, email: ProcessedEmail, processing_id: str
    ) -> None:
        """Perform multi-dimensional sentiment analysis."""
        try:
            logger.debug(f"Analyzing sentiment for {processing_id}")

            # Perform advanced sentiment analysis
            sentiment_result = (
                await self.sentiment_engine.analyze_sentiment_comprehensive(
                    email_data=email.email_data, existing_analysis=email.analysis
                )
            )

            # Update sentiment information
            email.analysis.sentiment = (
                sentiment_result.sentiment_analysis.primary_emotion.value
            )

            # Enhance confidence based on AI analysis
            if (
                sentiment_result.sentiment_analysis.confidence
                > email.analysis.confidence
            ):
                email.analysis.confidence = (
                    sentiment_result.sentiment_analysis.confidence
                )

            # Add sentiment tags
            email.analysis.tags.append(
                f"ai:sentiment-{sentiment_result.sentiment_analysis.primary_emotion.value}"
            )
            email.analysis.tags.append(
                f"ai:tone-{sentiment_result.sentiment_analysis.professional_tone.value}"
            )

            # Add intent classification tags
            if sentiment_result.intent_analysis.primary_intent:
                email.analysis.tags.append(
                    f"ai:intent-{sentiment_result.intent_analysis.primary_intent.value}"
                )

            # Add urgency indicators from sentiment
            if sentiment_result.sentiment_analysis.urgency_level in [
                "immediate",
                "same_day",
            ]:
                email.analysis.tags.append("ai:urgent-sentiment")

            # Add conflict detection tags
            if sentiment_result.conflict_analysis.has_conflict:
                email.analysis.tags.append("ai:conflict-detected")
                if sentiment_result.conflict_analysis.escalation_risk > 0.7:
                    email.analysis.tags.append("ai:high-escalation-risk")

            # Add engagement tags
            if sentiment_result.engagement_analysis.satisfaction_score > 0.8:
                email.analysis.tags.append("ai:high-satisfaction")
            elif sentiment_result.engagement_analysis.satisfaction_score < 0.3:
                email.analysis.tags.append("ai:low-satisfaction")

            logger.debug(f"Sentiment analysis completed for {processing_id}")

        except Exception as e:
            logger.error(f"Sentiment analysis failed for {processing_id}: {e}")
            email.analysis.tags.append("ai:sentiment-analysis-error")

    async def _analyze_context(self, email: ProcessedEmail, processing_id: str) -> None:
        """Perform context analysis and relationship detection."""
        try:
            logger.debug(f"Analyzing context for {processing_id}")

            # For now, perform single-email context analysis
            # In the future, this could analyze email threads
            context_result = await self.context_engine.analyze_single_email(
                email_data=email.email_data, existing_analysis=email.analysis
            )

            # Add context-related keywords
            if context_result.context_keywords:
                for keyword in context_result.context_keywords:
                    if keyword not in email.analysis.keywords:
                        email.analysis.keywords.append(keyword)

            # Add context tags
            if context_result.organizational_context:
                email.analysis.tags.append(
                    f"ai:org-context-{context_result.organizational_context}"
                )

            if context_result.project_indicators:
                email.analysis.tags.append("ai:project-related")

            if context_result.requires_collaboration:
                email.analysis.tags.append("ai:collaboration-needed")

            logger.debug(f"Context analysis completed for {processing_id}")

        except Exception as e:
            logger.error(f"Context analysis failed for {processing_id}: {e}")
            email.analysis.tags.append("ai:context-analysis-error")

    async def _enhance_metadata(
        self, email: ProcessedEmail, processing_id: str
    ) -> None:
        """Add final AI-enhanced metadata."""
        try:
            # Add AI processing timestamp
            email.analysis.tags.append(f"ai:processed-{datetime.now().isoformat()}")

            # Add confidence level tags
            if email.analysis.confidence >= 0.9:
                email.analysis.tags.append("ai:high-confidence")
            elif email.analysis.confidence >= 0.7:
                email.analysis.tags.append("ai:medium-confidence")
            else:
                email.analysis.tags.append("ai:low-confidence")

            # Add comprehensive analysis tag
            email.analysis.tags.append("ai:comprehensive-analysis")

            # Deduplicate tags
            email.analysis.tags = list(set(email.analysis.tags))

            logger.debug(f"Metadata enhancement completed for {processing_id}")

        except Exception as e:
            logger.error(f"Metadata enhancement failed for {processing_id}: {e}")

    def _update_stats(self, processing_time: float) -> None:
        """Update processing statistics."""
        self.processing_stats["emails_processed"] += 1

        # Update average processing time using running average
        n = self.processing_stats["emails_processed"]
        current_avg = self.processing_stats["avg_processing_time"]
        self.processing_stats["avg_processing_time"] = (
            current_avg * (n - 1) + processing_time
        ) / n

    async def batch_process_emails(
        self, emails: List[ProcessedEmail]
    ) -> List[ProcessedEmail]:
        """
        Process multiple emails in batch for improved efficiency.

        Args:
            emails: List of emails to process

        Returns:
            List of enhanced emails
        """
        if not self.is_initialized:
            logger.warning("SambaNova plugin not initialized for batch processing")
            return emails

        if not self.config.batch_processing:
            # Fall back to individual processing
            return [await self.process_email(email) for email in emails]

        logger.info(f"Starting batch processing of {len(emails)} emails")

        try:
            # Process emails concurrently with controlled concurrency
            semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)

            async def process_with_semaphore(email):
                async with semaphore:
                    return await self.process_email(email)

            tasks = [process_with_semaphore(email) for email in emails]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions in results
            processed_emails = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Batch processing failed for email {emails[i].id}: {result}"
                    )
                    processed_emails.append(emails[i])  # Return original email
                else:
                    processed_emails.append(result)

            logger.info(
                f"Batch processing completed: {len(processed_emails)} emails processed"
            )
            return processed_emails

        except Exception as e:
            logger.error(f"Batch processing failed: {e}", exc_info=True)
            return emails  # Return original emails on failure

    async def analyze_email_thread(
        self, emails: List[ProcessedEmail]
    ) -> Dict[str, Any]:
        """
        Analyze an email thread for multi-email intelligence insights.

        Args:
            emails: List of emails in the thread (chronologically ordered)

        Returns:
            Dictionary containing thread intelligence analysis results
        """
        if not self.is_initialized or not self.thread_intelligence:
            logger.warning(
                "Thread intelligence not available, skipping thread analysis"
            )
            return {}

        try:
            logger.info(
                f"Starting thread intelligence analysis for {len(emails)} emails"
            )

            # Use ThreadIntelligenceEngine for comprehensive analysis
            conversation_summary = await self.thread_intelligence.analyze_thread(emails)

            # Convert to dictionary format for easy consumption
            thread_analysis = {
                "thread_id": conversation_summary.thread_id,
                "subject_line": conversation_summary.subject_line,
                "participants": conversation_summary.participants,
                "email_count": conversation_summary.email_count,
                "conversation_state": conversation_summary.conversation_state.value,
                "key_topics": conversation_summary.key_topics,
                "consensus_level": conversation_summary.consensus_level,
                "urgency_escalation": conversation_summary.urgency_escalation,
                "executive_summary": conversation_summary.executive_summary,
                "next_steps": conversation_summary.next_steps,
                "decisions_made": [
                    {
                        "id": decision.id,
                        "description": decision.description,
                        "decision_made": decision.decision_made,
                        "decision_maker": decision.decision_maker,
                        "confidence": decision.confidence,
                        "status": decision.status,
                    }
                    for decision in conversation_summary.decisions_made
                ],
                "action_items": [
                    {
                        "original_item": item.original_item,
                        "current_item": item.current_item,
                        "completion_status": item.completion_status,
                    }
                    for item in conversation_summary.action_items
                ],
                "stakeholder_profiles": [
                    {
                        "email_address": profile.email_address,
                        "role": profile.role.value,
                        "influence_score": profile.influence_score,
                        "participation_level": profile.participation_level,
                    }
                    for profile in conversation_summary.stakeholder_profiles
                ],
                "conflict_indicators": conversation_summary.conflict_indicators,
            }

            logger.info(
                f"Thread intelligence analysis completed for {conversation_summary.thread_id}"
            )
            return thread_analysis

        except Exception as e:
            logger.error(f"Thread intelligence analysis failed: {e}", exc_info=True)
            return {}

    async def batch_analyze_threads(
        self, thread_groups: List[List[ProcessedEmail]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple email threads for intelligence insights.

        Args:
            thread_groups: List of email thread lists

        Returns:
            List of thread analysis results
        """
        if not self.is_initialized or not self.thread_intelligence:
            logger.warning(
                "Thread intelligence not available, skipping batch thread analysis"
            )
            return []

        try:
            logger.info(
                f"Starting batch thread intelligence analysis for {len(thread_groups)} threads"
            )

            # Use ThreadIntelligenceEngine for batch analysis
            conversation_summaries = (
                await self.thread_intelligence.batch_analyze_threads(thread_groups)
            )

            # Convert summaries to dictionary format
            thread_analyses = []
            for summary in conversation_summaries:
                thread_analysis = {
                    "thread_id": summary.thread_id,
                    "subject_line": summary.subject_line,
                    "participants": summary.participants,
                    "email_count": summary.email_count,
                    "conversation_state": summary.conversation_state.value,
                    "key_topics": summary.key_topics,
                    "consensus_level": summary.consensus_level,
                    "urgency_escalation": summary.urgency_escalation,
                    "executive_summary": summary.executive_summary,
                    "next_steps": summary.next_steps,
                    "decisions_count": len(summary.decisions_made),
                    "action_items_count": len(summary.action_items),
                    "stakeholders_count": len(summary.stakeholder_profiles),
                    "conflicts_detected": len(summary.conflict_indicators),
                }
                thread_analyses.append(thread_analysis)

            logger.info(
                f"Batch thread analysis completed: {len(thread_analyses)} threads analyzed"
            )
            return thread_analyses

        except Exception as e:
            logger.error(f"Batch thread analysis failed: {e}", exc_info=True)
            return []

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get plugin processing statistics."""
        stats = {
            **self.processing_stats,
            "plugin_name": self.get_name(),
            "plugin_version": self.get_version(),
            "is_initialized": self.is_initialized,
            "config_model": self.config.model if self.config else None,
        }

        # Add thread intelligence statistics if available
        if self.thread_intelligence and self.thread_intelligence.is_initialized:
            thread_stats = self.thread_intelligence.get_statistics()
            stats["thread_intelligence"] = thread_stats

        return stats

    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        try:
            logger.info("Cleaning up SambaNova AI plugin...")

            if self.sambanova_interface:
                await self.sambanova_interface.cleanup()

            if self.task_engine:
                await self.task_engine.cleanup()

            if self.context_engine:
                await self.context_engine.cleanup()

            if self.sentiment_engine:
                await self.sentiment_engine.cleanup()

            if self.thread_intelligence:
                await self.thread_intelligence.cleanup()

            if self.performance_optimizer:
                await self.performance_optimizer.cleanup()

            self.is_initialized = False
            logger.info("SambaNova AI plugin cleanup completed")

        except Exception as e:
            logger.error(f"Error during SambaNova plugin cleanup: {e}", exc_info=True)

    # === Performance Monitoring Methods ===

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        if not self.performance_optimizer:
            return {"error": "Performance optimizer not initialized"}

        return self.performance_optimizer.get_performance_report()

    async def optimize_api_request(
        self, request_key: str, content: str, request_func, fallback_func=None, **kwargs
    ) -> Any:
        """
        Optimize API request with performance enhancements.

        This method wraps API calls with:
        - Intelligent caching with similarity detection
        - Rate limiting and quota management
        - Fallback mechanisms for failures
        - Cost tracking and budget management
        """
        if not self.performance_optimizer:
            logger.warning("Performance optimizer not available, making direct request")
            return await request_func(**kwargs)

        return await self.performance_optimizer.optimize_request(
            request_key=request_key,
            content=content,
            request_func=request_func,
            fallback_func=fallback_func,
            **kwargs,
        )

    def configure_performance_settings(self, settings: Dict[str, Any]):
        """Configure performance optimization settings."""
        if not self.performance_optimizer:
            logger.warning("Performance optimizer not available")
            return

        if "daily_budget" in settings:
            self.performance_optimizer.daily_budget = settings["daily_budget"]

        if "cost_per_token" in settings:
            self.performance_optimizer.cost_per_token = settings["cost_per_token"]

        if "rate_limit" in settings:
            rate_config = settings["rate_limit"]
            self.performance_optimizer.rate_limiter.config.requests_per_minute = (
                rate_config.get("per_minute", 60)
            )
            self.performance_optimizer.rate_limiter.config.requests_per_hour = (
                rate_config.get("per_hour", 1000)
            )
            self.performance_optimizer.rate_limiter.config.requests_per_day = (
                rate_config.get("per_day", 10000)
            )

        logger.info("Performance settings updated")

    # === MCP Tool Methods ===
    # These methods are called by the MCP server tools for AI-powered analysis

    async def extract_tasks_with_context(
        self,
        email_content: str,
        email_subject: str,
        context: str = "",
        priority_threshold: str = "medium",
    ) -> Dict[str, Any]:
        """
        Extract tasks from email content with additional context awareness.

        Args:
            email_content: The email body text to analyze
            email_subject: The email subject line
            context: Additional context information
            priority_threshold: Priority threshold ('low', 'medium', 'high')

        Returns:
            Dictionary containing extracted tasks with context and metadata
        """
        if not self.is_initialized or not self.task_engine:
            logger.warning("SambaNova plugin not initialized for task extraction")
            return {
                "error": "SambaNova AI plugin not available",
                "tasks": [],
                "context_analysis": {},
                "processing_metadata": {},
            }

        try:
            logger.info(
                f"Extracting tasks with context - Subject: {email_subject[:50]}..."
            )

            # Create temporary EmailData for task extraction
            from datetime import datetime

            temp_email_data = EmailData(
                message_id=f"temp-task-extraction-{int(datetime.now().timestamp())}",
                from_email="analysis@inboxzen.com",
                to_emails=["recipient@example.com"],
                subject=email_subject,
                text_body=email_content,
                html_body=None,
                received_at=datetime.now(),
            )

            # Perform advanced task extraction with performance optimization
            request_key = f"extract_tasks_{hashlib.md5((email_content + email_subject + context).encode()).hexdigest()}"

            async def task_extraction_request():
                return await self.task_engine.extract_tasks_advanced(
                    email_data=temp_email_data, existing_analysis=None
                )

            async def fallback_extraction():
                # Simple fallback using helper methods
                return {
                    "tasks": [
                        {
                            "description": "Review email content for actionable items",
                            "urgency_score": 50,
                            "confidence": 0.7,
                            "due_date": None,
                            "priority": "medium",
                            "assigned_to": None,
                            "context_keywords": self._extract_action_words(
                                email_content
                            ),
                        }
                    ],
                    "overall_urgency": "medium",
                    "has_deadlines": False,
                    "requires_followup": True,
                }

            # Use performance optimizer if available
            if self.performance_optimizer:
                task_analysis = await self.optimize_api_request(
                    request_key=request_key,
                    content=email_content + " " + email_subject,
                    request_func=task_extraction_request,
                    fallback_func=fallback_extraction,
                )
            else:
                task_analysis = await task_extraction_request()

            # Convert priority threshold to numeric value
            threshold_map = {"low": 30, "medium": 50, "high": 70}
            numeric_threshold = threshold_map.get(priority_threshold.lower(), 50)

            # Filter tasks by priority threshold
            filtered_tasks = []
            for task in task_analysis.tasks:
                if task.urgency_score >= numeric_threshold:
                    filtered_tasks.append(
                        {
                            "description": task.description,
                            "urgency_score": task.urgency_score,
                            "confidence": task.confidence,
                            "due_date": (
                                task.due_date.isoformat() if task.due_date else None
                            ),
                            "priority": (
                                task.priority.value if task.priority else "medium"
                            ),
                            "assigned_to": task.assigned_to,
                            "context_keywords": task.context_keywords or [],
                        }
                    )

            # Add context analysis
            context_analysis = {
                "subject_analysis": {
                    "urgency_indicators": self._extract_urgency_indicators(
                        email_subject
                    ),
                    "temporal_references": self._extract_temporal_references(
                        email_subject
                    ),
                },
                "content_analysis": {
                    "urgency_indicators": self._extract_urgency_indicators(
                        email_content
                    ),
                    "temporal_references": self._extract_temporal_references(
                        email_content
                    ),
                    "action_words": self._extract_action_words(email_content),
                },
                "additional_context": (
                    context if context else "No additional context provided"
                ),
            }

            result = {
                "tasks": filtered_tasks,
                "total_tasks_found": len(task_analysis.tasks),
                "filtered_tasks_count": len(filtered_tasks),
                "priority_threshold": priority_threshold,
                "overall_urgency": task_analysis.overall_urgency,
                "has_deadlines": task_analysis.has_deadlines,
                "requires_followup": task_analysis.requires_followup,
                "context_analysis": context_analysis,
                "processing_metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "processing_engine": "sambanova-task-extraction",
                    "email_length": len(email_content),
                    "subject_length": len(email_subject),
                    "context_provided": bool(context),
                },
            }

            logger.info(
                f"Task extraction completed: {len(filtered_tasks)} tasks found above threshold"
            )
            return result

        except Exception as e:
            logger.error(f"Task extraction with context failed: {e}", exc_info=True)
            return {
                "error": f"Task extraction failed: {str(e)}",
                "tasks": [],
                "context_analysis": {},
                "processing_metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "error": str(e),
                },
            }

    async def analyze_email_context(
        self, thread_data: List[ProcessedEmail], analysis_depth: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Analyze email context and relationships within a thread.

        Args:
            thread_data: List of ProcessedEmail objects in the thread
            analysis_depth: Analysis depth ('basic', 'detailed', 'comprehensive')

        Returns:
            Dictionary containing context analysis results
        """
        if not self.is_initialized or not self.context_engine:
            logger.warning("SambaNova plugin not initialized for context analysis")
            return {
                "error": "SambaNova AI context analysis not available",
                "context_analysis": {},
                "thread_metadata": {},
            }

        try:
            logger.info(
                f"Analyzing email context for {len(thread_data)} emails with {analysis_depth} depth"
            )

            if not thread_data:
                return {
                    "error": "No email data provided for context analysis",
                    "context_analysis": {},
                    "thread_metadata": {},
                }

            # Perform context analysis on the thread
            primary_email = thread_data[0]
            context_result = await self.context_engine.analyze_single_email(
                email_data=primary_email.email_data,
                existing_analysis=primary_email.analysis,
            )

            # Enhanced thread analysis
            thread_participants = set()
            thread_subjects = set()
            urgency_progression = []
            sentiment_progression = []

            for email in thread_data:
                thread_participants.add(email.email_data.from_email)
                thread_participants.update(email.email_data.to_emails)
                thread_subjects.add(email.email_data.subject)

                if email.analysis:
                    urgency_progression.append(
                        {
                            "email_id": email.id,
                            "urgency_score": email.analysis.urgency_score,
                            "timestamp": email.email_data.received_at.isoformat(),
                        }
                    )
                    sentiment_progression.append(
                        {
                            "email_id": email.id,
                            "sentiment": email.analysis.sentiment,
                            "timestamp": email.email_data.received_at.isoformat(),
                        }
                    )

            # Calculate relationship metrics
            relationship_analysis = {
                "thread_coherence": len(thread_subjects) == 1,  # Same subject
                "participant_count": len(thread_participants),
                "participants": list(thread_participants),
                "subject_variations": list(thread_subjects),
                "urgency_trend": self._analyze_urgency_trend(urgency_progression),
                "sentiment_trend": self._analyze_sentiment_trend(sentiment_progression),
                "conversation_flow": self._analyze_conversation_flow(thread_data),
            }

            # Context insights
            context_insights = {
                "organizational_context": context_result.organizational_context,
                "project_indicators": context_result.project_indicators,
                "collaboration_required": context_result.requires_collaboration,
                "decision_points": self._identify_decision_points(thread_data),
                "action_dependencies": self._identify_action_dependencies(thread_data),
                "stakeholder_roles": self._analyze_stakeholder_roles(thread_data),
            }

            result = {
                "context_analysis": {
                    "thread_summary": f"Email thread with {len(thread_data)} messages between {len(thread_participants)} participants",
                    "primary_context": context_result.organizational_context,
                    "context_keywords": context_result.context_keywords,
                    "relationship_analysis": relationship_analysis,
                    "context_insights": context_insights,
                },
                "thread_metadata": {
                    "analysis_depth": analysis_depth,
                    "email_count": len(thread_data),
                    "time_span": self._calculate_thread_timespan(thread_data),
                    "processed_at": datetime.now().isoformat(),
                    "processing_engine": "sambanova-context-analysis",
                },
            }

            logger.info(f"Context analysis completed for {len(thread_data)} emails")
            return result

        except Exception as e:
            logger.error(f"Email context analysis failed: {e}", exc_info=True)
            return {
                "error": f"Context analysis failed: {str(e)}",
                "context_analysis": {},
                "thread_metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "error": str(e),
                },
            }

    async def summarize_email_thread(
        self,
        thread_data: List[ProcessedEmail],
        summary_type: str = "executive",
        include_decisions: bool = True,
        include_action_items: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of an email thread.

        Args:
            thread_data: List of ProcessedEmail objects to summarize
            summary_type: Type of summary ('brief', 'executive', 'detailed')
            include_decisions: Whether to include decision analysis
            include_action_items: Whether to include action items

        Returns:
            Dictionary containing thread summary and analysis
        """
        if not self.is_initialized or not self.thread_intelligence:
            logger.warning("SambaNova plugin not initialized for thread summarization")
            return {
                "error": "SambaNova AI thread intelligence not available",
                "summary": {},
                "metadata": {},
            }

        try:
            logger.info(
                f"Summarizing email thread: {len(thread_data)} emails, type: {summary_type}"
            )

            if not thread_data:
                return {
                    "error": "No email data provided for summarization",
                    "summary": {},
                    "metadata": {},
                }

            # Use ThreadIntelligenceEngine for comprehensive analysis
            conversation_summary = await self.thread_intelligence.analyze_thread(
                thread_data
            )

            # Build summary based on type
            if summary_type == "brief":
                summary_content = self._generate_brief_summary(conversation_summary)
            elif summary_type == "executive":
                summary_content = self._generate_executive_summary(conversation_summary)
            else:  # detailed
                summary_content = self._generate_detailed_summary(conversation_summary)

            # Extract decisions if requested
            decisions = []
            if include_decisions and conversation_summary.decisions_made:
                for decision in conversation_summary.decisions_made:
                    decisions.append(
                        {
                            "description": decision.description,
                            "decision_made": decision.decision_made,
                            "decision_maker": decision.decision_maker,
                            "confidence": decision.confidence,
                            "status": decision.status,
                            "context": decision.context_factors,
                        }
                    )

            # Extract action items if requested
            action_items = []
            if include_action_items and conversation_summary.action_items:
                for item in conversation_summary.action_items:
                    action_items.append(
                        {
                            "original_item": item.original_item,
                            "current_item": item.current_item,
                            "completion_status": item.completion_status,
                            "assigned_to": getattr(item, "assigned_to", None),
                            "due_date": getattr(item, "due_date", None),
                        }
                    )

            result = {
                "summary": {
                    "thread_id": conversation_summary.thread_id,
                    "subject_line": conversation_summary.subject_line,
                    "summary_type": summary_type,
                    "content": summary_content,
                    "key_topics": conversation_summary.key_topics,
                    "participants": conversation_summary.participants,
                    "conversation_state": conversation_summary.conversation_state.value,
                    "consensus_level": conversation_summary.consensus_level,
                    "urgency_escalation": conversation_summary.urgency_escalation,
                },
                "decisions": decisions if include_decisions else None,
                "action_items": action_items if include_action_items else None,
                "metadata": {
                    "email_count": conversation_summary.email_count,
                    "summary_type": summary_type,
                    "include_decisions": include_decisions,
                    "include_action_items": include_action_items,
                    "processed_at": datetime.now().isoformat(),
                    "processing_engine": "sambanova-thread-intelligence",
                    "confidence_score": getattr(
                        conversation_summary, "confidence_score", 0.85
                    ),
                },
            }

            logger.info(
                f"Thread summarization completed: {summary_type} summary generated"
            )
            return result

        except Exception as e:
            logger.error(f"Thread summarization failed: {e}", exc_info=True)
            return {
                "error": f"Thread summarization failed: {str(e)}",
                "summary": {},
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "error": str(e),
                },
            }

    async def detect_urgency_with_context(
        self,
        email_data: EmailData,
        sender_context: str = "",
        business_hours: bool = True,
    ) -> Dict[str, Any]:
        """
        Detect urgency level with enhanced context awareness.

        Args:
            email_data: EmailData object to analyze
            sender_context: Context about the sender
            business_hours: Whether the email was sent during business hours

        Returns:
            Dictionary containing urgency analysis results
        """
        if not self.is_initialized or not self.sentiment_engine:
            logger.warning("SambaNova plugin not initialized for urgency detection")
            return {
                "error": "SambaNova AI urgency detection not available",
                "urgency_analysis": {},
                "context_factors": {},
            }

        try:
            logger.info(
                f"Detecting urgency with context for email: {email_data.subject[:50]}..."
            )

            # Perform comprehensive sentiment analysis (includes urgency)
            sentiment_result = (
                await self.sentiment_engine.analyze_sentiment_comprehensive(
                    email_data=email_data, existing_analysis=None
                )
            )

            # Calculate base urgency score
            base_urgency = sentiment_result.sentiment_analysis.urgency_level
            urgency_score = self._calculate_urgency_score(base_urgency)

            # Context factors that influence urgency
            context_factors = {
                "sender_context": {
                    "description": (
                        sender_context
                        if sender_context
                        else "No sender context provided"
                    ),
                    "authority_indicators": self._detect_authority_indicators(
                        sender_context
                    ),
                    "relationship_type": self._determine_relationship_type(
                        sender_context
                    ),
                },
                "temporal_context": {
                    "business_hours": business_hours,
                    "time_sensitivity": self._analyze_time_sensitivity(
                        email_data.text_body or ""
                    ),
                    "deadline_proximity": self._analyze_deadline_proximity(
                        email_data.text_body or ""
                    ),
                },
                "content_context": {
                    "escalation_language": self._detect_escalation_language(
                        email_data.text_body or ""
                    ),
                    "emotional_intensity": sentiment_result.sentiment_analysis.emotional_intensity,
                    "formal_tone": sentiment_result.sentiment_analysis.professional_tone.value,
                },
            }

            # Apply context adjustments to urgency score
            adjusted_urgency = self._apply_context_adjustments(
                urgency_score, context_factors, business_hours
            )

            # Determine final urgency level
            if adjusted_urgency >= 80:
                urgency_level = "critical"
            elif adjusted_urgency >= 65:
                urgency_level = "high"
            elif adjusted_urgency >= 40:
                urgency_level = "medium"
            else:
                urgency_level = "low"

            result = {
                "urgency_analysis": {
                    "urgency_level": urgency_level,
                    "urgency_score": adjusted_urgency,
                    "base_urgency_score": urgency_score,
                    "confidence": sentiment_result.sentiment_analysis.confidence,
                    "urgency_indicators": self._extract_urgency_indicators(
                        email_data.text_body or ""
                    ),
                    "recommended_response_time": self._calculate_response_time(
                        adjusted_urgency
                    ),
                    "escalation_risk": sentiment_result.conflict_analysis.escalation_risk,
                },
                "context_factors": context_factors,
                "processing_metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "processing_engine": "sambanova-urgency-detection",
                    "context_applied": bool(sender_context),
                    "business_hours_considered": business_hours,
                    "analysis_confidence": sentiment_result.sentiment_analysis.confidence,
                },
            }

            logger.info(
                f"Urgency detection completed: {urgency_level} ({adjusted_urgency}/100)"
            )
            return result

        except Exception as e:
            logger.error(f"Urgency detection with context failed: {e}", exc_info=True)
            return {
                "error": f"Urgency detection failed: {str(e)}",
                "urgency_analysis": {},
                "context_factors": {},
                "processing_metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "error": str(e),
                },
            }

    async def suggest_email_response(
        self,
        processed_email: ProcessedEmail,
        response_type: str = "detailed",
        tone: str = "professional",
        include_action_items: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate intelligent email response suggestions.

        Args:
            processed_email: ProcessedEmail object to respond to
            response_type: Type of response ('brief', 'detailed', 'comprehensive')
            tone: Response tone ('professional', 'friendly', 'formal', 'casual')
            include_action_items: Whether to include action items in response

        Returns:
            Dictionary containing response suggestions and analysis
        """
        if not self.is_initialized or not self.sentiment_engine:
            logger.warning("SambaNova plugin not initialized for response suggestions")
            return {
                "error": "SambaNova AI response suggestion not available",
                "response_suggestions": {},
                "analysis": {},
            }

        try:
            logger.info(
                f"Generating response suggestions for email: {processed_email.email_data.subject[:50]}..."
            )

            # Analyze the email for response context
            sentiment_result = (
                await self.sentiment_engine.analyze_sentiment_comprehensive(
                    email_data=processed_email.email_data,
                    existing_analysis=processed_email.analysis,
                )
            )

            # Generate response framework
            response_framework = self._generate_response_framework(
                processed_email, sentiment_result, response_type, tone
            )

            # Create response suggestions
            response_suggestions = {
                "primary_response": self._generate_primary_response(
                    processed_email, response_framework, tone
                ),
                "alternative_responses": self._generate_alternative_responses(
                    processed_email, response_framework, tone
                ),
                "key_points_to_address": self._identify_key_points(processed_email),
                "suggested_tone_adjustments": self._suggest_tone_adjustments(
                    sentiment_result, tone
                ),
            }

            # Add action items if requested
            if (
                include_action_items
                and processed_email.analysis
                and processed_email.analysis.action_items
            ):
                response_suggestions["action_items_to_acknowledge"] = [
                    {
                        "original_item": item,
                        "suggested_acknowledgment": self._generate_acknowledgment(
                            item, tone
                        ),
                    }
                    for item in processed_email.analysis.action_items[
                        :5
                    ]  # Limit to 5 items
                ]

            # Response analysis
            analysis = {
                "email_intent": (
                    sentiment_result.intent_analysis.primary_intent.value
                    if sentiment_result.intent_analysis.primary_intent
                    else "unknown"
                ),
                "response_urgency": self._calculate_response_urgency(processed_email),
                "complexity_assessment": self._assess_response_complexity(
                    processed_email
                ),
                "stakeholder_considerations": self._analyze_stakeholders(
                    processed_email
                ),
                "follow_up_requirements": self._determine_follow_up_needs(
                    processed_email
                ),
                "emotional_considerations": {
                    "sender_emotion": sentiment_result.sentiment_analysis.primary_emotion.value,
                    "recommended_empathy_level": self._recommend_empathy_level(
                        sentiment_result
                    ),
                    "conflict_mitigation": sentiment_result.conflict_analysis.has_conflict,
                },
            }

            result = {
                "response_suggestions": response_suggestions,
                "analysis": analysis,
                "metadata": {
                    "response_type": response_type,
                    "tone": tone,
                    "include_action_items": include_action_items,
                    "processed_at": datetime.now().isoformat(),
                    "processing_engine": "sambanova-response-generation",
                    "confidence": sentiment_result.sentiment_analysis.confidence,
                    "original_email_urgency": (
                        processed_email.analysis.urgency_score
                        if processed_email.analysis
                        else 0
                    ),
                },
            }

            logger.info(
                f"Response suggestions generated: {response_type} response with {tone} tone"
            )
            return result

        except Exception as e:
            logger.error(f"Email response suggestion failed: {e}", exc_info=True)
            return {
                "error": f"Response suggestion failed: {str(e)}",
                "response_suggestions": {},
                "analysis": {},
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "error": str(e),
                },
            }

    # === Helper Methods for MCP Tool Support ===

    def _extract_urgency_indicators(self, text: str) -> List[str]:
        """Extract urgency indicators from text."""
        urgency_patterns = [
            r"\b(urgent|asap|immediately|critical|emergency)\b",
            r"\b(deadline|due|expires?)\b",
            r"\b(priority|important|crucial)\b",
            r"!+",  # Exclamation marks
        ]

        indicators = []
        for pattern in urgency_patterns:
            import re

            matches = re.findall(pattern, text.lower())
            indicators.extend(matches)

        return list(set(indicators))  # Remove duplicates

    def _extract_temporal_references(self, text: str) -> List[str]:
        """Extract temporal references from text."""
        temporal_patterns = [
            r"\b(today|tomorrow|yesterday)\b",
            r"\b(this|next|last)\s+(week|month|year)\b",
            r"\b\d{1,2}[:/]\d{1,2}\b",  # Time patterns
            r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        ]

        references = []
        for pattern in temporal_patterns:
            import re

            matches = re.findall(pattern, text.lower())
            if matches:
                # Handle both string matches and tuple matches
                for match in matches:
                    if isinstance(match, tuple):
                        references.extend([item for item in match if item])
                    elif isinstance(match, str) and match:
                        references.append(match)

        return list(set(references))

    def _extract_action_words(self, text: str) -> List[str]:
        """Extract action words from text."""
        action_patterns = [
            r"\b(please|kindly)\s+(\w+)\b",
            r"\b(need|want|require)\s+to\s+(\w+)\b",
            r"\b(can|could|would)\s+you\s+(\w+)\b",
            r"\b(review|check|verify|confirm|send|provide|update)\b",
        ]

        actions = []
        for pattern in action_patterns:
            import re

            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    actions.extend([word for word in match if word])
                else:
                    actions.append(match)

        return list(set(actions))

    # === Helper Methods for Email Analysis ===

    def _analyze_urgency_trend(self, urgency_progression: List[Dict[str, Any]]) -> str:
        """Analyze urgency trend in email thread."""
        if len(urgency_progression) < 2:
            return "insufficient_data"

        scores = [item["urgency_score"] for item in urgency_progression]
        if len(scores) < 2:
            return "stable"

        # Calculate trend
        first_half = scores[: len(scores) // 2]
        second_half = scores[len(scores) // 2 :]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        difference = avg_second - avg_first

        if difference > 10:
            return "escalating"
        elif difference < -10:
            return "de-escalating"
        else:
            return "stable"

    def _analyze_sentiment_trend(
        self, sentiment_progression: List[Dict[str, Any]]
    ) -> str:
        """Analyze sentiment trend in email thread."""
        if len(sentiment_progression) < 2:
            return "insufficient_data"

        sentiments = [item["sentiment"] for item in sentiment_progression]

        # Simple sentiment scoring for trend analysis
        sentiment_scores = []
        for sentiment in sentiments:
            if sentiment == "positive":
                sentiment_scores.append(1)
            elif sentiment == "negative":
                sentiment_scores.append(-1)
            else:
                sentiment_scores.append(0)

        if len(sentiment_scores) < 2:
            return "stable"

        # Calculate trend
        first_half = sentiment_scores[: len(sentiment_scores) // 2]
        second_half = sentiment_scores[len(sentiment_scores) // 2 :]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        difference = avg_second - avg_first

        if difference > 0.3:
            return "improving"
        elif difference < -0.3:
            return "deteriorating"
        else:
            return "stable"

    def _analyze_conversation_flow(
        self, thread_data: List[ProcessedEmail]
    ) -> Dict[str, Any]:
        """Analyze conversation flow patterns."""
        if not thread_data:
            return {"pattern": "empty", "participants": 0, "response_rate": 0}

        participants = set()
        response_times = []

        for i, email in enumerate(thread_data):
            participants.add(email.email_data.from_email)
            participants.update(email.email_data.to_emails)

            # Calculate response time if not first email
            if i > 0:
                prev_email = thread_data[i - 1]
                time_diff = (
                    email.email_data.received_at - prev_email.email_data.received_at
                )
                response_times.append(time_diff.total_seconds() / 3600)  # hours

        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        # Determine conversation pattern
        if len(thread_data) == 1:
            pattern = "initial"
        elif avg_response_time < 1:  # < 1 hour
            pattern = "rapid"
        elif avg_response_time < 24:  # < 1 day
            pattern = "normal"
        else:
            pattern = "slow"

        return {
            "pattern": pattern,
            "participants": len(participants),
            "email_count": len(thread_data),
            "avg_response_time_hours": avg_response_time,
            "response_rate": (
                len(response_times) / len(thread_data) if thread_data else 0
            ),
        }

    def _identify_decision_points(
        self, thread_data: List[ProcessedEmail]
    ) -> List[Dict[str, Any]]:
        """Identify decision points in email thread."""
        decision_keywords = [
            "decide",
            "decision",
            "choose",
            "option",
            "alternative",
            "approve",
            "reject",
            "accept",
            "decline",
            "agree",
            "disagree",
        ]

        decision_points = []

        for email in thread_data:
            content = (email.email_data.text_body or "").lower()
            subject = email.email_data.subject.lower()

            # Check for decision keywords
            decisions_found = []
            for keyword in decision_keywords:
                if keyword in content or keyword in subject:
                    decisions_found.append(keyword)

            if decisions_found:
                decision_points.append(
                    {
                        "email_id": email.id,
                        "sender": email.email_data.from_email,
                        "timestamp": email.email_data.received_at.isoformat(),
                        "decision_indicators": decisions_found,
                        "subject": email.email_data.subject,
                    }
                )

        return decision_points

    def _identify_action_dependencies(
        self, thread_data: List[ProcessedEmail]
    ) -> List[Dict[str, Any]]:
        """Identify action dependencies in email thread."""
        dependency_keywords = [
            "after",
            "before",
            "once",
            "when",
            "until",
            "depends on",
            "waiting for",
            "blocked by",
            "requires",
            "needs",
        ]

        dependencies = []

        for email in thread_data:
            content = (email.email_data.text_body or "").lower()

            for keyword in dependency_keywords:
                if keyword in content:
                    # Extract context around the keyword
                    start = max(0, content.find(keyword) - 50)
                    end = min(len(content), content.find(keyword) + 100)
                    context = content[start:end].strip()

                    dependencies.append(
                        {
                            "email_id": email.id,
                            "dependency_type": keyword,
                            "context": context,
                            "sender": email.email_data.from_email,
                            "timestamp": email.email_data.received_at.isoformat(),
                        }
                    )

        return dependencies

    def _analyze_stakeholder_roles(
        self, thread_data: List[ProcessedEmail]
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze stakeholder roles in email thread."""
        stakeholders = {}

        for email in thread_data:
            sender = email.email_data.from_email

            if sender not in stakeholders:
                stakeholders[sender] = {
                    "email_count": 0,
                    "first_contact": email.email_data.received_at,
                    "last_contact": email.email_data.received_at,
                    "role_indicators": [],
                    "urgency_scores": [],
                }

            stakeholders[sender]["email_count"] += 1
            stakeholders[sender]["last_contact"] = max(
                stakeholders[sender]["last_contact"], email.email_data.received_at
            )

            if email.analysis:
                stakeholders[sender]["urgency_scores"].append(
                    email.analysis.urgency_score
                )

            # Add recipients as stakeholders too
            for recipient in email.email_data.to_emails:
                if recipient not in stakeholders:
                    stakeholders[recipient] = {
                        "email_count": 0,
                        "first_contact": email.email_data.received_at,
                        "last_contact": email.email_data.received_at,
                        "role_indicators": ["recipient"],
                        "urgency_scores": [],
                    }

        # Calculate average urgency for each stakeholder
        for stakeholder_data in stakeholders.values():
            if stakeholder_data["urgency_scores"]:
                stakeholder_data["avg_urgency"] = sum(
                    stakeholder_data["urgency_scores"]
                ) / len(stakeholder_data["urgency_scores"])
            else:
                stakeholder_data["avg_urgency"] = 0

        return stakeholders

    def _calculate_thread_timespan(
        self, thread_data: List[ProcessedEmail]
    ) -> Dict[str, Any]:
        """Calculate timespan information for email thread."""
        if not thread_data:
            return {"duration_hours": 0, "start_time": None, "end_time": None}

        timestamps = [email.email_data.received_at for email in thread_data]
        start_time = min(timestamps)
        end_time = max(timestamps)

        duration = end_time - start_time
        duration_hours = duration.total_seconds() / 3600

        return {
            "duration_hours": duration_hours,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "email_count": len(thread_data),
        }

    def _generate_brief_summary(self, conversation_summary) -> str:
        """Generate brief summary from conversation analysis."""
        return (
            f"Email thread with {conversation_summary.email_count} messages. "
            f"Key topics: {', '.join(conversation_summary.key_topics[:3])}. "
            f"Status: {conversation_summary.conversation_state.value}."
        )

    def _generate_executive_summary(self, conversation_summary) -> str:
        """Generate executive summary from conversation analysis."""
        summary = f"Thread Summary: {conversation_summary.subject_line}\n\n"
        summary += f"Participants: {len(conversation_summary.participants)} people\n"
        summary += f"Messages: {conversation_summary.email_count}\n"
        summary += f"Status: {conversation_summary.conversation_state.value}\n\n"
        summary += f"Key Topics: {', '.join(conversation_summary.key_topics)}\n\n"

        if conversation_summary.executive_summary:
            summary += (
                f"Executive Summary: {conversation_summary.executive_summary}\n\n"
            )

        if conversation_summary.next_steps:
            summary += f"Next Steps: {', '.join(conversation_summary.next_steps)}"

        return summary

    def _generate_detailed_summary(self, conversation_summary) -> str:
        """Generate detailed summary from conversation analysis."""
        summary = self._generate_executive_summary(conversation_summary)
        summary += "\n\nDetailed Analysis:\n"
        summary += f"Consensus Level: {conversation_summary.consensus_level}\n"
        summary += f"Urgency Escalation: {conversation_summary.urgency_escalation}\n"
        summary += f"Decisions Made: {len(conversation_summary.decisions_made)}\n"
        summary += f"Action Items: {len(conversation_summary.action_items)}\n"
        summary += f"Stakeholders: {len(conversation_summary.stakeholder_profiles)}\n"

        if conversation_summary.conflict_indicators:
            summary += (
                f"Conflicts Detected: {len(conversation_summary.conflict_indicators)}"
            )

        return summary

    def _detect_authority_indicators(self, sender_context: str) -> List[str]:
        """Detect authority indicators in sender context."""
        authority_keywords = [
            "ceo",
            "cto",
            "cfo",
            "president",
            "director",
            "manager",
            "lead",
            "senior",
            "head",
            "chief",
            "boss",
            "supervisor",
        ]

        indicators = []
        context_lower = sender_context.lower()

        for keyword in authority_keywords:
            if keyword in context_lower:
                indicators.append(keyword)

        return indicators

    def _determine_relationship_type(self, sender_context: str) -> str:
        """Determine relationship type from sender context."""
        context_lower = sender_context.lower()

        if any(
            word in context_lower
            for word in ["boss", "manager", "director", "ceo", "supervisor"]
        ):
            return "superior"
        elif any(
            word in context_lower for word in ["team", "colleague", "peer", "coworker"]
        ):
            return "peer"
        elif any(word in context_lower for word in ["report", "subordinate", "junior"]):
            return "subordinate"
        elif any(word in context_lower for word in ["client", "customer", "external"]):
            return "external"
        else:
            return "unknown"

    def _analyze_time_sensitivity(self, content: str) -> Dict[str, Any]:
        """Analyze time sensitivity indicators in content."""
        time_patterns = [
            (r"\b(today|now|immediately|asap)\b", "immediate"),
            (r"\b(tomorrow|next day)\b", "urgent"),
            (r"\b(this week|end of week)\b", "short_term"),
            (r"\b(next week|next month)\b", "medium_term"),
            (r"\b(deadline|due date|expires?)\b", "deadline"),
        ]

        import re

        sensitivity_indicators = []
        max_sensitivity = "low"

        for pattern, sensitivity in time_patterns:
            matches = re.findall(pattern, content.lower())
            if matches:
                sensitivity_indicators.extend(matches)
                if sensitivity == "immediate":
                    max_sensitivity = "immediate"
                elif sensitivity == "urgent" and max_sensitivity != "immediate":
                    max_sensitivity = "urgent"
                elif sensitivity in [
                    "short_term",
                    "deadline",
                ] and max_sensitivity not in ["immediate", "urgent"]:
                    max_sensitivity = "medium"

        return {
            "level": max_sensitivity,
            "indicators": sensitivity_indicators,
            "count": len(sensitivity_indicators),
        }

    def _analyze_deadline_proximity(self, content: str) -> Dict[str, Any]:
        """Analyze deadline proximity in content."""
        import re
        from datetime import datetime, timedelta

        deadline_patterns = [
            r"\b(today|now)\b",
            r"\b(tomorrow)\b",
            r"\b(this week)\b",
            r"\b(next week)\b",
            r"\b(\d{1,2}[:/]\d{1,2})\b",  # Time patterns
        ]

        deadlines_found = []
        proximity_score = 0

        for pattern in deadline_patterns:
            matches = re.findall(pattern, content.lower())
            if matches:
                deadlines_found.extend(matches)
                if "today" in pattern or "now" in pattern:
                    proximity_score = max(proximity_score, 100)
                elif "tomorrow" in pattern:
                    proximity_score = max(proximity_score, 80)
                elif "this week" in pattern:
                    proximity_score = max(proximity_score, 60)
                elif "next week" in pattern:
                    proximity_score = max(proximity_score, 40)

        if proximity_score >= 80:
            urgency_level = "high"
        elif proximity_score >= 60:
            urgency_level = "medium"
        else:
            urgency_level = "low"

        return {
            "proximity_score": proximity_score,
            "deadlines_found": deadlines_found,
            "urgency_level": urgency_level,
        }

    def _detect_escalation_language(self, content: str) -> List[str]:
        """Detect escalation language in content."""
        escalation_keywords = [
            "escalate",
            "urgent",
            "critical",
            "emergency",
            "asap",
            "immediately",
            "frustrated",
            "disappointed",
            "unacceptable",
            "management",
            "supervisor",
            "boss",
            "complaint",
        ]

        import re

        escalation_found = []
        content_lower = content.lower()

        for keyword in escalation_keywords:
            if re.search(r"\b" + keyword + r"\b", content_lower):
                escalation_found.append(keyword)

        return escalation_found

    def _apply_context_adjustments(
        self, base_urgency: int, context_factors: Dict[str, Any], business_hours: bool
    ) -> int:
        """Apply context adjustments to urgency score."""
        adjusted_urgency = base_urgency

        # Authority adjustments
        authority_indicators = context_factors.get("sender_context", {}).get(
            "authority_indicators", []
        )
        if authority_indicators:
            # Higher urgency for authority figures
            adjusted_urgency += len(authority_indicators) * 5

        # Relationship adjustments
        relationship = context_factors.get("sender_context", {}).get(
            "relationship_type", "unknown"
        )
        if relationship == "superior":
            adjusted_urgency += 10
        elif relationship == "external":
            adjusted_urgency += 5

        # Time sensitivity adjustments
        time_sensitivity = context_factors.get("temporal_context", {}).get(
            "time_sensitivity", {}
        )
        if time_sensitivity.get("level") == "immediate":
            adjusted_urgency += 15
        elif time_sensitivity.get("level") == "urgent":
            adjusted_urgency += 10

        # Business hours adjustment
        if not business_hours:
            # After hours emails are more urgent
            adjusted_urgency += 5

        # Escalation language adjustments
        escalation_language = context_factors.get("content_context", {}).get(
            "escalation_language", []
        )
        if escalation_language:
            adjusted_urgency += len(escalation_language) * 3

        # Cap at 100
        return min(adjusted_urgency, 100)

    def _calculate_urgency_score(self, urgency_level: str) -> int:
        """Convert urgency level to numeric score."""
        level_map = {"low": 25, "medium": 50, "high": 75, "critical": 90}
        return level_map.get(urgency_level.lower(), 50)

    def _calculate_response_time(self, urgency_score: int) -> str:
        """Calculate recommended response time based on urgency."""
        if urgency_score >= 90:
            return "within 15 minutes"
        elif urgency_score >= 75:
            return "within 1 hour"
        elif urgency_score >= 60:
            return "within 4 hours"
        elif urgency_score >= 40:
            return "within 1 business day"
        else:
            return "within 2-3 business days"

    def _generate_response_framework(
        self,
        processed_email: ProcessedEmail,
        sentiment_result,
        response_type: str,
        tone: str,
    ) -> Dict[str, Any]:
        """Generate response framework for email."""
        return {
            "response_type": response_type,
            "tone": tone,
            "key_points": self._identify_key_points(processed_email),
            "sentiment_context": {
                "primary_emotion": sentiment_result.sentiment_analysis.primary_emotion.value,
                "intensity": sentiment_result.sentiment_analysis.emotional_intensity,
                "professional_tone": sentiment_result.sentiment_analysis.professional_tone.value,
            },
            "urgency_context": {
                "level": (
                    processed_email.analysis.urgency_level.value
                    if processed_email.analysis
                    else "medium"
                ),
                "score": (
                    processed_email.analysis.urgency_score
                    if processed_email.analysis
                    else 50
                ),
            },
        }

    def _generate_primary_response(
        self, processed_email: ProcessedEmail, framework: Dict[str, Any], tone: str
    ) -> str:
        """Generate primary response suggestion."""
        sender = processed_email.email_data.from_email
        subject = processed_email.email_data.subject

        if tone == "professional":
            greeting = "Dear " + sender.split("@")[0].replace(".", " ").title() + ","
            closing = "Best regards,"
        elif tone == "friendly":
            greeting = "Hi " + sender.split("@")[0].replace(".", " ").title() + "!"
            closing = "Thanks!"
        elif tone == "formal":
            greeting = "Dear Sir/Madam,"
            closing = "Yours sincerely,"
        else:  # casual
            greeting = "Hey!"
            closing = "Cheers!"

        # Build response based on framework
        response = f"{greeting}\n\n"
        response += f"Thank you for your email regarding {subject}.\n\n"

        # Add content based on urgency
        urgency_level = framework.get("urgency_context", {}).get("level", "medium")
        if urgency_level == "high":
            response += (
                "I understand this is urgent and will prioritize accordingly.\n\n"
            )

        response += "I'll review your request and get back to you shortly.\n\n"
        response += closing

        return response

    def _generate_alternative_responses(self) -> List[str]:
        """Generate alternative response suggestions."""
        alternatives = []

        # Brief acknowledgment
        alternatives.append(
            "Thank you for your email. I'll review and respond by [timeframe]."
        )

        # Detailed response
        alternatives.append(
            "I've received your email and appreciate you bringing this to my attention. Let me look into this and provide a comprehensive response."
        )

        # Question-based response
        alternatives.append(
            "Thank you for reaching out. To better assist you, could you provide additional details about [specific aspect]?"
        )

        return alternatives

    def _identify_key_points(self, processed_email: ProcessedEmail) -> List[str]:
        """Identify key points to address in response."""
        key_points = []

        if processed_email.analysis and processed_email.analysis.action_items:
            key_points.extend(
                [
                    f"Action: {item}"
                    for item in processed_email.analysis.action_items[:3]
                ]
            )

        # Add subject-based key points
        subject_lower = processed_email.email_data.subject.lower()
        if "meeting" in subject_lower:
            key_points.append("Schedule/confirm meeting details")
        if "deadline" in subject_lower:
            key_points.append("Address deadline concerns")
        if "question" in subject_lower or "?" in processed_email.email_data.subject:
            key_points.append("Answer specific questions")

        return key_points[:5]  # Limit to 5 key points

    def _suggest_tone_adjustments(
        self, sentiment_result, requested_tone: str
    ) -> List[str]:
        """Suggest tone adjustments based on sentiment analysis."""
        suggestions = []

        primary_emotion = sentiment_result.sentiment_analysis.primary_emotion.value

        if primary_emotion in ["anger", "frustration"] and requested_tone != "formal":
            suggestions.append(
                "Consider using a more formal tone to address concerns professionally"
            )

        if (
            primary_emotion in ["sadness", "disappointment"]
            and requested_tone != "friendly"
        ):
            suggestions.append("A friendly, empathetic tone might be more appropriate")

        if (
            sentiment_result.conflict_analysis.has_conflict
            and requested_tone == "casual"
        ):
            suggestions.append(
                "Avoid casual tone due to detected conflict - use professional approach"
            )

        return suggestions

    def _calculate_response_urgency(self, processed_email: ProcessedEmail) -> str:
        """Calculate response urgency level."""
        if not processed_email.analysis:
            return "medium"

        urgency_score = processed_email.analysis.urgency_score

        if urgency_score >= 80:
            return "immediate"
        elif urgency_score >= 60:
            return "high"
        elif urgency_score >= 40:
            return "medium"
        else:
            return "low"

    def _assess_response_complexity(self, processed_email: ProcessedEmail) -> str:
        """Assess response complexity requirements."""
        complexity_indicators = 0

        if processed_email.analysis:
            # Multiple action items increase complexity
            if len(processed_email.analysis.action_items) > 3:
                complexity_indicators += 1

            # High urgency increases complexity
            if processed_email.analysis.urgency_score >= 70:
                complexity_indicators += 1

        # Long email content increases complexity
        content_length = len(processed_email.email_data.text_body or "")
        if content_length > 1000:
            complexity_indicators += 1

        # Multiple recipients increase complexity
        if len(processed_email.email_data.to_emails) > 3:
            complexity_indicators += 1

        if complexity_indicators >= 3:
            return "complex"
        elif complexity_indicators >= 2:
            return "moderate"
        else:
            return "simple"

    def _analyze_stakeholders(self, processed_email: ProcessedEmail) -> List[str]:
        """Analyze stakeholders mentioned in email."""
        stakeholders = []

        # Direct recipients
        stakeholders.extend(processed_email.email_data.to_emails)

        # CC recipients if available
        if hasattr(processed_email.email_data, "cc_emails"):
            stakeholders.extend(processed_email.email_data.cc_emails or [])

        # Extract mentioned emails from content
        import re

        content = processed_email.email_data.text_body or ""
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        mentioned_emails = re.findall(email_pattern, content)
        stakeholders.extend(mentioned_emails)

        return list(set(stakeholders))  # Remove duplicates

    def _determine_follow_up_needs(
        self, processed_email: ProcessedEmail
    ) -> Dict[str, Any]:
        """Determine follow-up requirements."""
        follow_up = {"required": False, "timeline": None, "type": None, "reason": None}

        if processed_email.analysis:
            # High urgency emails typically need follow-up
            if processed_email.analysis.urgency_score >= 70:
                follow_up["required"] = True
                follow_up["timeline"] = "within 24 hours"
                follow_up["type"] = "status_update"
                follow_up["reason"] = "high_urgency"

            # Emails with action items need follow-up
            if processed_email.analysis.action_items:
                follow_up["required"] = True
                follow_up["timeline"] = "upon completion"
                follow_up["type"] = "completion_confirmation"
                follow_up["reason"] = "action_items_present"

        # Check for explicit follow-up requests in content
        content = (processed_email.email_data.text_body or "").lower()
        follow_up_keywords = ["follow up", "check in", "update", "status", "progress"]

        if any(keyword in content for keyword in follow_up_keywords):
            follow_up["required"] = True
            follow_up["type"] = "requested_update"
            follow_up["reason"] = "explicit_request"

        return follow_up

    def _recommend_empathy_level(self, sentiment_result) -> str:
        """Recommend empathy level for response."""
        primary_emotion = sentiment_result.sentiment_analysis.primary_emotion.value
        emotional_intensity = sentiment_result.sentiment_analysis.emotional_intensity

        if primary_emotion in ["sadness", "frustration", "anger", "disappointment"]:
            if emotional_intensity > 0.7:
                return "high"
            else:
                return "medium"
        elif primary_emotion in ["happiness", "satisfaction"]:
            return "low"
        else:
            return "medium"

    def _generate_acknowledgment(self, action_item: str, tone: str) -> str:
        """Generate acknowledgment for action item."""
        if tone == "professional":
            return f"I acknowledge the action item: {action_item}. I will ensure this is completed as requested."
        elif tone == "friendly":
            return f"Got it! I'll take care of: {action_item}"
        elif tone == "formal":
            return f"I formally acknowledge receipt of the following action item: {action_item}"
        else:  # casual
            return f"Sure thing! I'll handle: {action_item}"
