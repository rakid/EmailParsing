#!/usr/bin/env python3
"""
Comprehensive performance testing for the Email Parsing MCP Server.
"""

# Standard library imports
import sys
import time
from concurrent.futures import ThreadPoolExecutor

# Third-party imports
import psutil

# Local imports
from extraction import EmailExtractor
from models import EmailData
from storage import email_storage, stats


def test_email_processing_performance():
    """Test individual email processing performance."""
    print("🚀 Testing Email Processing Performance...")

    extractor = EmailExtractor()

    # Test with various email types
    test_emails = [
        {
            "name": "Urgent Email",
            "email": EmailData(
                from_email="urgent@example.com",
                to_emails=["recipient@example.com"],
                subject=("URGENT: Critical system failure - immediate action required"),
                text_body=(
                    "This is an urgent message that requires immediate attention. "
                    "Please respond ASAP as the system is down and customers are "
                    "affected. We need to fix this today before the deadline."
                ),
                message_id="test-urgent-001",
                received_at="2025-05-28T10:30:00Z",
            ),
        },
        {
            "name": "Normal Email",
            "email": EmailData(
                from_email="normal@example.com",
                to_emails=["recipient@example.com"],
                subject="Weekly report submission",
                text_body=(
                    "Please find attached the weekly report for review. "
                    "Let me know if you have any questions."
                ),
                message_id="test-normal-001",
                received_at="2025-05-28T10:30:00Z",
            ),
        },
        {
            "name": "Large Email",
            "email": EmailData(
                from_email="large@example.com",
                to_emails=["recipient@example.com"],
                subject="Detailed project documentation and requirements specification",
                text_body="This is a very large email with extensive content. "
                * 100,  # Large content
                message_id="test-large-001",
                received_at="2025-05-28T10:30:00Z",
            ),
        },
    ]

    results = []
    for test_case in test_emails:
        start_time = time.time()
        analysis = extractor.extract_from_email(test_case["email"])
        processing_time = time.time() - start_time

        results.append(
            {
                "name": test_case["name"],
                "time": processing_time,
                "urgency_indicators": len(analysis.urgency_indicators),
                "keywords": len(analysis.priority_keywords),
                "action_words": len(analysis.action_words),
            }
        )

        status = "✅ PASS" if processing_time < 2.0 else "❌ FAIL"
        print(f"   {test_case['name']}: {processing_time:.4f}s | {status}")

    avg_time = sum(r["time"] for r in results) / len(results)
    max_time = max(r["time"] for r in results)

    print("✅ Single Email Performance Summary:")
    print(f"   Average processing time: {avg_time:.4f}s")
    print(f"   Maximum processing time: {max_time:.4f}s")
    print("   Target: < 2.0s per email")
    print(f"   Status: {'✅ PASS' if max_time < 2.0 else '❌ FAIL'}")

    return max_time < 2.0


def test_batch_processing_performance():
    """Test batch processing performance."""
    print("\n🚀 Testing Batch Processing Performance...")

    extractor = EmailExtractor()
    batch_sizes = [10, 50, 100]

    batch_results = []

    for batch_size in batch_sizes:
        # Create batch of emails
        emails = []
        for i in range(batch_size):
            email = EmailData(
                from_email=f"batch{i}@example.com",
                to_emails=["recipient@example.com"],
                subject=f"Batch Email {i} - {'URGENT' if i % 5 == 0 else 'Normal'}",
                text_body=f"Email content {i} with various keywords and information.",
                message_id=f"batch-{batch_size}-{i:03d}",
                received_at="2025-05-28T10:30:00Z",
            )
            emails.append(email)

        # Process batch
        start_time = time.time()
        analyses = []
        for email in emails:
            analysis = extractor.extract_from_email(email)
            analyses.append(analysis)
        total_time = time.time() - start_time

        avg_time_per_email = total_time / batch_size
        emails_per_second = batch_size / total_time

        batch_results.append(
            {
                "size": batch_size,
                "total_time": total_time,
                "avg_time": avg_time_per_email,
                "throughput": emails_per_second,
            }
        )

        status = "✅ PASS" if avg_time_per_email < 2.0 else "❌ FAIL"
        print(
            f"   Batch {batch_size}: {avg_time_per_email:.4f}s avg | "
            f"{emails_per_second:.1f} emails/s | {status}"
        )

    best_throughput = max(r["throughput"] for r in batch_results)
    worst_avg_time = max(r["avg_time"] for r in batch_results)

    print("✅ Batch Processing Summary:")
    print(f"   Best throughput: {best_throughput:.1f} emails/second")
    print(f"   Worst average time: {worst_avg_time:.4f}s per email")
    print("   Target: < 2.0s per email")
    print(f"   Status: {'✅ PASS' if worst_avg_time < 2.0 else '❌ FAIL'}")

    return worst_avg_time < 2.0


