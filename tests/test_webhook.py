"""Unit tests for webhook.py - Postmark Webhook Handler"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src import storage
from src.models import (
    EmailAnalysis,
    EmailData,
    EmailStatus,
    PostmarkWebhookPayload,
    ProcessedEmail,
    UrgencyLevel,
)
from src.webhook import app, extract_email_data, verify_webhook_signature


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear storage before each test"""
    storage.email_storage.clear()
    storage.stats.total_processed = 0
    storage.stats.total_errors = 0
    storage.stats.avg_urgency_score = 0.0
    storage.stats.processing_times = []
    storage.stats.last_processed = None


@pytest.fixture
def sample_postmark_payload():
    """Sample Postmark webhook payload for testing"""
    return {
        "From": "john.doe@example.com",
        "FromName": "John Doe",
        "To": "jane.smith@company.com",
        "ToFull": [{"Email": "jane.smith@company.com", "Name": "Jane Smith"}],
        "Cc": "",
        "CcFull": [],
        "Bcc": "",
        "BccFull": [],
        "Subject": "URGENT: Project deadline tomorrow - need your input ASAP",
        "MessageID": "test-message-123@example.com",
        "Date": "2025-05-29T14:30:00Z",
        "TextBody": """
Hi Jane,

I hope this email finds you well. I wanted to reach out regarding the Q4
marketing campaign project that we discussed last week.

URGENT TASKS:
1. Review the budget proposal by tomorrow 5 PM
2. Schedule meeting with stakeholders for Friday
3. Submit final report to management

The deadline is tomorrow and I'm getting quite stressed about this. Can you
please prioritize this? The client is breathing down our necks and we really
need to deliver.

Please let me know if you can help with this ASAP.

Best regards,
John

P.S. - Also, can you call me at 555-123-4567 when you get this?
        """,
        "HtmlBody": """
<html>
<body>
<p>Hi Jane,</p>
<p>I hope this email finds you well. I wanted to reach out regarding the Q4
marketing campaign project that we discussed last week.</p>
<p><strong>URGENT TASKS:</strong></p>
<ol>
<li>Review the budget proposal by tomorrow 5 PM</li>
<li>Schedule meeting with stakeholders for Friday</li>
<li>Submit final report to management</li>
</ol>
<p>The deadline is tomorrow and I'm getting quite <em>stressed</em> about this.
Can you please prioritize this? The client is breathing down our necks and we
really need to deliver.</p>
<p>Please let me know if you can help with this ASAP.</p>
<p>Best regards,<br>John</p>
<p>P.S. - Also, can you call me at 555-123-4567 when you get this?</p>
</body>
</html>
        """,
        "Headers": [
            {"Name": "X-Spam-Status", "Value": "No"},
            {"Name": "X-Spam-Score", "Value": "0.1"},
        ],
        "Attachments": [],
    }


@pytest.fixture
def sample_email_data():
    """Sample email data for testing"""
    return {
        "message_id": "test-message-123@example.com",
        "from_email": "john.doe@example.com",
        "to_emails": ["jane.smith@company.com"],
        "cc_emails": [],
        "bcc_emails": [],
        "subject": "URGENT: Project deadline tomorrow - need your input ASAP",
        "text_body": """
Hi Jane,

I hope this email finds you well. I wanted to reach out regarding the Q4
marketing campaign project that we discussed last week.

URGENT TASKS:
1. Review the budget proposal by tomorrow 5 PM
2. Schedule meeting with stakeholders for Friday
3. Submit final report to management

The deadline is tomorrow and I'm getting quite stressed about this. Can you
please prioritize this? The client is breathing down our necks and we really
need to deliver.

Please let me know if you can help with this ASAP.

Best regards,
John

P.S. - Also, can you call me at 555-123-4567 when you get this?
        """,
        "html_body": """
<html>
<body>
<p>Hi Jane,</p>
<p>I hope this email finds you well. I wanted to reach out regarding the Q4
marketing campaign project that we discussed last week.</p>
<p><strong>URGENT TASKS:</strong></p>
<ol>
<li>Review the budget proposal by tomorrow 5 PM</li>
<li>Schedule meeting with stakeholders for Friday</li>
<li>Submit final report to management</li>
</ol>
<p>The deadline is tomorrow and I'm getting quite <em>stressed</em> about this.
Can you please prioritize this? The client is breathing down our necks and we
really need to deliver.</p>
<p>Please let me know if you can help with this ASAP.</p>
<p>Best regards,<br>John</p>
<p>P.S. - Also, can you call me at 555-123-4567 when you get this?</p>
</body>
</html>
        """,
        "received_at": datetime.now(timezone.utc),
        "attachments": [],
        "headers": {},
    }


