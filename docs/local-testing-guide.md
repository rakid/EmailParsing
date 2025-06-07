# 🧪 Local Testing Guide - Inbox Zen MCP Server

> **Complete guide for running tests, debugging, and developing locally with confidence**

## 🚀 Quick Start

### Minimal Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run all tests
pytest tests/ -v

# 3. Run with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

### Verify Everything Works
```bash
# Run the core test suite (should complete in ~30 seconds)
pytest tests/test_server.py tests/test_storage.py tests/test_webhook.py -v
```

---

## 🏗️ Environment Setup

### Prerequisites
- **Python**: 3.12 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: 4GB RAM minimum for full test suite
- **Disk Space**: 500MB for dependencies and test artifacts

### Installation Steps

1. **Clone and Navigate**
   ```bash
   git clone https://github.com/rakid/EmailParsing.git
   cd EmailParsing
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # Activate (Windows)
   venv\Scripts\activate
   
   # Activate (macOS/Linux)
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify Installation**
   ```bash
   python -c "import pytest, src.server, src.webhook; print('✅ All imports successful')"
   ```

### Environment Variables (Optional)

Create `.env` file for advanced testing:
```bash
# Basic configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# SambaNova AI testing (optional)
SAMBANOVA_API_KEY=your_api_key_here
SAMBANOVA_BASE_URL=https://api.sambanova.ai/v1
SAMBANOVA_MODEL=Meta-Llama-3.3-70B-Instruct

# Test configuration
TEST_TEMPERATURE=0.1
TEST_MAX_TOKENS=1000
TEST_TIMEOUT=30
```

---

## 📋 Test Categories

### Core Tests (Always Run These)
```bash
# MCP Server functionality
pytest tests/test_server.py -v
# Expected: ~45 tests, all passing

# Email storage system
pytest tests/test_storage.py -v
# Expected: ~25 tests, all passing

# Webhook processing
pytest tests/test_webhook.py -v
# Expected: ~30 tests, all passing
```

### Feature Tests
```bash
# Email extraction and analysis
pytest tests/test_extraction.py -v

# Data models and validation
pytest tests/test_models.py -v

# Configuration management
pytest tests/test_config.py -v

# API routes
pytest tests/test_api_routes.py -v
```

### Integration Tests
```bash
# Full system integration
pytest tests/test_integration.py -v
# Expected: ~35 tests, 1 may be skipped

# MCP protocol integration
pytest tests/test_mcp_integration.py -v
# Expected: ~15 tests, all passing
```

### Performance Tests
```bash
# Performance and scalability
pytest tests/test_performance.py -v
# Expected: ~20 tests, may take 2-3 minutes

# Memory usage and optimization
pytest tests/test_performance.py::TestMemoryUsage -v
```

---

## 🎯 Development Workflows

### Test-Driven Development (TDD)

1. **Write a failing test**
   ```bash
   # Create or modify test
   pytest tests/test_your_feature.py::test_new_feature -v
   # Should fail initially
   ```

2. **Implement minimal code**
   ```bash
   # Write just enough code to pass
   pytest tests/test_your_feature.py::test_new_feature -v
   ```

3. **Refactor and verify**
   ```bash
   # Run all related tests
   pytest tests/test_your_feature.py -v
   ```

### Feature Development Workflow

1. **Start with unit tests**
   ```bash
   # Test the specific component
   pytest tests/test_server.py::TestToolHandling::test_new_tool -v
   ```

2. **Add integration tests**
   ```bash
   # Test how it works with other components
   pytest tests/test_integration.py::TestNewFeatureIntegration -v
   ```

3. **Verify full system**
   ```bash
   # Run complete test suite
   pytest tests/ -x  # Stop on first failure
   ```

### Bug Fix Workflow

1. **Reproduce the bug**
   ```bash
   # Create a test that demonstrates the issue
   pytest tests/test_bug_reproduction.py -v --tb=long
   ```

2. **Fix and verify**
   ```bash
   # Run the specific test
   pytest tests/test_bug_reproduction.py -v
   
   # Run related tests
   pytest tests/ -k "bug_related_keyword" -v
   ```

3. **Regression testing**
   ```bash
   # Ensure fix doesn't break anything
   pytest tests/ --maxfail=3
   ```

---

## 🔍 Test Execution Patterns

### Running Specific Tests

```bash
# Single test method
pytest tests/test_server.py::TestToolHandling::test_analyze_email_tool -v

# Test class
pytest tests/test_server.py::TestToolHandling -v

# Tests matching pattern
pytest tests/ -k "email_analysis" -v

# Tests with specific marker
pytest tests/ -m "unit" -v
```

### Coverage Analysis

```bash
# Full coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term

# Coverage for specific module
pytest tests/test_server.py --cov=src.server --cov-report=term