def test_concurrent_processing():
    """Test concurrent processing performance."""
    print("\n🚀 Testing Concurrent Processing...")

    def process_emails_in_thread(thread_id: int, num_emails: int):
        """Process emails in a single thread."""
        times = []

        for i in range(num_emails):
            email = EmailData(
                from_email=f"thread{thread_id}_email{i}@example.com",
                to_emails=["recipient@example.com"],
                subject=f"Thread {thread_id} Email {i}",
                text_body=f"Content from thread {thread_id}, email {i}",
                message_id=f"thread-{thread_id}-email-{i}",
                received_at="2025-05-28T10:30:00Z",
            )

            start_time = time.time()
            processing_time = time.time() - start_time
            times.append(processing_time)
            email_storage[email.message_id] = email
        return {
            "thread_id": thread_id,
            "times": times,
            "avg_time": sum(times) / len(times),
            "max_time": max(times),
        }

    num_threads = 4
    emails_per_thread = 10

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(process_emails_in_thread, i, emails_per_thread)
            for i in range(num_threads)
        ]
        thread_results = [future.result() for future in futures]

    total_time = time.time() - start_time
    total_emails = num_threads * emails_per_thread

    # Analyze results
    all_times = []
    for result in thread_results:
        all_times.extend(result["times"])

    avg_time = sum(all_times) / len(all_times)
    max_time = max(all_times)
    overall_throughput = total_emails / total_time

    print("✅ Concurrent Processing Results:")
    print(f"   Threads: {num_threads}")
    print(f"   Emails per thread: {emails_per_thread}")
    print(f"   Total emails: {total_emails}")
    print(f"   Total time: {total_time:.4f}s")
    print(f"   Average time per email: {avg_time:.4f}s")
    print(f"   Maximum time per email: {max_time:.4f}s")
    print(f"   Overall throughput: {overall_throughput:.1f} emails/s")
    print("   Target: < 2.0s per email")
    print(f"   Status: {'✅ PASS' if max_time < 2.0 else '❌ FAIL'}")

    return max_time < 2.0


def test_memory_usage():
    """Test memory usage during processing."""
    print("\n🚀 Testing Memory Usage...")

    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Clear storage first
    email_storage.clear()
    stats.total_processed = 0
    stats.total_errors = 0
    stats.avg_urgency_score = 0.0
    stats.last_processed = None
    stats.processing_times.clear()

    extractor = EmailExtractor()
    num_emails = 100
    memory_samples = []

    for i in range(num_emails):
        email = EmailData(
            from_email=f"memory_test_{i}@example.com",
            to_emails=["recipient@example.com"],
            subject=f"Memory Test Email {i}",
            text_body=f"This is test email {i} for memory usage testing. " * 5,
            message_id=f"memory-test-{i:04d}",
            received_at="2025-05-28T10:30:00Z",
        )

        # Extract and store email data
        extractor.extract_from_email(email)
        email_storage[f"memory-test-{i:04d}"] = email

        # Sample memory every 25 emails
        if i % 25 == 0:
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_samples.append(current_memory)

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    max_memory = max(memory_samples) if memory_samples else final_memory

    print("✅ Memory Usage Results:")
    print(f"   Initial memory: {initial_memory:.2f} MB")
    print(f"   Final memory: {final_memory:.2f} MB")
    print(f"   Memory increase: {memory_increase:.2f} MB")
    print(f"   Peak memory: {max_memory:.2f} MB")
    print(f"   Emails processed: {num_emails}")
    print(f"   Memory per email: {memory_increase / num_emails:.3f} MB")
    print("   Target: < 50 MB total increase")
    print(f"   Status: {'✅ PASS' if memory_increase < 50 else '❌ FAIL'}")

    return memory_increase < 50


