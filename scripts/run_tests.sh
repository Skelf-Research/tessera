#!/bin/bash

# CallDNS Test Runner Script
# Runs the complete test suite with coverage reporting

set -e

echo "🧪 Running CallDNS Test Suite"
echo "=============================="

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Run tests with coverage
echo "Running tests with coverage..."
poetry run pytest tests/ -v --cov=calldns --cov-report=html --cov-report=term

echo ""
echo "✅ Tests completed successfully!"
echo ""
echo "📊 Coverage report generated in htmlcov/"
echo "🔗 Open htmlcov/index.html in your browser to view detailed coverage"