#!/usr/bin/env python3
"""
Simple performance test runner to validate email processing performance.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from extraction import EmailExtractor
from models import EmailData
from server import server
from storage import storage


def test_email_processing_performance():
    """Test basic email processing performance."""
    print("🚀 Testing Email Processing Performance...")

    # Reset storage
    storage.email_storage.clear()
    storage.stats.total_processed = 0
    storage.stats.total_errors = 0
    storage.stats.avg_urgency_score = 0.0
    storage.stats.last_processed = None
    storage.stats.processing_times.clear()

    extractor = EmailExtractor()

    # Create test email
    email_data = EmailData(
        from_email="urgent@example.com",
        to_emails=["recipient@example.com"],
        subject="URGENT: Critical system failure - immediate action required",
        text_body="This is an urgent message that requires immediate attention. Please respond ASAP as the system is down and customers are affected. We need to fix this today before the deadline.",
        html_body="<p>This is an <strong>urgent</strong> message...</p>",
        message_id="test-urgent-001",
        received_at="2025-05-28T10:30:00Z",
    )

    # Benchmark processing time
    start_time = time.time()
    analysis = extractor.extract_from_email(email_data)
    processing_time = time.time() - start_time

    print(f"✅ Single email processing time: {processing_time:.4f}s")
    print(f"   Target: < 2.0s | Status: {'PASS' if processing_time < 2.0 else 'FAIL'}")
    print(f"   Urgency score: {analysis.urgency_score}")

    return processing_time < 2.0


def test_batch_processing_performance():
    """Test batch processing performance."""
    print("\n🚀 Testing Batch Processing Performance...")

    extractor = EmailExtractor()
    num_emails = 10

    # Create batch of emails
    emails = []
    for i in range(num_emails):
        email = EmailData(
            from_email=f"sender{i}@example.com",
            to_emails=[f"recipient{i}@example.com"],
            subject=f"Test Email {i} - {'URGENT' if i % 3 == 0 else 'Normal'}",
            text_body=f"Email content {i} with {'urgent deadline' if i % 3 == 0 else 'regular'} information.",
            message_id=f"test-batch-{i:03d}",
            received_at="2025-05-28T10:30:00Z",
        )
        emails.append(email)

    # Process batch
    start_time = time.time()
    results = []
    for email in emails:
        analysis = extractor.extract_from_email(email)
        results.append(analysis)
    total_time = time.time() - start_time

    avg_time_per_email = total_time / num_emails

    print(f"✅ Batch processing results:")
    print(f"   Total emails: {num_emails}")
    print(f"   Total time: {total_time:.4f}s")
    print(f"   Average time per email: {avg_time_per_email:.4f}s")
    print(
        f"   Target: < 2.0s per email | Status: {'PASS' if avg_time_per_email < 2.0 else 'FAIL'}"
    )
    print(f"   Emails per second: {num_emails / total_time:.2f}")

    return avg_time_per_email < 2.0


async def test_mcp_tool_performance():
    """Test MCP tool performance."""
    print("\n🚀 Testing MCP Tool Performance...")

    # Setup test data
    email_data = EmailData(
        from_email="test@example.com",
        to_emails=["recipient@example.com"],
        subject="Test Email for MCP Tools",
        text_body="Test content for MCP tool performance testing.",
        message_id="mcp-test-001",
        received_at="2025-05-28T10:30:00Z",
    )

    storage.email_storage["test-001"] = email_data
    storage.stats.total_processed = 1

    # Test different MCP tools
    tools_to_test = [
        ("analyze_email", {"email_id": "test-001"}),
        ("get_email_stats", {}),
        ("search_emails", {"query": "test"}),
        ("extract_tasks", {}),
    ]

    results = []
    for tool_name, params in tools_to_test:
        start_time = time.time()
        try:
            result = await server.call_tool(tool_name, params)
            tool_time = time.time() - start_time
            success = True
        except Exception as e:
            tool_time = time.time() - start_time
            success = False
            result = str(e)

        results.append(
            {"tool": tool_name, "time": tool_time, "success": success, "result": result}
        )

        print(
            f"   {tool_name}: {tool_time:.4f}s | {'✅ PASS' if success and tool_time < 1.0 else '❌ FAIL'}"
        )

    avg_tool_time = sum(r["time"] for r in results) / len(results)
    successful_tools = sum(1 for r in results if r["success"])

    print(f"✅ MCP tools summary:")
    print(f"   Average response time: {avg_tool_time:.4f}s")
    print(f"   Successful tools: {successful_tools}/{len(results)}")
    print(
        f"   Target: < 1.0s average | Status: {'PASS' if avg_tool_time < 1.0 else 'FAIL'}"
    )

    return avg_tool_time < 1.0 and successful_tools >= len(results) * 0.8


def test_memory_usage():
    """Test memory usage during processing."""
    print("\n🚀 Testing Memory Usage...")

    import psutil

    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    extractor = EmailExtractor()

    # Process multiple emails to test memory
    num_emails = 50
    for i in range(num_emails):
        email_data = EmailData(
            from_email=f"memory_test_{i}@example.com",
            to_emails=["recipient@example.com"],
            subject=f"Memory Test Email {i}",
            text_body=f"This is test email {i} for memory usage testing. " * 10,
            message_id=f"memory-test-{i:04d}",
            received_at="2025-05-28T10:30:00Z",
        )

        analysis = extractor.extract_from_email(email_data)
        storage.email_storage[f"memory-test-{i:04d}"] = email_data

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    print(f"✅ Memory usage results:")
    print(f"   Initial memory: {initial_memory:.2f} MB")
    print(f"   Final memory: {final_memory:.2f} MB")
    print(f"   Memory increase: {memory_increase:.2f} MB")
    print(f"   Emails processed: {num_emails}")
    print(f"   Memory per email: {memory_increase / num_emails:.3f} MB")
    print(
        f"   Target: < 20 MB total | Status: {'PASS' if memory_increase < 20 else 'FAIL'}"
    )

    return memory_increase < 20


def main():
    """Run all performance tests."""
    print("📊 Email Parsing MCP Server - Performance Testing")
    print("=" * 60)

    tests = [
        ("Email Processing Performance", test_email_processing_performance),
        ("Batch Processing Performance", test_batch_processing_performance),
        ("MCP Tool Performance", lambda: asyncio.run(test_mcp_tool_performance())),
        ("Memory Usage", test_memory_usage),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            start_time = time.time()
            success = test_func()
            test_time = time.time() - start_time
            results.append((test_name, success, test_time))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False, 0))

    # Summary
    print("\n" + "=" * 60)
    print("📊 Performance Test Summary")
    print("=" * 60)

    passed_tests = 0
    for test_name, success, test_time in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name} ({test_time:.2f}s)")
        if success:
            passed_tests += 1

    print(f"\n🎯 Overall Result: {passed_tests}/{len(results)} tests passed")

    if passed_tests == len(results):
        print("🚀 All performance tests PASSED! System meets performance requirements.")
        return 0
    else:
        print("⚠️  Some performance tests FAILED. Review results above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
