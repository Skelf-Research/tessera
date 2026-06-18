#!/bin/bash

# Tessera Service Startup Script
# Starts the Tessera web service with proper configuration

set -e

echo "🌐 Starting Tessera Service"
echo "=========================="

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Set default port if not specified
PORT=${PORT:-8000}
HOST=${HOST:-127.0.0.1}

echo "🔧 Configuration:"
echo "   Host: $HOST"
echo "   Port: $PORT"
echo ""

# Check if dependencies are installed
if ! poetry run python -c "import tessera" 2>/dev/null; then
    echo "❌ Tessera not properly installed. Run ./scripts/setup_dev.sh first"
    exit 1
fi

echo "🚀 Starting service..."
echo "📍 Service will be available at: http://$HOST:$PORT"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Start the service
poetry run python -m tessera.service.web --host "$HOST" --port "$PORT"