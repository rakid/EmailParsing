# Tests Organization for Email Parsing MCP Server

This directory contains a comprehensive test suite organized by functional domains to improve maintainability, execution efficiency, and development workflow.

## 📁 Directory Structure

```
tests/
├── conftest.py                    # Global test configuration and fixtures
├── run_tests.sh                   # Test execution script
├── README.md                      # This documentation
├── core/                          # Core functionality tests
│   ├── __init__.py
│   ├── pytest.ini                # Core-specific pytest configuration
│   ├── test_api_routes.py         # API endpoint tests
│   ├── test_config.py             # Configuration management tests
│   ├── test_extraction.py         # Email extraction logic tests
│   ├── test_logging_system.py     # Logging system tests
│   ├── test_mcp_tools.py          # MCP tools tests
│   ├── test_models.py             # Data model tests
│   ├── test_server.py             # Server functionality tests
│   ├── test_storage.py            # Storage abstraction tests
│   └── test_webhook.py            # Webhook handling tests
├── supabase_integration/          # Supabase-related tests
│   ├── __init__.py
│   ├── pytest.ini                # Supabase-specific pytest configuration
│   ├── test_auth_interface.py     # Authentication interface tests
│   ├── test_database_interface.py # Database operations tests
│   ├── test_integration.py        # Overall Supabase integration tests
│   ├── test_plugin.py             # Supabase plugin tests
│   ├── test_realtime_interface.py # Real-time features tests
│   └── test_user_manager.py       # User management tests
├── integration/                   # System integration tests
│   ├── __init__.py
│   ├── pytest.ini                # Integration-specific pytest configuration
│   ├── test_integration.py        # Component integration tests
│   ├── test_integration_system.py # Full system integration tests
│   ├── test_realtime_tools.py     # Real-time tools integration tests
│   └── test_user_management.py    # User management integration tests
├── performance/                   # Performance and benchmark tests
│   ├── __init__.py
│   ├── pytest.ini                # Performance-specific pytest configuration
│   ├── test_comprehensive_performance.py # Comprehensive performance tests
│   └── test_performance.py        # Standard performance tests
└── deployment/                    # Deployment-related tests
    ├── __init__.py
    ├── pytest.ini                # Deployment-specific pytest configuration
    └── test_vercel_deployment.py  # Vercel deployment tests
```

## 🚀 Running Tests

### Using the Test Runner Script

The easiest way to run tests is using the provided test runner script:

```bash
# Run all tests
./tests/run_tests.sh all

# Run specific module tests
./tests/run_tests.sh core
./tests/run_tests.sh supabase
./tests/run_tests.sh integration
./tests/run_tests.sh performance
./tests/run_tests.sh deployment

# Run tests with coverage
./tests/run_tests.sh supabase --coverage

# Run tests excluding slow tests
./tests/run_tests.sh all --fast

# Run tests with verbose output
./tests/run_tests.sh core --verbose
```

### Using pytest Directly

You can also run tests directly with pytest:

```bash
# Run all tests
pytest tests/

# Run specific module tests
pytest tests/core/
pytest tests/supabase_integration/
pytest tests/integration/
pytest tests/performance/
pytest tests/deployment/

# Run specific test files
pytest tests/supabase_integration/test_database_interface.py

# Run with coverage
pytest tests/supabase_integration/ --cov=src/supabase_integration --cov-report=html

# Run tests by markers
pytest -m "not slow"  # Skip slow tests
pytest -m "supabase"  # Run only Supabase tests
pytest -m "unit"      # Run only unit tests
```

## 🏷️ Test Markers

Tests are organized using pytest markers for flexible execution:

### Core Module Markers
- `unit`: Unit tests
- `api`: API-related tests
- `config`: Configuration tests
- `extraction`: Email extraction tests
- `models`: Data model tests
- `server`: Server functionality tests
- `webhook`: Webhook tests

### Supabase Integration Markers
- `supabase`: Supabase integration tests
- `database`: Database interface tests
- `auth`: Authentication tests
- `realtime`: Real-time feature tests
- `plugin`: Plugin tests
- `user_management`: User management tests
- `integration`: Integration tests

### General Markers
- `slow`: Slow-running tests (excluded with --fast)
- `performance`: Performance tests
- `benchmark`: Benchmark tests
- `integration`: Integration tests
- `system`: System tests
- `deployment`: Deployment tests
- `network`: Tests requiring network access

## 📊 Coverage Analysis

### Module-Specific Coverage

Each module can generate its own coverage report:

```bash
# Generate coverage for Supabase integration only
./tests/run_tests.sh supabase --coverage
# Report saved to htmlcov/supabase/

# Generate coverage for core functionality only
./tests/run_tests.sh core --coverage
# Report saved to htmlcov/core/
```

### Overall Coverage

```bash
# Generate overall coverage report
./tests/run_tests.sh all --coverage
# Report saved to htmlcov/
```

## 🔧 Configuration

### Global Configuration
- `conftest.py`: Global fixtures and test configuration
- Root `pytest.ini`: Overall project test configuration

### Module-Specific Configuration
Each module has its own `pytest.ini` file with:
- Specific test discovery settings
- Module-relevant markers
- Timeout configurations (for performance tests)
- Async mode settings (where needed)

## 📈 Current Coverage Status

Based on recent analysis:

- **Overall Coverage**: 86%
- **Database Interface**: 83% (significantly improved)
- **Core Modules**: 90%+ average
- **Integration Points**: Well covered

### Recent Improvements

- ✅ Fixed all failing database interface tests
- ✅ Added comprehensive coverage for authentication methods
- ✅ Improved real-time subscription testing
- ✅ Enhanced error handling test coverage
- ✅ Added user management test coverage

---

*Last updated: June 2025*
*Test organization version: 2.0*
