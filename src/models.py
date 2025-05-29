# Email Data Models for MCP Server
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class UrgencyLevel(str, Enum):
    """Email urgency levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmailStatus(str, Enum):
    """Email processing status"""

    RECEIVED = "received"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    ERROR = "error"


class AttachmentData(BaseModel):
    """Email attachment metadata"""

    name: str
    content_type: str
    size: int
    content_id: Optional[str] = None


class EmailData(BaseModel):
    """Core email data structure"""

    message_id: str = Field(..., description="Unique message identifier")
    from_email: str = Field(..., description="Sender email address")
    to_emails: List[str] = Field(..., description="Recipient email addresses")
    cc_emails: Optional[List[str]] = Field(default=[], description="CC recipients")
    bcc_emails: Optional[List[str]] = Field(default=[], description="BCC recipients")
    subject: str = Field(..., description="Email subject")
    text_body: Optional[str] = Field(None, description="Plain text email body")
    html_body: Optional[str] = Field(None, description="HTML email body")
    received_at: datetime = Field(..., description="When email was received")
    attachments: List[AttachmentData] = Field(
        default=[], description="Email attachments"
    )
    headers: Dict[str, str] = Field(default={}, description="Email headers")


class EmailAnalysis(BaseModel):
    """Email analysis results"""

    urgency_score: int = Field(..., ge=0, le=100, description="Urgency score 0-100")
    urgency_level: UrgencyLevel = Field(..., description="Categorized urgency level")
    sentiment: str = Field(..., description="Sentiment analysis result")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")
    keywords: List[str] = Field(default=[], description="Extracted keywords")
    action_items: List[str] = Field(default=[], description="Identified action items")
    temporal_references: List[str] = Field(
        default=[], description="Date/time references found"
    )
    tags: List[str] = Field(default=[], description="Auto-generated tags")
    category: Optional[str] = Field(None, description="Email category")


class ProcessedEmail(BaseModel):
    """Complete processed email with analysis"""

    id: str = Field(..., description="Unique processing ID")
    email_data: EmailData
    analysis: Optional[EmailAnalysis] = None
    status: EmailStatus = Field(default=EmailStatus.RECEIVED)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    webhook_payload: Dict[str, Any] = Field(
        default={}, description="Original webhook data"
    )


class EmailStats(BaseModel):
    """Email processing statistics"""

    total_processed: int = 0
    total_errors: int = 0
    avg_urgency_score: float = 0.0
    urgency_distribution: Dict[UrgencyLevel, int] = Field(default_factory=dict)
    last_processed: Optional[datetime] = None
    processing_times: List[float] = Field(
        default=[], description="Processing time samples"
    )


class PostmarkWebhookPayload(BaseModel):
    """Postmark inbound webhook payload structure"""

    From: str
    FromName: Optional[str] = None
    To: str
    ToFull: List[Dict[str, str]]
    Cc: Optional[str] = None
    CcFull: Optional[List[Dict[str, str]]] = None
    Bcc: Optional[str] = None
    BccFull: Optional[List[Dict[str, str]]] = None
    Subject: str
    MessageID: str
    Date: str
    TextBody: Optional[str] = None
    HtmlBody: Optional[str] = None
    Headers: List[Dict[str, str]]
    Attachments: List[Dict[str, Any]] = Field(default=[])
    Tag: Optional[str] = None
    MessageStream: Optional[str] = None
