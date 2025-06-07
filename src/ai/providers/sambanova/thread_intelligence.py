"""
Multi-Email Thread Intelligence Engine for SambaNova AI Integration

This module provides advanced thread analysis capabilities that understand
email conversations, track decisions, consolidate action items, and analyze
stakeholder interactions across entire email threads.

Key Features:
- Thread reconstruction and conversation flow analysis
- Decision point identification and tracking
- Action item consolidation across multiple emails
- Conflict resolution and consensus detection
- Stakeholder influence mapping and relationship analysis
- Conversation summarization with key insights

Author: GitHub Copilot
Created: May 31, 2025
Version: 1.0.0
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from src.models import EmailAnalysis, EmailData, ProcessedEmail

from .sambanova_interface import SambaNovaInterface

# Setup logging
logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """Conversation state tracking."""

    INITIATED = "initiated"
    ONGOING = "ongoing"
    DECISION_PENDING = "decision_pending"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    STALLED = "stalled"


class StakeholderRole(Enum):
    """Stakeholder roles in email threads."""

    INITIATOR = "initiator"
    DECISION_MAKER = "decision_maker"
    CONTRIBUTOR = "contributor"
    OBSERVER = "observer"
    EXTERNAL = "external"


@dataclass
class DecisionPoint:
    """Represents a decision point in an email thread."""

    id: str
    description: str
    emails_involved: List[str] = field(default_factory=list)
    stakeholders: List[str] = field(default_factory=list)
    options_discussed: List[str] = field(default_factory=list)
    decision_made: Optional[str] = None
    decision_maker: Optional[str] = None
    confidence: float = 0.0
    timestamp: Optional[datetime] = None
    status: str = "pending"  # pending, decided, implemented, blocked


@dataclass
class ActionItemEvolution:
    """Tracks how action items evolve across email threads."""

    original_item: str
    current_item: str
    email_chain: List[str] = field(default_factory=list)
    status_changes: List[Dict[str, Any]] = field(default_factory=list)
    assignee_changes: List[Dict[str, Any]] = field(default_factory=list)
    priority_changes: List[Dict[str, Any]] = field(default_factory=list)
    completion_status: str = "open"  # open, in_progress, completed, blocked, cancelled


@dataclass
class StakeholderProfile:
    """Profile of a stakeholder in email threads."""

    email_address: str
    name: Optional[str] = None
    role: StakeholderRole = StakeholderRole.CONTRIBUTOR
    influence_score: float = 0.0
    participation_level: float = 0.0
    decision_making_authority: float = 0.0
    response_pattern: Dict[str, Any] = field(default_factory=dict)
    communication_style: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSummary:
    """Summary of an email conversation thread."""

    thread_id: str
    subject_line: str
    participants: List[str] = field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    email_count: int = 0
    conversation_state: ConversationState = ConversationState.INITIATED
    key_topics: List[str] = field(default_factory=list)
    decisions_made: List[DecisionPoint] = field(default_factory=list)
    action_items: List[ActionItemEvolution] = field(default_factory=list)
    stakeholder_profiles: List[StakeholderProfile] = field(default_factory=list)
    conflict_indicators: List[str] = field(default_factory=list)
    consensus_level: float = 0.0
    urgency_escalation: float = 0.0
    executive_summary: str = ""
    next_steps: List[str] = field(default_factory=list)


class ThreadIntelligenceEngine:
    """
    Advanced engine for multi-email thread intelligence and analysis.

    This engine provides sophisticated analysis of email conversations,
    including decision tracking, stakeholder analysis, and action item
    consolidation across entire email threads.
    """

    def __init__(self, sambanova_interface: SambaNovaInterface):
        """Initialize the Thread Intelligence Engine."""
        self.sambanova_interface = sambanova_interface
        self.is_initialized = False

        # Thread analysis configuration
        self.max_thread_length = 50  # Maximum emails to analyze in a thread
        self.decision_confidence_threshold = 0.7
        self.conflict_detection_threshold = 0.6
        self.consensus_threshold = 0.8

        # Processing statistics
        self.stats = {
            "threads_analyzed": 0,
            "decisions_tracked": 0,
            "conflicts_detected": 0,
            "action_items_consolidated": 0,
            "stakeholders_profiled": 0,
            "avg_processing_time": 0.0,
        }

    async def initialize(self) -> None:
        """Initialize the thread intelligence engine."""
        try:
            logger.info("Initializing Thread Intelligence Engine...")

            # Verify SambaNova interface is available
            if not self.sambanova_interface.is_initialized:
                raise Exception("SambaNova interface not initialized")

            self.is_initialized = True
            logger.info("Thread Intelligence Engine initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Thread Intelligence Engine: {e}")
            raise

    async def analyze_thread(self, emails: List[ProcessedEmail]) -> ConversationSummary:
        """
        Analyze an email thread for intelligence insights.

        Args:
            emails: List of emails in the thread (chronologically ordered)

        Returns:
            Comprehensive conversation summary with intelligence insights
        """
        if not self.is_initialized:
            raise Exception("Thread Intelligence Engine not initialized")

        if not emails:
            raise ValueError("Email list cannot be empty")

        start_time = datetime.now()
        thread_id = f"thread_{emails[0].id}_{len(emails)}"

        try:
            logger.info(f"Analyzing thread {thread_id} with {len(emails)} emails")

            # Create conversation summary
            summary = ConversationSummary(
                thread_id=thread_id,
                subject_line=emails[0].email_data.subject,
                start_date=emails[0].email_data.received_at,
                end_date=emails[-1].email_data.received_at,
                email_count=len(emails),
            )

            # Step 1: Extract participants and build stakeholder profiles
            await self._analyze_stakeholders(emails, summary)

            # Step 2: Reconstruct conversation flow and identify key topics
            await self._analyze_conversation_flow(emails, summary)

            # Step 3: Track decisions across the thread
            await self._track_decisions(emails, summary)

            # Step 4: Consolidate action items
            await self._consolidate_action_items(emails, summary)

            # Step 5: Detect conflicts and measure consensus
            await self._analyze_conflicts_and_consensus(emails, summary)

            # Step 6: Generate executive summary and next steps
            await self._generate_executive_summary(emails, summary)

            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(processing_time, summary)

            logger.info(f"Thread analysis completed for {thread_id}")
            return summary

        except Exception as e:
            logger.error(f"Thread analysis failed for {thread_id}: {e}")
            raise

    async def _analyze_stakeholders(
        self, emails: List[ProcessedEmail], summary: ConversationSummary
    ) -> None:
        """Analyze stakeholders and their roles in the conversation."""
        try:
            logger.debug(f"Analyzing stakeholders for thread {summary.thread_id}")

            # Extract all participants
            participants = set()
            email_counts = {}

            for email in emails:
                # Add sender
                sender = email.email_data.from_email
                participants.add(sender)
                email_counts[sender] = email_counts.get(sender, 0) + 1

                # Add recipients
                for recipient in email.email_data.to_emails:
                    participants.add(recipient)

            summary.participants = list(participants)

            # Build stakeholder profiles
            for participant in participants:
                profile = await self._build_stakeholder_profile(
                    participant, emails, email_counts
                )
                summary.stakeholder_profiles.append(profile)

            self.stats["stakeholders_profiled"] += len(summary.stakeholder_profiles)
            logger.debug(f"Analyzed {len(summary.stakeholder_profiles)} stakeholders")

        except Exception as e:
            logger.error(f"Stakeholder analysis failed: {e}")

    async def _build_stakeholder_profile(
        self,
        participant: str,
        emails: List[ProcessedEmail],
        email_counts: Dict[str, int],
    ) -> StakeholderProfile:
        """Build a detailed profile for a stakeholder."""
        try:
            # Determine role based on participation patterns
            role = StakeholderRole.CONTRIBUTOR

            # Check if initiator (sent first email)
            if emails[0].email_data.from_email == participant:
                role = StakeholderRole.INITIATOR

            # Calculate participation metrics
            total_emails = len(emails)
            participant_emails = email_counts.get(participant, 0)
            participation_level = (
                participant_emails / total_emails if total_emails > 0 else 0.0
            )

            # Analyze communication style using AI
            communication_style = await self._analyze_communication_style(
                participant, emails
            )

            # Calculate influence score
            influence_score = await self._calculate_influence_score(participant, emails)

            return StakeholderProfile(
                email_address=participant,
                role=role,
                participation_level=participation_level,
                influence_score=influence_score,
                communication_style=communication_style,
            )

        except Exception as e:
            logger.error(f"Failed to build stakeholder profile for {participant}: {e}")
            return StakeholderProfile(email_address=participant)

    async def _analyze_communication_style(
        self, participant: str, emails: List[ProcessedEmail]
    ) -> Dict[str, Any]:
        """Analyze communication style of a participant using AI."""
        try:
            # Extract emails from this participant
            participant_emails = [
                e for e in emails if e.email_data.from_email == participant
            ]

            if not participant_emails:
                return {"style": "observer", "tone": "neutral"}

            # Prepare content for AI analysis
            content_sample = "\n\n".join(
                [
                    f"Subject: {email.email_data.subject}\nBody: {email.email_data.body[:500]}..."
                    for email in participant_emails[:3]  # Analyze up to 3 emails
                ]
            )

            # AI prompt for communication style analysis
            prompt = f"""Analyze the communication style of the following email content:

{content_sample}

Identify:
1. Communication style (formal, casual, direct, diplomatic, technical, persuasive)
2. Tone (professional, friendly, urgent, concerned, confident, collaborative)
3. Decision-making approach (directive, consultative, consensus-seeking, analytical)
4. Response pattern (quick responder, detailed responder, brief responder)

Provide response in JSON format:
{{
    "style": "communication_style",
    "tone": "primary_tone", 
    "decision_approach": "decision_making_style",
    "response_pattern": "response_style",
    "confidence": 0.0-1.0
}}"""

            # Get AI analysis
            response = await self.sambanova_interface.make_request(prompt)

            # Parse AI response
            try:
                import json

                style_data = json.loads(response)
                return style_data
            except:
                return {
                    "style": "professional",
                    "tone": "neutral",
                    "decision_approach": "consultative",
                    "response_pattern": "standard",
                    "confidence": 0.5,
                }

        except Exception as e:
            logger.error(f"Communication style analysis failed for {participant}: {e}")
            return {"style": "unknown", "tone": "neutral"}

    async def _calculate_influence_score(
        self, participant: str, emails: List[ProcessedEmail]
    ) -> float:
        """Calculate influence score based on response patterns and content."""
        try:
            influence_score = 0.0

            # Factor 1: Response generation (how often others respond to this person)
            participant_emails = [
                e for e in emails if e.email_data.from_email == participant
            ]
            responses_generated = 0

            for i, email in enumerate(emails):
                if email.email_data.from_email == participant and i < len(emails) - 1:
                    # Check if next email is a response
                    next_email = emails[i + 1]
                    if participant in next_email.email_data.to_emails:
                        responses_generated += 1

            if participant_emails:
                response_rate = responses_generated / len(participant_emails)
                influence_score += response_rate * 0.4

            # Factor 2: Decision-making indicators in content
            decision_keywords = [
                "decide",
                "approve",
                "authorize",
                "confirm",
                "proceed",
                "implement",
            ]
            for email in participant_emails:
                content = email.email_data.body.lower()
                decision_words = sum(1 for word in decision_keywords if word in content)
                influence_score += min(decision_words * 0.1, 0.3)

            # Factor 3: Position indicators (domain analysis, titles)
            if any(
                word in participant.lower()
                for word in ["ceo", "cto", "director", "manager", "lead"]
            ):
                influence_score += 0.3

            return min(influence_score, 1.0)

        except Exception as e:
            logger.error(f"Influence score calculation failed for {participant}: {e}")
            return 0.5

    async def _analyze_conversation_flow(
        self, emails: List[ProcessedEmail], summary: ConversationSummary
    ) -> None:
        """Analyze conversation flow and identify key topics."""
        try:
            logger.debug(f"Analyzing conversation flow for thread {summary.thread_id}")

            # Extract key topics using AI
            topics = await self._extract_key_topics(emails)
            summary.key_topics = topics

            # Determine conversation state
            summary.conversation_state = await self._determine_conversation_state(
                emails
            )

            logger.debug(
                f"Identified {len(topics)} key topics and state: {summary.conversation_state}"
            )

        except Exception as e:
            logger.error(f"Conversation flow analysis failed: {e}")

    async def _extract_key_topics(self, emails: List[ProcessedEmail]) -> List[str]:
        """Extract key topics from the email thread using AI."""
        try:
            # Prepare content for topic extraction
            thread_content = "\n\n".join(
                [
                    f"Email {i+1}:\nSubject: {email.email_data.subject}\nBody: {email.email_data.body[:300]}..."
                    for i, email in enumerate(emails[:10])  # Analyze up to 10 emails
                ]
            )

            prompt = f"""Analyze the following email thread and extract the main topics being discussed:

{thread_content}

Extract 3-7 key topics that represent the main themes of this conversation.
Provide topics as a simple list, one per line, without numbering or bullets.
Focus on:
- Business objectives and goals
- Technical issues and solutions
- Project milestones and deliverables
- Process improvements
- Resource and budget concerns
- Timeline and scheduling matters

Topics:"""

            # Get AI analysis
            response = await self.sambanova_interface.make_request(prompt)

            # Parse topics
            topics = [topic.strip() for topic in response.split("\n") if topic.strip()]
            topics = [topic for topic in topics if len(topic) > 5 and len(topic) < 100]

            return topics[:7]  # Return max 7 topics

        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
            return ["General Discussion"]

    async def _determine_conversation_state(
        self, emails: List[ProcessedEmail]
    ) -> ConversationState:
        """Determine the current state of the conversation."""
        try:
            latest_email = emails[-1]
            latest_content = latest_email.email_data.body.lower()

            # Check for resolution indicators
            resolution_keywords = [
                "resolved",
                "completed",
                "done",
                "finished",
                "closed",
                "solved",
            ]
            if any(keyword in latest_content for keyword in resolution_keywords):
                return ConversationState.RESOLVED

            # Check for decision pending indicators
            decision_keywords = [
                "decide",
                "decision",
                "choose",
                "select",
                "approve",
                "pending",
            ]
            if any(keyword in latest_content for keyword in decision_keywords):
                return ConversationState.DECISION_PENDING

            # Check for escalation indicators
            escalation_keywords = [
                "escalate",
                "urgent",
                "critical",
                "emergency",
                "asap",
            ]
            if any(keyword in latest_content for keyword in escalation_keywords):
                return ConversationState.ESCALATED

            # Check for stalled indicators (no recent activity)
            if latest_email.email_data.received_at:
                days_since_last = (
                    datetime.now() - latest_email.email_data.received_at
                ).days
                if days_since_last > 7:
                    return ConversationState.STALLED

            # Default to ongoing
            return ConversationState.ONGOING

        except Exception as e:
            logger.error(f"Conversation state determination failed: {e}")
            return ConversationState.ONGOING

    async def _track_decisions(
        self, emails: List[ProcessedEmail], summary: ConversationSummary
    ) -> None:
        """Track decisions made across the email thread."""
        try:
            logger.debug(f"Tracking decisions for thread {summary.thread_id}")

            decisions = []

            for i, email in enumerate(emails):
                # Look for decision-making content
                decision_points = await self._extract_decision_points(email, i)
                decisions.extend(decision_points)

            summary.decisions_made = decisions
            self.stats["decisions_tracked"] += len(decisions)

            logger.debug(f"Tracked {len(decisions)} decision points")

        except Exception as e:
            logger.error(f"Decision tracking failed: {e}")

    async def _extract_decision_points(
        self, email: ProcessedEmail, email_index: int
    ) -> List[DecisionPoint]:
        """Extract decision points from a single email."""
        try:
            content = email.email_data.body.lower()

            # Decision keywords
            decision_indicators = [
                "we have decided",
                "decision has been made",
                "we will proceed",
                "approved",
                "confirmed",
                "selected",
                "chosen",
                "agreed",
            ]

            decisions = []

            for indicator in decision_indicators:
                if indicator in content:
                    # Extract decision context using AI
                    decision = await self._analyze_decision_context(
                        email, indicator, email_index
                    )
                    if decision:
                        decisions.append(decision)

            return decisions

        except Exception as e:
            logger.error(f"Decision point extraction failed: {e}")
            return []

    async def _analyze_decision_context(
        self, email: ProcessedEmail, indicator: str, email_index: int
    ) -> Optional[DecisionPoint]:
        """Analyze decision context using AI."""
        try:
            prompt = f"""Analyze the following email for decision-making content:

Subject: {email.email_data.subject}
From: {email.email_data.from_email}
Body: {email.email_data.body}

The email contains the decision indicator: "{indicator}"

Extract:
1. What decision was made?
2. Who made the decision?
3. What options were considered?
4. What is the impact or next steps?

Provide response in JSON format:
{{
    "decision_made": "description of the decision",
    "decision_maker": "email_address",
    "options_discussed": ["option1", "option2"],
    "next_steps": ["step1", "step2"],
    "confidence": 0.0-1.0
}}"""

            response = await self.sambanova_interface.make_request(prompt)

            try:
                import json

                decision_data = json.loads(response)

                if (
                    decision_data.get("confidence", 0)
                    >= self.decision_confidence_threshold
                ):
                    return DecisionPoint(
                        id=f"decision_{email.id}_{email_index}",
                        description=decision_data.get("decision_made", ""),
                        emails_involved=[email.id],
                        stakeholders=[email.email_data.from_email],
                        options_discussed=decision_data.get("options_discussed", []),
                        decision_made=decision_data.get("decision_made"),
                        decision_maker=decision_data.get("decision_maker"),
                        confidence=decision_data.get("confidence", 0.0),
                        timestamp=email.email_data.received_at,
                        status="decided",
                    )
            except:
                pass

            return None

        except Exception as e:
            logger.error(f"Decision context analysis failed: {e}")
            return None

    async def _consolidate_action_items(
        self, emails: List[ProcessedEmail], summary: ConversationSummary
    ) -> None:
        """Consolidate action items across the email thread."""
        try:
            logger.debug(f"Consolidating action items for thread {summary.thread_id}")

            all_action_items = []

            # Collect all action items from emails
            for email in emails:
                if email.analysis and email.analysis.action_items:
                    for item in email.analysis.action_items:
                        evolution = ActionItemEvolution(
                            original_item=item,
                            current_item=item,
                            email_chain=[email.id],
                            status_changes=[
                                {
                                    "status": "identified",
                                    "email_id": email.id,
                                    "timestamp": email.email_data.received_at,
                                }
                            ],
                        )
                        all_action_items.append(evolution)

            # Consolidate similar action items using AI
            consolidated_items = await self._consolidate_similar_items(all_action_items)

            summary.action_items = consolidated_items
            self.stats["action_items_consolidated"] += len(consolidated_items)

            logger.debug(f"Consolidated {len(consolidated_items)} action items")

        except Exception as e:
            logger.error(f"Action item consolidation failed: {e}")

    async def _consolidate_similar_items(
        self, items: List[ActionItemEvolution]
    ) -> List[ActionItemEvolution]:
        """Consolidate similar action items using AI analysis."""
        try:
            if len(items) <= 1:
                return items

            # For now, implement simple deduplication
            # In a full implementation, this would use AI to identify similar items
            unique_items = {}

            for item in items:
                key = item.original_item.lower().strip()
                if key in unique_items:
                    # Merge email chains
                    unique_items[key].email_chain.extend(item.email_chain)
                    unique_items[key].status_changes.extend(item.status_changes)
                else:
                    unique_items[key] = item

            return list(unique_items.values())

        except Exception as e:
            logger.error(f"Similar items consolidation failed: {e}")
            return items

    async def _analyze_conflicts_and_consensus(
        self, emails: List[ProcessedEmail], summary: ConversationSummary
    ) -> None:
        """Analyze conflicts and measure consensus in the thread."""
        try:
            logger.debug(
                f"Analyzing conflicts and consensus for thread {summary.thread_id}"
            )

            # Detect conflict indicators
            conflicts = await self._detect_conflicts(emails)
            summary.conflict_indicators = conflicts

            # Measure consensus level
            consensus_level = await self._measure_consensus(emails)
            summary.consensus_level = consensus_level

            if conflicts:
                self.stats["conflicts_detected"] += len(conflicts)

            logger.debug(
                f"Found {len(conflicts)} conflict indicators, consensus level: {consensus_level:.2f}"
            )

        except Exception as e:
            logger.error(f"Conflict and consensus analysis failed: {e}")

    async def _detect_conflicts(self, emails: List[ProcessedEmail]) -> List[str]:
        """Detect conflict indicators in the email thread."""
        try:
            conflict_keywords = [
                "disagree",
                "oppose",
                "object",
                "concern",
                "issue",
                "problem",
                "but",
                "however",
                "unfortunately",
                "worried",
                "risk",
            ]

            conflicts = []

            for email in emails:
                content = email.email_data.body.lower()
                found_conflicts = [
                    keyword for keyword in conflict_keywords if keyword in content
                ]

                if found_conflicts:
                    conflicts.append(
                        f"Email from {email.email_data.from_email}: {', '.join(found_conflicts)}"
                    )

            return conflicts

        except Exception as e:
            logger.error(f"Conflict detection failed: {e}")
            return []

    async def _measure_consensus(self, emails: List[ProcessedEmail]) -> float:
        """Measure consensus level in the conversation."""
        try:
            positive_indicators = [
                "agree",
                "sounds good",
                "yes",
                "correct",
                "exactly",
                "support",
            ]
            negative_indicators = [
                "disagree",
                "no",
                "incorrect",
                "wrong",
                "oppose",
                "against",
            ]

            positive_count = 0
            negative_count = 0

            for email in emails:
                content = email.email_data.body.lower()
                positive_count += sum(
                    1 for indicator in positive_indicators if indicator in content
                )
                negative_count += sum(
                    1 for indicator in negative_indicators if indicator in content
                )

            total_indicators = positive_count + negative_count
            if total_indicators == 0:
                return 0.5  # Neutral consensus

            consensus_level = positive_count / total_indicators
            return consensus_level

        except Exception as e:
            logger.error(f"Consensus measurement failed: {e}")
            return 0.5

    async def _generate_executive_summary(
        self, emails: List[ProcessedEmail], summary: ConversationSummary
    ) -> None:
        """Generate executive summary and next steps."""
        try:
            logger.debug(f"Generating executive summary for thread {summary.thread_id}")

            # Prepare thread overview for AI
            thread_overview = f"""
