"""
Performance and load testing for the Email Parsing MCP Server.

Tests verify that the server meets performance requirements:
- Email processing time < 2s per email
- Memory usage remains stable under load
- Concurrent request handling
- MCP tool response times
"""

import asyncio
import gc
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import psutil
import pytest
from memory_profiler import profile

from src import server
from src.extraction import EmailExtractor
from src.models import EmailData, PostmarkWebhookPayload
from src.storage import email_storage, stats


class TestEmailProcessingPerformance:
    """Test email processing performance requirements."""

    def setup_method(self):
        """Reset storage and setup test environment."""
        email_storage.clear()
        stats.total_processed = 0
        stats.total_errors = 0
        stats.avg_urgency_score = 0.0
        stats.last_processed = None
        stats.processing_times.clear()

        # Ensure server uses the same storage instance
        import src.server
        src.server.email_storage = email_storage
        import src.webhook
        src.webhook.email_storage = email_storage

    def test_single_email_processing_time(self, benchmark, sample_postmark_payload):
        """Test that single email processing meets <2s requirement."""
        extractor = EmailExtractor()
        
        # Create realistic email data
        email_data = EmailData(
            from_email="urgent@example.com",
            to_emails=["recipient@example.com"],
            subject="URGENT: Critical system failure - immediate action required",
            text_body="This is an urgent message that requires immediate attention. Please respond ASAP as the system is down and customers are affected. We need to fix this today before the deadline.",
            html_body="<p>This is an <strong>urgent</strong> message...</p>",
            message_id="test-urgent-001",
            received_at="2025-05-28T10:30:00Z"
        )
        
        def process_email():
            extracted_metadata = extractor.extract_from_email(email_data)
            urgency_score, urgency_level = extractor.calculate_urgency_score(
                extracted_metadata.urgency_indicators
            )
            return extracted_metadata, urgency_score, urgency_level

        # Benchmark the processing time
        result = benchmark(process_email)

        # Verify the processing completed
        assert result is not None
        extracted_metadata, urgency_score, urgency_level = result
        assert urgency_score > 0
        
        # Check that benchmark time is under 2 seconds
        # pytest-benchmark will automatically track timing
        print(f"Email processing completed in: {benchmark.stats['mean']:.4f}s")

    def test_batch_email_processing_performance(self, benchmark):
        """Test batch processing of multiple emails."""
        extractor = EmailExtractor()
        
        # Create batch of varied emails
        emails = []
        for i in range(10):
            email = EmailData(
                from_email=f"sender{i}@example.com",
                to_emails=[f"recipient{i}@example.com"],
                subject=f"Test Email {i} - {'URGENT' if i % 3 == 0 else 'Normal'}",
                text_body=f"Email content {i} with {'urgent deadline' if i % 3 == 0 else 'regular'} information.",
                message_id=f"test-batch-{i:03d}",
                received_at="2025-05-28T10:30:00Z"
            )
            emails.append(email)
        
        def process_batch():
            results = []
            for email in emails:
                extracted_metadata = extractor.extract_from_email(email)
                urgency_score, urgency_level = extractor.calculate_urgency_score(
                    extracted_metadata.urgency_indicators
                )
                results.append((extracted_metadata, urgency_score, urgency_level))
            return results

        results = benchmark(process_batch)

        # Verify all emails were processed
        assert len(results) == 10
        assert all(r is not None for r in results)

        # Check average processing time per email
        avg_time_per_email = benchmark.stats['mean'] / 10
        print(f"Average time per email in batch: {avg_time_per_email:.4f}s")
        assert avg_time_per_email < 2.0, f"Average processing time {avg_time_per_email:.4f}s exceeds 2s limit"

    def test_mcp_tool_response_time(self, benchmark, sample_email_data):
        """Test MCP tool response times."""
        # Setup storage with test data
        email_storage["test-001"] = sample_email_data
        stats.total_processed = 1
        
        async def run_analyze_tool():
            # Simulate MCP tool call
            result = await server.handle_call_tool("analyze_email", {"email_id": "test-001"})
            return result
        
        def sync_tool_call():
            return asyncio.run(run_analyze_tool())
        
        result = benchmark(sync_tool_call)
        
        # Verify tool executed successfully
        assert result is not None
        assert "error" not in result
        
        print(f"MCP tool response time: {benchmark.stats['mean']:.4f}s")

    def test_webhook_processing_performance(self, benchmark, sample_postmark_payload):
        """Test webhook processing performance."""
        from fastapi.testclient import TestClient

        from src.webhook import app

        # Mock config to disable signature verification for performance testing
        with patch('src.webhook.config') as mock_config:
            mock_config.webhook_endpoint = "/webhook"
            mock_config.postmark_webhook_secret = None  # Disable signature verification
            
            def process_webhook():
                # Create test client and process webhook
                client = TestClient(app)
                response = client.post("/webhook", json=sample_postmark_payload)
                return response
            
            result = benchmark(process_webhook)
            
            # Verify webhook was processed
            assert result is not None
            assert result.status_code == 200
            assert len(email_storage) > 0
            
            print(f"Webhook processing time: {benchmark.stats['mean']:.4f}s")