# Missing coverage lines
pytest tests/ --cov=src --cov-report=term-missing
```

### Performance Monitoring

```bash
# Test execution time
pytest tests/ --durations=10

# Memory usage during tests
pytest tests/test_performance.py::TestMemoryUsage -v -s

# Benchmark specific functions
pytest tests/test_performance.py -v --benchmark-only
```

---

## 🤖 AI and Integration Testing

### SambaNova AI Testing

**With API Key (Full Testing)**
```bash
# Set environment variable
export SAMBANOVA_API_KEY="your_actual_api_key"

# Run AI-specific tests
pytest tests/test_mcp_integration.py -k "ai_" -v

# Test AI tools integration
pytest tests/test_server.py -k "ai_tools" -v
```

**Without API Key (Mock Testing)**
```bash
# Mock tests (default behavior)
pytest tests/test_mcp_integration.py -v
# All AI calls will be mocked automatically
```

### MCP Protocol Testing

```bash
# Test MCP server functionality
pytest tests/test_server.py::TestServerInitialization -v

# Test MCP tools
pytest tests/test_server.py::TestToolHandling -v

# Test MCP resources
pytest tests/test_server.py::TestResourceHandling -v
```

### Integration Availability Testing

```bash
# Check what integrations are available
python -c "
from src.server import INTEGRATIONS_AVAILABLE, AI_TOOLS_AVAILABLE
print(f'Integrations: {INTEGRATIONS_AVAILABLE}')
print(f'AI Tools: {AI_TOOLS_AVAILABLE}')
"

# Run tests based on availability
pytest tests/test_server.py -v  # Will skip unavailable integrations
```

---

## 🐛 Debugging and Troubleshooting

### Common Test Failures

**1. Import Errors**
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify src directory
pytest tests/test_server.py::TestServerInitialization::test_server_metadata -v
```

**2. Storage Isolation Issues**
```bash
# Run storage-specific debug
python debug_detailed.py

# Test storage isolation
pytest tests/test_storage.py -v -s
```

**3. Async/Await Issues**
```bash
# Check asyncio configuration
pytest tests/test_server.py::TestToolHandling -v --tb=long

# Debug async tool calls
pytest tests/test_server.py::TestToolHandling::test_analyze_email_tool -v -s
```

**4. Mock and Patch Issues**
```bash
# Verbose mock debugging
pytest tests/test_webhook.py -v -s --tb=long

# Check patch targets
pytest tests/test_integration.py -v --tb=short
```

### Debug Scripts

```bash
# Simple integration test
python simple_integration_test.py

# Storage system test
python simple_storage_test.py

# Performance baseline
python simple_performance_test.py

# Detailed debugging
python debug_detailed.py
```

### Log Analysis

```bash
# Create and check logs directory
mkdir -p logs

# Run tests with logging
pytest tests/ -v -s --log-cli-level=DEBUG

# Check test logs
tail -f logs/inbox-zen.log  # If created during tests
```

---

## 📊 Test Data and Fixtures

### Understanding Test Fixtures

**Email Data Fixtures**
```python
# Available in conftest.py
sample_email_data          # Basic email structure
sample_analysis_data       # Email analysis results
sample_postmark_payload    # Webhook payload
edge_case_emails          # Boundary condition emails
```

**Using Fixtures in Tests**
```python
def test_your_feature(sample_email_data, sample_analysis_data):
    # Fixtures are automatically injected
    email = EmailData(**sample_email_data)
    analysis = EmailAnalysis(**sample_analysis_data)
```

### Creating Test Data

```bash
# Generate test email
python -c "
from tests.conftest import sample_email_data
print(sample_email_data())
"

# Create custom test data
python -c "
from src.models import EmailData
from datetime import datetime
email = EmailData(
    message_id='test-123',
    from_email='test@example.com',
    to_emails=['user@test.com'],
    subject='Test Email',
    text_body='Test content',
    received_at=datetime.now()
)
print(email.model_dump_json(indent=2))
"
```

---

## ⚡ Performance and Optimization

### Baseline Performance Testing

```bash
# Quick performance check
python simple_performance_test.py

# Comprehensive performance suite
pytest tests/test_performance.py -v

# Memory usage analysis
pytest tests/test_performance.py::TestMemoryUsage -v -s
```

### Profiling Tests

```bash
# Profile test execution
python -m cProfile -o profile_output.prof -m pytest tests/test_server.py

# Analyze profile
python -c "
import pstats
p = pstats.Stats('profile_output.prof')
p.sort_stats('cumulative').print_stats(20)
"
```

### Memory Testing

```bash
# Install memory profiler if needed
pip install memory-profiler psutil

# Memory usage during tests
pytest tests/test_performance.py::TestMemoryUsage::test_memory_usage_stability -v -s
```

---

