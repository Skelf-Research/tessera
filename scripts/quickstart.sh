#!/bin/bash

# CallDNS Quickstart Script
# Demonstrates running a complete CallDNS network locally

set -e

echo "================================"
echo "CallDNS Quickstart"
echo "================================"
echo ""

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Error: Poetry is not installed"
    echo "Install with: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
poetry install --quiet

echo ""
echo "This script will start a CallDNS network with:"
echo "  - 1 Core node (port 8100)"
echo "  - 1 Organization node (port 8101)"
echo ""
echo "Then demonstrate proof broadcasting and subscription."
echo ""

# Create data directory
DATA_DIR="/tmp/calldns_quickstart"
rm -rf "$DATA_DIR"
mkdir -p "$DATA_DIR"

echo "Data directory: $DATA_DIR"
echo ""

# Start core node in background
echo "Starting core node..."
poetry run calldns-node start --type core --id core-1 --port 8100 --data-dir "$DATA_DIR/core1" &
CORE_PID=$!
sleep 2

# Start org node connected to core
echo "Starting organization node..."
poetry run calldns-node start --type org --id acme-bank --port 8101 --data-dir "$DATA_DIR/org1" --peer core-1@localhost:8100 &
ORG_PID=$!
sleep 2

echo ""
echo "================================"
echo "Network is running!"
echo "================================"
echo ""
echo "Core node PID: $CORE_PID (port 8100)"
echo "Org node PID: $ORG_PID (port 8101)"
echo ""
echo "Commands you can run:"
echo ""
echo "  # Check node status"
echo "  poetry run calldns-node status --port 8100"
echo ""
echo "  # Generate a commitment"
echo "  poetry run calldns-proof commitment +1234567890"
echo ""
echo "  # Subscribe to proofs"
echo "  poetry run calldns-proof subscribe --commitment <hex> --node localhost:8100"
echo ""
echo "  # Generate and broadcast a test proof"
echo "  poetry run calldns-proof broadcast --bucket 42 --fingerprint $(head -c 8 /dev/urandom | xxd -p) --ciphertext $(head -c 128 /dev/urandom | xxd -p) --node localhost:8100"
echo ""
echo "  # Watch for proofs"
echo "  poetry run calldns-proof watch --subscriber-id <id> --node localhost:8100"
echo ""
echo "Press Ctrl+C to stop the network"
echo ""

# Wait for interrupt
cleanup() {
    echo ""
    echo "Stopping network..."
    kill $CORE_PID 2>/dev/null || true
    kill $ORG_PID 2>/dev/null || true
    echo "Network stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Keep running
wait