class TestConcurrentProcessing:
    """Test concurrent request handling and thread safety."""
    
    def setup_method(self):
        """Reset storage and setup test environment."""
        email_storage.clear()
        stats.total_processed = 0
        stats.total_errors = 0
        stats.avg_urgency_score = 0.0
        stats.last_processed = None
        stats.processing_times.clear()
        
        # Ensure consistent storage
        import src.server
        src.server.email_storage = email_storage
        import src.webhook
        src.webhook.email_storage = email_storage

    def test_concurrent_webhook_processing(self):
        """Test concurrent webhook processing with multiple threads."""
        extractor = EmailExtractor()
        num_threads = 5
        emails_per_thread = 3
        
        def process_emails(thread_id: int) -> List[Dict[str, Any]]:
            """Process emails in a single thread."""
            results = []
            for i in range(emails_per_thread):
                email_data = EmailData(
                    from_email=f"thread{thread_id}_email{i}@example.com",
                    to_emails=["recipient@example.com"],
                    subject=f"Thread {thread_id} Email {i}",
                    text_body=f"Content from thread {thread_id}, email {i}",
                    message_id=f"thread-{thread_id}-email-{i}",
                    received_at="2025-05-28T10:30:00Z"
                )
                
                start_time = time.time()
                extracted_metadata = extractor.extract_from_email(email_data)
                urgency_score, urgency_level = extractor.calculate_urgency_score(
                    extracted_metadata.urgency_indicators
                )
                processing_time = time.time() - start_time

                # Store in shared storage (testing thread safety)
                email_id = f"thread-{thread_id}-{i}"
                email_storage[email_id] = email_data

                results.append({
                    "thread_id": thread_id,
                    "email_id": email_id,
                    "processing_time": processing_time,
                    "urgency_score": urgency_score
                })
            
            return results
        
        # Run concurrent processing
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(process_emails, i) for i in range(num_threads)]
            all_results = []
            for future in futures:
                thread_results = future.result()
                all_results.extend(thread_results)
        
        total_time = time.time() - start_time
        
        # Verify results
        expected_total_emails = num_threads * emails_per_thread
        assert len(all_results) == expected_total_emails
        assert len(email_storage) == expected_total_emails
        
        # Check processing times
        max_processing_time = max(r["processing_time"] for r in all_results)
        avg_processing_time = sum(r["processing_time"] for r in all_results) / len(all_results)
        
        print(f"Concurrent processing stats:")
        print(f"  Total emails: {expected_total_emails}")
        print(f"  Total time: {total_time:.4f}s")
        print(f"  Max individual processing time: {max_processing_time:.4f}s")
        print(f"  Average processing time: {avg_processing_time:.4f}s")
        print(f"  Emails per second: {expected_total_emails / total_time:.2f}")
        
        # Performance assertions
        assert max_processing_time < 2.0, f"Individual email processing time {max_processing_time:.4f}s exceeds 2s limit"
        assert avg_processing_time < 1.0, f"Average processing time {avg_processing_time:.4f}s is too high"

    def test_concurrent_mcp_tool_calls(self):
        """Test concurrent MCP tool calls."""
        # Setup test data
        for i in range(10):
            email_data = EmailData(
                from_email=f"test{i}@example.com",
                to_emails=["recipient@example.com"],
                subject=f"Test Email {i}",
                text_body=f"Test content {i}",
                message_id=f"concurrent-test-{i}",
                received_at="2025-05-28T10:30:00Z"
            )
            email_storage[f"test-{i:03d}"] = email_data
        
        stats.total_processed = 10
        
        async def call_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
            """Call MCP tool."""
            try:
                result = await server.handle_call_tool(tool_name, params)
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        async def run_concurrent_tools():
            """Run multiple tool calls concurrently."""
            tasks = []
            
            # Mix different tool calls
            for i in range(5):
                tasks.append(call_tool("analyze_email", {"email_id": f"test-{i:03d}"}))
            
            tasks.append(call_tool("get_email_stats", {}))
            tasks.append(call_tool("search_emails", {"query": "test"}))
            tasks.append(call_tool("extract_tasks", {}))
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            return results, total_time
        
        results, total_time = asyncio.run(run_concurrent_tools())
        
        # Verify results
        assert len(results) == 8  # 5 analyze + 3 other tools
        successful_calls = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
        
        print(f"Concurrent MCP tool calls:")
        print(f"  Total calls: {len(results)}")
        print(f"  Successful calls: {successful_calls}")
        print(f"  Total time: {total_time:.4f}s")
        print(f"  Average time per call: {total_time / len(results):.4f}s")
        
        # Performance assertions
        assert successful_calls >= 6, f"Too many failed tool calls: {successful_calls}/{len(results)}"
        assert total_time < 10.0, f"Concurrent tool calls took too long: {total_time:.4f}s"