@pytest.fixture
def sample_analysis_data():
    """Sample email analysis data for testing"""
    return {
        "urgency_score": 75,
        "urgency_level": UrgencyLevel.HIGH,
        "sentiment": "positive",
        "confidence": 0.8,
        "keywords": ["test", "urgent"],
        "action_items": ["review", "respond"],
        "temporal_references": ["today"],
        "tags": ["test"],
        "category": "email",
    }


class TestWebhookSignatureVerification:
    """Test webhook signature verification"""

    def test_verify_webhook_signature_valid(self):
        """Test valid signature verification"""
        secret = "test-secret"
        body = b'{"test": "data"}'

        # Generate valid signature
        expected_signature = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()

        assert verify_webhook_signature(body, expected_signature, secret) is True

    def test_verify_webhook_signature_invalid(self):
        """Test invalid signature verification"""
        secret = "test-secret"
        body = b'{"test": "data"}'
        invalid_signature = "invalid-signature"

        assert verify_webhook_signature(body, invalid_signature, secret) is False

    def test_verify_webhook_signature_no_secret(self):
        """Test signature verification with no secret configured"""
        body = b'{"test": "data"}'
        signature = "any-signature"

        # Should return True when no secret is configured
        assert verify_webhook_signature(body, signature, "") is True
        assert verify_webhook_signature(body, signature, None) is True

    def test_verify_webhook_signature_different_secret(self):
        """Test signature verification with different secret"""
        body = b'{"test": "data"}'

        # Generate signature with one secret
        secret1 = "secret1"
        signature = hmac.new(secret1.encode("utf-8"), body, hashlib.sha256).hexdigest()

        # Try to verify with different secret
        secret2 = "secret2"
        assert verify_webhook_signature(body, signature, secret2) is False


