# Test file for API routes
"""
Tests for the API routes module
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src import storage
from src.models import (
    EmailAnalysis,
    EmailData,
    EmailStatus,
    ProcessedEmail,
    UrgencyLevel,
)

# Import the app with API routes
from src.webhook import app


@pytest.fixture
def client():
    """Create test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def sample_processed_email():
    """Create a sample processed email for testing"""
    email_data = EmailData(
        message_id="test-123",
        from_email="test@example.com",
        to_emails=["recipient@example.com"],
        cc_emails=[],
        bcc_emails=[],
        subject="Test Email",
        text_body="This is a test email",
        html_body="<p>This is a test email</p>",
        received_at=datetime.now(timezone.utc),
        attachments=[],
        headers={},
    )

    analysis = EmailAnalysis(
        urgency_score=75,
        urgency_level=UrgencyLevel.HIGH,
        sentiment="positive",
        confidence=0.8,
        keywords=["test", "urgent"],
        action_items=["review", "respond"],
        temporal_references=["today"],
        tags=["test"],
        category="email",
    )

    return ProcessedEmail(
        id="test-email-1",
        email_data=email_data,
        analysis=analysis,
        status=EmailStatus.ANALYZED,
        processed_at=datetime.now(timezone.utc),
        webhook_payload={},
    )


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear storage before each test"""
    storage.email_storage.clear()
    storage.stats.total_processed = 0
    storage.stats.total_errors = 0
    storage.stats.avg_urgency_score = 0.0
    storage.stats.processing_times = []
    storage.stats.last_processed = None


class TestAPIRoutes:
    """Test class for API routes"""

    def test_stats_endpoint_empty(self, client):
        """Test /api/stats endpoint with no data"""
        response = client.get("/api/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["total_processed"] == 0
        assert data["total_errors"] == 0
        assert data["avg_urgency_score"] == 0.0
        assert data["avg_processing_time_ms"] == 0
        assert data["processing_times_samples"] == 0
        assert data["last_processed"] is None

    def test_stats_endpoint_with_data(self, client, sample_processed_email):
        """Test /api/stats endpoint with sample data"""
        # Add sample data to storage
        storage.email_storage["test-email-1"] = sample_processed_email
        storage.stats.total_processed = 1
        storage.stats.processing_times = [0.5, 0.7, 0.3]
        storage.stats.last_processed = datetime.now(timezone.utc)

        response = client.get("/api/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["total_processed"] == 1
        assert data["avg_processing_time_ms"] > 0
        assert data["processing_times_samples"] == 3
        assert data["last_processed"] is not None

    def test_recent_emails_endpoint_empty(self, client):
        """Test /api/emails/recent endpoint with no emails"""
        response = client.get("/api/emails/recent")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 0
        assert data["emails"] == []

    def test_recent_emails_endpoint_with_data(self, client, sample_processed_email):
        """Test /api/emails/recent endpoint with sample data"""
        storage.email_storage["test-email-1"] = sample_processed_email

        response = client.get("/api/emails/recent")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 1
        assert len(data["emails"]) == 1
        assert data["emails"][0]["id"] == "test-email-1"
        assert data["emails"][0]["subject"] == "Test Email"
        assert data["emails"][0]["urgency_level"] == "high"

    def test_recent_emails_with_limit(self, client, sample_processed_email):
        """Test /api/emails/recent endpoint with limit parameter"""
        # Add multiple emails
        for i in range(5):
            email = sample_processed_email.model_copy()
            email.id = f"test-email-{i}"
            storage.email_storage[f"test-email-{i}"] = email

        response = client.get("/api/emails/recent?limit=3")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 3
        assert len(data["emails"]) == 3

    def test_emails_endpoint_with_pagination(self, client, sample_processed_email):
        """Test /api/emails endpoint with pagination"""
        # Add multiple emails
        for i in range(15):
            email = sample_processed_email.model_copy()
            email.id = f"test-email-{i}"
            storage.email_storage[f"test-email-{i}"] = email

        response = client.get("/api/emails?skip=5&limit=5")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 15
        assert data["skip"] == 5
        assert data["limit"] == 5
        assert len(data["emails"]) == 5

    def test_emails_endpoint_with_urgency_filter(self, client, sample_processed_email):
        """Test /api/emails endpoint with urgency level filter"""
        storage.email_storage["test-email-1"] = sample_processed_email

        response = client.get("/api/emails?urgency_level=high")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["emails"][0]["urgency_level"] == "high"

    def test_emails_endpoint_with_sentiment_filter(
        self, client, sample_processed_email
    ):
        """Test /api/emails endpoint with sentiment filter"""
        storage.email_storage["test-email-1"] = sample_processed_email

        response = client.get("/api/emails?sentiment=positive")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["emails"][0]["sentiment"] == "positive"

    def test_emails_endpoint_with_search(self, client, sample_processed_email):
        """Test /api/emails endpoint with search query"""
        storage.email_storage["test-email-1"] = sample_processed_email

        response = client.get("/api/emails?search=test")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert "test" in data["emails"][0]["subject"].lower()

    def test_specific_email_endpoint(self, client, sample_processed_email):
        """Test /api/emails/{email_id} endpoint"""
        storage.email_storage["test-email-1"] = sample_processed_email

        response = client.get("/api/emails/test-email-1")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "test-email-1"
        assert data["email_data"]["subject"] == "Test Email"
        assert data["analysis"]["urgency_level"] == "high"
        assert data["analysis"]["sentiment"] == "positive"

    def test_specific_email_not_found(self, client):
        """Test /api/emails/{email_id} endpoint with non-existent email"""
        response = client.get("/api/emails/non-existent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_search_endpoint(self, client, sample_processed_email):
        """Test /api/search endpoint"""
        storage.email_storage["test-email-1"] = sample_processed_email

        response = client.get("/api/search?q=test")
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "test"
        assert data["total_found"] == 1
        assert data["returned"] == 1
        assert len(data["results"]) == 1

    def test_search_endpoint_no_query(self, client):
        """Test /api/search endpoint without query parameter"""
        response = client.get("/api/search")
        assert response.status_code == 422  # Validation error

    def test_analytics_endpoint_empty(self, client):
        """Test /api/analytics endpoint with no data"""
        response = client.get("/api/analytics")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "No emails processed yet"
        assert data["total_emails"] == 0
        assert data["analyzed_emails"] == 0

    def test_analytics_endpoint_with_data(self, client, sample_processed_email):
        """Test /api/analytics endpoint with sample data"""
        storage.email_storage["test-email-1"] = sample_processed_email
        storage.stats.total_processed = 1
        storage.stats.processing_times = [0.5]

        response = client.get("/api/analytics")
        assert response.status_code == 200

        data = response.json()
        assert data["total_emails"] == 1
        assert data["analyzed_emails"] == 1
        assert "urgency_distribution" in data
        assert "sentiment_distribution" in data
        assert "urgency_stats" in data
        assert "processing_stats" in data
        assert data["urgency_distribution"]["high"] == 1
        assert data["sentiment_distribution"]["positive"] == 1


if __name__ == "__main__":
    pytest.main([__file__])
