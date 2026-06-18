#!/bin/bash

# Tessera Development Setup Script
# Sets up the development environment

set -e

echo "🚀 Setting up Tessera Development Environment"
echo "============================================="

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed. Please install Poetry first:"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

echo "📦 Installing dependencies with Poetry..."
poetry install

echo "🔧 Setting up pre-commit hooks..."
poetry run pre-commit install 2>/dev/null || echo "ℹ️  Pre-commit not configured (optional)"

echo "🧪 Running initial test suite to verify installation..."
poetry run pytest tests/ -x

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "   • Run tests: ./scripts/run_tests.sh"
echo "   • Start service: poetry run tessera-service"
echo "   • View docs: open docs/README.md"