## 🔧 Continuous Integration Testing

### Pre-commit Testing

```bash
# Run the same tests as CI
pytest tests/ --cov=src --cov-fail-under=85

# Code quality checks
black --check src/ tests/
isort --check-only src/ tests/
flake8 src/ tests/
```

### Local CI Simulation

```bash
# Full CI test suite
#!/bin/bash
echo "Running local CI simulation..."

# 1. Code quality
echo "1. Code quality checks..."
black --check src/ tests/
isort --check-only src/ tests/
flake8 src/ tests/

# 2. Unit tests
echo "2. Unit tests..."
pytest tests/ --cov=src --cov-fail-under=85 --cov-report=xml

# 3. Integration tests
echo "3. Integration tests..."
pytest tests/test_integration.py -v

# 4. Performance tests
echo "4. Performance tests..."
pytest tests/test_performance.py -v

echo "✅ Local CI simulation complete!"
```

---

## 📖 Best Practices

### Test Organization

1. **Naming Conventions**
   ```
   test_<component>_<functionality>_<scenario>
   test_server_tool_handling_success
   test_storage_email_retrieval_not_found
   ```

2. **Test Structure**
   ```python
   def test_feature_scenario():
       # Arrange
       setup_test_data()
       
       # Act
       result = perform_action()
       
       # Assert
       assert result == expected_outcome
   ```

3. **Fixture Usage**
   ```python
   # Use fixtures for test data
   def test_with_fixtures(sample_email_data, clean_storage):
       pass
   
   # Create temporary resources
   def test_with_temp_data(temp_cache_dir):
       pass
   ```

### Development Practices

1. **Run Tests Frequently**
   ```bash
   # Quick smoke test
   pytest tests/test_server.py::TestServerInitialization -v
   
   # After each change
   pytest tests/test_relevant_module.py -v
   ```

2. **Use Test Markers**
   ```bash
   # Run only unit tests
   pytest tests/ -m "unit" -v
   
   # Skip slow tests during development
   pytest tests/ -m "not slow" -v
   ```

3. **Debugging Workflow**
   ```bash
   # Debug specific test
   pytest tests/test_server.py::test_failing_test -v -s --tb=long --pdb
   ```

---

## 📱 IDE Integration

### VS Code Configuration

Create `.vscode/settings.json`:
```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests/",
        "-v"
    ],
    "python.testing.cwd": "${workspaceFolder}",
    "python.defaultInterpreterPath": "./venv/bin/python"
}
```

### PyCharm Configuration

1. Go to `Run/Debug Configurations`
2. Add new `pytest` configuration
3. Set working directory to project root
4. Add environment variables if needed

---

## 🎯 Test Coverage Goals

### Current Status
- **Overall Coverage**: 90% (exceeds target of 85%)
- **Core Modules**: 95%+ coverage
- **Test Count**: 262 tests passing

### Maintaining Coverage

```bash
# Check coverage
pytest tests/ --cov=src --cov-report=term-missing

# Coverage by module
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in browser

# Coverage threshold enforcement
pytest tests/ --cov=src --cov-fail-under=85
```

---

## 🆘 Getting Help

### Quick Diagnostics

```bash
# Run built-in diagnostics
python -c "
from src import server, webhook, storage, models, extraction
print('✅ All core modules imported successfully')
"

# Test MCP server
python -c "
from src.server import server
print(f'✅ MCP server: {server.name}')
"

# Check test discovery
pytest --collect-only tests/ | grep "collected"
```

### Common Solutions

1. **"No module named 'src'"**
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   pytest tests/ -v
   ```

2. **"Fixture not found"**
   ```bash
   # Check conftest.py is present
   ls tests/conftest.py
   pytest --fixtures tests/
   ```

3. **"Event loop is closed"**
   ```bash
   # Check asyncio marker
   pytest tests/test_server.py -v --tb=short
   ```

### Support Resources

- **Documentation**: `/docs` directory
- **Examples**: `/tests` directory test cases
- **Debug Scripts**: Root directory `.py` files
- **Logs**: `logs/` directory (created during runs)

---

## 🎉 Success Metrics

### Test Execution Benchmarks
- **Full Suite**: ~2-3 minutes
- **Core Tests**: ~30 seconds  
- **Unit Tests Only**: ~15 seconds
- **Integration Tests**: ~45 seconds

### Quality Metrics
- **Coverage**: 90%+ overall
- **Pass Rate**: 100% (262/262 tests)
- **Performance**: <2s average test execution
- **Memory**: <100MB growth during full suite

---

*This guide covers comprehensive local testing for the Inbox Zen MCP Server. For deployment testing, see the [Vercel Deployment Guide](vercel-deployment-guide.md). For troubleshooting, see the [Troubleshooting Guide](troubleshooting-guide.md).*