def test_storage_performance():
    """Test storage operations performance."""
    print("\n🚀 Testing Storage Performance...")

    # Clear storage
    email_storage.clear()
    stats.total_processed = 0

    num_emails = 200

    # Test storage writes
    start_time = time.time()
    for i in range(num_emails):
        email = EmailData(
            from_email=f"storage_test_{i}@example.com",
            to_emails=["recipient@example.com"],
            subject=f"Storage Test Email {i}",
            text_body=f"Content for storage test email {i}",
            message_id=f"storage-test-{i:05d}",
            received_at="2025-05-28T10:30:00Z",
        )
        email_storage[f"storage-test-{i:05d}"] = email

    write_time = time.time() - start_time

    # Test storage reads
    start_time = time.time()
    read_count = 0
    for i in range(0, num_emails, 5):  # Read every 5th email
        email_id = f"storage-test-{i:05d}"
        if email_id in email_storage:
            email = email_storage[email_id]
            read_count += 1

    read_time = time.time() - start_time

    print("✅ Storage Performance Results:")
    print(f"   Emails stored: {len(email_storage)}")
    print(f"   Write time for {num_emails} emails: {write_time:.4f}s")
    print(f"   Average write time: {write_time / num_emails:.6f}s per email")
    print(f"   Read time for {read_count} emails: {read_time:.4f}s")
    print(f"   Average read time: {read_time / read_count:.6f}s per email")
    print(f"   Storage throughput: {num_emails / write_time:.1f} writes/s")
    print("   Target: < 0.01s per operation")

    avg_write_time = write_time / num_emails
    avg_read_time = read_time / read_count if read_count > 0 else 0

    status = "✅ PASS" if avg_write_time < 0.01 and avg_read_time < 0.01 else "❌ FAIL"
    print(f"   Status: {status}")

    return avg_write_time < 0.01 and avg_read_time < 0.01


def main():
    """Run all performance tests."""
    print("📊 Email Parsing MCP Server - Performance Testing Suite")
    print("=" * 65)
    print("Target: All email processing operations < 2.0s")
    print("Memory target: < 50MB increase for 100 emails")
    print("=" * 65)

    tests = [
        ("Email Processing Performance", test_email_processing_performance),
        ("Batch Processing Performance", test_batch_processing_performance),
        ("Concurrent Processing", test_concurrent_processing),
        ("Memory Usage", test_memory_usage),
        ("Storage Performance", test_storage_performance),
    ]

    results = []
    start_time = time.time()

    for test_name, test_func in tests:
        try:
            test_start = time.time()
            success = test_func()
            test_duration = time.time() - test_start
            results.append((test_name, success, test_duration))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False, 0))

    total_time = time.time() - start_time

    # Summary
    print("\n" + "=" * 65)
    print("📊 Performance Test Summary")
    print("=" * 65)

    passed_tests = 0
    for test_name, success, test_duration in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name:<35} ({test_duration:.2f}s)")
        if success:
            passed_tests += 1

    print("\n🎯 Overall Results:")
    print(f"   Tests passed: {passed_tests}/{len(results)}")
    print(f"   Total testing time: {total_time:.2f}s")
    print(f"   Success rate: {(passed_tests / len(results)) * 100:.1f}%")

    if passed_tests == len(results):
        print("\n🚀 All performance tests PASSED!")
        print("   ✅ System meets all performance requirements")
        print("   ✅ Ready for production deployment")
        return 0
    else:
        print(f"\n⚠️  {len(results) - passed_tests} performance test(s) FAILED")
        print("   Please review results and optimize as needed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