Email Thread Analysis:
- Subject: {summary.subject_line}
- Participants: {len(summary.participants)} people
- Duration: {summary.start_date} to {summary.end_date}
- Key Topics: {', '.join(summary.key_topics)}
- Decisions Made: {len(summary.decisions_made)}
- Action Items: {len(summary.action_items)}
- Consensus Level: {summary.consensus_level:.2f}
- Conflicts: {len(summary.conflict_indicators)}
"""

            prompt = f"""Create an executive summary for this email thread:

{thread_overview}

Recent email content sample:
{emails[-1].email_data.body[:500]}...

Provide:
1. Executive Summary (2-3 sentences)
2. Next Steps (3-5 action items)
3. Urgency Escalation Level (0.0-1.0)

Format as JSON:
{{
    "executive_summary": "brief summary",
    "next_steps": ["step1", "step2", "step3"],
    "urgency_escalation": 0.0-1.0
}}"""

            response = await self.sambanova_interface.make_request(prompt)

            try:
                import json

                summary_data = json.loads(response)

                summary.executive_summary = summary_data.get("executive_summary", "")
                summary.next_steps = summary_data.get("next_steps", [])
                summary.urgency_escalation = summary_data.get("urgency_escalation", 0.0)

            except:
                summary.executive_summary = f"Email thread with {len(emails)} messages discussing {', '.join(summary.key_topics[:3])}"
                summary.next_steps = ["Review action items", "Follow up on decisions"]
                summary.urgency_escalation = 0.3

            logger.debug("Executive summary generated successfully")

        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")

    def _update_stats(
        self, processing_time: float, summary: ConversationSummary
    ) -> None:
        """Update processing statistics."""
        self.stats["threads_analyzed"] += 1

        # Update average processing time
        n = self.stats["threads_analyzed"]
        current_avg = self.stats["avg_processing_time"]
        self.stats["avg_processing_time"] = (
            current_avg * (n - 1) + processing_time
        ) / n

    async def batch_analyze_threads(
        self, thread_groups: List[List[ProcessedEmail]]
    ) -> List[ConversationSummary]:
        """
        Analyze multiple email threads in batch.

        Args:
            thread_groups: List of email thread lists

        Returns:
            List of conversation summaries
        """
        if not self.is_initialized:
            raise Exception("Thread Intelligence Engine not initialized")

        logger.info(f"Starting batch analysis of {len(thread_groups)} threads")

        try:
            # Process threads concurrently with controlled concurrency
            semaphore = asyncio.Semaphore(3)  # Limit concurrent thread analysis

            async def analyze_with_semaphore(emails):
                async with semaphore:
                    return await self.analyze_thread(emails)

            tasks = [analyze_with_semaphore(emails) for emails in thread_groups]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions in results
            summaries = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Thread analysis failed for group {i}: {result}")
                else:
                    summaries.append(result)

            logger.info(f"Batch analysis completed: {len(summaries)} threads analyzed")
            return summaries

        except Exception as e:
            logger.error(f"Batch thread analysis failed: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """Get thread intelligence processing statistics."""
        return {
            **self.stats,
            "engine_name": "ThreadIntelligenceEngine",
            "is_initialized": self.is_initialized,
            "configuration": {
                "max_thread_length": self.max_thread_length,
                "decision_confidence_threshold": self.decision_confidence_threshold,
                "conflict_detection_threshold": self.conflict_detection_threshold,
                "consensus_threshold": self.consensus_threshold,
            },
        }

    async def cleanup(self) -> None:
        """Cleanup thread intelligence engine resources."""
        try:
            logger.info("Cleaning up Thread Intelligence Engine...")
            self.is_initialized = False
            logger.info("Thread Intelligence Engine cleanup completed")

        except Exception as e:
            logger.error(f"Thread Intelligence Engine cleanup failed: {e}")
