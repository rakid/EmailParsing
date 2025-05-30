# Test file for API routes
"""
Tests for the API routes module
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from fastapi.testclient import TestClient

from src import storage

# Importer le logger utilisé dans api_routes.py pour pouvoir le mocker
from src.logging_system import logger as api_routes_logger
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
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 0
        assert data["last_processed"] is None

    def test_stats_endpoint_with_data(self, client, sample_processed_email):
        storage.email_storage["test-email-1"] = sample_processed_email
        storage.stats.total_processed = 1
        storage.stats.processing_times = [0.5, 0.7, 0.3]
        storage.stats.last_processed = datetime.now(timezone.utc)
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 1
        assert data["last_processed"] is not None

    @patch("src.api_routes.storage.stats")
    @patch.object(api_routes_logger, "error")
    def test_stats_endpoint_generic_exception(
        self, mock_logger_error, mock_storage_stats, client
    ):
        mock_pt_list = MagicMock()
        mock_pt_list.__len__.side_effect = Exception("Simulated storage error")
        mock_storage_stats.processing_times = mock_pt_list

        mock_storage_stats.total_processed = 0
        mock_storage_stats.total_errors = 0
        mock_storage_stats.avg_urgency_score = 0.0
        mock_storage_stats.last_processed = None

        response = client.get("/api/stats")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to retrieve system statistics"
        mock_logger_error.assert_called_once()
        assert (
            "Error retrieving system stats: Simulated storage error"
            in mock_logger_error.call_args[0][0]
        )

    def test_recent_emails_endpoint_empty(self, client):
        response = client.get("/api/emails/recent")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["emails"] == []

    def test_recent_emails_endpoint_with_data(self, client, sample_processed_email):
        storage.email_storage["test-email-1"] = sample_processed_email
        response = client.get("/api/emails/recent")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["emails"][0]["id"] == "test-email-1"

    @patch("src.api_routes.storage.email_storage")
    @patch.object(api_routes_logger, "error")
    def test_recent_emails_endpoint_generic_exception(
        self, mock_logger_error, mock_email_storage, client
    ):
        mock_email_storage.values.side_effect = Exception(
            "Simulated storage access error"
        )
        response = client.get("/api/emails/recent")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to retrieve recent emails"
        mock_logger_error.assert_called_once()
        assert (
            "Error retrieving recent emails: Simulated storage access error"
            in mock_logger_error.call_args[0][0]
        )

    def test_emails_endpoint_with_pagination(self, client, sample_processed_email):
        for i in range(15):
            email = sample_processed_email.model_copy(
                deep=True
            )  # Use deep=True for Pydantic v2
            email.id = f"test-email-{i}"
            storage.email_storage[f"test-email-{i}"] = email
        response = client.get("/api/emails?skip=5&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["emails"]) == 5

    @patch("src.api_routes.storage.email_storage")
    @patch.object(api_routes_logger, "error")
    def test_emails_endpoint_generic_exception(
        self, mock_logger_error, mock_email_storage, client
    ):
        mock_email_storage.values.side_effect = Exception("Simulated list error")
        response = client.get("/api/emails")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to retrieve emails"
        mock_logger_error.assert_called_once()
        assert (
            "Error retrieving emails: Simulated list error"
            in mock_logger_error.call_args[0][0]
        )

    def test_specific_email_endpoint(self, client, sample_processed_email):
        storage.email_storage["test-email-1"] = sample_processed_email
        response = client.get("/api/emails/test-email-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-email-1"

    def test_specific_email_not_found(self, client):
        response = client.get("/api/emails/non-existent")
        assert response.status_code == 404

    @patch("src.api_routes.storage.email_storage")
    @patch.object(api_routes_logger, "error")
    def test_specific_email_endpoint_generic_exception(
        self, mock_logger_error, mock_email_storage, client
    ):
        email_id = "test-email-generic-error"
        mock_email_storage.__contains__.return_value = True  # Email "exists"

        # This is the mock for the 'email' object retrieved from storage
        mocked_retrieved_email = MagicMock(spec=ProcessedEmail)

        # Set attributes that are accessed *before* the intended error point
        mocked_retrieved_email.id = email_id  # Crucial: set the 'id' attribute

        # Mock the email_data attribute to return another mock
        mock_email_data_obj = MagicMock(spec=EmailData)
        # Configure the .subject access on this nested mock to raise the error
        type(mock_email_data_obj).subject = PropertyMock(
            side_effect=Exception("Simulated attribute error")
        )
        type(mock_email_data_obj).message_id = PropertyMock(
            return_value="msg-id-ok"
        )  # Example of another field
        type(mock_email_data_obj).from_email = PropertyMock(
            return_value="ok@example.com"
        )
        type(mock_email_data_obj).to_emails = PropertyMock(
            return_value=["to@example.com"]
        )
        type(mock_email_data_obj).cc_emails = PropertyMock(return_value=[])
        type(mock_email_data_obj).bcc_emails = PropertyMock(return_value=[])
        type(mock_email_data_obj).text_body = PropertyMock(return_value="ok body")
        type(mock_email_data_obj).html_body = PropertyMock(
            return_value="<p>ok html</p>"
        )
        type(mock_email_data_obj).received_at = PropertyMock(
            return_value=datetime.now(timezone.utc)
        )
        type(mock_email_data_obj).attachments = PropertyMock(return_value=[])
        type(mock_email_data_obj).headers = PropertyMock(return_value={})

        # Make the .email_data attribute of ProcessedEmail return our mock_email_data_obj
        type(mocked_retrieved_email).email_data = PropertyMock(
            return_value=mock_email_data_obj
        )

        # Configure other attributes of ProcessedEmail that might be accessed
        # If analysis is None, its attributes won't be accessed.
        type(mocked_retrieved_email).analysis = PropertyMock(return_value=None)
        type(mocked_retrieved_email).status = PropertyMock(
            return_value=EmailStatus.ANALYZED
        )
        type(mocked_retrieved_email).processed_at = PropertyMock(
            return_value=datetime.now(timezone.utc)
        )

        mock_email_storage.__getitem__.return_value = mocked_retrieved_email

        response = client.get(f"/api/emails/{email_id}")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to retrieve email"
        mock_logger_error.assert_called_once()

        # The logged exception 'e' should now be Exception("Simulated attribute error")
        logged_error_message = mock_logger_error.call_args[0][0]
        assert (
            f"Error retrieving email {email_id}: Simulated attribute error"
            in logged_error_message
        )

    def test_search_endpoint(self, client, sample_processed_email):
        storage.email_storage["test-email-1"] = sample_processed_email
        response = client.get("/api/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert data["total_found"] == 1

    def test_search_endpoint_no_query(self, client):
        response = client.get("/api/search")
        assert response.status_code == 422

    @patch("src.api_routes.storage.email_storage")
    @patch.object(api_routes_logger, "error")
    def test_search_endpoint_generic_exception(
        self, mock_logger_error, mock_email_storage, client
    ):
        mock_email_storage.values.side_effect = Exception(
            "Simulated search processing error"
        )
        response = client.get("/api/search?q=anything")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to search emails"
        mock_logger_error.assert_called_once()
        assert (
            "Error searching emails with query 'anything': Simulated search processing error"
            in mock_logger_error.call_args[0][0]
        )

    def test_analytics_endpoint_empty(self, client):
        response = client.get("/api/analytics")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "No emails processed yet"

    def test_analytics_endpoint_with_data(self, client, sample_processed_email):
        storage.email_storage["test-email-1"] = sample_processed_email
        storage.stats.total_processed = 1
        storage.stats.processing_times = [0.5]
        response = client.get("/api/analytics")
        assert response.status_code == 200
        data = response.json()
        assert data["total_emails"] == 1
        assert data["analyzed_emails"] == 1

    @patch("src.api_routes.storage.email_storage")
    @patch.object(api_routes_logger, "error")
    def test_analytics_endpoint_generic_exception(
        self, mock_logger_error, mock_email_storage, client
    ):
        mock_email_storage.values.side_effect = Exception("Simulated analytics error")
        response = client.get("/api/analytics")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to generate analytics"
        mock_logger_error.assert_called_once()
        assert (
            "Error generating analytics: Simulated analytics error"
            in mock_logger_error.call_args[0][0]
        )
