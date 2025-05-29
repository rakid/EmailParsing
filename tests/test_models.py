"""Unit tests for models.py - Email Data Models"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models import (
    AttachmentData,
    EmailAnalysis,
    EmailData,
    EmailStats,
    EmailStatus,
    PostmarkWebhookPayload,
    ProcessedEmail,
    UrgencyLevel,
)


class TestEnums:
    """Test enum classes"""

    def test_urgency_level_values(self):
        """Test UrgencyLevel enum values"""
        assert UrgencyLevel.LOW == "low"
        assert UrgencyLevel.MEDIUM == "medium"
        assert UrgencyLevel.HIGH == "high"
        assert UrgencyLevel.CRITICAL == "critical"

    def test_email_status_values(self):
        """Test EmailStatus enum values"""
        assert EmailStatus.RECEIVED == "received"
        assert EmailStatus.PROCESSING == "processing"
        assert EmailStatus.ANALYZED == "analyzed"
        assert EmailStatus.ERROR == "error"


class TestAttachmentData:
    """Test AttachmentData model"""

    def test_attachment_creation(self):
        """Test creating attachment with required fields"""
        attachment = AttachmentData(
            name="test.pdf", content_type="application/pdf", size=1024
        )
        assert attachment.name == "test.pdf"
        assert attachment.content_type == "application/pdf"
        assert attachment.size == 1024
        assert attachment.content_id is None

    def test_attachment_with_content_id(self):
        """Test attachment with optional content_id"""
        attachment = AttachmentData(
            name="image.png", content_type="image/png", size=2048, content_id="img123"
        )
        assert attachment.content_id == "img123"

    def test_attachment_validation_missing_fields(self):
        """Test validation with missing required fields"""
        with pytest.raises(ValidationError):
            AttachmentData(
                name="test.pdf", content_type="application/pdf"
            )  # Missing size


class TestEmailData:
    """Test EmailData model"""

    def test_email_data_creation(self, sample_email_data):
        """Test creating EmailData with valid data"""
        email = EmailData(**sample_email_data)
        assert email.message_id == "test-message-123@example.com"
        assert email.from_email == "john.doe@example.com"
        assert email.to_emails == ["jane.smith@company.com"]
        assert (
            email.subject == "URGENT: Project deadline tomorrow - need your input ASAP"
        )
        assert isinstance(email.received_at, datetime)

    def test_email_data_with_optional_fields(self):
        """Test EmailData with all optional fields"""
        email_data = {
            "message_id": "test-456",
            "from_email": "sender@example.com",
            "to_emails": ["recipient@example.com"],
            "cc_emails": ["cc@example.com"],
            "bcc_emails": ["bcc@example.com"],
            "subject": "Test with CC/BCC",
            "text_body": "This is a test email",
            "html_body": "<p>This is a test email</p>",
            "received_at": datetime.now(),
            "attachments": [
                AttachmentData(
                    name="test.pdf", content_type="application/pdf", size=1024
                )
            ],
            "headers": {"X-Custom": "test-value"},
        }
        email = EmailData(**email_data)
        assert email.cc_emails == ["cc@example.com"]
        assert email.bcc_emails == ["bcc@example.com"]
        assert len(email.attachments) == 1
        assert email.headers["X-Custom"] == "test-value"

    def test_email_data_defaults(self):
        """Test default values for optional fields"""
        email = EmailData(
            message_id="test-789",
            from_email="sender@example.com",
            to_emails=["recipient@example.com"],
            subject="Test Defaults",
            received_at=datetime.now(),
        )
        assert email.cc_emails == []
        assert email.bcc_emails == []
        assert email.text_body is None
        assert email.html_body is None
        assert email.attachments == []
        assert email.headers == {}

    def test_email_data_validation_errors(self):
        """Test validation errors for invalid data"""
        # Missing required fields
        with pytest.raises(ValidationError):
            EmailData(from_email="sender@example.com")

        # Missing to_emails field
        with pytest.raises(ValidationError):
            EmailData(
                message_id="test",
                from_email="sender@example.com",
                subject="Test",
                received_at=datetime.now(),
            )


class TestEmailAnalysis:
    """Test EmailAnalysis model"""

    def test_analysis_creation(self, sample_analysis_data):
        """Test creating EmailAnalysis with valid data"""
        analysis = EmailAnalysis(**sample_analysis_data)
        assert analysis.urgency_score == 75
        assert analysis.urgency_level == UrgencyLevel.HIGH
        assert analysis.sentiment == "negative"
        assert analysis.confidence == 0.85

    def test_analysis_score_validation(self):
        """Test urgency score validation (0-100)"""
        # Valid scores
        analysis = EmailAnalysis(
            urgency_score=0,
            urgency_level=UrgencyLevel.LOW,
            sentiment="neutral",
            confidence=0.5,
        )
        assert analysis.urgency_score == 0

        analysis = EmailAnalysis(
            urgency_score=100,
            urgency_level=UrgencyLevel.CRITICAL,
            sentiment="negative",
            confidence=0.9,
        )
        assert analysis.urgency_score == 100

        # Invalid scores
        with pytest.raises(ValidationError):
            EmailAnalysis(
                urgency_score=-1,
                urgency_level=UrgencyLevel.LOW,
                sentiment="neutral",
                confidence=0.5,
            )

        with pytest.raises(ValidationError):
            EmailAnalysis(
                urgency_score=101,
                urgency_level=UrgencyLevel.HIGH,
                sentiment="positive",
                confidence=0.8,
            )

    def test_confidence_validation(self):
        """Test confidence validation (0.0-1.0)"""
        # Valid confidence values
        analysis = EmailAnalysis(
            urgency_score=50,
            urgency_level=UrgencyLevel.MEDIUM,
            sentiment="neutral",
            confidence=0.0,
        )
        assert analysis.confidence == 0.0

        analysis = EmailAnalysis(
            urgency_score=50,
            urgency_level=UrgencyLevel.MEDIUM,
            sentiment="neutral",
            confidence=1.0,
        )
        assert analysis.confidence == 1.0

        # Invalid confidence values
        with pytest.raises(ValidationError):
            EmailAnalysis(
                urgency_score=50,
                urgency_level=UrgencyLevel.MEDIUM,
                sentiment="neutral",
                confidence=-0.1,
            )

        with pytest.raises(ValidationError):
            EmailAnalysis(
                urgency_score=50,
                urgency_level=UrgencyLevel.MEDIUM,
                sentiment="neutral",
                confidence=1.1,
            )

    def test_analysis_defaults(self):
        """Test default values for optional fields"""
        analysis = EmailAnalysis(
            urgency_score=60,
            urgency_level=UrgencyLevel.MEDIUM,
            sentiment="positive",
            confidence=0.7,
        )
        assert analysis.keywords == []
        assert analysis.action_items == []
        assert analysis.temporal_references == []
        assert analysis.tags == []
        assert analysis.category is None


class TestProcessedEmail:
    """Test ProcessedEmail model"""

    def test_processed_email_creation(self, sample_email_data, sample_analysis_data):
        """Test creating ProcessedEmail with valid data"""
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)

        processed = ProcessedEmail(
            id="proc-123", email_data=email_data, analysis=analysis
        )

        assert processed.id == "proc-123"
        assert processed.email_data.message_id == "test-message-123@example.com"
        assert processed.analysis.urgency_score == 75
        assert processed.status == EmailStatus.RECEIVED  # Default
        assert processed.processed_at is None
        assert processed.error_message is None

    def test_processed_email_with_status(self, sample_email_data):
        """Test ProcessedEmail with different statuses"""
        email_data = EmailData(**sample_email_data)

        processed = ProcessedEmail(
            id="proc-456",
            email_data=email_data,
            status=EmailStatus.ANALYZED,
            processed_at=datetime.now(),
        )

        assert processed.status == EmailStatus.ANALYZED
        assert processed.processed_at is not None

    def test_processed_email_with_error(self, sample_email_data):
        """Test ProcessedEmail with error status"""
        email_data = EmailData(**sample_email_data)

        processed = ProcessedEmail(
            id="proc-error",
            email_data=email_data,
            status=EmailStatus.ERROR,
            error_message="Processing failed",
        )

        assert processed.status == EmailStatus.ERROR
        assert processed.error_message == "Processing failed"

    def test_processed_email_webhook_payload(self, sample_email_data):
        """Test ProcessedEmail with webhook payload"""
        email_data = EmailData(**sample_email_data)
        webhook_payload = {"From": "sender@example.com", "Subject": "Test"}

        processed = ProcessedEmail(
            id="proc-webhook", email_data=email_data, webhook_payload=webhook_payload
        )

        assert processed.webhook_payload == webhook_payload


class TestEmailStats:
    """Test EmailStats model"""

    def test_stats_creation(self):
        """Test creating EmailStats with defaults"""
        stats = EmailStats()
        assert stats.total_processed == 0
        assert stats.total_errors == 0
        assert stats.avg_urgency_score == 0.0
        assert stats.urgency_distribution == {}
        assert stats.last_processed is None
        assert stats.processing_times == []

    def test_stats_with_data(self):
        """Test EmailStats with actual data"""
        urgency_dist = {
            UrgencyLevel.LOW: 5,
            UrgencyLevel.MEDIUM: 3,
            UrgencyLevel.HIGH: 2,
        }

        stats = EmailStats(
            total_processed=10,
            total_errors=1,
            avg_urgency_score=45.5,
            urgency_distribution=urgency_dist,
            last_processed=datetime.now(),
            processing_times=[0.1, 0.2, 0.15],
        )

        assert stats.total_processed == 10
        assert stats.total_errors == 1
        assert stats.avg_urgency_score == 45.5
        assert stats.urgency_distribution[UrgencyLevel.LOW] == 5
        assert len(stats.processing_times) == 3


class TestPostmarkWebhookPayload:
    """Test PostmarkWebhookPayload model"""

    def test_postmark_payload_creation(self, sample_postmark_payload):
        """Test creating PostmarkWebhookPayload with valid data"""
        payload = PostmarkWebhookPayload(**sample_postmark_payload)

        assert payload.From == "john.doe@example.com"
        assert payload.To == "jane.smith@company.com"
        assert (
            payload.Subject
            == "URGENT: Project deadline tomorrow - need your input ASAP"
        )
        assert payload.MessageID == "test-message-123@example.com"
        assert len(payload.ToFull) == 1
        assert payload.ToFull[0]["Email"] == "jane.smith@company.com"

    def test_postmark_payload_with_optional_fields(self):
        """Test PostmarkWebhookPayload with optional fields"""
        payload_data = {
            "From": "sender@example.com",
            "FromName": "John Doe",
            "To": "recipient@example.com",
            "ToFull": [{"Email": "recipient@example.com", "Name": "Jane Doe"}],
            "Cc": "cc@example.com",
            "CcFull": [{"Email": "cc@example.com", "Name": "CC Person"}],
            "Subject": "Test with CC",
            "MessageID": "postmark-456",
            "Date": "2024-01-01T12:00:00Z",
            "TextBody": "This is a test",
            "HtmlBody": "<p>This is a test</p>",
            "Headers": [{"Name": "X-Test", "Value": "test-value"}],
            "Attachments": [
                {
                    "Name": "test.pdf",
                    "ContentType": "application/pdf",
                    "ContentLength": 1024,
                }
            ],
            "Tag": "test-tag",
            "MessageStream": "inbound",
        }

        payload = PostmarkWebhookPayload(**payload_data)

        assert payload.FromName == "John Doe"
        assert payload.Cc == "cc@example.com"
        assert len(payload.CcFull) == 1
        assert payload.Tag == "test-tag"
        assert payload.MessageStream == "inbound"
        assert len(payload.Attachments) == 1

    def test_postmark_payload_required_fields(self):
        """Test validation of required fields"""
        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            PostmarkWebhookPayload()

        minimal_payload = {
            "From": "sender@example.com",
            "To": "recipient@example.com",
            "ToFull": [{"Email": "recipient@example.com"}],
            "Subject": "Test",
            "MessageID": "test-123",
            "Date": "2024-01-01T12:00:00Z",
            "Headers": [],
        }

        # This should work with minimal required fields
        payload = PostmarkWebhookPayload(**minimal_payload)
        assert payload.From == "sender@example.com"
        assert payload.ToFull[0]["Email"] == "recipient@example.com"


class TestModelIntegration:
    """Test integration between models"""

    def test_complete_email_processing_flow(
        self, sample_email_data, sample_analysis_data
    ):
        """Test complete flow from EmailData to ProcessedEmail"""
        # Create email data
        email_data = EmailData(**sample_email_data)

        # Create analysis
        analysis = EmailAnalysis(**sample_analysis_data)

        # Create processed email
        processed = ProcessedEmail(
            id="integration-test",
            email_data=email_data,
            analysis=analysis,
            status=EmailStatus.ANALYZED,
            processed_at=datetime.now(),
        )

        # Verify the complete flow
        assert processed.email_data.message_id == email_data.message_id
        assert processed.analysis.urgency_score == analysis.urgency_score
        assert processed.status == EmailStatus.ANALYZED

        # Test serialization
        data_dict = processed.model_dump()
        assert "email_data" in data_dict
        assert "analysis" in data_dict
        assert data_dict["status"] == "analyzed"

    def test_model_serialization_deserialization(
        self, sample_email_data, sample_analysis_data
    ):
        """Test that models can be serialized and deserialized"""
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)

        processed = ProcessedEmail(
            id="serialize-test", email_data=email_data, analysis=analysis
        )

        # Serialize to dict
        data_dict = processed.model_dump()

        # Deserialize back
        restored = ProcessedEmail(**data_dict)

        assert restored.id == processed.id
        assert restored.email_data.message_id == processed.email_data.message_id
        assert restored.analysis.urgency_score == processed.analysis.urgency_score

    def test_postmark_to_email_data_conversion(self, sample_postmark_payload):
        """Test conversion from Postmark payload to EmailData"""
        postmark_payload = PostmarkWebhookPayload(**sample_postmark_payload)

        # This would typically be done in webhook.py
        email_data = EmailData(
            message_id=postmark_payload.MessageID,
            from_email=postmark_payload.From,
            to_emails=[recipient["Email"] for recipient in postmark_payload.ToFull],
            subject=postmark_payload.Subject,
            text_body=postmark_payload.TextBody,
            html_body=postmark_payload.HtmlBody,
            received_at=datetime.fromisoformat(
                postmark_payload.Date.replace("Z", "+00:00")
            ),
            headers={
                header["Name"]: header["Value"] for header in postmark_payload.Headers
            },
        )

        assert email_data.message_id == postmark_payload.MessageID
        assert email_data.from_email == postmark_payload.From
        assert email_data.to_emails[0] == postmark_payload.ToFull[0]["Email"]
        assert email_data.subject == postmark_payload.Subject
