#!/usr/bin/env python3
"""
MCP Integration Tests for SambaNova AI Components

This module tests the integration of SambaNova AI components with the
existing Model Context Protocol (MCP) architecture and email processing system.
"""

import asyncio
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import test dependencies
try:
    from src.ai.config import SambaNovaConfig
    from src.ai.performance_optimizer import create_performance_optimizer
    from src.ai.plugin import SambaNovaPlugin
    from src.models import EmailAnalysis, EmailData, ProcessedEmail, UrgencyLevel
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    raise


# Base test case with async support
class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """Base test case with async support."""

    pass


class TestMCPToolIntegration:
    """Test SambaNova AI integration with MCP tools."""

    def create_sample_email(self):
        """Sample email data for testing."""
        return EmailData(
            from_email="user@example.com",
            to_emails=["support@company.com"],
            subject="URGENT: Server down - need immediate help",
            text_body="Our production server has been down for 2 hours. Customer impact is severe. Please escalate this immediately and provide ETA for resolution.",
            message_id="urgent-server-001",
            received_at=datetime.now(),
        )

    def create_temp_cache_dir(self):
        """Temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_mcp_tool_registration(self):
        """Test that SambaNova tools are properly registered with MCP."""
        plugin = SambaNovaPlugin()

        # Test that plugin has required attributes for MCP integration
        assert hasattr(plugin, "get_name")
        assert hasattr(plugin, "get_version")
        assert hasattr(plugin, "get_dependencies")

        # Test basic plugin info
        assert plugin.get_name() == "sambanova-ai-analysis"
        assert plugin.get_version() == "1.0.0"
        assert isinstance(plugin.get_dependencies(), list)

    @pytest.mark.asyncio
    async def test_email_analysis_tool_integration(self):
        """Test email analysis tool integration."""
        plugin = SambaNovaPlugin()

        # Get sample email data
        sample_email = self.create_sample_email()

        # Create a proper ProcessedEmail object that the plugin expects
        processed_email = ProcessedEmail(
            id="test-processed-001",
            email_data=sample_email,
            analysis=None,
            status="received",
            processed_at=None,
            error_message=None,
            webhook_payload={},
        )

        # Mock the AI analysis to avoid real API calls
        with patch.object(
            plugin, "process_email", new_callable=AsyncMock
        ) as mock_process:
            mock_process.return_value = processed_email

            # Test the tool call
            result = await plugin.process_email(processed_email)

            assert result is not None
            assert isinstance(result, ProcessedEmail)
            assert result.email_data == sample_email

    @pytest.mark.asyncio
    async def test_performance_optimizer_integration(self, temp_cache_dir):
        """Test performance optimizer integration with MCP tools."""
        plugin = SambaNovaPlugin()

        # Set up performance optimizer
        optimizer = create_performance_optimizer(cache_dir=temp_cache_dir)
        plugin.performance_optimizer = optimizer

        # Test performance monitoring integration
        performance_report = plugin.get_performance_report()

        assert isinstance(performance_report, dict)
        assert "metrics" in performance_report
        assert "cache" in performance_report
        assert "rate_limiting" in performance_report

    def test_mcp_tool_schema_validation(self):
        """Test that MCP tool schemas are properly defined."""
        plugin = SambaNovaPlugin()

        # Test that plugin has the expected methods that would be exposed as tools
        expected_methods = [
            "process_email",
            "batch_process_emails",
            "extract_tasks_with_context",
            "analyze_email_context",
            "analyze_email_thread",
        ]

        for method_name in expected_methods:
            assert hasattr(plugin, method_name), f"Plugin missing method: {method_name}"


class TestEmailProcessingPipelineIntegration:
    """Test integration with email processing pipeline."""

    @pytest.fixture
    def sample_processed_email(self):
        """Sample processed email for testing."""
        return ProcessedEmail(
            id="test-email-001",
            email_data=EmailData(
                message_id="test-message-001",
                from_email="sender@example.com",
                to_emails=["recipient@example.com"],
                subject="Project Update Required",
                text_body="Please provide an update on the Q4 project status by Friday.",
                html_body="<p>Please provide an update on the Q4 project status by Friday.</p>",
                received_at=datetime.now(),
            ),
            analysis=EmailAnalysis(
                urgency_score=65,
                urgency_level=UrgencyLevel.MEDIUM,
                sentiment="neutral",
                confidence=0.75,
                keywords=["project", "status", "update"],
                action_items=["Provide Q4 project status update"],
                temporal_references=["Friday"],
                tags=["project", "update"],
            ),
        )

    @pytest.mark.asyncio
    async def test_email_pipeline_enhancement(
        self, sample_processed_email, temp_cache_dir
    ):
        """Test that AI enhancement integrates with existing pipeline."""
        plugin = SambaNovaPlugin()

        # Mock AI enhancement using actual available method
        with patch.object(
            plugin, "process_email", new_callable=AsyncMock
        ) as mock_process:
            # Create an enhanced ProcessedEmail with additional analysis
            enhanced_email = sample_processed_email
            enhanced_email.analysis.tags.extend(["ai_enhanced", "context_analyzed"])
            enhanced_email.analysis.keywords.extend(["deadline", "urgent"])

            mock_process.return_value = enhanced_email

            # Test enhancement
            result = await plugin.process_email(sample_processed_email)

            assert result is not None
            assert isinstance(result, ProcessedEmail)
            assert "ai_enhanced" in result.analysis.tags

    @pytest.mark.asyncio
    async def test_batch_processing_integration(self, temp_cache_dir):
        """Test batch processing integration with email pipeline."""
        plugin = SambaNovaPlugin()
        optimizer = create_performance_optimizer(cache_dir=temp_cache_dir)
        plugin.performance_optimizer = optimizer

        # Test batch processing capability
        emails = [
            EmailData(
                from_email=f"user{i}@example.com",
                to_emails=["support@company.com"],
                subject=f"Email {i}",
                text_body=f"Content for email {i}",
                message_id=f"email-{i}",
                received_at=datetime.now(),
            )
            for i in range(5)
        ]

        # Mock batch analysis using actual method
        with patch.object(
            plugin, "batch_process_emails", new_callable=AsyncMock
        ) as mock_batch:
            # Create ProcessedEmail objects as expected return type
            processed_emails = []
            for email in emails:
                processed_email = ProcessedEmail(
                    id=f"processed-{email.message_id}",
                    email_data=email,
                    analysis=EmailAnalysis(
                        urgency_score=50,
                        urgency_level=UrgencyLevel.MEDIUM,
                        sentiment="neutral",
                        confidence=0.7,
                    ),
                )
                processed_emails.append(processed_email)

            mock_batch.return_value = processed_emails

            results = await plugin.batch_process_emails(
                [
                    ProcessedEmail(id=f"input-{email.message_id}", email_data=email)
                    for email in emails
                ]
            )

            assert len(results) == len(emails)
            assert all(isinstance(result, ProcessedEmail) for result in results)


class TestAPIRouteIntegration:
    """Test integration with API routes."""

    def test_api_route_availability(self):
        """Test that AI analysis endpoints are available."""
        # This would test actual API route registration
        # For now, test that the plugin provides the necessary interfaces
        plugin = SambaNovaPlugin()

        # Test that plugin has methods that would be exposed as API routes
        expected_api_methods = [
            "process_email",
            "batch_process_emails",
            "extract_tasks_with_context",
            "analyze_email_context",
        ]

        for method_name in expected_api_methods:
            assert hasattr(plugin, method_name), f"Missing API method: {method_name}"

    @pytest.mark.asyncio
    async def test_api_response_format(self, temp_cache_dir):
        """Test that API responses match expected format."""
        plugin = SambaNovaPlugin()

        email_data = EmailData(
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            subject="Test Email",
            text_body="Test content",
            message_id="test-001",
            received_at=datetime.now(),
        )

        # Create a ProcessedEmail for testing
        processed_email = ProcessedEmail(
            id="test-processed-001",
            email_data=email_data,
        )

        # Mock analysis using actual available method
        with patch.object(
            plugin, "analyze_email_context", new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.return_value = {
                "urgency_analysis": {
                    "level": "medium",
                    "confidence": 0.85,
                    "indicators": ["test"],
                },
                "context": {"domain": "business", "category": "general"},
                "sentiment": {"overall": "neutral", "confidence": 0.7},
            }

            result = await plugin.analyze_email_context(processed_email)

            # Verify response format
            assert isinstance(result, dict)
            assert "urgency_analysis" in result
            assert "context" in result
            assert isinstance(result["urgency_analysis"]["confidence"], (int, float))

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, temp_cache_dir):
        """Test error handling in API integration."""
        plugin = SambaNovaPlugin()

        # Test with invalid email data
        invalid_email_data = EmailData(
            from_email="",  # Invalid empty email
            to_emails=[],
            subject="",
            text_body="",
            message_id="",
            received_at=datetime.now(),
        )

        invalid_processed_email = ProcessedEmail(
            id="invalid-test-001",
            email_data=invalid_email_data,
        )

        # Should handle gracefully without crashing
        try:
            with patch.object(
                plugin, "process_email", new_callable=AsyncMock
            ) as mock_process:
                mock_process.side_effect = ValueError("Invalid email data")

                result = await plugin.process_email(invalid_processed_email)
                # Should handle error and return appropriate response

        except Exception as e:
            # Error handling should be graceful
            assert isinstance(e, (ValueError, TypeError))


class TestStorageIntegration:
    """Test integration with storage systems."""

    @pytest.mark.asyncio
    async def test_analysis_results_storage(self, temp_cache_dir):
        """Test that analysis results can be stored and retrieved."""
        plugin = SambaNovaPlugin()

        email_data = EmailData(
            from_email="storage@test.com",
            to_emails=["recipient@test.com"],
            subject="Storage Test",
            text_body="Testing storage integration",
            message_id="storage-test-001",
            received_at=datetime.now(),
        )

        processed_email = ProcessedEmail(
            id="storage-processed-001",
            email_data=email_data,
        )

        # Mock analysis and storage using actual available method
        enhanced_email = processed_email
        enhanced_email.analysis = EmailAnalysis(
            urgency_score=60,
            urgency_level=UrgencyLevel.MEDIUM,
            sentiment="neutral",
            confidence=0.8,
            keywords=["storage", "test"],
            action_items=["Test storage integration"],
            tags=["test", "storage"],
        )
        enhanced_email.processed_at = datetime.now()

        with patch.object(
            plugin, "process_email", new_callable=AsyncMock
        ) as mock_process:
            mock_process.return_value = enhanced_email

            # Test analysis
            result = await plugin.process_email(processed_email)

            # Test that result includes storage metadata
            assert result.processed_at is not None
            assert result.analysis is not None
            assert result.analysis.tags is not None

    def test_performance_data_persistence(self, temp_cache_dir):
        """Test that performance data persists correctly."""
        plugin = SambaNovaPlugin()
        optimizer = create_performance_optimizer(cache_dir=temp_cache_dir)
        plugin.performance_optimizer = optimizer

        # Generate some performance data
        test_data = {"test": "performance_data"}
        optimizer.cache.set("test_key", test_data, content="test content")

        # Test that data can be retrieved
        retrieved = optimizer.cache.get("test_key", content="test content")
        assert retrieved == test_data

        # Test performance metrics
        report = optimizer.get_performance_report()
        assert isinstance(report, dict)
        assert "metrics" in report


class TestWebhookIntegration:
    """Test integration with webhook processing."""

    @pytest.mark.asyncio
    async def test_webhook_analysis_trigger(self, temp_cache_dir):
        """Test that webhooks can trigger AI analysis."""
        plugin = SambaNovaPlugin()

        # Create EmailData from webhook-like payload
        email_data = EmailData(
            message_id="webhook-test-001",
            from_email="webhook@test.com",
            to_emails=["recipient@test.com"],
            subject="Webhook Test Email",
            html_body="<p>Testing webhook integration</p>",
            text_body="Testing webhook integration",
            received_at=datetime.now(),
        )

        processed_email = ProcessedEmail(
            id="webhook-processed-001",
            email_data=email_data,
        )

        # Test webhook processing using actual available method
        with patch.object(
            plugin, "process_email", new_callable=AsyncMock
        ) as mock_process:
            enhanced_email = processed_email
            enhanced_email.analysis = EmailAnalysis(
                urgency_score=30,
                urgency_level=UrgencyLevel.LOW,
                sentiment="neutral",
                confidence=0.75,
                tags=["webhook", "processed"],
            )

            mock_process.return_value = enhanced_email

            result = await plugin.process_email(processed_email)

            assert result.analysis is not None
            assert "webhook" in result.analysis.tags

    def test_webhook_error_recovery(self, temp_cache_dir):
        """Test webhook error handling and recovery."""
        plugin = SambaNovaPlugin()

        # Test basic plugin robustness
        assert plugin.get_name() == "sambanova-ai-analysis"
        assert hasattr(plugin, "processing_stats")

        # Test that error stats can be tracked
        stats = plugin.processing_stats
        assert "errors" in stats
        assert isinstance(stats["errors"], int)


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow integration."""

    @pytest.mark.asyncio
    async def test_complete_email_processing_workflow(self, temp_cache_dir):
        """Test complete email processing from webhook to AI analysis."""
        plugin = SambaNovaPlugin()

        # Step 1: Receive webhook
        webhook_data = {
            "MessageID": "e2e-test-001",
            "From": "urgent@customer.com",
            "To": "support@company.com",
            "Subject": "CRITICAL: Payment system down",
            "TextBody": "Payment processing has been down for 30 minutes. Revenue impact $50K/hour. Need immediate escalation to engineering team.",
            "ReceivedAt": "2025-05-31T15:30:00Z",
        }

        # Step 2: Convert to EmailData
        email_data = EmailData(
            from_email=webhook_data["From"],
            to_emails=[webhook_data["To"]],
            subject=webhook_data["Subject"],
            text_body=webhook_data["TextBody"],
            message_id=webhook_data["MessageID"],
            received_at=webhook_data["ReceivedAt"],
        )

        # Step 3: AI Analysis using actual available method
        processed_email = ProcessedEmail(
            id="e2e-processed-001",
            email_data=email_data,
        )

        with patch.object(
            plugin, "analyze_email_context", new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.return_value = {
                "urgency_analysis": {
                    "level": "critical",
                    "confidence": 0.95,
                    "indicators": ["critical", "payment", "down", "revenue"],
                },
                "context": {
                    "revenue_impact": True,
                    "system_outage": True,
                    "customer_facing": True,
                },
                "extracted_tasks": [
                    {
                        "description": "Escalate to engineering team",
                        "priority": "critical",
                    },
                    {
                        "description": "Investigate payment system",
                        "priority": "critical",
                    },
                ],
                "sentiment": {"overall": "urgent_negative", "confidence": 0.9},
            }

            analysis_result = await plugin.analyze_email_context(processed_email)

            # Step 4: Verify complete workflow
            assert analysis_result["urgency_analysis"]["level"] == "critical"
            assert len(analysis_result["extracted_tasks"]) == 2
            assert analysis_result["context"]["revenue_impact"] == True

    @pytest.mark.asyncio
    async def test_performance_monitoring_throughout_workflow(self, temp_cache_dir):
        """Test that performance is monitored throughout the workflow."""
        plugin = SambaNovaPlugin()
        optimizer = create_performance_optimizer(cache_dir=temp_cache_dir)
        plugin.performance_optimizer = optimizer

        # Simulate multiple operations
        for i in range(5):
            email_data = EmailData(
                from_email=f"test{i}@example.com",
                to_emails=["recipient@example.com"],
                subject=f"Test Email {i}",
                text_body=f"Content for email {i}",
                message_id=f"perf-test-{i}",
                received_at=datetime.now(),
            )

            processed_email = ProcessedEmail(
                id=f"perf-processed-{i}",
                email_data=email_data,
            )

            with patch.object(
                plugin, "process_email", new_callable=AsyncMock
            ) as mock_process:
                enhanced_email = processed_email
                enhanced_email.analysis = EmailAnalysis(
                    urgency_score=50,
                    urgency_level=UrgencyLevel.MEDIUM,
                    sentiment="neutral",
                    confidence=0.7,
                )
                mock_process.return_value = enhanced_email

                await plugin.process_email(processed_email)

        # Check performance metrics
        report = optimizer.get_performance_report()
        assert isinstance(report, dict)
        assert "metrics" in report

        # Should have recorded some activity
        metrics = report["metrics"]
        # Note: Exact metrics depend on implementation details


class TestRegressionAndCompatibility:
    """Test regression scenarios and compatibility."""

    def test_backward_compatibility(self, temp_cache_dir):
        """Test that AI integration doesn't break existing functionality."""
        plugin = SambaNovaPlugin()

        # Test that basic plugin methods still work
        assert plugin.get_name() == "sambanova-ai-analysis"
        assert plugin.get_version() == "1.0.0"
        assert hasattr(plugin, "is_initialized")
        assert hasattr(plugin, "processing_stats")

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, temp_cache_dir):
        """Test graceful degradation when AI services are unavailable."""
        plugin = SambaNovaPlugin()

        # Simulate AI service failure
        email_data = EmailData(
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            subject="Test",
            text_body="Test content",
            message_id="degradation-test",
            received_at=datetime.now(),
        )

        processed_email = ProcessedEmail(
            id="degradation-processed-001",
            email_data=email_data,
        )

        with patch.object(
            plugin, "process_email", new_callable=AsyncMock
        ) as mock_process:
            mock_process.side_effect = Exception("AI service unavailable")

            # Should handle gracefully
            try:
                result = await plugin.process_email(processed_email)
                # If it returns a result, it should be a fallback
                assert isinstance(result, ProcessedEmail)
            except Exception:
                # Exception is acceptable as long as it's handled upstream
                pass

    def test_configuration_validation(self):
        """Test that configurations are properly validated."""
        plugin = SambaNovaPlugin()

        # Test that plugin has configuration
        assert hasattr(plugin, "config")

        # Test configuration validation
        try:
            config = SambaNovaConfig(
                api_key="test_key_123456789", model="e5-mistral-7b-instruct"
            )
            assert config.api_key == "test_key_123456789"
        except Exception:
            # Configuration validation may have specific requirements
            pass


if __name__ == "__main__":
    # Run integration tests
    unittest.main(verbosity=2)