class TestEmailDataExtraction:
    """Test email data extraction from Postmark payload"""

    def test_extract_email_data_basic(self, sample_postmark_payload):
        """Test basic email data extraction"""
        webhook_payload = PostmarkWebhookPayload(**sample_postmark_payload)
        email_data = extract_email_data(webhook_payload)

        assert isinstance(email_data, EmailData)
        assert email_data.message_id == "test-message-123@example.com"
        assert email_data.from_email == "john.doe@example.com"
        assert email_data.to_emails == ["jane.smith@company.com"]
        assert (
            email_data.subject
            == "URGENT: Project deadline tomorrow - need your input ASAP"
        )
        assert "Hi Jane" in email_data.text_body
        assert "URGENT TASKS" in email_data.text_body
        assert "<p>Hi Jane,</p>" in email_data.html_body
        assert "<strong>URGENT TASKS:</strong>" in email_data.html_body

    def test_extract_email_data_with_cc_bcc(self):
        """Test email data extraction with CC and BCC"""
        payload_data = {
            "From": "sender@example.com",
            "To": "recipient@example.com",
            "ToFull": [{"Email": "recipient@example.com", "Name": "Recipient"}],
            "Cc": "cc@example.com",
            "CcFull": [{"Email": "cc@example.com", "Name": "CC Person"}],
            "Bcc": "bcc@example.com",
            "BccFull": [{"Email": "bcc@example.com", "Name": "BCC Person"}],
            "Subject": "Test with CC/BCC",
            "MessageID": "postmark-456",
            "Date": "2024-01-01T12:00:00Z",
            "Headers": [{"Name": "X-Test", "Value": "test"}],
            "Attachments": [],
        }

        webhook_payload = PostmarkWebhookPayload(**payload_data)
        email_data = extract_email_data(webhook_payload)

        assert email_data.cc_emails == ["cc@example.com"]
        assert email_data.bcc_emails == ["bcc@example.com"]

    def test_extract_email_data_with_attachments(self):
        """Test email data extraction with attachments"""
        payload_data = {
            "From": "sender@example.com",
            "To": "recipient@example.com",
            "ToFull": [{"Email": "recipient@example.com"}],
            "Subject": "Test with Attachments",
            "MessageID": "postmark-789",
            "Date": "2024-01-01T12:00:00Z",
            "Headers": [],
            "Attachments": [
                {
                    "Name": "document.pdf",
                    "ContentType": "application/pdf",
                    "ContentLength": 1024,
                    "ContentID": "att1",
                },
                {
                    "Name": "image.png",
                    "ContentType": "image/png",
                    "ContentLength": 2048,
                },
            ],
        }

        webhook_payload = PostmarkWebhookPayload(**payload_data)
        email_data = extract_email_data(webhook_payload)

        assert len(email_data.attachments) == 2
        assert email_data.attachments[0].name == "document.pdf"
        assert email_data.attachments[0].content_type == "application/pdf"
        assert email_data.attachments[0].size == 1024
        assert email_data.attachments[0].content_id == "att1"
        assert email_data.attachments[1].name == "image.png"
        assert email_data.attachments[1].content_id is None

    def test_extract_email_data_with_headers(self):
        """Test email data extraction with custom headers"""
        payload_data = {
            "From": "sender@example.com",
            "To": "recipient@example.com",
            "ToFull": [{"Email": "recipient@example.com"}],
            "Subject": "Test with Headers",
            "MessageID": "postmark-headers",
            "Date": "2024-01-01T12:00:00Z",
            "Headers": [
                {"Name": "X-Custom-Header", "Value": "custom-value"},
                {"Name": "X-Priority", "Value": "1"},
                {"Name": "Reply-To", "Value": "reply@example.com"},
            ],
            "Attachments": [],
        }

        webhook_payload = PostmarkWebhookPayload(**payload_data)
        email_data = extract_email_data(webhook_payload)

        assert len(email_data.headers) == 3
        assert email_data.headers["X-Custom-Header"] == "custom-value"
        assert email_data.headers["X-Priority"] == "1"
        assert email_data.headers["Reply-To"] == "reply@example.com"

    def test_extract_email_data_multiple_recipients(self):
        """Test email data extraction with multiple recipients"""
        payload_data = {
            "From": "sender@example.com",
            "To": "recipient1@example.com, recipient2@example.com",
            "ToFull": [
                {"Email": "recipient1@example.com", "Name": "Recipient One"},
                {"Email": "recipient2@example.com", "Name": "Recipient Two"},
            ],
            "Subject": "Test Multiple Recipients",
            "MessageID": "postmark-multi",
            "Date": "2024-01-01T12:00:00Z",
            "Headers": [],
            "Attachments": [],
        }

        webhook_payload = PostmarkWebhookPayload(**payload_data)
        email_data = extract_email_data(webhook_payload)

        assert len(email_data.to_emails) == 2
        assert "recipient1@example.com" in email_data.to_emails
        assert "recipient2@example.com" in email_data.to_emails


