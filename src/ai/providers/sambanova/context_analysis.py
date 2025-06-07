"""
Context-Aware Email Analysis Engine
Implements intelligent analysis that understands email relationships, history, and organizational context.
"""

import asyncio
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from ...config import get_sambanova_config
from .sambanova_interface import ContextAnalysis, EmailData, SambaNovaInterface


class RelationshipType(str, Enum):
    """Types of email relationships."""

    SENDER_RECIPIENT = "sender_recipient"
    THREAD_CONTINUATION = "thread_continuation"
    PROJECT_RELATED = "project_related"
    TOPIC_RELATED = "topic_related"
    ESCALATION = "escalation"
    COLLABORATION = "collaboration"


class OrganizationalRole(str, Enum):
    """Organizational roles for context analysis."""

    EXECUTIVE = "executive"
    MANAGER = "manager"
    TEAM_LEAD = "team_lead"
    INDIVIDUAL_CONTRIBUTOR = "individual_contributor"
    CLIENT = "client"
    VENDOR = "vendor"
    EXTERNAL = "external"


class ConversationState(str, Enum):
    """States of email conversations."""

    INITIATED = "initiated"
    ONGOING = "ongoing"
    WAITING_RESPONSE = "waiting_response"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    STALLED = "stalled"


class EmailRelationship(BaseModel):
    """Relationship between emails or participants."""

    email_id: str
    related_email_id: str
    relationship_type: RelationshipType
    strength: float = Field(ge=0.0, le=1.0)
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SenderProfile(BaseModel):
    """Profile of an email sender with context."""

    email_address: str
    name: Optional[str] = None
    role: Optional[OrganizationalRole] = None
    authority_level: float = Field(default=0.5, ge=0.0, le=1.0)
    communication_style: str = Field(default="professional")
    frequent_topics: List[str] = Field(default_factory=list)
    response_patterns: Dict[str, Any] = Field(default_factory=dict)


class ProjectContext(BaseModel):
    """Project context for email analysis."""

    project_name: str
    participants: List[str] = Field(default_factory=list)
    key_topics: List[str] = Field(default_factory=list)
    current_phase: str = Field(default="active")
    priority_level: str = Field(default="medium")
    deadline: Optional[datetime] = None
    status_indicators: List[str] = Field(default_factory=list)


class EnhancedContextAnalysis(ContextAnalysis):
    """Enhanced context analysis with additional SambaNova insights."""

    email_relationships: List[EmailRelationship] = Field(default_factory=list)
    sender_profiles: List[SenderProfile] = Field(default_factory=list)
    organizational_hierarchy: Dict[str, Any] = Field(default_factory=dict)
    communication_patterns: Dict[str, Any] = Field(default_factory=dict)
    urgency_escalation_indicators: List[str] = Field(default_factory=list)
    conflict_indicators: List[str] = Field(default_factory=list)
    consensus_building_signals: List[str] = Field(default_factory=list)
    project_contexts: List[ProjectContext] = Field(default_factory=list)


@dataclass
class ContextAnalysisConfig:
    """Configuration for context analysis."""

    max_thread_depth: int = 10
    relationship_threshold: float = 0.6
    authority_detection_enabled: bool = True
    project_correlation_enabled: bool = True
    sentiment_tracking_enabled: bool = True
    escalation_detection_enabled: bool = True


