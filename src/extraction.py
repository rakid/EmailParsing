#!/usr/bin/env python3
"""
Email Data Extraction Engine for Inbox Zen
Handles intelligent parsing and extraction of email content and metadata
"""
import html
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ExtractedMetadata:
    """Container for extracted email metadata"""

    urgency_indicators: Dict[str, List[str]]
    temporal_references: List[str]
    contact_info: Dict[str, List[str]]  # phone, email, etc.
    links: List[str]
    action_words: List[str]
    sentiment_indicators: Dict[str, List[str]]
    priority_keywords: List[str]


class EmailExtractor:
    """Advanced email content extraction and analysis engine"""

    # Urgency detection patterns
    URGENCY_PATTERNS = {
        "high": [
            r"\b(urgent|emergency|asap|immediately|critical|deadline)\b",
            r"\b(rush|hurry|quick|fast|soon)\b",
            r"\b(important|priority|crucial)\b",
            r"(!)(\s*!)*",  # Multiple exclamation marks
            r"\b(respond|reply)\s+(by|before|within)",
            r"\b(due|expires?|deadline)\s+(today|tomorrow|this week)",
            r"\b(meeting|call|conference)\s+(in|at)\s+\d+\s+(minutes?|hours?)",
        ],
        "medium": [
            r"\b(please\s+)?(respond|reply|confirm|let\s+me\s+know)\b",
            r"\b(when\s+you\s+get\s+a\s+chance|at\s+your\s+convenience)\b",
            r"\b(follow[\s-]?up|reminder)\b",
            r"\b(schedule|plan|arrange)\b",
        ],
        "low": [
            r"\b(fyi|for\s+your\s+information|heads\s+up)\b",
            r"\b(no\s+rush|when\s+convenient|whenever)\b",
            r"\b(just\s+wanted\s+to|thought\s+you\s+might)\b",
        ],
    }

    # Temporal reference patterns
    TIME_PATTERNS = [
        r"\b(today|tomorrow|yesterday)\b",
        r"\b(this|next|last)\s+"
        r"(week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b\d{1,2}[:/]\d{1,2}(?:[:/]\d{2,4})?\b",  # Time formats
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",  # Date formats
        r"\b(january|february|march|april|may|june|july|august|september|october"
        r"|november|december)\s+\d{1,2}\b",
        r"\bin\s+\d+\s+(minutes?|hours?|days?|weeks?|months?)\b",
        r"\b(due|expires?|deadline)\s+\w+\b",
        r"\b(before|after|by)\s+\d+[ap]m\b",
    ]

    # Contact information patterns
    CONTACT_PATTERNS = {
        "phone": [
            r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?"
            r"([0-9]{4})\b",
            r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
        ],
        "email": [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ],
        "url": [
            r'https?://[^\s<>"\']+',
            r'www\.[^\s<>"\']+',
        ],
    }

    # Action word patterns
    ACTION_PATTERNS = [
        r"\b(please\s+)?(do|send|provide|submit|complete|finish|review|approve|"
        r"confirm|schedule|call|email|respond|reply)\b",
        r"\b(need|require|must|should|have\s+to)\b",
        r"\b(can\s+you|could\s+you|would\s+you)\b",
        r"\b(let\s+me\s+know|keep\s+me\s+posted|update\s+me)\b",
    ]

    # Sentiment indicators
    SENTIMENT_PATTERNS = {
        "positive": [
            r"\b(thank|thanks|appreciate|excellent|great|wonderful|perfect|"
            r"good\s+news)\b",
            r"\b(congratulations|well\s+done|good\s+job)\b",
            r"[😊😃😄😁🙂👍✅]",  # Positive emojis
        ],
        "negative": [
            r"\b(sorry|apologize|unfortunately|problem|issue|error|mistake|wrong|"
            r"failed?)\b",
            r"\b(concerned|worried|frustrated|disappointed|upset)\b",
            r"[😞😟😢😠😡❌]",  # Negative emojis
        ],
        "neutral": [
            r"\b(fyi|information|update|notice|announcement)\b",
            r"\b(regarding|concerning|about|re:)\b",
        ],
    }

    def __init__(self):
        """Initialize the email extractor"""
        self.compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, Any]:
        """Pre-compile regex patterns for better performance"""
        compiled: Dict[str, Any] = {}

        # Compile urgency patterns
        compiled["urgency"] = {}
        for level, patterns in self.URGENCY_PATTERNS.items():
            compiled["urgency"][level] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

        # Compile other patterns
        compiled["time"] = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.TIME_PATTERNS
        ]
        compiled["actions"] = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.ACTION_PATTERNS
        ]

        # Compile contact patterns
        compiled["contact"] = {}
        for contact_type, patterns in self.CONTACT_PATTERNS.items():
            compiled["contact"][contact_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

        # Compile sentiment patterns
        compiled["sentiment"] = {}
        for sentiment, patterns in self.SENTIMENT_PATTERNS.items():
            compiled["sentiment"][sentiment] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

        return compiled

    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""

        # Remove HTML tags and decode entities
        text = html.unescape(text)
        text = re.sub(r"<[^>]+>", " ", text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        # Remove quoted content (email chains)
        text = re.sub(r"^>.*$", "", text, flags=re.MULTILINE)

        return text

    def extract_urgency_indicators(self, text: str) -> Dict[str, List[str]]:
        """Extract urgency indicators from text"""
        indicators: Dict[str, List[str]] = {"high": [], "medium": [], "low": []}

        for level, patterns in self.compiled_patterns["urgency"].items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    # Handle both string matches and tuple matches
                    for match in matches:
                        if isinstance(match, tuple):
                            # Take the first non-empty group
                            match_str = next(
                                (group for group in match if group), str(match[0])
                            )
                        else:
                            match_str = str(match)
                        indicators[level].append(match_str.lower().strip())

                        # Early termination for performance - limit to 20 matches per level
                        if len(indicators[level]) >= 20:
                            break

                # Stop processing more patterns if we have enough high urgency indicators
                if level == "high" and len(indicators[level]) >= 10:
                    break

        return indicators

    def extract_temporal_references(self, text: str) -> List[str]:
        """Extract temporal references from text"""
        references = []

        for pattern in self.compiled_patterns["time"]:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    # Take the first non-empty group or join the tuple
                    match_str = next(
                        (group for group in match if group), " ".join(match)
                    )
                else:
                    match_str = str(match)
                references.append(match_str.lower().strip())

                # Early termination for performance - limit to 15 temporal references
                if len(references) >= 15:
                    break

            if len(references) >= 15:
                break

        return list(set(references))  # Remove duplicates

    def extract_contact_info(self, text: str) -> Dict[str, List[str]]:
        """Extract contact information from text"""
        contact_info: Dict[str, List[str]] = {"phone": [], "email": [], "url": []}

        for contact_type, patterns in self.compiled_patterns["contact"].items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if contact_type == "phone":
                    # Format phone numbers consistently
                    formatted_phones = []
                    for match in matches:
                        if isinstance(match, tuple):
                            formatted_phones.append(
                                f"({match[0]}) {match[1]}-{match[2]}"
                            )
                        else:
                            formatted_phones.append(match)

                        # Early termination for performance - limit to 10 phone numbers
                        if len(formatted_phones) >= 10:
                            break
                    contact_info[contact_type].extend(formatted_phones)
                else:
                    # Limit other contact types too
                    limited_matches = matches[:10] if len(matches) > 10 else matches
                    contact_info[contact_type].extend(limited_matches)

                # Stop if we have enough matches for this contact type
                if len(contact_info[contact_type]) >= 10:
                    break

        return contact_info

    def extract_action_words(self, text: str) -> List[str]:
        """Extract action words and phrases"""
        actions = []

        for pattern in self.compiled_patterns["actions"]:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    # Take the second group (action word) or first non-empty
                    # group
                    if len(match) > 1 and match[1]:
                        match_str = match[1]
                    else:
                        match_str = next(
                            (group for group in match if group), str(match[0])
                        )
                else:
                    match_str = str(match)
                actions.append(match_str.lower().strip())

                # Early termination for performance - limit to 20 action words
                if len(actions) >= 20:
                    break

            if len(actions) >= 20:
                break

        return list(set(actions))

    def extract_sentiment_indicators(self, text: str) -> Dict[str, List[str]]:
        """Extract sentiment indicators"""
        sentiment: Dict[str, List[str]] = {
            "positive": [],
            "negative": [],
            "neutral": [],
        }

        for sentiment_type, patterns in self.compiled_patterns["sentiment"].items():
            for pattern in patterns:
                matches = pattern.findall(text)
                for match in matches:
                    if isinstance(match, tuple):
                        # Take the first non-empty group
                        match_str = next(
                            (group for group in match if group), str(match[0])
                        )
                    else:
                        match_str = str(match)
                    sentiment[sentiment_type].append(match_str.lower().strip())

                    # Early termination for performance - limit to 10 matches per sentiment type
                    if len(sentiment[sentiment_type]) >= 10:
                        break

                if len(sentiment[sentiment_type]) >= 10:
                    break

        return sentiment

    def calculate_urgency_score(
        self, urgency_indicators: Dict[str, List[str]]
    ) -> Tuple[int, str]:
        """Calculate urgency score and level based on indicators"""
        high_count = len(urgency_indicators["high"])
        medium_count = len(urgency_indicators["medium"])
        low_count = len(urgency_indicators["low"])

        # Calculate weighted score
        score = (high_count * 30) + (medium_count * 15) + (low_count * 5)
        score = min(score, 100)  # Cap at 100

        # Determine urgency level
        if score >= 70 or high_count >= 2:
            level = "high"
        elif score >= 40 or medium_count >= 2:
            level = "medium"
        else:
            level = "low"

        return score, level

    def extract_from_email(self, email_data) -> ExtractedMetadata:
        """Main extraction method - process an EmailData object"""

        # Combine text content
        text_content = ""
        if email_data.text_body:
            text_content += email_data.text_body + " "
        if email_data.html_body:
            text_content += self.clean_text(email_data.html_body) + " "

        # Add subject line with extra weight
        text_content += f"{email_data.subject} " * 3

        # Optimize for large content - limit to first 10KB for regex processing
        # Most important content is usually at the beginning
        if len(text_content) > 10000:
            # Take first 8KB and last 2KB to capture both intro and conclusion
            text_for_analysis = text_content[:8000] + " " + text_content[-2000:]
        else:
            text_for_analysis = text_content

        logger.info(
            f"Extracting metadata from email {email_data.message_id} (content size: {len(text_content)} chars)"
        )

        # Extract all metadata using optimized text
        urgency_indicators = self.extract_urgency_indicators(text_for_analysis)
        temporal_references = self.extract_temporal_references(text_for_analysis)
        contact_info = self.extract_contact_info(text_for_analysis)
        action_words = self.extract_action_words(text_for_analysis)
        sentiment_indicators = self.extract_sentiment_indicators(text_for_analysis)

        # Extract priority keywords (combines urgency and action words)
        priority_keywords = []
        for level_indicators in urgency_indicators.values():
            priority_keywords.extend(level_indicators)
        priority_keywords.extend(action_words[:10])  # Limit to top 10

        # Extract links from contact info
        links = contact_info.get("url", [])

        return ExtractedMetadata(
            urgency_indicators=urgency_indicators,
            temporal_references=temporal_references,
            contact_info=contact_info,
            links=links,
            action_words=action_words,
            sentiment_indicators=sentiment_indicators,
            priority_keywords=list(set(priority_keywords)),
            # Remove duplicates
        )


# Global extractor instance
email_extractor = EmailExtractor()