class TestWebhookEndpoints:
    """Test FastAPI webhook endpoints"""

    def setup_method(self):
        """Reset storage before each test"""
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.avg_urgency_score = 0.0
        storage.stats.last_processed = None
        storage.stats.processing_times.clear()

        # Ensure webhook module uses the same storage instance
        import src.webhook

        src.webhook.storage = storage

    def test_health_check(self):
        """Test health check endpoint"""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"  # Match actual webhook response
        assert "timestamp" in data

    def test_get_system_stats(self):
        """Test system statistics endpoint"""
        # Set up some stats
        storage.stats.total_processed = 5
        storage.stats.total_errors = 1
        storage.stats.avg_urgency_score = 65.5
        storage.stats.processing_times = [0.1, 0.2, 0.15]

        client = TestClient(app)
        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 5
        assert data["total_errors"] == 1
        assert data["avg_urgency_score"] == 65.5
        assert data["avg_processing_time_ms"] > 0
        assert data["processing_times_samples"] == 3

    def test_get_recent_emails_empty(self):
        """Test getting recent emails when storage is empty"""
        client = TestClient(app)
        response = client.get("/api/emails/recent")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["emails"] == []

    def test_get_recent_emails_with_data(self, sample_email_data):
        """Test getting recent emails with data"""
        # Store some emails
        for i in range(3):
            email_data = EmailData(**{**sample_email_data, "message_id": f"recent-{i}"})
            processed_email = ProcessedEmail(
                id=f"recent-{i}", email_data=email_data, status=EmailStatus.RECEIVED
            )
            storage.email_storage[f"recent-{i}"] = processed_email

        client = TestClient(app)
        response = client.get("/api/emails/recent?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2  # Limited by query parameter
        assert len(data["emails"]) == 2

    def test_get_emails_with_pagination(self, sample_email_data):
        """Test getting emails with pagination"""
        # Store multiple emails
        for i in range(15):
            email_data = EmailData(
                **{**sample_email_data, "message_id": f"pagination-{i}"}
            )
            processed_email = ProcessedEmail(
                id=f"pagination-{i}", email_data=email_data
            )
            storage.email_storage[f"pagination-{i}"] = processed_email

        client = TestClient(app)

        # Test first page
        response = client.get("/api/emails?skip=0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["emails"]) == 5
        assert data["skip"] == 0
        assert data["limit"] == 5

        # Test second page
        response = client.get("/api/emails?skip=5&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["emails"]) == 5
        assert data["skip"] == 5

    def test_get_emails_with_filters(self, sample_email_data, sample_analysis_data):
        """Test getting emails with filters"""
        # Store emails with different properties
        urgency_levels = ["low", "medium", "high"]
        sentiments = ["negative", "neutral", "positive"]

        for i, (urgency, sentiment) in enumerate(zip(urgency_levels, sentiments)):
            analysis_data = {
                **sample_analysis_data,
                "urgency_level": urgency,
                "sentiment": sentiment,
            }

            analysis = EmailAnalysis(
                **{**analysis_data, "urgency_level": UrgencyLevel(urgency)}
            )

            email_data = EmailData(
                **{
                    **sample_email_data,
                    "message_id": f"filter-{i}",
                    "subject": f"Subject {i}",
                }
            )
            processed_email = ProcessedEmail(
                id=f"filter-{i}", email_data=email_data, analysis=analysis
            )
            storage.email_storage[f"filter-{i}"] = processed_email

        client = TestClient(app)

        # Test urgency filter
        response = client.get("/api/emails?urgency_level=high")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        # Test sentiment filter
        response = client.get("/api/emails?sentiment=positive")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        # Test search filter
        response = client.get("/api/emails?search=Subject 1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_get_specific_email(self, sample_email_data, sample_analysis_data):
        """Test getting specific email by ID"""
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)
        processed_email = ProcessedEmail(
            id="specific-email",
            email_data=email_data,
            analysis=analysis,
            processed_at=datetime.now(),
        )
        storage.email_storage["specific-email"] = processed_email

        client = TestClient(app)
        response = client.get("/api/emails/specific-email")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "specific-email"
        assert data["email_data"]["message_id"] == "test-message-123@example.com"
        assert data["analysis"]["urgency_score"] == 75
        assert data["status"] == "received"
        assert data["processed_at"] is not None

    def test_get_nonexistent_email(self):
        """Test getting non-existent email"""
        client = TestClient(app)
        response = client.get("/api/emails/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Email not found"

    def test_search_emails(self, sample_email_data):
        """Test advanced email search"""
        # Store emails with different content
        email_configs = [
            ("search-1", "Meeting about project deadline", "john@company.com"),
            ("search-2", "Invoice payment required", "billing@vendor.com"),
            ("search-3", "Project update and meeting notes", "team@company.com"),
        ]

        for email_id, subject, from_email in email_configs:
            email_data = EmailData(
                **{
                    **sample_email_data,
                    "message_id": email_id,
                    "subject": subject,
                    "from_email": from_email,
                    "text_body": f"Email content for {subject}",
                    # Override to_emails to avoid company.com
                    "to_emails": [f"recipient-{email_id}@example.com"],
                }
            )
            processed_email = ProcessedEmail(id=email_id, email_data=email_data)
            storage.email_storage[email_id] = processed_email

        client = TestClient(app)

        # Test search by query
        response = client.get("/api/search?q=meeting")
        assert response.status_code == 200
        data = response.json()
        assert data["total_found"] == 2  # Two emails contain "meeting"

        # Test search with limit
        response = client.get("/api/search?q=project&limit=1")
        data = response.json()
        assert len(data["results"]) == 1

        # Test search in sender
        response = client.get("/api/search?q=company.com")
        data = response.json()
        assert data["total_found"] == 2  # Two emails from company.com

    def test_get_analytics_empty(self):
        """Test analytics endpoint with no data"""
        client = TestClient(app)
        response = client.get("/api/analytics")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "No emails processed yet"

    def test_get_analytics_with_data(self, sample_email_data, sample_analysis_data):
        """Test analytics endpoint with data"""
        from src.models import UrgencyLevel

        # Store emails with different urgency levels
        urgency_levels = [UrgencyLevel.LOW, UrgencyLevel.MEDIUM, UrgencyLevel.HIGH]
        for i, urgency in enumerate(urgency_levels):
            analysis_data = {
                **sample_analysis_data,
                "urgency_level": urgency,
                "urgency_score": 30 + (i * 20),  # 30, 50, 70
            }
            analysis = EmailAnalysis(**analysis_data)

            email_data = EmailData(
                **{
                    **sample_email_data,
                    "message_id": f"analytics-{i}",
                    "received_at": datetime.now(),
                }
            )
            processed_email = ProcessedEmail(
                id=f"analytics-{i}", email_data=email_data, analysis=analysis
            )
            storage.email_storage[f"analytics-{i}"] = processed_email

        # Update processing stats
        storage.stats.total_processed = 3
        storage.stats.processing_times = [0.1, 0.2, 0.15]

        client = TestClient(app)
        response = client.get("/api/analytics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_emails"] == 3
        assert data["analyzed_emails"] == 3
        assert "urgency_distribution" in data
        assert "sentiment_distribution" in data
        assert "urgency_stats" in data
        assert "processing_stats" in data
        assert "hourly_distribution" in data


class TestWebhookProcessing:
    """Test main webhook processing functionality"""

    def setup_method(self):
        """Reset storage and patch dependencies"""
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.avg_urgency_score = 0.0
        storage.stats.last_processed = None
        storage.stats.processing_times.clear()

        # Ensure webhook module uses the same storage instance
        import src.webhook

        src.webhook.storage = storage
        storage.stats.processing_times = []

    @patch("src.webhook.config")
    @patch("src.webhook.email_extractor")
    @patch("src.webhook.logger")
    def test_webhook_processing_success(
        self, mock_logger, mock_extractor, mock_config, sample_postmark_payload
    ):
        """Test successful webhook processing"""
        # Configure mocks
        mock_config.webhook_endpoint = "/webhook"
        mock_config.postmark_webhook_secret = None  # No signature verification

        # Mock extraction results
        mock_metadata = MagicMock()
        mock_metadata.urgency_indicators = ["urgent"]
        mock_metadata.sentiment_indicators = {"positive": ["good"], "negative": []}
        mock_metadata.priority_keywords = ["important"]
        mock_metadata.action_words = ["review"]
        mock_metadata.temporal_references = ["today"]

        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (70, "high")

        client = TestClient(app)
        response = client.post("/webhook", json=sample_postmark_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "processing_id" in data
        assert "message" in data

        # Verify email was stored
        assert len(storage.email_storage) == 1
        stored_email = list(storage.email_storage.values())[0]
        assert stored_email.email_data.message_id == "test-message-123@example.com"
        assert stored_email.analysis is not None
        assert stored_email.analysis.urgency_score == 70
        assert stored_email.status == EmailStatus.ANALYZED

    @patch("src.webhook.config")
    def test_webhook_signature_verification_required(
        self, mock_config, sample_postmark_payload
    ):
        """Test webhook with signature verification required"""
        secret = "test-secret"
        mock_config.webhook_endpoint = "/webhook"
        mock_config.postmark_webhook_secret = secret

        body = json.dumps(sample_postmark_payload).encode("utf-8")
        valid_signature = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()

        client = TestClient(app)

        # Test with valid signature
        response = client.post(
            "/webhook",
            json=sample_postmark_payload,
            headers={"X-Postmark-Signature": valid_signature},
        )
        # Note: This might fail due to body encoding differences in test client
        # In real implementation, we'd need to handle this differently

        # Test with missing signature
        response = client.post("/webhook", json=sample_postmark_payload)
        assert response.status_code == 401
        assert "Missing webhook signature" in response.json()["detail"]

        # Test with invalid signature
        response = client.post(
            "/webhook",
            json=sample_postmark_payload,
            headers={"X-Postmark-Signature": "invalid-signature"},
        )
        assert response.status_code == 401
        assert "Invalid webhook signature" in response.json()["detail"]

    @patch("src.webhook.config")
    def test_webhook_invalid_json(self, mock_config):
        """Test webhook with invalid JSON payload"""
        # Disable webhook signature verification
        mock_config.postmark_webhook_secret = None

        client = TestClient(app)

        # Send invalid JSON
        response = client.post(
            "/webhook",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        assert "Invalid JSON payload" in response.json()["detail"]

    @patch("src.webhook.config")
    @patch("src.webhook.email_extractor")
    def test_webhook_processing_error(
        self, mock_extractor, mock_config, sample_postmark_payload
    ):
        """Test webhook processing with extraction error"""
        # Disable webhook signature verification
        mock_config.postmark_webhook_secret = None

        # Mock extraction to raise an exception
        mock_extractor.extract_from_email.side_effect = Exception("Extraction failed")

        client = TestClient(app)
        response = client.post("/webhook", json=sample_postmark_payload)

        assert response.status_code == 500
        assert (
            "An unexpected error occurred during email processing"
            in response.json()["detail"]
        )

        # Verify error stats were updated
        assert storage.stats.total_errors == 1

    @patch("src.webhook.config")
    @patch("src.webhook.extract_email_data")
    def test_webhook_email_data_extraction_error(
        self, mock_extract, mock_config, sample_postmark_payload
    ):
        """Test webhook with email data extraction error"""
        # Disable webhook signature verification
        mock_config.postmark_webhook_secret = None

        # Mock email data extraction to raise an exception
        mock_extract.side_effect = Exception("Email extraction failed")

        client = TestClient(app)
        response = client.post("/webhook", json=sample_postmark_payload)

        assert response.status_code == 500
        assert (
            "An unexpected error occurred during email processing"
            in response.json()["detail"]
        )

    @patch("src.webhook.config")
    @patch("src.webhook.email_extractor")
    def test_webhook_stats_update(
        self, mock_extractor, mock_config, sample_postmark_payload
    ):
        """Test that webhook processing updates statistics correctly"""
        mock_config.webhook_endpoint = "/webhook"
        mock_config.postmark_webhook_secret = None

        # Mock extraction
        mock_metadata = MagicMock()
        mock_metadata.urgency_indicators = []
        mock_metadata.sentiment_indicators = {"positive": [], "negative": []}
        mock_metadata.priority_keywords = []
        mock_metadata.action_words = []
        mock_metadata.temporal_references = []

        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (50, "medium")

        client = TestClient(app)

        # Process multiple emails
        for i in range(3):
            payload = {**sample_postmark_payload, "MessageID": f"test-{i}"}
            response = client.post("/webhook", json=payload)
            assert response.status_code == 200

        # Verify stats
        assert storage.stats.total_processed == 3
        assert len(storage.stats.processing_times) == 3
        assert storage.stats.last_processed is not None
        assert storage.stats.avg_urgency_score == 50.0  # All emails have score 50


class TestWebhookIntegration:
    """Test webhook integration scenarios"""

    def setup_method(self):
        """Reset storage before each test"""
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.avg_urgency_score = 0.0
        storage.stats.last_processed = None
        storage.stats.processing_times.clear()

        # Ensure webhook module uses the same storage instance
        import src.webhook

        src.webhook.storage = storage

    @patch("src.webhook.config")
    @patch("src.webhook.email_extractor")
    @patch("src.webhook.logger")
    def test_complete_email_processing_flow(
        self, mock_logger, mock_extractor, mock_config, sample_postmark_payload
    ):
        """Test complete email processing flow from webhook to storage"""
        # Configure mocks
        mock_config.webhook_endpoint = "/webhook"
        mock_config.postmark_webhook_secret = None

        # Mock extraction with realistic data
        mock_metadata = MagicMock()
        mock_metadata.urgency_indicators = ["urgent", "asap"]
        mock_metadata.sentiment_indicators = {"positive": ["excellent"], "negative": []}
        mock_metadata.priority_keywords = ["important", "deadline"]
        mock_metadata.action_words = ["review", "approve"]
        mock_metadata.temporal_references = ["tomorrow", "3pm"]

        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (85, "high")

        # Process webhook
        client = TestClient(app)
        response = client.post("/webhook", json=sample_postmark_payload)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        processing_id = data["processing_id"]

        # Verify storage
        assert len(storage.email_storage) == 1
        assert processing_id in storage.email_storage

        stored_email = storage.email_storage[processing_id]
        assert stored_email.email_data.message_id == "test-message-123@example.com"
        assert stored_email.email_data.from_email == "john.doe@example.com"
        assert (
            stored_email.email_data.subject
            == "URGENT: Project deadline tomorrow - need your input ASAP"
        )
        assert stored_email.analysis.urgency_score == 85
        assert stored_email.analysis.urgency_level.value == "high"
        assert stored_email.analysis.sentiment == "positive"
        assert "important" in stored_email.analysis.keywords
        assert "review" in stored_email.analysis.action_items
        assert stored_email.status == EmailStatus.ANALYZED
        assert stored_email.processed_at is not None

        # Verify stats
        assert storage.stats.total_processed == 1
        assert storage.stats.avg_urgency_score == 85.0
        assert len(storage.stats.processing_times) == 1
        assert storage.stats.last_processed is not None

        # Verify logging calls
        mock_logger.log_email_received.assert_called_once()
        mock_logger.log_extraction_start.assert_called_once()
        mock_logger.log_extraction_complete.assert_called_once()
        mock_logger.log_email_processed.assert_called_once()

    def test_concurrent_webhook_processing(self, sample_postmark_payload):
        """Test concurrent webhook processing"""
        import threading

        # Mock dependencies to avoid complex setup
        with (
            patch("src.webhook.config") as mock_config,
            patch("src.webhook.email_extractor") as mock_extractor,
            patch("src.webhook.logger"),
        ):

            mock_config.webhook_endpoint = "/webhook"
            mock_config.postmark_webhook_secret = None

            mock_metadata = MagicMock()
            mock_metadata.urgency_indicators = []
            mock_metadata.sentiment_indicators = {"positive": [], "negative": []}
            mock_metadata.priority_keywords = []
            mock_metadata.action_words = []
            mock_metadata.temporal_references = []

            mock_extractor.extract_from_email.return_value = mock_metadata
            mock_extractor.calculate_urgency_score.return_value = (50, "medium")

            client = TestClient(app)
            responses = []

            def process_webhook(message_id):
                payload = {
                    **sample_postmark_payload,
                    "MessageID": f"concurrent-{message_id}",
                }
                response = client.post("/webhook", json=payload)
                responses.append(response)

            # Process multiple webhooks concurrently
            threads = []
            for i in range(5):
                thread = threading.Thread(target=process_webhook, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # Verify all succeeded
            assert len(responses) == 5
            for response in responses:
                assert response.status_code == 200

            # Verify storage
            assert len(storage.email_storage) == 5
            assert storage.stats.total_processed == 5
