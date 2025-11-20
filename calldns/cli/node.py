"""
CallDNS Node CLI.
Commands for running and managing CallDNS network nodes.
"""

import argparse
import asyncio
import json
import signal
import sys
import os
from pathlib import Path
from typing import Optional

from ..network.async_node import AsyncDecentralizedNode, AsyncPrivacyPreservingBroadcaster
from ..network.decentralized import NodeType
from .transport import NodeTransport


def main():
    """Main entry point for the CallDNS node CLI."""
    parser = argparse.ArgumentParser(
        prog='calldns-node',
        description='CallDNS Node - Run a decentralized network node',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start a core node
  calldns-node start --type core --id core-1 --port 8100

  # Start an organization node
  calldns-node start --type org --id acme-bank --port 8101 --peer core-1@localhost:8100

  # Start a customer node
  calldns-node start --type customer --id device-123 --port 8102 --peer core-1@localhost:8100

  # Check node status
  calldns-node status --port 8100

  # List peers
  calldns-node peers --port 8100
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Start command
    start_parser = subparsers.add_parser('start', help='Start a CallDNS node')
    start_parser.add_argument('--type', '-t', required=True,
                              choices=['core', 'org', 'customer'],
                              help='Node type')
    start_parser.add_argument('--id', '-i', required=True, help='Node identifier')
    start_parser.add_argument('--port', '-p', type=int, default=8100,
                              help='Port to listen on (default: 8100)')
    start_parser.add_argument('--host', default='0.0.0.0',
                              help='Host to bind to (default: 0.0.0.0)')
    start_parser.add_argument('--data-dir', '-d',
                              help='Data directory (default: ./calldns_data/<node_id>)')
    start_parser.add_argument('--peer', action='append', default=[],
                              help='Peer to connect to (format: id@host:port)')
    start_parser.add_argument('--api-port', type=int,
                              help='HTTP API port (optional)')

    # Status command
    status_parser = subparsers.add_parser('status', help='Get node status')
    status_parser.add_argument('--host', default='localhost', help='Node host')
    status_parser.add_argument('--port', '-p', type=int, default=8100, help='Node port')

    # Peers command
    peers_parser = subparsers.add_parser('peers', help='List connected peers')
    peers_parser.add_argument('--host', default='localhost', help='Node host')
    peers_parser.add_argument('--port', '-p', type=int, default=8100, help='Node port')

    # Connect command
    connect_parser = subparsers.add_parser('connect', help='Connect to a peer')
    connect_parser.add_argument('peer', help='Peer to connect to (format: id@host:port)')
    connect_parser.add_argument('--host', default='localhost', help='Local node host')
    connect_parser.add_argument('--port', '-p', type=int, default=8100, help='Local node port')

    args = parser.parse_args()

    if args.command == 'start':
        asyncio.run(handle_start_command(args))
    elif args.command == 'status':
        asyncio.run(handle_status_command(args))
    elif args.command == 'peers':
        asyncio.run(handle_peers_command(args))
    elif args.command == 'connect':
        asyncio.run(handle_connect_command(args))
    else:
        parser.print_help()


async def handle_start_command(args):
    """Start a CallDNS node."""
    node_type = NodeType(args.type)
    node_id = args.id

    print(f"Starting CallDNS {args.type} node: {node_id}")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")

    # Create node
    node = AsyncDecentralizedNode(
        node_id=node_id,
        node_type=node_type,
        data_dir=args.data_dir
    )

    # Initialize storage
    await node.initialize()
    print(f"  Data directory: {node.data_dir}")

    # Create transport layer
    transport = NodeTransport(node, args.host, args.port)

    # Set send handler
    node.set_send_handler(transport.send_to_peer)

    # Start transport
    await transport.start()

    # Connect to initial peers
    for peer_spec in args.peer:
        try:
            peer_id, peer_addr = peer_spec.split('@')
            peer_host, peer_port = peer_addr.split(':')
            peer_port = int(peer_port)

            print(f"  Connecting to peer: {peer_id}@{peer_host}:{peer_port}")
            await transport.connect_to_peer(peer_id, peer_host, peer_port)
        except ValueError:
            print(f"  Invalid peer format: {peer_spec} (expected: id@host:port)")

    # Start API server if requested
    api_task = None
    if args.api_port:
        from .api_server import start_api_server
        api_task = asyncio.create_task(
            start_api_server(node, args.host, args.api_port)
        )
        print(f"  API server: http://{args.host}:{args.api_port}")

    # Start maintenance loop
    maintenance_task = asyncio.create_task(run_maintenance(node))

    print(f"\nNode {node_id} is running. Press Ctrl+C to stop.")

    # Handle shutdown
    shutdown_event = asyncio.Event()

    def signal_handler():
        print("\nShutting down...")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Wait for shutdown
    await shutdown_event.wait()

    # Cleanup
    maintenance_task.cancel()
    if api_task:
        api_task.cancel()

    await transport.stop()
    await node.shutdown()

    print("Node stopped.")


async def run_maintenance(node: AsyncDecentralizedNode):
    """Run periodic maintenance tasks."""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            await node.run_maintenance()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Maintenance error: {e}")


async def handle_status_command(args):
    """Get node status via transport protocol."""
    import websockets

    uri = f"ws://{args.host}:{args.port}"

    try:
        async with websockets.connect(uri) as ws:
            # Send status request
            await ws.send(json.dumps({
                "type": "status_request"
            }))

            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("type") == "status_response":
                stats = data.get("stats", {})
                print(f"Node Status: {stats.get('node_id', 'unknown')}")
                print(f"  Type: {stats.get('node_type', 'unknown')}")
                print(f"  Peers: {stats.get('peers', 0)}")
                print(f"  Subscriptions: {stats.get('subscriptions', 0)}")
                print(f"  Cached proofs: {stats.get('cached_proofs', 0)}")
                print(f"  Pending proofs: {stats.get('pending_proofs', 0)}")
                print(f"  DB size: {stats.get('db_size_bytes', 0)} bytes")

                counters = stats.get('counters', {})
                if counters:
                    print("  Counters:")
                    for key, value in counters.items():
                        print(f"    {key}: {value}")
            else:
                print(f"Unexpected response: {data}")

    except Exception as e:
        print(f"Failed to connect to node: {e}")


async def handle_peers_command(args):
    """List connected peers."""
    import websockets

    uri = f"ws://{args.host}:{args.port}"

    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({
                "type": "peers_request"
            }))

            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("type") == "peers_response":
                peers = data.get("peers", [])
                if not peers:
                    print("No peers connected")
                else:
                    print(f"Connected peers ({len(peers)}):")
                    for peer in peers:
                        print(f"  - {peer.get('peer_id', 'unknown')}")
                        print(f"    Type: {peer.get('node_type', 'unknown')}")
                        print(f"    Address: {peer.get('host', '?')}:{peer.get('port', '?')}")
            else:
                print(f"Unexpected response: {data}")

    except Exception as e:
        print(f"Failed to connect to node: {e}")


async def handle_connect_command(args):
    """Connect to a new peer."""
    import websockets

    try:
        peer_id, peer_addr = args.peer.split('@')
        peer_host, peer_port = peer_addr.split(':')
        peer_port = int(peer_port)
    except ValueError:
        print(f"Invalid peer format: {args.peer} (expected: id@host:port)")
        return

    uri = f"ws://{args.host}:{args.port}"

    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({
                "type": "connect_request",
                "peer_id": peer_id,
                "peer_host": peer_host,
                "peer_port": peer_port
            }))

            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            data = json.loads(response)

            if data.get("type") == "connect_response":
                if data.get("success"):
                    print(f"Connected to peer: {peer_id}@{peer_host}:{peer_port}")
                else:
                    print(f"Failed to connect: {data.get('error', 'unknown error')}")
            else:
                print(f"Unexpected response: {data}")

    except Exception as e:
        print(f"Failed to connect to node: {e}")


if __name__ == '__main__':
    main()
