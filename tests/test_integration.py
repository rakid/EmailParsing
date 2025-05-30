"""
Integration tests for the MCP Email Parsing Server
Tests end-to-end functionality including webhook processing, MCP protocol compliance,
and real-world scenarios.
"""

import json
import os

# Import MCP and server components
import sys
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src import server  # MCP Server module
from src import storage
from src.integrations import DatabaseFormat  # Added DatabaseFormat
from src.integrations import DataExporter  # Added DataExporter
from src.integrations import ExportFormat  # Added ExportFormat
from src.integrations import PluginInterface  # Added PluginInterface for example plugin
from src.integrations import PluginManager  # Added PluginManager
from src.integrations import (
    AIAnalysisFormat,
    DatabaseInterface,
    PostgreSQLInterface,
    SQLiteInterface,
)
from src.models import (  # Added EmailStatus
    EmailAnalysis,
    EmailData,
    EmailStatus,
    ProcessedEmail,
    UrgencyLevel,
)
from src.webhook import app as webhook_app  # FastAPI app instance

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


# Example Plugin for testing PluginManager
class ExampleTestPlugin(PluginInterface):
    def get_name(self) -> str:
        return "example_test_plugin"

    def get_version(self) -> str:
        return "1.0.0"

    def get_dependencies(self) -> list:
        return []

    async def initialize(self, config: dict) -> None:
        self.initialized_config = config
        print(f"{self.get_name()} initialized.")

    async def process_email(self, email: ProcessedEmail) -> ProcessedEmail:
        if email.analysis:
            email.analysis.tags.append(f"{self.get_name()}_processed")
        return email

    async def cleanup(self) -> None:
        print(f"{self.get_name()} cleaned up.")