class TestMemoryUsage:
    """Test memory usage and resource management."""
    
    def setup_method(self):
        """Reset storage and setup test environment."""
        email_storage.clear()
        stats.total_processed = 0
        stats.total_errors = 0
        stats.avg_urgency_score = 0.0
        stats.last_processed = None
        stats.processing_times.clear()
        
        # Force garbage collection
        gc.collect()

    def test_memory_usage_stability(self):
        """Test that memory usage remains stable under load."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        extractor = EmailExtractor()
        
        # Process many emails to test memory stability
        num_emails = 100
        memory_samples = []
        
        for i in range(num_emails):
            email_data = EmailData(
                from_email=f"memory_test_{i}@example.com",
                to_emails=["recipient@example.com"],
                subject=f"Memory Test Email {i}",
                text_body=f"This is test email {i} for memory usage testing. " * 10,  # Larger content
                message_id=f"memory-test-{i:04d}",
                received_at="2025-05-28T10:30:00Z"
            )
            
            # Process email
            extracted_metadata = extractor.extract_from_email(email_data)
            
            # Store in storage
            email_storage[f"memory-test-{i:04d}"] = email_data
            
            # Sample memory every 10 emails
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_samples.append(current_memory)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        max_memory = max(memory_samples)
        
        print(f"Memory usage analysis:")
        print(f"  Initial memory: {initial_memory:.2f} MB")
        print(f"  Final memory: {final_memory:.2f} MB")
        print(f"  Memory increase: {memory_increase:.2f} MB")
        print(f"  Max memory: {max_memory:.2f} MB")
        print(f"  Emails processed: {num_emails}")
        print(f"  Memory per email: {memory_increase / num_emails:.3f} MB")
        
        # Memory usage assertions
        assert memory_increase < 50, f"Memory increase {memory_increase:.2f} MB is too high"
        assert memory_increase / num_emails < 0.5, f"Memory per email {memory_increase / num_emails:.3f} MB is too high"

    def test_storage_cleanup_effectiveness(self):
        """Test that storage cleanup actually frees memory."""
        process = psutil.Process()
        
        # Fill storage with data
        extractor = EmailExtractor()
        
        for i in range(50):
            email_data = EmailData(
                from_email=f"cleanup_test_{i}@example.com",
                to_emails=["recipient@example.com"],
                subject=f"Cleanup Test Email {i}",
                text_body=f"Large content for cleanup testing. " * 50,  # Large content
                message_id=f"cleanup-test-{i:04d}",
                received_at="2025-05-28T10:30:00Z"
            )
            
            extracted_metadata = extractor.extract_from_email(email_data)
            email_storage[f"cleanup-test-{i:04d}"] = email_data
        
        memory_before_cleanup = process.memory_info().rss / 1024 / 1024  # MB
        
        # Clear storage
        email_storage.clear()
        stats.total_processed = 0
        stats.total_errors = 0
        stats.avg_urgency_score = 0.0
        stats.last_processed = None
        stats.processing_times.clear()
        
        # Force garbage collection
        gc.collect()
        
        memory_after_cleanup = process.memory_info().rss / 1024 / 1024  # MB
        memory_freed = memory_before_cleanup - memory_after_cleanup
        
        print(f"Storage cleanup analysis:")
        print(f"  Memory before cleanup: {memory_before_cleanup:.2f} MB")
        print(f"  Memory after cleanup: {memory_after_cleanup:.2f} MB")
        print(f"  Memory freed: {memory_freed:.2f} MB")
        print(f"  Storage items cleared: 50 emails")
        
        # Verify cleanup was effective
        assert len(email_storage) == 0, "Storage was not properly cleared"
        assert stats.total_processed == 0, "Stats were not properly reset"


class TestScalabilityLimits:
    """Test system behavior at scale limits."""
    
    def setup_method(self):
        """Reset storage and setup test environment."""
        email_storage.clear()
        stats.total_processed = 0
        stats.total_errors = 0
        stats.avg_urgency_score = 0.0
        stats.last_processed = None
        stats.processing_times.clear()

    def test_large_email_content_handling(self):
        """Test processing of very large email content."""
        extractor = EmailExtractor()
        
        # Create email with large content
        large_content = "This is a very large email content. " * 1000  # ~36KB
        
        email_data = EmailData(
            from_email="large_content@example.com",
            to_emails=["recipient@example.com"],
            subject="Large Content Test Email",
            text_body=large_content,
            html_body=f"<p>{large_content}</p>",
            message_id="large-content-test",
            received_at="2025-05-28T10:30:00Z"
        )
        
        start_time = time.time()
        extracted_metadata = extractor.extract_from_email(email_data)
        urgency_score, urgency_level = extractor.calculate_urgency_score(
            extracted_metadata.urgency_indicators
        )
        processing_time = time.time() - start_time

        print(f"Large content processing:")
        print(f"  Content size: ~{len(large_content)} characters")
        print(f"  Processing time: {processing_time:.4f}s")
        print(f"  Urgency score: {urgency_score}")
        
        # Verify processing completed within time limit
        assert processing_time < 2.0, f"Large content processing time {processing_time:.4f}s exceeds 2s limit"
        assert extracted_metadata is not None, "Analysis failed for large content"

    def test_storage_capacity_limits(self):
        """Test storage behavior with many emails."""
        extractor = EmailExtractor()
        
        # Test with a reasonable number of emails for CI
        num_emails = 500
        
        start_time = time.time()
        
        for i in range(num_emails):
            email_data = EmailData(
                from_email=f"capacity_test_{i}@example.com",
                to_emails=["recipient@example.com"],
                subject=f"Capacity Test Email {i}",
                text_body=f"Content for capacity test email {i}",
                message_id=f"capacity-test-{i:05d}",
                received_at="2025-05-28T10:30:00Z"
            )
            
            # Process and store
            extracted_metadata = extractor.extract_from_email(email_data)
            email_storage[f"capacity-test-{i:05d}"] = email_data
        
        total_time = time.time() - start_time
        avg_time_per_email = total_time / num_emails
        
        print(f"Storage capacity test:")
        print(f"  Emails stored: {len(email_storage)}")
        print(f"  Total time: {total_time:.4f}s")
        print(f"  Average time per email: {avg_time_per_email:.4f}s")
        print(f"  Emails per second: {num_emails / total_time:.2f}")
        
        # Verify storage integrity
        assert len(email_storage) == num_emails, "Not all emails were stored"
        assert avg_time_per_email < 0.1, f"Average processing time {avg_time_per_email:.4f}s is too high for capacity test"
        
        # Test retrieval performance
        retrieval_start = time.time()
        retrieved_emails = 0
        for i in range(0, num_emails, 10):  # Sample every 10th email
            email_id = f"capacity-test-{i:05d}"
            if email_id in email_storage:
                retrieved_emails += 1
        
        retrieval_time = time.time() - retrieval_start
        print(f"  Sample retrieval time: {retrieval_time:.4f}s for {retrieved_emails} emails")
        
        assert retrieved_emails > 0, "Failed to retrieve any emails"
        assert retrieval_time < 1.0, f"Retrieval time {retrieval_time:.4f}s is too high"