# Unit Tests Configuration

This directory contains comprehensive unit tests for the Inbox Zen Email Parsing MCP Server.

## Test Structure

- `test_extraction.py` - Email parsing and analysis tests
- `test_models.py` - Data model validation tests
- `test_storage.py` - Storage system tests
- `test_server.py` - MCP server functionality tests
- `test_webhook.py` - Webhook processing tests
- `conftest.py` - Pytest configuration and fixtures

## Running Tests

```bash
# Run all tests with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_extraction.py -v

# Run tests with detailed output
pytest tests/ -v --tb=short

# Run tests and generate coverage report
pytest tests/ --cov=src --cov-report=html
```

## Coverage Target

- **Target:** >85% code coverage
- **Critical components:** 100% coverage required
- **Documentation:** Coverage reports in `htmlcov/` directory
