"""
Advanced Sentiment & Intent Analysis Engine
Implements sophisticated sentiment and intent classification using SambaNova's advanced language understanding.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from ...config import get_sambanova_config
from .sambanova_interface import EmailData, SambaNovaInterface


class PrimaryEmotion(str, Enum):
    """Primary emotions detected in emails."""

    FRUSTRATED = "frustrated"
    SATISFIED = "satisfied"
    URGENT = "urgent"
    APPRECIATIVE = "appreciative"
    CONCERNED = "concerned"
    EXCITED = "excited"
    DISAPPOINTED = "disappointed"
    NEUTRAL = "neutral"
    ANGRY = "angry"
    HOPEFUL = "hopeful"


class ProfessionalTone(str, Enum):
    """Professional tone classification."""

    FORMAL = "formal"
    CASUAL = "casual"
    AGGRESSIVE = "aggressive"
    DIPLOMATIC = "diplomatic"
    FRIENDLY = "friendly"
    AUTHORITATIVE = "authoritative"
    SUBMISSIVE = "submissive"
    COLLABORATIVE = "collaborative"


class ResponseUrgency(str, Enum):
    """Response urgency classification."""

    IMMEDIATE = "immediate"
    SAME_DAY = "same_day"
    NEXT_BUSINESS_DAY = "next_business_day"
    WITHIN_WEEK = "within_week"
    NO_RUSH = "no_rush"


class IntentType(str, Enum):
    """Types of intents in emails."""

    REQUEST = "request"
    COMPLAINT = "complaint"
    APPRECIATION = "appreciation"
    INFORMATION_SHARING = "information_sharing"
    MEETING_SCHEDULING = "meeting_scheduling"
    DECISION_MAKING = "decision_making"
    STATUS_UPDATE = "status_update"
    FOLLOW_UP = "follow_up"
    ESCALATION = "escalation"
    COLLABORATION = "collaboration"
    NEGOTIATION = "negotiation"
    APPROVAL_SEEKING = "approval_seeking"


class CulturalContext(str, Enum):
    """Cultural communication contexts."""

    WESTERN_DIRECT = "western_direct"
    WESTERN_POLITE = "western_polite"
    ASIAN_HIERARCHICAL = "asian_hierarchical"
    LATIN_EXPRESSIVE = "latin_expressive"
    MIDDLE_EASTERN_FORMAL = "middle_eastern_formal"
    SCANDINAVIAN_EGALITARIAN = "scandinavian_egalitarian"
    UNIVERSAL_PROFESSIONAL = "universal_professional"


class SentimentAnalysis(BaseModel):
    """Enhanced multi-dimensional sentiment analysis."""

    primary_emotion: PrimaryEmotion = Field(..., description="Primary detected emotion")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Emotional intensity")
    professional_tone: ProfessionalTone = Field(
        ..., description="Professional communication tone"
    )
    escalation_risk: float = Field(
        ..., ge=0.0, le=1.0, description="Risk of escalation"
    )
    response_urgency: ResponseUrgency = Field(
        ..., description="Required response urgency"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")

    # Additional sentiment dimensions
    valence: float = Field(
        ..., ge=-1.0, le=1.0, description="Positive/negative sentiment"
    )
    arousal: float = Field(
        ..., ge=0.0, le=1.0, description="Emotional activation level"
    )
    dominance: float = Field(
        ..., ge=0.0, le=1.0, description="Control/submission level"
    )

    # Context factors
    cultural_context: Optional[CulturalContext] = Field(
        None, description="Cultural communication context"
    )
    stress_indicators: List[str] = Field(
        default_factory=list, description="Detected stress signals"
    )
    satisfaction_indicators: List[str] = Field(
        default_factory=list, description="Satisfaction signals"
    )


class IntentAnalysis(BaseModel):
    """Intent classification and analysis."""

    primary_intent: IntentType = Field(..., description="Primary detected intent")
    secondary_intents: List[IntentType] = Field(
        default_factory=list, description="Secondary intents"
    )
    intent_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Intent classification confidence"
    )

    # Intent-specific details
    action_required: bool = Field(
        default=False, description="Whether action is required"
    )
    deadline_implied: bool = Field(
        default=False, description="Whether deadline is implied"
    )
    stakeholders_involved: List[str] = Field(
        default_factory=list, description="Identified stakeholders"
    )
    decision_points: List[str] = Field(
        default_factory=list, description="Decision points identified"
    )

    # Communication patterns
    communication_style: str = Field(
        default="direct", description="Communication style used"
    )
    politeness_level: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Politeness level"
    )
    assertiveness_level: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Assertiveness level"
    )


class ConflictAnalysis(BaseModel):
    """Conflict and tension detection."""

    conflict_detected: bool = Field(
        default=False, description="Whether conflict is detected"
    )
    conflict_intensity: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Conflict intensity"
    )
    conflict_type: Optional[str] = Field(None, description="Type of conflict")

    tension_indicators: List[str] = Field(
        default_factory=list, description="Tension indicators"
    )
    disagreement_points: List[str] = Field(
        default_factory=list, description="Points of disagreement"
    )
    resolution_potential: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Resolution potential"
    )

    escalation_triggers: List[str] = Field(
        default_factory=list, description="Escalation triggers"
    )
    de_escalation_opportunities: List[str] = Field(
        default_factory=list, description="De-escalation opportunities"
    )


class EngagementAnalysis(BaseModel):
    """Engagement and satisfaction scoring."""

    engagement_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall engagement level"
    )
    satisfaction_score: float = Field(
        ..., ge=0.0, le=1.0, description="Satisfaction level"
    )

    engagement_indicators: List[str] = Field(
        default_factory=list, description="Engagement indicators"
    )
    disengagement_signals: List[str] = Field(
        default_factory=list, description="Disengagement signals"
    )

    collaboration_willingness: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Willingness to collaborate"
    )
    responsiveness_prediction: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Predicted responsiveness"
    )


class EnhancedSentimentAnalysis(BaseModel):
    """Comprehensive sentiment and intent analysis result."""

    email_id: str = Field(..., description="Email identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Analysis timestamp"
    )

    sentiment: SentimentAnalysis = Field(..., description="Sentiment analysis")
    intent: IntentAnalysis = Field(..., description="Intent analysis")
    conflict: ConflictAnalysis = Field(..., description="Conflict analysis")
    engagement: EngagementAnalysis = Field(..., description="Engagement analysis")

    # Overall assessment
    overall_risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall communication risk"
    )
    recommended_response_strategy: str = Field(
        ..., description="Recommended response approach"
    )
    priority_score: float = Field(
        ..., ge=0.0, le=1.0, description="Priority score for response"
    )

    # Metadata
    analysis_version: str = Field(default="1.0", description="Analysis engine version")
    processing_time_ms: Optional[float] = Field(
        None, description="Processing time in milliseconds"
    )


@dataclass
class SentimentAnalysisConfig:
    """Configuration for sentiment analysis engine."""

    enable_cultural_context: bool = True
    enable_conflict_detection: bool = True
    enable_engagement_scoring: bool = True
    confidence_threshold: float = 0.6
    escalation_threshold: float = 0.7
    max_analysis_length: int = 5000
    use_advanced_prompting: bool = True


class SentimentAnalysisEngine:
    """
    Advanced sentiment and intent analysis engine using SambaNova.

    Provides sophisticated multi-dimensional sentiment analysis, intent classification,
    conflict detection, and engagement scoring with cultural context awareness.
    """

    def __init__(
        self,
        sambanova_interface: Optional[SambaNovaInterface] = None,
        config: Optional[SentimentAnalysisConfig] = None,
    ):
        """
        Initialize sentiment analysis engine.

        Args:
            sambanova_interface: Optional SambaNova interface
            config: Optional configuration for analysis
        """
        self.sambanova = sambanova_interface or SambaNovaInterface(
            get_sambanova_config()
        )
        self.config = config or SentimentAnalysisConfig()
        self.logger = logging.getLogger(__name__)

        # Pattern matchers for quick detection
        self.stress_patterns = [
            r"stress\w*",
            r"overwhelm\w*",
            r"pressure",
            r"deadline",
            r"urgent",
            r"can\'t handle",
            r"too much",
            r"burning out",
            r"exhausted",
        ]

        self.satisfaction_patterns = [
            r"thank",
            r"appreciate",
            r"excellent",
            r"great job",
            r"well done",
            r"satisfied",
            r"happy with",
            r"pleased",
            r"impressed",
        ]

        self.conflict_patterns = [
            r"disagree",
            r"unacceptable",
            r"disappointed",
            r"concern\w*",
            r"issue",
            r"problem",
            r"not happy",
            r"frustrated",
        ]

        self.escalation_patterns = [
            r"escalat\w*",
            r"management",
            r"supervisor",
            r"complaint",
            r"formal complaint",
            r"take this further",
            r"higher up",
        ]

        # Cultural context indicators
        self.cultural_indicators = {
            "western_direct": [r"frankly", r"honestly", r"straight up", r"bottom line"],
            "western_polite": [
                r"please",
                r"would you mind",
                r"if possible",
                r"thank you",
            ],
            "asian_hierarchical": [
                r"respectfully",
                r"humbly",
                r"honor",
                r"consideration",
            ],
            "latin_expressive": [r"!+", r"excitement", r"enthusiasm", r"passion"],
            "middle_eastern_formal": [
                r"esteemed",
                r"distinguished",
                r"honor",
                r"respect",
            ],
        }

        self.logger.info(
            "SentimentAnalysisEngine initialized with SambaNova integration"
        )

    async def analyze_sentiment_and_intent(
        self, email_data: EmailData, context_emails: Optional[List[EmailData]] = None
    ) -> EnhancedSentimentAnalysis:
        """
        Perform comprehensive sentiment and intent analysis.

        Args:
            email_data: Email to analyze
            context_emails: Optional context emails for better analysis

        Returns:
            Enhanced sentiment analysis with all dimensions
        """
        start_time = datetime.utcnow()
        self.logger.info(f"Starting sentiment analysis for email {email_data.id}")

        try:
            # Prepare email content for analysis
            email_content = self._prepare_email_content(email_data)

            # Phase 1: Multi-dimensional sentiment analysis
            sentiment = await self._analyze_sentiment_dimensions(
                email_data, email_content
            )

            # Phase 2: Intent classification
            intent = await self._analyze_intent(
                email_data, email_content, context_emails
            )

            # Phase 3: Conflict and tension detection
            conflict = (
                await self._analyze_conflict(email_data, email_content)
                if self.config.enable_conflict_detection
                else ConflictAnalysis()
            )

            # Phase 4: Engagement and satisfaction scoring
            engagement = (
                await self._analyze_engagement(email_data, email_content)
                if self.config.enable_engagement_scoring
                else EngagementAnalysis(engagement_score=0.5, satisfaction_score=0.5)
            )

            # Phase 5: Overall assessment
            overall_risk = self._calculate_overall_risk(
                sentiment, intent, conflict, engagement
            )
            response_strategy = await self._generate_response_strategy(
                sentiment, intent, conflict, engagement
            )
            priority = self._calculate_priority_score(
                sentiment, intent, conflict, engagement
            )

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Build comprehensive analysis
            analysis = EnhancedSentimentAnalysis(
                email_id=email_data.id,
                sentiment=sentiment,
                intent=intent,
                conflict=conflict,
                engagement=engagement,
                overall_risk_score=overall_risk,
                recommended_response_strategy=response_strategy,
                priority_score=priority,
                processing_time_ms=processing_time,
            )

            self.logger.info(f"Sentiment analysis completed in {processing_time:.2f}ms")
            return analysis

        except Exception as e:
            self.logger.error(f"Error in sentiment analysis: {e}")
            # Return basic analysis on error
            return self._create_fallback_analysis(email_data)

    def _prepare_email_content(self, email_data: EmailData) -> str:
        """Prepare email content for analysis."""
        content = f"Subject: {email_data.subject}\n\n{email_data.body}"

        # Limit content length for analysis
        if len(content) > self.config.max_analysis_length:
            content = content[: self.config.max_analysis_length] + "..."

        return content

    async def _analyze_sentiment_dimensions(
        self, email_data: EmailData, content: str
    ) -> SentimentAnalysis:
        """Analyze multi-dimensional sentiment."""

        system_prompt = """You are an expert at analyzing emotions and sentiment in professional communications. 
        Analyze the email for multiple sentiment dimensions including emotion, tone, urgency, and cultural context.
        Provide precise numerical scores and classifications."""

        user_prompt = f"""Analyze this email for advanced sentiment dimensions:

{content}

Please analyze and provide:

1. PRIMARY_EMOTION: Choose from frustrated, satisfied, urgent, appreciative, concerned, excited, disappointed, neutral, angry, hopeful
2. INTENSITY: Emotional intensity (0.0-1.0)
3. PROFESSIONAL_TONE: Choose from formal, casual, aggressive, diplomatic, friendly, authoritative, submissive, collaborative
4. ESCALATION_RISK: Risk of escalation (0.0-1.0)
5. RESPONSE_URGENCY: Choose from immediate, same_day, next_business_day, within_week, no_rush
6. VALENCE: Positive/negative sentiment (-1.0 to 1.0)
7. AROUSAL: Emotional activation level (0.0-1.0)
8. DOMINANCE: Control/submission level (0.0-1.0)
9. CULTURAL_CONTEXT: Choose from western_direct, western_polite, asian_hierarchical, latin_expressive, middle_eastern_formal, scandinavian_egalitarian, universal_professional
10. CONFIDENCE: Analysis confidence (0.0-1.0)

Respond with JSON:
{{
    "primary_emotion": "...",
    "intensity": 0.0,
    "professional_tone": "...",
    "escalation_risk": 0.0,
    "response_urgency": "...",
    "valence": 0.0,
    "arousal": 0.0,
    "dominance": 0.0,
    "cultural_context": "...",
    "confidence": 0.0
}}"""

        try:
            response = await self.sambanova._make_api_request(
                user_prompt, system_prompt
            )
            response_text = response["choices"][0]["message"]["content"]

            sentiment_data = self.sambanova._extract_json_from_response(response_text)

            # Extract pattern-based indicators
            stress_indicators = self._extract_stress_indicators(content)
            satisfaction_indicators = self._extract_satisfaction_indicators(content)

            return SentimentAnalysis(
                primary_emotion=PrimaryEmotion(
                    sentiment_data.get("primary_emotion", "neutral")
                ),
                intensity=float(sentiment_data.get("intensity", 0.5)),
                professional_tone=ProfessionalTone(
                    sentiment_data.get("professional_tone", "professional")
                ),
                escalation_risk=float(sentiment_data.get("escalation_risk", 0.0)),
                response_urgency=ResponseUrgency(
                    sentiment_data.get("response_urgency", "next_business_day")
                ),
                confidence=float(sentiment_data.get("confidence", 0.5)),
                valence=float(sentiment_data.get("valence", 0.0)),
                arousal=float(sentiment_data.get("arousal", 0.5)),
                dominance=float(sentiment_data.get("dominance", 0.5)),
                cultural_context=(
                    CulturalContext(
                        sentiment_data.get("cultural_context", "universal_professional")
                    )
                    if sentiment_data.get("cultural_context")
                    else None
                ),
                stress_indicators=stress_indicators,
                satisfaction_indicators=satisfaction_indicators,
            )

        except Exception as e:
            self.logger.warning(f"Failed to analyze sentiment dimensions: {e}")
            return self._create_fallback_sentiment()

    async def _analyze_intent(
        self,
        email_data: EmailData,
        content: str,
        context_emails: Optional[List[EmailData]] = None,
    ) -> IntentAnalysis:
        """Analyze email intent and communication patterns."""

        # Build context if available
        context_info = ""
        if context_emails:
            context_info = "\n\nContext from previous emails:\n"
            for email in context_emails[-2:]:  # Last 2 emails for context
                context_info += f"- {email.subject}: {email.body[:200]}...\n"

        system_prompt = """You are an expert at understanding communication intent in professional emails.
        Analyze the primary and secondary intents, required actions, and communication patterns."""

        user_prompt = f"""Analyze the intent and communication patterns in this email:

{content}{context_info}

Please identify:

1. PRIMARY_INTENT: Choose from request, complaint, appreciation, information_sharing, meeting_scheduling, decision_making, status_update, follow_up, escalation, collaboration, negotiation, approval_seeking
2. SECONDARY_INTENTS: List up to 3 secondary intents
3. ACTION_REQUIRED: true/false if action is required
4. DEADLINE_IMPLIED: true/false if deadline is implied
5. STAKEHOLDERS: List key stakeholders mentioned
6. DECISION_POINTS: List decision points identified
7. COMMUNICATION_STYLE: direct, indirect, collaborative, authoritative, diplomatic
8. POLITENESS_LEVEL: 0.0-1.0 (how polite)
9. ASSERTIVENESS_LEVEL: 0.0-1.0 (how assertive)
10. INTENT_CONFIDENCE: 0.0-1.0 confidence in classification

Respond with JSON:
{{
    "primary_intent": "...",
    "secondary_intents": ["...", "..."],
    "action_required": true,
    "deadline_implied": false,
    "stakeholders_involved": ["...", "..."],
    "decision_points": ["...", "..."],
    "communication_style": "...",
    "politeness_level": 0.0,
    "assertiveness_level": 0.0,
    "intent_confidence": 0.0
}}"""

        try:
            response = await self.sambanova._make_api_request(
                user_prompt, system_prompt
            )
            response_text = response["choices"][0]["message"]["content"]

            intent_data = self.sambanova._extract_json_from_response(response_text)

            return IntentAnalysis(
                primary_intent=IntentType(
                    intent_data.get("primary_intent", "information_sharing")
                ),
                secondary_intents=[
                    IntentType(intent)
                    for intent in intent_data.get("secondary_intents", [])
                ],
                intent_confidence=float(intent_data.get("intent_confidence", 0.5)),
                action_required=bool(intent_data.get("action_required", False)),
                deadline_implied=bool(intent_data.get("deadline_implied", False)),
                stakeholders_involved=intent_data.get("stakeholders_involved", []),
                decision_points=intent_data.get("decision_points", []),
                communication_style=intent_data.get("communication_style", "direct"),
                politeness_level=float(intent_data.get("politeness_level", 0.5)),
                assertiveness_level=float(intent_data.get("assertiveness_level", 0.5)),
            )

        except Exception as e:
            self.logger.warning(f"Failed to analyze intent: {e}")
            return self._create_fallback_intent()

    async def _analyze_conflict(
        self, email_data: EmailData, content: str
    ) -> ConflictAnalysis:
        """Analyze conflict and tension indicators."""

        # Quick pattern-based detection
        conflict_indicators = self._extract_conflict_indicators(content)
        tension_indicators = self._extract_tension_indicators(content)
        escalation_triggers = self._extract_escalation_triggers(content)

        if not conflict_indicators and not tension_indicators:
            return ConflictAnalysis()

        system_prompt = """You are an expert at detecting conflict, tension, and disagreement in professional communications.
        Analyze the email for signs of conflict and provide detailed assessment."""

        user_prompt = f"""Analyze this email for conflict and tension:

{content}

Detected indicators: {conflict_indicators + tension_indicators}

Please assess:

1. CONFLICT_DETECTED: true/false
2. CONFLICT_INTENSITY: 0.0-1.0 (intensity level)
3. CONFLICT_TYPE: interpersonal, procedural, task-related, resource-based, or null
4. DISAGREEMENT_POINTS: List specific points of disagreement
5. RESOLUTION_POTENTIAL: 0.0-1.0 (likelihood of easy resolution)
6. DE_ESCALATION_OPPORTUNITIES: List opportunities to de-escalate

Respond with JSON:
{{
    "conflict_detected": false,
    "conflict_intensity": 0.0,
    "conflict_type": null,
    "disagreement_points": ["...", "..."],
    "resolution_potential": 0.0,
    "de_escalation_opportunities": ["...", "..."]
}}"""

        try:
            response = await self.sambanova._make_api_request(
                user_prompt, system_prompt
            )
            response_text = response["choices"][0]["message"]["content"]

            conflict_data = self.sambanova._extract_json_from_response(response_text)

            return ConflictAnalysis(
                conflict_detected=bool(conflict_data.get("conflict_detected", False)),
                conflict_intensity=float(conflict_data.get("conflict_intensity", 0.0)),
                conflict_type=conflict_data.get("conflict_type"),
                tension_indicators=tension_indicators,
                disagreement_points=conflict_data.get("disagreement_points", []),
                resolution_potential=float(
                    conflict_data.get("resolution_potential", 0.5)
                ),
                escalation_triggers=escalation_triggers,
                de_escalation_opportunities=conflict_data.get(
                    "de_escalation_opportunities", []
                ),
            )

        except Exception as e:
            self.logger.warning(f"Failed to analyze conflict: {e}")
            return ConflictAnalysis()

    async def _analyze_engagement(
        self, email_data: EmailData, content: str
    ) -> EngagementAnalysis:
        """Analyze engagement and satisfaction levels."""

        # Extract engagement indicators
        engagement_indicators = self._extract_engagement_indicators(content)
        disengagement_signals = self._extract_disengagement_signals(content)

        system_prompt = """You are an expert at assessing engagement and satisfaction in professional communications.
        Analyze the email for signs of engagement, satisfaction, and collaboration willingness."""

        user_prompt = f"""Analyze this email for engagement and satisfaction:

{content}

Please assess:

1. ENGAGEMENT_SCORE: 0.0-1.0 (overall engagement level)
2. SATISFACTION_SCORE: 0.0-1.0 (satisfaction level)
3. COLLABORATION_WILLINGNESS: 0.0-1.0 (willingness to collaborate)
4. RESPONSIVENESS_PREDICTION: 0.0-1.0 (predicted responsiveness)

Respond with JSON:
{{
    "engagement_score": 0.0,
    "satisfaction_score": 0.0,
    "collaboration_willingness": 0.0,
    "responsiveness_prediction": 0.0
}}"""

        try:
            response = await self.sambanova._make_api_request(
                user_prompt, system_prompt
            )
            response_text = response["choices"][0]["message"]["content"]

            engagement_data = self.sambanova._extract_json_from_response(response_text)

            return EngagementAnalysis(
                engagement_score=float(engagement_data.get("engagement_score", 0.5)),
                satisfaction_score=float(
                    engagement_data.get("satisfaction_score", 0.5)
                ),
                engagement_indicators=engagement_indicators,
                disengagement_signals=disengagement_signals,
                collaboration_willingness=float(
                    engagement_data.get("collaboration_willingness", 0.5)
                ),
                responsiveness_prediction=float(
                    engagement_data.get("responsiveness_prediction", 0.5)
                ),
            )

        except Exception as e:
            self.logger.warning(f"Failed to analyze engagement: {e}")
            return EngagementAnalysis(engagement_score=0.5, satisfaction_score=0.5)

    # Pattern extraction methods
    def _extract_stress_indicators(self, content: str) -> List[str]:
        """Extract stress indicators from content."""
        indicators = []
        content_lower = content.lower()

        for pattern in self.stress_patterns:
            matches = re.findall(pattern, content_lower)
            indicators.extend(matches)

        return list(set(indicators))

    def _extract_satisfaction_indicators(self, content: str) -> List[str]:
        """Extract satisfaction indicators from content."""
        indicators = []
        content_lower = content.lower()

        for pattern in self.satisfaction_patterns:
            matches = re.findall(pattern, content_lower)
            indicators.extend(matches)

        return list(set(indicators))

    def _extract_conflict_indicators(self, content: str) -> List[str]:
        """Extract conflict indicators from content."""
        indicators = []
        content_lower = content.lower()

        for pattern in self.conflict_patterns:
            matches = re.findall(pattern, content_lower)
            indicators.extend(matches)

        return list(set(indicators))

    def _extract_tension_indicators(self, content: str) -> List[str]:
        """Extract tension indicators from content."""
        tension_patterns = [
            r"tension",
            r"uncomfortable",
            r"awkward",
            r"difficult",
            r"challenging",
            r"problematic",
            r"concerning",
        ]

        indicators = []
        content_lower = content.lower()

        for pattern in tension_patterns:
            matches = re.findall(pattern, content_lower)
            indicators.extend(matches)

        return list(set(indicators))

    def _extract_escalation_triggers(self, content: str) -> List[str]:
        """Extract escalation triggers from content."""
        triggers = []
        content_lower = content.lower()

        for pattern in self.escalation_patterns:
            matches = re.findall(pattern, content_lower)
            triggers.extend(matches)

        return list(set(triggers))

    def _extract_engagement_indicators(self, content: str) -> List[str]:
        """Extract engagement indicators from content."""
        engagement_patterns = [
            r"excited",
            r"interested",
            r"eager",
            r"looking forward",
            r"happy to",
            r"pleased to",
            r"great opportunity",
        ]

        indicators = []
        content_lower = content.lower()

        for pattern in engagement_patterns:
            matches = re.findall(pattern, content_lower)
            indicators.extend(matches)

        return list(set(indicators))

    def _extract_disengagement_signals(self, content: str) -> List[str]:
        """Extract disengagement signals from content."""
        disengagement_patterns = [
            r"not interested",
            r"can\'t participate",
            r"too busy",
            r"unavailable",
            r"step back",
            r"withdraw",
        ]

        signals = []
        content_lower = content.lower()

        for pattern in disengagement_patterns:
            matches = re.findall(pattern, content_lower)
            signals.extend(matches)

        return list(set(signals))

    # Assessment calculation methods
    def _calculate_overall_risk(
        self,
        sentiment: SentimentAnalysis,
        intent: IntentAnalysis,
        conflict: ConflictAnalysis,
        engagement: EngagementAnalysis,
    ) -> float:
        """Calculate overall communication risk score."""

        risk_factors = [
            sentiment.escalation_risk * 0.3,
            (
                (1.0 - sentiment.intensity) * 0.1
                if sentiment.primary_emotion
                in [PrimaryEmotion.FRUSTRATED, PrimaryEmotion.ANGRY]
                else 0
            ),
            conflict.conflict_intensity * 0.3 if conflict.conflict_detected else 0,
            (1.0 - engagement.satisfaction_score) * 0.2,
            (1.0 - intent.politeness_level) * 0.1,
        ]

        return min(1.0, sum(risk_factors))

    async def _generate_response_strategy(
        self,
        sentiment: SentimentAnalysis,
        intent: IntentAnalysis,
        conflict: ConflictAnalysis,
        engagement: EngagementAnalysis,
    ) -> str:
        """Generate recommended response strategy."""

        # High-level strategy based on analysis
        if conflict.conflict_detected and conflict.conflict_intensity > 0.7:
            return "diplomatic_de_escalation"
        elif sentiment.escalation_risk > 0.7:
            return "immediate_attention_required"
        elif sentiment.primary_emotion == PrimaryEmotion.APPRECIATIVE:
            return "acknowledge_appreciation"
        elif intent.action_required and intent.deadline_implied:
            return "prompt_action_response"
        elif engagement.satisfaction_score < 0.3:
            return "relationship_repair"
        else:
            return "standard_professional_response"

    def _calculate_priority_score(
        self,
        sentiment: SentimentAnalysis,
        intent: IntentAnalysis,
        conflict: ConflictAnalysis,
        engagement: EngagementAnalysis,
    ) -> float:
        """Calculate priority score for response."""

        priority_factors = [
            sentiment.escalation_risk * 0.3,
            (
                0.8
                if sentiment.response_urgency == ResponseUrgency.IMMEDIATE
                else (
                    0.6
                    if sentiment.response_urgency == ResponseUrgency.SAME_DAY
                    else 0.3
                )
            ),
            0.7 if intent.action_required else 0.2,
            conflict.conflict_intensity * 0.2 if conflict.conflict_detected else 0,
            (1.0 - engagement.satisfaction_score) * 0.2,
        ]

        return min(1.0, sum(priority_factors))

    # Fallback methods
    def _create_fallback_analysis(
        self, email_data: EmailData
    ) -> EnhancedSentimentAnalysis:
        """Create fallback analysis when main analysis fails."""
        return EnhancedSentimentAnalysis(
            email_id=email_data.id,
            sentiment=self._create_fallback_sentiment(),
            intent=self._create_fallback_intent(),
            conflict=ConflictAnalysis(),
            engagement=EngagementAnalysis(engagement_score=0.5, satisfaction_score=0.5),
            overall_risk_score=0.5,
            recommended_response_strategy="standard_professional_response",
            priority_score=0.5,
        )

    def _create_fallback_sentiment(self) -> SentimentAnalysis:
        """Create fallback sentiment analysis."""
        return SentimentAnalysis(
            primary_emotion=PrimaryEmotion.NEUTRAL,
            intensity=0.5,
            professional_tone=ProfessionalTone.FORMAL,
            escalation_risk=0.0,
            response_urgency=ResponseUrgency.NEXT_BUSINESS_DAY,
            confidence=0.3,
            valence=0.0,
            arousal=0.5,
            dominance=0.5,
        )

    def _create_fallback_intent(self) -> IntentAnalysis:
        """Create fallback intent analysis."""
        return IntentAnalysis(
            primary_intent=IntentType.INFORMATION_SHARING,
            intent_confidence=0.3,
            action_required=False,
            deadline_implied=False,
            communication_style="professional",
            politeness_level=0.5,
            assertiveness_level=0.5,
        )

    async def batch_analyze_sentiment(
        self, emails: List[EmailData], max_concurrent: int = 3
    ) -> List[EnhancedSentimentAnalysis]:
        """Batch analyze multiple emails for sentiment and intent."""

        self.logger.info(f"Starting batch sentiment analysis for {len(emails)} emails")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_single(email: EmailData) -> EnhancedSentimentAnalysis:
            async with semaphore:
                return await self.analyze_sentiment_and_intent(email)

        tasks = [analyze_single(email) for email in emails]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and log errors
        analyses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to analyze email {emails[i].id}: {result}")
                analyses.append(self._create_fallback_analysis(emails[i]))
            else:
                analyses.append(result)

        self.logger.info(
            f"Completed batch sentiment analysis for {len(analyses)} emails"
        )
        return analyses

    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get statistics about sentiment analysis engine."""
        return {
            "engine_name": "SambaNova Sentiment Analysis Engine",
            "version": "1.0.0",
            "config": {
                "cultural_context_enabled": self.config.enable_cultural_context,
                "conflict_detection_enabled": self.config.enable_conflict_detection,
                "engagement_scoring_enabled": self.config.enable_engagement_scoring,
                "confidence_threshold": self.config.confidence_threshold,
                "escalation_threshold": self.config.escalation_threshold,
            },
            "capabilities": [
                "multi_dimensional_sentiment",
                "intent_classification",
                "conflict_detection",
                "engagement_scoring",
                "cultural_context_awareness",
            ],
        }


# Factory function for easy integration
async def create_sentiment_analysis_engine(
    sambanova_interface: Optional[SambaNovaInterface] = None,
    config: Optional[SentimentAnalysisConfig] = None,
) -> SentimentAnalysisEngine:
    """Create and initialize sentiment analysis engine."""
    engine = SentimentAnalysisEngine(sambanova_interface, config)
    return engine
