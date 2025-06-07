#!/usr/bin/env python3
"""
Simple test runner for AI components to validate functionality
"""
import sys
import tempfile
import time
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_intelligent_cache():
    """Test IntelligentCache functionality."""
    print("Testing IntelligentCache...")

    try:
        from ai.performance_optimizer import IntelligentCache

        with tempfile.TemporaryDirectory() as temp_dir:
            cache = IntelligentCache(cache_dir=temp_dir, max_size=100)

            # Test basic operations
            test_data = {"analysis": "test_result", "confidence": 0.95}
            cache.set("test_key", test_data, content="test content")
            retrieved = cache.get("test_key", content="test content")

            assert retrieved == test_data, f"Expected {test_data}, got {retrieved}"
            print("✓ IntelligentCache basic operations work")
            return True

    except Exception as e:
        print(f"✗ IntelligentCache test failed: {e}")
        return False


def test_rate_limiter():
    """Test RateLimiter functionality."""
    print("Testing RateLimiter...")

    try:
        from ai.performance_optimizer import RateLimiter, RateLimitConfig

        config = RateLimitConfig()
        limiter = RateLimiter(config)

        # Test basic functionality
        assert limiter is not None
        assert hasattr(limiter, "config")
        print("✓ RateLimiter initialization works")
        return True

    except Exception as e:
        print(f"✗ RateLimiter test failed: {e}")
        return False


async def test_rate_limiter_async():
    """Test RateLimiter async functionality."""
    print("Testing RateLimiter async operations...")

    try:
        from ai.performance_optimizer import RateLimiter, RateLimitConfig

        config = RateLimitConfig()
        limiter = RateLimiter(config)

        # Test async acquire
        allowed = await limiter.acquire()
        assert isinstance(allowed, bool), f"Expected bool, got {type(allowed)}"
        print("✓ RateLimiter async operations work")
        return True

    except Exception as e:
        print(f"✗ RateLimiter async test failed: {e}")
        return False


def test_batch_processor():
    """Test BatchProcessor functionality."""
    print("Testing BatchProcessor...")

    try:
        from ai.performance_optimizer import BatchProcessor, BatchRequest
        from models import EmailData

        processor = BatchProcessor(batch_size=5, batch_timeout=2.0)

        # Test basic initialization
        assert processor.batch_size == 5
        assert processor.batch_timeout == 2.0
        print("✓ BatchProcessor initialization works")
        return True

    except Exception as e:
        print(f"✗ BatchProcessor test failed: {e}")
        return False


async def test_batch_processor_async():
    """Test BatchProcessor async functionality."""
    print("Testing BatchProcessor async operations...")

    try:
        from ai.performance_optimizer import BatchProcessor, BatchRequest
        from models import EmailData

        processor = BatchProcessor(batch_size=3, batch_timeout=1.0)

        # Create a test request
        from datetime import datetime

        request = BatchRequest(
            id="test_1",
            email_data=EmailData(
                from_email="test@example.com",
                to_emails=["recipient@example.com"],
                subject="Test subject",
                text_body="Test body",
                message_id="test-1",
                received_at=datetime.now(),
            ),
            request_type="test_type",
            parameters={"data": "test_data"},
        )

        # Test adding request
        request_id = await processor.add_request(request)
        assert request_id == "test_1", f"Expected test_1, got {request_id}"
        print("✓ BatchProcessor async operations work")
        return True

    except Exception as e:
        print(f"✗ BatchProcessor async test failed: {e}")
        return False


def test_performance_optimizer():
    """Test PerformanceOptimizer functionality."""
    print("Testing PerformanceOptimizer...")

    try:
        from ai.performance_optimizer import create_performance_optimizer

        with tempfile.TemporaryDirectory() as temp_dir:
            optimizer = create_performance_optimizer(cache_dir=temp_dir)

            # Test basic attributes
            assert optimizer is not None
            assert hasattr(optimizer, "cache")
            assert hasattr(optimizer, "rate_limiter")
            assert hasattr(optimizer, "batch_processor")
            assert hasattr(optimizer, "metrics")

            # Test performance report
            report = optimizer.get_performance_report()
            assert isinstance(report, dict)
            assert "metrics" in report

            print("✓ PerformanceOptimizer works")
            return True

    except Exception as e:
        print(f"✗ PerformanceOptimizer test failed: {e}")
        return False


def test_plugin():
    """Test SambaNovaPlugin functionality."""
    print("Testing SambaNovaPlugin...")

    try:
        from ai.plugin import SambaNovaPlugin

        plugin = SambaNovaPlugin()

        # Test basic attributes
        assert plugin is not None
        assert plugin.get_name() == "sambanova-ai-analysis"
        assert plugin.get_version() == "1.0.0"

        print("✓ SambaNovaPlugin works")
        return True

    except Exception as e:
        print(f"✗ SambaNovaPlugin test failed: {e}")
        return False


def test_config():
    """Test SambaNovaConfig functionality."""
    print("Testing SambaNovaConfig...")

    try:
        from ai.config import SambaNovaConfig

        config = SambaNovaConfig(
            api_key="valid_test_key_123456789",
            model="e5-mistral-7b-instruct",
            max_concurrent_requests=5,
            timeout_seconds=30,
        )

        assert config.api_key == "valid_test_key_123456789"
        assert config.model == "e5-mistral-7b-instruct"

        print("✓ SambaNovaConfig works")
        return True

    except Exception as e:
        print(f"✗ SambaNovaConfig test failed: {e}")
        return False


async def run_async_tests():
    """Run async tests."""
    results = []
    results.append(await test_rate_limiter_async())
    results.append(await test_batch_processor_async())
    return results


def main():
    """Run all tests."""
    print("Running AI Components Validation Tests...")
    print("=" * 50)

    # Run synchronous tests
    sync_results = [
        test_intelligent_cache(),
        test_rate_limiter(),
        test_batch_processor(),
        test_performance_optimizer(),
        test_plugin(),
        test_config(),
    ]

    # Run async tests
    async_results = asyncio.run(run_async_tests())

    # Combine results
    all_results = sync_results + async_results

    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print(f"Total Tests: {len(all_results)}")
    print(f"Passed: {sum(all_results)}")
    print(f"Failed: {len(all_results) - sum(all_results)}")

    if all(all_results):
        print("✅ All AI components are working correctly!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