class TestIntegrationComponents:  # Renamed from TestAIIntegrationComponents for broader scope
    """Test integration components like data formats, DB interfaces, and plugin manager."""

    def test_ai_analysis_format_creation_no_analysis(self):  # Renamed and updated
        """Test AIAnalysisFormat creation from ProcessedEmail with no analysis."""
        email_data = EmailData(
            message_id="test-message-1",
            subject="Test Subject",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            text_body="Test email content",
            html_body="<p>Test email content</p>",
            received_at=datetime.now(timezone.utc),
        )

        processed_email_no_analysis = ProcessedEmail(
            id="test-no-analysis",
            email_data=email_data,
            analysis=None,  # Explicitly no analysis
            status=EmailStatus.RECEIVED,  # Use Enum
            processed_at=datetime.now(timezone.utc),
        )

        ai_format_no_analysis = AIAnalysisFormat.from_processed_email(
            processed_email_no_analysis
        )

        assert ai_format_no_analysis.email_id == "test-no-analysis"
        assert ai_format_no_analysis.content["subject"] == "Test Subject"
        # Check default feature values when analysis is None
        assert ai_format_no_analysis.features["urgency_score"] == 0
        assert ai_format_no_analysis.features["urgency_level"] == "low"
        assert ai_format_no_analysis.features["sentiment"] == "neutral"
        assert ai_format_no_analysis.features["keywords"] == []

    def test_ai_analysis_format_with_analysis(self):
        """Test AIAnalysisFormat with email analysis data."""
        email_data = EmailData(
            message_id="test-urgent-456",
            subject="Urgent Task",
            from_email="manager@company.com",
            to_emails=["employee@company.com"],
            text_body="Please complete this task urgently",
            html_body="<p>Please complete this task <b>urgently</b></p>",
            received_at=datetime.now(timezone.utc),
        )

        # Instantiate EmailAnalysis with fields defined in src/models.py
        analysis = EmailAnalysis(
            urgency_score=85,
            urgency_level=UrgencyLevel.HIGH,
            sentiment="neutral",
            confidence=0.87,
            keywords=["task", "complete", "urgent"],  # Using 'keywords' field
            action_items=["complete this task"],  # Using 'action_items' field
            temporal_references=["urgently"],
            tags=["project_alpha"],
        )

        processed_email = ProcessedEmail(
            id="test-urgent-456",
            email_data=email_data,
            analysis=analysis,
            status=EmailStatus.ANALYZED,  # Use Enum
            processed_at=datetime.now(timezone.utc),
        )

        ai_format = AIAnalysisFormat.from_processed_email(processed_email)

        assert ai_format.email_id == "test-urgent-456"
        # Access analysis data via 'features' attribute
        assert ai_format.features is not None
        assert ai_format.features["urgency_score"] == 85
        assert ai_format.features["urgency_level"] == "high"
        assert "task" in ai_format.features["keywords"]
        assert "urgent" in ai_format.features["keywords"]
        assert "complete this task" in ai_format.features["action_items"]
        assert "project_alpha" in ai_format.features["tags"]

    @pytest.mark.asyncio
    async def test_sqlite_interface(self):
        """Test SQLiteInterface implementation (basic connection and stats)."""
        sqlite_interface = SQLiteInterface()

        await sqlite_interface.connect(":memory:")  # Use in-memory for testing
        assert sqlite_interface.db_path == ":memory:"

        stats_result = await sqlite_interface.get_stats()
        assert stats_result is not None
        assert hasattr(stats_result, "total_processed")
        assert stats_result.total_processed == 0  # Initially

        await sqlite_interface.disconnect()  # No explicit close in aiosqlite, but good to have

    @pytest.mark.asyncio
    async def test_postgresql_interface(self):
        """Test PostgreSQLInterface implementation (mocked connection)."""
        # Mock asyncpg at the module level
        with patch("src.integrations.asyncpg") as mock_asyncpg:
            mock_pool = AsyncMock()
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            postgres_interface = PostgreSQLInterface()

            await postgres_interface.connect(
                "postgresql://test:test@localhost:5432/testdb"
            )
            mock_asyncpg.create_pool.assert_called_once_with(
                "postgresql://test:test@localhost:5432/testdb"
            )

            # Mock stats retrieval from PostgreSQL
            stats_result = (
                await postgres_interface.get_stats()
            )  # Will use default EmailStats
            assert stats_result is not None
            assert hasattr(stats_result, "total_processed")

            await postgres_interface.disconnect()
            mock_pool.close.assert_called_once()

    def test_database_interface_abstract_methods(self):  # Corrected this test
        """Test that DatabaseInterface enforces abstract methods"""
        # Attempting to instantiate abstract class should raise TypeError
        with pytest.raises(
            TypeError,
            match="Can't instantiate abstract class DatabaseInterface without an implementation for abstract methods",
        ):
            DatabaseInterface()  # type: ignore

    def test_ai_analysis_format_serialization(self):
        """Test AIAnalysisFormat JSON serialization."""
        email_data = EmailData(
            message_id="serialize-789",
            subject="Serialization Test",
            from_email="sender@test.com",
            to_emails=["receiver@test.com"],
            text_body="Test content for serialization",
            html_body="<p>Test content for serialization</p>",
            received_at=datetime.now(timezone.utc),
        )

        processed_email = ProcessedEmail(
            id="serialize-789",
            email_data=email_data,
            status=EmailStatus.ANALYZED,  # Use Enum
            processed_at=datetime.now(timezone.utc),
        )

        ai_format = AIAnalysisFormat.from_processed_email(processed_email)

        format_dict = ai_format.model_dump()  # Use model_dump for Pydantic v2
        assert format_dict["email_id"] == "serialize-789"
        assert format_dict["content"]["subject"] == "Serialization Test"

        json_str = ai_format.model_dump_json()  # Use model_dump_json for Pydantic v2
        assert "serialize-789" in json_str
        assert "Serialization Test" in json_str

    def test_database_format_creation(
        self,
    ):
        """Test DatabaseFormat creation from ProcessedEmail."""
        email_data = EmailData(
            message_id="db-format-test",
            subject="DB Format Test",
            from_email="db@example.com",
            to_emails=["db_user@example.com"],
            cc_emails=["cc@example.com"],
            text_body="Database format test content.",
            received_at=datetime.now(timezone.utc),
            headers={"X-Custom": "Value"},
            attachments=[],  # Add attachments for full coverage
        )
        analysis = EmailAnalysis(
            urgency_score=60,
            urgency_level=UrgencyLevel.MEDIUM,
            sentiment="neutral",
            confidence=0.7,
            keywords=["db", "format"],
            action_items=["test db format"],
            tags=["db_test"],
        )
        processed_email = ProcessedEmail(
            id="db-id-1",
            email_data=email_data,
            analysis=analysis,
            status=EmailStatus.ANALYZED,
            processed_at=datetime.now(timezone.utc),
        )

        db_format = DatabaseFormat.from_processed_email(processed_email)

        assert db_format.id == "db-id-1"
        assert db_format.message_id == "db-format-test"
        assert json.loads(db_format.to_emails) == ["db_user@example.com"]
        assert db_format.urgency_score == 60
        assert json.loads(db_format.keywords) == ["db", "format"]
        assert json.loads(db_format.headers) == {"X-Custom": "Value"}
        assert json.loads(db_format.attachments) == []

    @pytest.mark.asyncio
    async def test_plugin_manager_registration_and_execution(self):
        """Test PluginManager registration, ordering, and execution."""
        manager = PluginManager()
        plugin1 = ExampleTestPlugin()
        await plugin1.initialize({"setting": "value1"})

        plugin2 = ExampleTestPlugin()  # Create a new instance for the second plugin
        plugin2.get_name = lambda: "example_test_plugin_2"  # mock new name
        await plugin2.initialize({"setting": "value2"})

        manager.register_plugin(plugin1, priority=10)
        manager.register_plugin(plugin2, priority=5)  # Higher priority (lower number)

        assert len(manager.plugins) == 2
        assert manager.plugin_order == ["example_test_plugin_2", "example_test_plugin"]

        email_data = EmailData(
            message_id="plugin-email",
            subject="Plugin Test",
            from_email="p@e.com",
            to_emails=["r@e.com"],
            received_at=datetime.now(timezone.utc),
        )
        analysis = EmailAnalysis(
            urgency_score=50,
            urgency_level=UrgencyLevel.MEDIUM,
            sentiment="neutral",
            confidence=0.5,
            tags=[],
        )
        test_email = ProcessedEmail(
            id="plugin-email-id", email_data=email_data, analysis=analysis
        )

        processed = await manager.process_email_through_plugins(test_email)

        assert "example_test_plugin_2_processed" in processed.analysis.tags
        assert "example_test_plugin_processed" in processed.analysis.tags
        # Check order based on tag addition (plugin2 runs first, so its tag should appear before plugin1's)
        # This assumes plugins append tags.
        if processed.analysis.tags:
            assert processed.analysis.tags.index(
                "example_test_plugin_2_processed"
            ) < processed.analysis.tags.index("example_test_plugin_processed")

        manager.unregister_plugin("example_test_plugin")
        assert len(manager.plugins) == 1
        assert "example_test_plugin" not in manager.plugin_order

        plugin_info = manager.get_plugin_info()
        assert "example_test_plugin_2" in plugin_info
        assert plugin_info["example_test_plugin_2"]["version"] == "1.0.0"

    @patch("builtins.open", new_callable=MagicMock)
    def test_data_exporter_json(
        self,
        mock_open,
    ):
        """Test DataExporter._export_json method."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        email_data = EmailData(
            message_id="export-json",
            subject="JSON Export",
            from_email="e@e.com",
            to_emails=["r@e.com"],
            received_at=datetime.now(timezone.utc),
        )
        processed_email = ProcessedEmail(
            id="export-id",
            email_data=email_data,
            status=EmailStatus.ANALYZED,
            processed_at=datetime.now(timezone.utc),
        )

        dest_file = "test_export.json"
        result_path = DataExporter.export_emails(
            [processed_email], ExportFormat.JSON, dest_file
        )

        assert result_path == dest_file
        mock_open.assert_called_once_with(dest_file, "w")
        # Check that json.dump was called (indirectly via file write)
        # For a more robust test, you could check `mock_file.write.call_args`
        assert mock_file.write.call_count > 0

        # Verify JSONL export
        dest_file_jsonl = "test_export.jsonl"
        mock_open.reset_mock()
        result_path_jsonl = DataExporter.export_emails(
            [processed_email], ExportFormat.JSONL, dest_file_jsonl
        )
        assert result_path_jsonl == dest_file_jsonl
        mock_open.assert_called_once_with(dest_file_jsonl, "w")
        # JSONL writes line by line
        assert mock_file.write.call_count >= 1

    def test_data_exporter_unsupported_format(
        self,
    ):
        """Test DataExporter with an unsupported format."""
        with pytest.raises(
            ValueError, match="Unsupported export format: ExportFormat.XML"
        ):
            DataExporter.export_emails([], ExportFormat.XML, "test.xml")


# --- TestEndToEndIntegration Class (largely unchanged but ensure it uses updated models if necessary) ---
class TestEndToEndIntegration:
    """Test complete end-to-end email processing workflow"""

    def setup_method(self):
        """Setup for each test method"""
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.avg_urgency_score = 0.0
        storage.stats.last_processed = None
        storage.stats.processing_times.clear()

        import src.server
        import src.webhook

        src.webhook.storage = storage
        src.server.storage = storage

    @pytest.mark.asyncio
    @patch("src.webhook.config")
    @patch("src.webhook.email_extractor")
    async def test_complete_postmark_to_mcp_workflow(self, mock_extractor, mock_config):
        """Test complete workflow from Postmark webhook to MCP resource access"""

        mock_config.webhook_endpoint = "/webhook"
        mock_config.postmark_webhook_secret = None

        mock_metadata = MagicMock()
        # Ensure mocked ExtractedMetadata fields align with what EmailAnalysis expects
        mock_metadata.urgency_indicators = {
            "high": ["urgent", "asap", "critical"],
            "medium": [],
            "low": [],
        }
        mock_metadata.sentiment_indicators = {
            "positive": [],
            "negative": ["outage", "down"],
            "neutral": [],
        }
        mock_metadata.priority_keywords = ["urgent", "critical", "server", "outage"]
        mock_metadata.action_words = ["check", "restart", "contact", "send"]
        mock_metadata.temporal_references = ["1 hour", "tomorrow"]
        mock_metadata.contact_info = {}
        mock_metadata.links = []

        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (
            95,
            UrgencyLevel.CRITICAL.value,
        )  # Ensure string value for level

        webhook_payload = {
            "From": "urgent.sender@company.com",
            "To": "recipient@example.com",
            "ToFull": [{"Email": "recipient@example.com", "Name": "Recipient User"}],
            "Subject": "URGENT: Server outage - immediate action required",
            "TextBody": """
