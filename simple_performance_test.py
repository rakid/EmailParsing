#!/usr/bin/env python3
"""
Simple performance test for email extraction only.
"""

import sys
import time
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from extraction import EmailExtractor
from models import EmailData


def main():
    """Run basic performance test."""
    print("📊 Simple Email Processing Performance Test")
    print("=" * 50)
    
    extractor = EmailExtractor()
    
    # Create test email
    email_data = EmailData(
        from_email="urgent@example.com",
        to_emails=["recipient@example.com"],
        subject="URGENT: Critical system failure - immediate action required",
        text_body="This is an urgent message that requires immediate attention. Please respond ASAP as the system is down and customers are affected. We need to fix this today before the deadline.",
        html_body="<p>This is an <strong>urgent</strong> message...</p>",
        message_id="test-urgent-001",
        received_at="2025-05-28T10:30:00Z"
    )
    
    print("🚀 Testing single email processing...")
    
    # Benchmark processing time
    start_time = time.time()
    analysis = extractor.extract_from_email(email_data)
    processing_time = time.time() - start_time
    
    print(f"✅ Results:")
    print(f"   Processing time: {processing_time:.4f}s")
    print(f"   Target: < 2.0s")
    print(f"   Status: {'✅ PASS' if processing_time < 2.0 else '❌ FAIL'}")
    print(f"   Urgency score: {analysis.urgency_score}")
    print(f"   Keywords found: {len(analysis.keywords)}")
    print(f"   Action items: {len(analysis.action_items)}")
    
    # Test batch processing
    print("\n🚀 Testing batch processing (10 emails)...")
    
    start_time = time.time()
    for i in range(10):
        test_email = EmailData(
            from_email=f"test{i}@example.com",
            to_emails=["recipient@example.com"],
            subject=f"Test Email {i}",
            text_body=f"Test content {i}",
            message_id=f"test-{i}",
            received_at="2025-05-28T10:30:00Z"
        )
        analysis = extractor.extract_from_email(test_email)
    
    batch_time = time.time() - start_time
    avg_time = batch_time / 10
    
    print(f"✅ Batch Results:")
    print(f"   Total time for 10 emails: {batch_time:.4f}s")
    print(f"   Average time per email: {avg_time:.4f}s")
    print(f"   Emails per second: {10 / batch_time:.2f}")
    print(f"   Status: {'✅ PASS' if avg_time < 2.0 else '❌ FAIL'}")
    
    if processing_time < 2.0 and avg_time < 2.0:
        print("\n🎯 Overall: ✅ PERFORMANCE TESTS PASSED")
        return 0
    else:
        print("\n🎯 Overall: ❌ PERFORMANCE TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