class ContextAnalysisEngine:
    """
    Advanced context analysis engine for email thread and relationship understanding.

    Provides sophisticated analysis of email relationships, organizational context,
    and conversation patterns using SambaNova's contextual understanding capabilities.
    """

    def __init__(
        self,
        sambanova_interface: Optional[SambaNovaInterface] = None,
        config: Optional[ContextAnalysisConfig] = None,
    ):
        """
        Initialize context analysis engine.

        Args:
            sambanova_interface: Optional SambaNova interface
            config: Optional configuration for analysis
        """
        self.sambanova = sambanova_interface or SambaNovaInterface(
            get_sambanova_config()
        )
        self.config = config or ContextAnalysisConfig()
        self.logger = logging.getLogger(__name__)

        # Cache for sender profiles and project contexts
        self.sender_profiles_cache: Dict[str, SenderProfile] = {}
        self.project_contexts_cache: Dict[str, ProjectContext] = {}

        # Pattern matchers for context detection
        self.authority_indicators = [
            "ceo",
            "president",
            "director",
            "vp",
            "vice president",
            "manager",
            "lead",
            "head",
            "chief",
            "senior",
        ]

        self.escalation_patterns = [
            r"escalat\w+",
            r"urgent",
            r"critical",
            r"immediate",
            r"please prioritize",
            r"need asap",
            r"top priority",
        ]

        self.conflict_patterns = [
            r"disagree",
            r"concern\w+",
            r"issue",
            r"problem",
            r"not acceptable",
            r"unacceptable",
            r"disappointed",
        ]

        self.consensus_patterns = [
            r"agree",
            r"consensus",
            r"alignment",
            r"approve",
            r"sounds good",
            r"looks good",
            r"confirmed",
        ]

        self.logger.info("ContextAnalysisEngine initialized with SambaNova integration")

    async def analyze_email_context(
        self,
        email_data: EmailData,
        thread_history: Optional[List[EmailData]] = None,
        organizational_context: Optional[Dict[str, Any]] = None,
    ) -> EnhancedContextAnalysis:
        """
        Analyze email context with comprehensive understanding.

        Args:
            email_data: Primary email to analyze
            thread_history: Optional email thread history
            organizational_context: Optional organizational information

        Returns:
            Enhanced context analysis with relationships and insights
        """
        self.logger.info(f"Starting context analysis for email {email_data.id}")

        # Build email thread for analysis
        email_thread = [email_data]
        if thread_history:
            email_thread.extend(thread_history)

        # Base context analysis using SambaNova
        base_analysis = await self.sambanova.analyze_context(email_thread)

        # Enhanced analysis components
        enhanced_analysis = EnhancedContextAnalysis(**base_analysis.dict())

        # Phase 1: Analyze email relationships
        enhanced_analysis.email_relationships = await self._analyze_email_relationships(
            email_thread
        )

        # Phase 2: Build sender profiles
        enhanced_analysis.sender_profiles = await self._analyze_sender_profiles(
            email_thread
        )

        # Phase 3: Detect organizational hierarchy
        enhanced_analysis.organizational_hierarchy = (
            await self._analyze_organizational_hierarchy(
                email_thread, organizational_context
            )
        )

        # Phase 4: Analyze communication patterns
        enhanced_analysis.communication_patterns = (
            await self._analyze_communication_patterns(email_thread)
        )

        # Phase 5: Detect escalation and conflict indicators
        enhanced_analysis.urgency_escalation_indicators = (
            self._detect_escalation_indicators(email_thread)
        )
        enhanced_analysis.conflict_indicators = self._detect_conflict_indicators(
            email_thread
        )
        enhanced_analysis.consensus_building_signals = self._detect_consensus_signals(
            email_thread
        )

        # Phase 6: Project correlation analysis
        if self.config.project_correlation_enabled:
            enhanced_analysis.project_contexts = await self._correlate_project_contexts(
                email_thread
            )

        self.logger.info("Context analysis completed successfully")
        return enhanced_analysis

    async def _analyze_email_relationships(
        self, email_thread: List[EmailData]
    ) -> List[EmailRelationship]:
        """Analyze relationships between emails in the thread."""
        relationships = []

        for i, email in enumerate(email_thread):
            for j, other_email in enumerate(email_thread):
                if i >= j:  # Avoid duplicates and self-relationships
                    continue

                relationship = await self._detect_email_relationship(email, other_email)
                if (
                    relationship
                    and relationship.strength >= self.config.relationship_threshold
                ):
                    relationships.append(relationship)

        return relationships

    async def _detect_email_relationship(
        self, email1: EmailData, email2: EmailData
    ) -> Optional[EmailRelationship]:
        """Detect relationship between two emails."""

        # Thread continuation (same subject or reply pattern)
        if self._is_thread_continuation(email1, email2):
            return EmailRelationship(
                email_id=email1.id,
                related_email_id=email2.id,
                relationship_type=RelationshipType.THREAD_CONTINUATION,
                strength=0.9,
                description="Part of same email thread",
            )

        # Sender-recipient relationship
        if self._has_sender_recipient_relationship(email1, email2):
            return EmailRelationship(
                email_id=email1.id,
                related_email_id=email2.id,
                relationship_type=RelationshipType.SENDER_RECIPIENT,
                strength=0.7,
                description="Sender-recipient communication",
            )

        # Topic similarity
        topic_similarity = await self._calculate_topic_similarity(email1, email2)
        if topic_similarity > 0.6:
            return EmailRelationship(
                email_id=email1.id,
                related_email_id=email2.id,
                relationship_type=RelationshipType.TOPIC_RELATED,
                strength=topic_similarity,
                description="Related by topic similarity",
            )

        return None

    def _is_thread_continuation(self, email1: EmailData, email2: EmailData) -> bool:
        """Check if emails are part of the same thread."""

        # Check for reply patterns in subject
        subject1 = email1.subject.lower().replace("re:", "").replace("fwd:", "").strip()
        subject2 = email2.subject.lower().replace("re:", "").replace("fwd:", "").strip()

        return subject1 == subject2 or abs(len(subject1) - len(subject2)) < 5

    def _has_sender_recipient_relationship(
        self, email1: EmailData, email2: EmailData
    ) -> bool:
        """Check if emails have sender-recipient relationship."""
        return email1.sender in email2.recipients or email2.sender in email1.recipients

    async def _calculate_topic_similarity(
        self, email1: EmailData, email2: EmailData
    ) -> float:
        """Calculate topic similarity between emails using SambaNova."""

        system_prompt = """You are an expert at analyzing email content similarity. Calculate the semantic similarity between two emails based on their topics, keywords, and business context."""

        user_prompt = f"""Calculate the topic similarity between these two emails on a scale of 0.0 to 1.0:

EMAIL 1:
Subject: {email1.subject}
Content: {email1.body[:500]}...

EMAIL 2:
Subject: {email2.subject}
Content: {email2.body[:500]}...

Consider:
- Common keywords and phrases
- Business context and project references
- Similar action items or requests
- Related stakeholders mentioned

Respond with only a number between 0.0 and 1.0 representing similarity."""

        try:
            response = await self.sambanova._make_api_request(
                user_prompt, system_prompt
            )
            response_text = response["choices"][0]["message"]["content"].strip()

            # Extract numerical value
            import re

            match = re.search(r"(\d+\.?\d*)", response_text)
            if match:
                similarity = float(match.group(1))
                return min(1.0, max(0.0, similarity))

        except Exception as e:
            self.logger.warning(f"Failed to calculate topic similarity: {e}")

        return 0.0

    async def _analyze_sender_profiles(
        self, email_thread: List[EmailData]
    ) -> List[SenderProfile]:
        """Analyze and build profiles for email senders."""

        sender_emails = set(email.sender for email in email_thread)
        profiles = []

        for sender_email in sender_emails:
            if sender_email in self.sender_profiles_cache:
                profiles.append(self.sender_profiles_cache[sender_email])
                continue

            # Collect all emails from this sender
            sender_emails_list = [
                email for email in email_thread if email.sender == sender_email
            ]

            profile = await self._build_sender_profile(sender_email, sender_emails_list)
            self.sender_profiles_cache[sender_email] = profile
            profiles.append(profile)

        return profiles

    async def _build_sender_profile(
        self, sender_email: str, sender_emails: List[EmailData]
    ) -> SenderProfile:
        """Build a comprehensive profile for a sender."""

        # Extract name from email content or address
        name = self._extract_sender_name(sender_emails)

        # Detect organizational role
        role = self._detect_organizational_role(sender_emails)

        # Calculate authority level
        authority_level = self._calculate_authority_level(sender_emails, role)

        # Analyze communication style
        communication_style = await self._analyze_communication_style(sender_emails)

        # Extract frequent topics
        frequent_topics = await self._extract_frequent_topics(sender_emails)

        return SenderProfile(
            email_address=sender_email,
            name=name,
            role=role,
            authority_level=authority_level,
            communication_style=communication_style,
            frequent_topics=frequent_topics,
        )

    def _extract_sender_name(self, emails: List[EmailData]) -> Optional[str]:
        """Extract sender name from email signatures or content."""
        # Simple implementation - in production, this would be more sophisticated
        for email in emails:
            # Look for signature patterns
            lines = email.body.split("\n")
            for line in lines[-5:]:  # Check last 5 lines for signature
                if any(
                    word in line.lower() for word in ["regards", "sincerely", "best"]
                ):
                    next_line_idx = lines.index(line) + 1
                    if next_line_idx < len(lines):
                        potential_name = lines[next_line_idx].strip()
                        if len(potential_name.split()) <= 3 and potential_name:
                            return potential_name

        return None

    def _detect_organizational_role(
        self, emails: List[EmailData]
    ) -> Optional[OrganizationalRole]:
        """Detect organizational role from email content and patterns."""

        all_content = " ".join(
            [f"{email.subject} {email.body}" for email in emails]
        ).lower()

        # Check for authority indicators in content
        if any(indicator in all_content for indicator in ["ceo", "president", "chief"]):
            return OrganizationalRole.EXECUTIVE
        elif any(
            indicator in all_content
            for indicator in ["director", "vp", "vice president"]
        ):
            return OrganizationalRole.MANAGER
        elif any(indicator in all_content for indicator in ["manager", "lead", "head"]):
            return OrganizationalRole.TEAM_LEAD
        elif any(indicator in all_content for indicator in ["client", "customer"]):
            return OrganizationalRole.CLIENT
        elif any(
            indicator in all_content
            for indicator in ["vendor", "supplier", "contractor"]
        ):
            return OrganizationalRole.VENDOR

        return OrganizationalRole.INDIVIDUAL_CONTRIBUTOR

    def _calculate_authority_level(
        self, emails: List[EmailData], role: Optional[OrganizationalRole]
    ) -> float:
        """Calculate authority level based on role and communication patterns."""

        base_authority = {
            OrganizationalRole.EXECUTIVE: 0.9,
            OrganizationalRole.MANAGER: 0.7,
            OrganizationalRole.TEAM_LEAD: 0.6,
            OrganizationalRole.INDIVIDUAL_CONTRIBUTOR: 0.4,
            OrganizationalRole.CLIENT: 0.8,
            OrganizationalRole.VENDOR: 0.3,
            OrganizationalRole.EXTERNAL: 0.2,
        }.get(role, 0.5)

        # Adjust based on communication patterns
        authority_indicators = 0
        total_content = " ".join([email.body for email in emails]).lower()

        if "please" in total_content:
            authority_indicators += 0.1  # Polite language
        if any(word in total_content for word in ["approve", "authorize", "decide"]):
            authority_indicators += 0.2  # Decision-making language
        if len(emails) > 5:  # Active communicator
            authority_indicators += 0.1

        return min(1.0, base_authority + authority_indicators)

    async def _analyze_communication_style(self, emails: List[EmailData]) -> str:
        """Analyze communication style of the sender."""

        if not emails:
            return "professional"

        system_prompt = """You are an expert at analyzing communication styles in professional emails. Identify the primary communication style based on tone, language patterns, and formality level."""

        email_samples = "\n\n".join(
            [
                f"Subject: {email.subject}\nContent: {email.body[:300]}..."
                for email in emails[:3]  # Analyze up to 3 emails
            ]
        )

        user_prompt = f"""Analyze the communication style of the sender based on these email samples:

{email_samples}

Identify the primary communication style from these options:
- formal: Very structured, official language, proper grammar
- professional: Business-appropriate, clear, respectful
- casual: Relaxed, friendly, conversational
- direct: Straightforward, brief, to-the-point
- diplomatic: Careful, tactful, considerate phrasing

Respond with only one word representing the primary style."""

        try:
            response = await self.sambanova._make_api_request(
                user_prompt, system_prompt
            )
            style = response["choices"][0]["message"]["content"].strip().lower()

            valid_styles = ["formal", "professional", "casual", "direct", "diplomatic"]
            return style if style in valid_styles else "professional"

        except Exception as e:
            self.logger.warning(f"Failed to analyze communication style: {e}")
            return "professional"

    async def _extract_frequent_topics(self, emails: List[EmailData]) -> List[str]:
        """Extract frequently discussed topics from sender's emails."""

        if not emails:
            return []

        system_prompt = """You are an expert at identifying key topics and themes in business email communications. Extract the main topics that appear frequently in the sender's emails."""

        email_content = "\n\n".join(
            [
                f"Subject: {email.subject}\nContent: {email.body[:200]}..."
                for email in emails
            ]
        )

        user_prompt = f"""Extract the main topics frequently discussed in these emails:

{email_content}

Identify 3-5 key topics or themes that appear across multiple emails. Focus on:
- Business projects or initiatives
- Specific products or services
- Recurring meeting topics
- Key business processes
- Important relationships or partnerships

Respond with a JSON array of topics: ["topic1", "topic2", "topic3"]"""

        try:
            response = await self.sambanova._make_api_request(
                user_prompt, system_prompt
            )
            response_text = response["choices"][0]["message"]["content"]

            topics_data = self.sambanova._extract_json_from_response(response_text)
            if isinstance(topics_data, list):
                return topics_data[:5]  # Limit to 5 topics

        except Exception as e:
            self.logger.warning(f"Failed to extract frequent topics: {e}")

        return []

    async def _analyze_organizational_hierarchy(
        self,
        email_thread: List[EmailData],
        organizational_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyze organizational hierarchy from email patterns."""

        hierarchy = {
            "authority_relationships": [],
            "reporting_structure": {},
            "decision_makers": [],
            "stakeholder_influence": {},
        }

        # Use sender profiles to build hierarchy
        for email in email_thread:
            # This is a simplified implementation
            # In production, this would analyze CC patterns, response times, etc.
            pass

        return hierarchy

    async def _analyze_communication_patterns(
        self, email_thread: List[EmailData]
    ) -> Dict[str, Any]:
        """Analyze communication patterns in the thread."""

        patterns = {
            "response_times": [],
            "communication_frequency": {},
            "escalation_patterns": [],
            "collaboration_indicators": [],
        }

        # Analyze response times
        sorted_emails = sorted(email_thread, key=lambda x: x.timestamp)
        for i in range(1, len(sorted_emails)):
            time_diff = (
                sorted_emails[i].timestamp - sorted_emails[i - 1].timestamp
            ).total_seconds()
            patterns["response_times"].append(time_diff)

        # Communication frequency by sender
        sender_counts = Counter(email.sender for email in email_thread)
        patterns["communication_frequency"] = dict(sender_counts)

        return patterns

    def _detect_escalation_indicators(self, email_thread: List[EmailData]) -> List[str]:
        """Detect escalation indicators in the email thread."""
        indicators = []

        for email in email_thread:
            content = f"{email.subject} {email.body}".lower()

            for pattern in self.escalation_patterns:
                if pattern in content:
                    indicators.append(pattern)

        return list(set(indicators))  # Remove duplicates

    def _detect_conflict_indicators(self, email_thread: List[EmailData]) -> List[str]:
        """Detect conflict indicators in the email thread."""
        indicators = []

        for email in email_thread:
            content = f"{email.subject} {email.body}".lower()

            for pattern in self.conflict_patterns:
                if pattern in content:
                    indicators.append(pattern)

        return list(set(indicators))

    def _detect_consensus_signals(self, email_thread: List[EmailData]) -> List[str]:
        """Detect consensus-building signals in the email thread."""
        signals = []

        for email in email_thread:
            content = f"{email.subject} {email.body}".lower()

            for pattern in self.consensus_patterns:
                if pattern in content:
                    signals.append(pattern)

        return list(set(signals))

    async def _correlate_project_contexts(
        self, email_thread: List[EmailData]
    ) -> List[ProjectContext]:
        """Correlate emails with project contexts."""

        project_contexts = []

        # Extract potential project names and contexts
        all_content = " ".join(
            [f"{email.subject} {email.body}" for email in email_thread]
        )

        system_prompt = """You are an expert at identifying project contexts in business email communications. Extract project information that appears to be discussed in the email thread."""

        user_prompt = f"""Analyze this email thread content for project contexts:

{all_content[:2000]}...

Identify any projects, initiatives, or business contexts being discussed. For each project identified, provide:
- Project name or identifier
- Key participants mentioned
- Current status or phase
- Priority indicators

Respond with JSON array of projects:
[{{"project_name": "...", "participants": ["..."], "current_phase": "...", "priority_level": "..."}}]"""

        try:
            response = await self.sambanova._make_api_request(
                user_prompt, system_prompt
            )
            response_text = response["choices"][0]["message"]["content"]

            projects_data = self.sambanova._extract_json_from_response(response_text)
            if isinstance(projects_data, list):
                for project_data in projects_data:
                    try:
                        project_context = ProjectContext(**project_data)
                        project_contexts.append(project_context)
                    except Exception as e:
                        self.logger.warning(f"Failed to create project context: {e}")

        except Exception as e:
            self.logger.warning(f"Failed to correlate project contexts: {e}")

        return project_contexts

    async def analyze_thread_summary(self, email_thread: List[EmailData]) -> str:
        """Generate an intelligent summary of the email thread."""

        # Use the base SambaNova interface for thread analysis
        context_analysis = await self.sambanova.analyze_context(email_thread)
        return context_analysis.thread_summary

    async def detect_decision_points(self, email_thread: List[EmailData]) -> List[str]:
        """Detect decision points in the email thread."""

        context_analysis = await self.sambanova.analyze_context(email_thread)
        return context_analysis.decision_points

    def get_context_analysis_stats(self) -> Dict[str, Any]:
        """Get statistics about context analysis engine."""
        return {
            "engine_name": "SambaNova Context Analysis Engine",
            "version": "1.0.0",
            "features": [
                "email_relationship_analysis",
                "sender_profiling",
                "organizational_hierarchy_detection",
                "communication_pattern_analysis",
                "escalation_detection",
                "conflict_indicator_detection",
                "consensus_building_detection",
                "project_correlation",
            ],
            "relationship_types": [r.value for r in RelationshipType],
            "organizational_roles": [r.value for r in OrganizationalRole],
            "conversation_states": [s.value for s in ConversationState],
            "cache_size": {
                "sender_profiles": len(self.sender_profiles_cache),
                "project_contexts": len(self.project_contexts_cache),
            },
        }


# Factory function for easy integration
async def create_context_analysis_engine(
    sambanova_interface: Optional[SambaNovaInterface] = None,
    config: Optional[ContextAnalysisConfig] = None,
) -> ContextAnalysisEngine:
    """
    Factory function to create context analysis engine.

    Args:
        sambanova_interface: Optional SambaNova interface
        config: Optional analysis configuration

    Returns:
        Initialized ContextAnalysisEngine
    """
    engine = ContextAnalysisEngine(sambanova_interface, config)

    # Test basic functionality
    try:
        test_email = EmailData(
            id="test_context",
            subject="Test Context Analysis",
            body="This is a test email for context analysis functionality.",
            sender="test@example.com",
            recipients=["recipient@example.com"],
            timestamp=datetime.now(),
        )

        await engine.analyze_email_context(test_email)

        logging.getLogger(__name__).info(
            "Context analysis engine initialized and tested successfully"
        )
        return engine

    except Exception as e:
        logging.getLogger(__name__).error(f"Context analysis engine test failed: {e}")
        raise RuntimeError(f"Failed to initialize context analysis engine: {e}")
