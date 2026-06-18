#!/bin/bash

# Start Tessera Node UI
# Usage: ./scripts/start_ui.sh [--build]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
UI_DIR="$PROJECT_ROOT/ui"

cd "$UI_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Check for --build flag
if [ "$1" == "--build" ]; then
    echo "Building for production..."
    npm run build
    echo "Build complete. Files are in ui/dist/"
    echo "Serve with: npm run preview"
else
    echo "Starting development server..."
    echo "UI will be available at http://localhost:3000"
    echo "API proxy configured to http://localhost:8000"
    npm run dev
fi
