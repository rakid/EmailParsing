"""
Supabase Configuration Module
============================

Configuration and constants for Supabase integration with the
Email Parsing MCP Server. This module handles Supabase connection
settings, authentication, and environment configuration.
"""

import os
from typing import Any, Dict, Optional


class SupabaseConfig:
    """Supabase connection configuration with AI-enhanced data support"""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        # Get from environment if not provided
        self.supabase_url = url or os.getenv("SUPABASE_URL", "")
        self.supabase_key = key or os.getenv("SUPABASE_ANON_KEY", "")

        # Optional settings with defaults
        self.auto_refresh_token = True
        self.persist_session = True
        self.detect_session_in_url = True

        # Database settings
        self.schema = "public"

        # Real-time settings
        self.realtime_enabled = True
        self.realtime_heartbeat_interval = 30

        # Connection settings
        self.timeout = 30
        self.max_retries = 3

        # Security settings
        self.jwt_auto_refresh = True
        self.jwt_expiry_margin = 60  # seconds before expiry to refresh

        # AI Processing settings (SambaNova integration)
        self.ai_processing_enabled = True
        self.ai_analysis_retention_days = 365  # Keep AI analysis for 1 year
        self.ai_batch_processing_size = 50
        self.ai_processing_timeout = 300  # 5 minutes

        # Table configuration (enhanced for AI data)
        self.TABLES = {
            "profiles": "profiles",
            "emails": "emails",
            "email_analysis": "email_analysis",
            "email_attachments": "email_attachments",
            "email_tasks": "email_tasks",
            "user_email_mappings": "user_email_mappings",
            "email_analytics": "email_analytics",
            "realtime_subscriptions": "realtime_subscriptions",
            "audit_logs": "audit_logs",
            # AI-enhanced tables
            "ai_processing_jobs": "ai_processing_jobs",
            "ai_model_versions": "ai_model_versions",
            "ai_performance_metrics": "ai_performance_metrics",
        }

        # AI Analysis storage structure
        self.AI_ANALYSIS_SCHEMA = {
            "sambanova_version": "string",
            "processing_timestamp": "timestamp",
            "processing_time": "float",
            "task_extraction": {
                "tasks": "array",
                "overall_urgency": "integer",
                "has_deadlines": "boolean",
                "requires_followup": "boolean",
                "extraction_confidence": "float",
            },
            "sentiment_analysis": {
                "primary_emotion": "string",
                "intensity": "float",
                "professional_tone": "string",
                "escalation_risk": "float",
                "response_urgency": "string",
                "confidence": "float",
                "valence": "float",
                "arousal": "float",
                "dominance": "float",
                "cultural_context": "string",
                "stress_indicators": "array",
                "satisfaction_indicators": "array",
            },
            "intent_analysis": {
                "primary_intent": "string",
                "secondary_intents": "array",
                "intent_confidence": "float",
                "action_required": "boolean",
                "deadline_implied": "boolean",
                "stakeholders_involved": "array",
                "decision_points": "array",
            },
            "context_analysis": {
                "context_keywords": "array",
                "business_context": "string",
                "technical_context": "string",
                "project_context": "string",
                "temporal_context": "string",
                "priority_context": "string",
            },
            "relationships": {
                "email_thread": "array",
                "related_projects": "array",
                "stakeholder_network": "array",
                "follow_up_chains": "array",
            },
        }

    def get_client_options(self) -> Dict[str, Any]:
        """Get Supabase client options"""
        return {
            "auto_refresh_token": self.auto_refresh_token,
            "persist_session": self.persist_session,
            "detect_session_in_url": self.detect_session_in_url,
            "schema": self.schema,
            "realtime": {
                "enabled": self.realtime_enabled,
                "heartbeat_interval": self.realtime_heartbeat_interval,
            },
        }

    def is_configured(self) -> bool:
        """Check if Supabase is properly configured"""
        return bool(self.supabase_url and self.supabase_key)


class SupabaseError(Exception):
    """Base exception for Supabase integration errors"""


class SupabaseConnectionError(SupabaseError):
    """Raised when Supabase connection fails"""


class SupabaseAuthError(SupabaseError):
    """Raised when Supabase authentication fails"""


class SupabaseDataError(SupabaseError):
    """Raised when Supabase data operations fail"""


# Constants
SUPABASE_EMAIL_STATUS_MAPPING = {
    "RECEIVED": "pending",
    "ANALYZED": "processed",
    "ERROR": "failed",
}

SUPABASE_URGENCY_LEVEL_MAPPING = {
    "LOW": "low",
    "MEDIUM": "medium",
    "HIGH": "high",
    "CRITICAL": "urgent",
}

# Rate limiting constants
DEFAULT_RATE_LIMITS = {
    "email_processing": 1000,  # emails per hour
    "realtime_subscriptions": 100,  # subscription updates per hour
    "api_calls": 5000,  # API calls per hour
}

# Real-time subscription types
REALTIME_SUBSCRIPTION_TYPES = [
    "new_emails",
    "urgent_emails",
    "task_updates",
    "analytics_updates",
]
