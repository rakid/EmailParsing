#!/bin/bash

# Test runner scripts for organized test execution
# Usage: ./run_tests.sh [module] [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to run tests for a specific module
run_module_tests() {
    local module=$1
    local options=$2
    
    print_info "Running $module tests..."
    
    case $module in
        "core")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/core/ --asyncio-mode=auto $options"
            ;;
        "supabase")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/supabase_integration/ --asyncio-mode=auto $options"
            ;;
        "integration")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/integration/ --asyncio-mode=auto $options"
            ;;
        "performance")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/performance/ --asyncio-mode=auto $options"
            ;;
        "deployment")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/deployment/ --asyncio-mode=auto $options"
            ;;
        "all")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/ --asyncio-mode=auto $options"
            ;;
        *)
            print_error "Unknown module: $module"
            print_info "Available modules: core, supabase, integration, performance, deployment, all"
            exit 1
            ;;
    esac
}

# Function to run tests with coverage
run_with_coverage() {
    local module=$1
    local options=$2
    
    print_info "Running $module tests with coverage..."
    
    case $module in
        "core")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/core/ --cov=src --cov-report=term-missing --cov-report=html:htmlcov/core --asyncio-mode=auto $options"
            ;;
        "supabase")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/supabase_integration/ --cov=src/supabase_integration --cov-report=term-missing --cov-report=html:htmlcov/supabase --asyncio-mode=auto $options"
            ;;
        "integration")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/integration/ --cov=src --cov-report=term-missing --cov-report=html:htmlcov/integration --asyncio-mode=auto $options"
            ;;
        "performance")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/performance/ --cov=src --cov-report=term-missing --cov-report=html:htmlcov/performance --asyncio-mode=auto $options"
            ;;
        "deployment")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/deployment/ --cov=src --cov-report=term-missing --cov-report=html:htmlcov/deployment --asyncio-mode=auto $options"
            ;;
        "all")
            cd "$PROJECT_ROOT"
            eval "python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --asyncio-mode=auto $options"
            ;;
        *)
            print_error "Unknown module: $module"
            exit 1
            ;;
    esac
}

# Function to show help
show_help() {
    echo "Test Runner for Email Parsing MCP Server"
    echo ""
    echo "Usage: $0 [MODULE] [OPTIONS]"
    echo ""
    echo "Modules:"
    echo "  core         - Run core functionality tests"
    echo "  supabase     - Run Supabase integration tests"
    echo "  integration  - Run integration and system tests"
    echo "  performance  - Run performance tests"
    echo "  deployment   - Run deployment tests"
    echo "  all          - Run all tests"
    echo ""
    echo "Options:"
    echo "  --coverage   - Run with coverage analysis"
    echo "  --fast       - Skip slow tests"
    echo "  --verbose    - Verbose output"
    echo "  --help       - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 core --verbose"
    echo "  $0 supabase --coverage"
    echo "  $0 all --fast"
}

# Main script logic
MODULE=""
COVERAGE=false
OTHER_OPTIONS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        --fast)
            OTHER_OPTIONS="$OTHER_OPTIONS -m \"not slow\""
            shift
            ;;
        --verbose)
            OTHER_OPTIONS="$OTHER_OPTIONS -v"
            shift
            ;;
        core|supabase|integration|performance|deployment|all)
            MODULE=$1
            shift
            ;;
        *)
            OTHER_OPTIONS="$OTHER_OPTIONS $1"
            shift
            ;;
    esac
done

# Default to all tests if no module specified
if [[ -z "$MODULE" ]]; then
    MODULE="all"
fi

# Run tests
print_info "Starting test execution for module: $MODULE"

if [[ "$COVERAGE" == "true" ]]; then
    run_with_coverage "$MODULE" "$OTHER_OPTIONS"
else
    run_module_tests "$MODULE" "$OTHER_OPTIONS"
fi

print_success "Test execution completed!"