URGENT: Production server is down!
We have a critical outage affecting all customers. Need immediate action:
1. Check server logs ASAP
2. Restart database cluster
3. Contact on-call engineer
4. Send customer communication
This needs to be resolved within 1 hour. Call me at 555-999-8888.
Status: CRITICAL
Priority: P0        """,
            "HtmlBody": (
                "<p><strong>URGENT:</strong> Production server is down!</p>"
                "<p>We have a critical outage affecting all customers...</p>"
            ),
            "MessageID": "integration-test-123@postmark.com",
            "Date": "2025-05-28T10:30:00.000Z",
            "Headers": [
                {"Name": "X-Priority", "Value": "1"},
                {"Name": "X-Urgency", "Value": "high"},
            ],
            "Attachments": [],
        }

        webhook_client = TestClient(webhook_app)
        response = webhook_client.post(
            mock_config.webhook_endpoint, json=webhook_payload
        )

        assert response.status_code == 200
        webhook_result = response.json()
        assert webhook_result["status"] == "success"
        processing_id = webhook_result["processing_id"]

        assert len(storage.email_storage) == 1
        assert processing_id in storage.email_storage

        stored_email = storage.email_storage[processing_id]
        assert isinstance(stored_email, ProcessedEmail)
        assert stored_email.email_data.from_email == "urgent.sender@company.com"
        assert "URGENT" in stored_email.email_data.subject

        assert stored_email.analysis is not None
        assert stored_email.analysis.urgency_level == UrgencyLevel.CRITICAL
        assert stored_email.analysis.urgency_score == 95

        resources = await server.handle_list_resources()
        assert len(resources) >= 6

        email_resource_result_str = await server.handle_read_resource(
            f"email://processed/{processing_id}"
        )
        assert email_resource_result_str is not None
        email_resource_result = json.loads(email_resource_result_str)
        assert email_resource_result["id"] == processing_id

        processed_emails_result_str = await server.handle_read_resource(
            "email://processed"
        )
        assert processed_emails_result_str is not None
        processed_data = json.loads(processed_emails_result_str)
        assert processed_data["total_count"] == 1
        assert len(processed_data["emails"]) == 1

        return processing_id

    @patch("src.webhook.email_extractor")
    @patch("src.webhook.config")
    def test_high_volume_concurrent_processing(self, mock_config, mock_extractor):
        mock_config.postmark_webhook_secret = None
        mock_metadata = MagicMock()
        mock_metadata.urgency_indicators = {"high": ["urgent"], "medium": [], "low": []}
        mock_metadata.sentiment_indicators = {
            "positive": [],
            "negative": [],
            "neutral": ["test"],
        }
        mock_metadata.priority_keywords = ["urgent", "critical"]
        mock_metadata.action_words = ["check", "review"]
        mock_metadata.temporal_references = ["tomorrow"]
        mock_metadata.contact_info = {}
        mock_metadata.links = []
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (
            75,
            UrgencyLevel.HIGH.value,
        )

        def create_webhook_payload(i):
            return {
                "From": f"sender{i}@example.com",
                "To": "recipient@example.com",
                "ToFull": [{"Email": "recipient@example.com", "Name": "Recipient"}],
                "Subject": f"Test Email {i}",
                "TextBody": f"This is test email number {i}",
                "MessageID": f"test-{i}@example.com",
                "Date": "2025-05-28T10:30:00.000Z",
                "Headers": [],
                "Attachments": [],
            }

        webhook_client = TestClient(webhook_app)
        num_emails = 10
        start_time = time.time()

        responses = []
        for i in range(num_emails):
            payload = create_webhook_payload(i)
            response = webhook_client.post(
                "/webhook", json=payload
            )  # Using the actual endpoint path
            responses.append(response)

        processing_time = time.time() - start_time

        for resp in responses:
            assert resp.status_code == 200
            assert resp.json()["status"] == "success"

        assert len(storage.email_storage) == num_emails
        assert processing_time < 5.0
        assert storage.stats.total_processed == num_emails
        assert storage.stats.total_errors == 0

    @patch("src.webhook.email_extractor")
    @patch("src.webhook.config")
    @pytest.mark.asyncio
    async def test_mcp_tools_integration(self, mock_config, mock_extractor):
        mock_config.postmark_webhook_secret = None
        mock_metadata = MagicMock()
        mock_metadata.urgency_indicators = {"high": ["urgent"], "medium": [], "low": []}
        mock_metadata.sentiment_indicators = {
            "positive": [],
            "negative": [],
            "neutral": ["test"],
        }
        mock_metadata.priority_keywords = ["urgent", "critical", "bug"]
        mock_metadata.action_words = ["fix", "review", "prepare"]
        mock_metadata.temporal_references = ["tomorrow", "Friday"]
        mock_metadata.contact_info = {}
        mock_metadata.links = []
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (
            85,
            UrgencyLevel.HIGH.value,
        )

        test_emails_payload_data = [
            {
                "From": "urgent@company.com",
                "To": "manager@company.com",
                "Subject": "URGENT: Critical bug in production",
                "TextBody": "We have a critical bug affecting payments. Need to fix ASAP. Deadline is tomorrow at 5 PM.",
                "MessageID": "urgent-bug@company.com",
            },
            {
                "From": "newsletter@company.com",
                "To": "subscriber@example.com",
                "Subject": "Weekly Newsletter",
                "TextBody": "Here's your weekly update with industry news and updates.",
                "MessageID": "newsletter@company.com",
            },
            {
                "From": "manager@company.com",
                "To": "team@company.com",
                "Subject": "Meeting scheduled for Friday",
                "TextBody": "Please review the agenda and prepare your status updates. Meeting is at 2 PM on Friday.",
                "MessageID": "meeting@company.com",
            },
        ]

        webhook_client = TestClient(webhook_app)
        processing_ids = []

        for email_payload_data in test_emails_payload_data:
            payload = {
                **email_payload_data,
                "ToFull": [{"Email": email_payload_data["To"], "Name": "User"}],
                "Date": "2025-05-28T10:30:00.000Z",
                "Headers": [],
                "Attachments": [],
            }
            response = webhook_client.post("/webhook", json=payload)
            assert response.status_code == 200
            processing_ids.append(response.json()["processing_id"])

        search_result_content_list = await server.handle_call_tool(
            "search_emails", {"query": "urgent", "limit": 10}
        )
        assert len(search_result_content_list) > 0
        search_content = json.loads(search_result_content_list[0].text)
        assert len(search_content["results"]) >= 1

        stats_result_content_list = await server.handle_call_tool("get_email_stats", {})
        assert len(stats_result_content_list) > 0
        stats_content = json.loads(stats_result_content_list[0].text)
        assert (
            stats_content["total_processed"] == 3
        )  # Updated to reflect actual processing

        tasks_result_content_list = await server.handle_call_tool(
            "extract_tasks", {"email_id": processing_ids[0]}
        )
        assert len(tasks_result_content_list) > 0
        tasks_content = json.loads(tasks_result_content_list[0].text)
        assert len(tasks_content["tasks"]) > 0  # Action words "fix" should be found

    # ... (rest of TestEndToEndIntegration, TestPerformanceIntegration, TestMCPProtocolCompliance are largely okay but ensure consistency)
    @patch("src.webhook.email_extractor")
    @patch("src.webhook.config")
    def test_error_handling_and_recovery(self, mock_config, mock_extractor):
        """Test error handling in integration scenarios"""

        mock_config.postmark_webhook_secret = None
        mock_metadata = MagicMock()
        mock_metadata.urgency_indicators = {
            "medium": ["test"],
            "high": [],
            "low": [],
        }  # Ensure all levels exist
        mock_metadata.sentiment_indicators = {
            "neutral": ["test"],
            "positive": [],
            "negative": [],
        }
        mock_metadata.priority_keywords = ["test"]
        mock_metadata.action_words = ["test"]
        mock_metadata.temporal_references = []
        mock_metadata.contact_info = {}
        mock_metadata.links = []
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (60, "medium")

        webhook_client = TestClient(webhook_app)

        response = webhook_client.post(
            "/webhook",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert (
            response.status_code == 400
        )  # Changed from [400,500] to specific 400 for invalid JSON

        incomplete_payload = {"From": "sender@example.com"}
        response = webhook_client.post("/webhook", json=incomplete_payload)
        assert response.status_code == 422  # Pydantic validation error

        malformed_payload = {
            "From": "sender@example.com",
            "To": "recipient@example.com",
            "Subject": "Test",
            "TextBody": "Test",
            "MessageID": "test@example.com",
            "Date": "invalid-date-format",
            "ToFull": [{"Email": "recipient@example.com"}],
            "Headers": [],
            "Attachments": [],
        }
        response = webhook_client.post("/webhook", json=malformed_payload)
        # This will be a 500 from ValueError in extract_email_data due to invalid date format
        assert response.status_code == 500

        # total_errors is incremented on Exception, not HTTPException(4xx)
        # For Pydantic validation errors (422) or JSONDecodeError (400),
        # the generic exception handler that increments total_errors might not be reached.
        # This assertion might need adjustment based on how errors are finally handled.
        assert (
            storage.stats.total_errors <= 1
        )  # Only an unhandled Exception would increment this.


class TestPerformanceIntegration:
    """Performance and load testing"""

    def setup_method(self):
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.avg_urgency_score = 0.0  # Added
        storage.stats.last_processed = None  # Added
        storage.stats.processing_times.clear()
        import src.webhook

        src.webhook.storage = storage

    @patch("src.webhook.email_extractor")
    @patch("src.webhook.config")
    def test_processing_time_requirements(self, mock_config, mock_extractor):
        mock_config.postmark_webhook_secret = None
        mock_metadata = MagicMock()
        mock_metadata.urgency_indicators = {
            "critical": ["urgent"],
            "high": [],
            "medium": [],
            "low": [],
        }
        mock_metadata.sentiment_indicators = {
            "neutral": ["test"],
            "positive": [],
            "negative": [],
        }
        mock_metadata.priority_keywords = ["urgent", "critical"]
        mock_metadata.action_words = ["review", "contact"]
        mock_metadata.temporal_references = ["tomorrow", "today"]
        mock_metadata.contact_info = {}
        mock_metadata.links = []
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (
            90,
            UrgencyLevel.CRITICAL.value,
        )

        webhook_payload = {
            "From": "performance@test.com",
            "To": "recipient@example.com",
            "ToFull": [{"Email": "recipient@example.com", "Name": "Recipient"}],
            "Subject": "Performance Test Email with URGENT content for analysis",
            "TextBody": "This is a performance test email...",
            "MessageID": "performance-test@example.com",
            "Date": "2025-05-28T10:30:00.000Z",
            "Headers": [{"Name": "X-Priority", "Value": "1"}],
            "Attachments": [],
        }
        webhook_client = TestClient(webhook_app)
        start_time = time.time()
        response = webhook_client.post("/webhook", json=webhook_payload)
        processing_time = time.time() - start_time

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert processing_time < 2.0

        stored_email = storage.email_storage[result["processing_id"]]
        assert stored_email.analysis is not None
        assert stored_email.analysis.urgency_score > 0

    @patch("src.webhook.email_extractor")
    @patch("src.webhook.config")
    def test_memory_usage_stability(self, mock_config, mock_extractor):
        mock_config.postmark_webhook_secret = None
        mock_metadata = MagicMock()
        mock_metadata.urgency_indicators = {"high": ["urgent"], "medium": [], "low": []}
        mock_metadata.sentiment_indicators = {
            "neutral": ["test"],
            "positive": [],
            "negative": [],
        }
        mock_metadata.priority_keywords = ["urgent"]
        mock_metadata.action_words = ["analyze"]
        mock_metadata.temporal_references = []
        mock_metadata.contact_info = {}
        mock_metadata.links = []
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (
            70,
            UrgencyLevel.HIGH.value,
        )

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        webhook_client = TestClient(webhook_app)
        for i in range(50):  # Reduced from 50 for faster local testing if needed
            payload = {
                "From": f"sender{i}@example.com",
                "To": "recipient@example.com",
                "ToFull": [{"Email": "recipient@example.com", "Name": "Recipient"}],
                "Subject": f"Test Email {i} ...",
                "TextBody": f"This is test email {i} ...",
                "MessageID": f"memory-test-{i}@example.com",
                "Date": "2025-05-28T10:30:00.000Z",
                "Headers": [],
                "Attachments": [],
            }
            response = webhook_client.post("/webhook", json=payload)
            assert response.status_code == 200

        final_memory = process.memory_info().rss
        memory_growth_mb = (final_memory - initial_memory) / 1024 / 1024

        assert memory_growth_mb < 100
        assert len(storage.email_storage) == 50


class TestMCPProtocolCompliance:
    def setup_method(self):
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.avg_urgency_score = 0.0
        storage.stats.last_processed = None
        storage.stats.processing_times.clear()
        import src.webhook  # Ensure storage is reset for webhook too

        src.webhook.storage = storage
        import src.server

        src.server.storage = storage  # And for server

    @pytest.mark.asyncio
    async def test_mcp_server_initialization(self):
        assert server.server.name == "inbox-zen-email-parser"
        assert server.server.version == "0.1.0"  # From default config in src/config.py
        assert "MCP server for unified email entry" in server.server.instructions

    @pytest.mark.asyncio
    async def test_mcp_capabilities_advertisement(self):
        resources = await server.handle_list_resources()
        assert len(resources) >= 6
        tools = await server.handle_list_tools()
        assert len(tools) >= 4
        prompts = await server.handle_list_prompts()
        assert len(prompts) >= 1

    @patch("src.webhook.email_extractor")
    @patch("src.webhook.config")
    @pytest.mark.asyncio
    async def test_mcp_resource_operations(self, mock_config, mock_extractor):
        mock_config.postmark_webhook_secret = None
        mock_metadata = MagicMock()
        mock_metadata.urgency_indicators = {"medium": ["test"], "high": [], "low": []}
        mock_metadata.sentiment_indicators = {
            "neutral": ["test"],
            "positive": [],
            "negative": [],
        }
        mock_metadata.priority_keywords = ["test"]
        mock_metadata.action_words = ["testing"]
        mock_metadata.temporal_references = []
        mock_metadata.contact_info = {}
        mock_metadata.links = []
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (60, "medium")

        webhook_payload = {
            "From": "test@example.com",
            "To": "recipient@example.com",
            "ToFull": [{"Email": "recipient@example.com", "Name": "Recipient"}],
            "Subject": "Test Email",
            "TextBody": "This is a test email for MCP resource testing",
            "MessageID": "mcp-test@example.com",
            "Date": "2025-05-28T10:30:00.000Z",
            "Headers": [],
            "Attachments": [],
        }
        webhook_client = TestClient(webhook_app)
        response = webhook_client.post("/webhook", json=webhook_payload)
        assert response.status_code == 200

        # Ensure an email exists to make email://processed meaningful
        assert len(storage.email_storage) > 0

        processed_emails_result_str = await server.handle_read_resource(
            "email://processed"
        )
        assert processed_emails_result_str is not None
        processed_data = json.loads(processed_emails_result_str)
        assert processed_data["total_count"] > 0  # Should have at least one email

        stats_result_str = await server.handle_read_resource("email://stats")
        assert stats_result_str is not None
        stats_data = json.loads(stats_result_str)
        assert "total_emails_in_storage" in stats_data  # Key check from server.py


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
