"""
CallDNS CLI - Unified command-line interface.
Single entry point with multiple modes: node, proof, identity, service.
"""

import argparse
import asyncio
import json
import sys
import time
import base64
import hashlib
import secrets
from typing import List

from ..sdk import Caller, Verifier
from ..sdk.identity_manager import IdentityManager
from ..sdk.commitment_manager import CommitmentManager


def main():
    """Main entry point for the CallDNS CLI."""
    parser = argparse.ArgumentParser(
        prog='calldns',
        description='CallDNS - Zero-knowledge caller verification system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  node       Run a network node (core, org, customer)
  proof      Manage proofs (broadcast, subscribe, fetch)
  identity   Manage your identity and keys
  service    Run the API service

Examples:
  # Start a core node
  calldns node start --type core --id core-1 --port 8100

  # Subscribe to proofs
  calldns proof subscribe --commitment <hex> --node localhost:8100

  # Start API service
  calldns service --port 8000

  # Register identity
  calldns identity register --name "My Name"
        """
    )

    subparsers = parser.add_subparsers(dest='mode', help='Operating mode')

    # Node mode
    node_parser = subparsers.add_parser('node', help='Run a network node')
    node_subparsers = node_parser.add_subparsers(dest='node_command')

    # node start
    start_parser = node_subparsers.add_parser('start', help='Start a node')
    start_parser.add_argument('--type', '-t', required=True,
                              choices=['core', 'org', 'customer'],
                              help='Node type')
    start_parser.add_argument('--id', '-i', required=True, help='Node ID')
    start_parser.add_argument('--port', '-p', type=int, default=8100, help='Port')
    start_parser.add_argument('--host', default='0.0.0.0', help='Host')
    start_parser.add_argument('--data-dir', '-d', help='Data directory')
    start_parser.add_argument('--peer', action='append', default=[],
                              help='Peer (format: id@host:port)')
    start_parser.add_argument('--bootstrap', action='append', default=[],
                              help='Bootstrap node (format: host:port)')
    start_parser.add_argument('--network', default='local',
                              choices=['local', 'testnet', 'mainnet'],
                              help='Network to join')
    start_parser.add_argument('--api-port', type=int, help='HTTP API port')
    start_parser.add_argument('--ws-port', type=int, help='WebSocket push port')
    start_parser.add_argument('--mqtt-host', help='MQTT broker host')
    start_parser.add_argument('--mqtt-port', type=int, default=1883, help='MQTT broker port')
    start_parser.add_argument('--mqtt-user', help='MQTT username')
    start_parser.add_argument('--mqtt-pass', help='MQTT password')
    start_parser.add_argument('--cert', help='TLS certificate file')
    start_parser.add_argument('--key', help='TLS key file')
    start_parser.add_argument('--ca', help='CA certificate for mTLS')

    # node status
    status_parser = node_subparsers.add_parser('status', help='Get node status')
    status_parser.add_argument('--host', default='localhost', help='Node host')
    status_parser.add_argument('--port', '-p', type=int, default=8100, help='Port')

    # node peers
    peers_parser = node_subparsers.add_parser('peers', help='List peers')
    peers_parser.add_argument('--host', default='localhost', help='Node host')
    peers_parser.add_argument('--port', '-p', type=int, default=8100, help='Port')

    # node connect
    connect_parser = node_subparsers.add_parser('connect', help='Connect to peer')
    connect_parser.add_argument('peer', help='Peer (format: id@host:port)')
    connect_parser.add_argument('--host', default='localhost', help='Local node')
    connect_parser.add_argument('--port', '-p', type=int, default=8100, help='Port')

    # Proof mode
    proof_parser = subparsers.add_parser('proof', help='Manage proofs')
    proof_subparsers = proof_parser.add_subparsers(dest='proof_command')

    # proof subscribe
    sub_parser = proof_subparsers.add_parser('subscribe', help='Subscribe')
    sub_parser.add_argument('--commitment', '-c', required=True, help='Commitment (hex)')
    sub_parser.add_argument('--subscriber-id', '-s', help='Subscriber ID')
    sub_parser.add_argument('--org-hints', nargs='*', default=[], help='Org filters')
    sub_parser.add_argument('--time-window', type=int, default=600, help='Time window')
    sub_parser.add_argument('--node', default='localhost:8100', help='Node')

    # proof broadcast
    broadcast_parser = proof_subparsers.add_parser('broadcast', help='Broadcast proof')
    broadcast_parser.add_argument('--bucket', '-b', type=int, required=True, help='Bucket')
    broadcast_parser.add_argument('--fingerprint', '-f', required=True, help='Fingerprint')
    broadcast_parser.add_argument('--ciphertext', required=True, help='Ciphertext')
    broadcast_parser.add_argument('--nonce', help='Nonce')
    broadcast_parser.add_argument('--org-hint', help='Org hint')
    broadcast_parser.add_argument('--decoys', type=int, default=3, help='Decoys')
    broadcast_parser.add_argument('--node', default='localhost:8100', help='Node')

    # proof fetch
    fetch_parser = proof_subparsers.add_parser('fetch', help='Fetch proofs')
    fetch_parser.add_argument('--subscriber-id', '-s', required=True, help='Subscriber')
    fetch_parser.add_argument('--node', default='localhost:8100', help='Node')

    # proof watch
    watch_parser = proof_subparsers.add_parser('watch', help='Watch for proofs')
    watch_parser.add_argument('--subscriber-id', '-s', required=True, help='Subscriber')
    watch_parser.add_argument('--node', default='localhost:8100', help='Node')

    # proof commitment
    commit_parser = proof_subparsers.add_parser('commitment', help='Generate commitment')
    commit_parser.add_argument('input', help='Input value')
    commit_parser.add_argument('--salt', help='Salt')

    # proof generate
    gen_parser = proof_subparsers.add_parser('generate', help='Generate test proof')
    gen_parser.add_argument('--bucket', '-b', type=int, default=0, help='Bucket')
    gen_parser.add_argument('--org-hint', help='Org hint')

    # Identity mode
    id_parser = subparsers.add_parser('identity', help='Manage identity')
    id_subparsers = id_parser.add_subparsers(dest='identity_command')

    # identity register
    reg_parser = id_subparsers.add_parser('register', help='Register identity')
    reg_parser.add_argument('--name', '-n', help='Display name')
    reg_parser.add_argument('--phone', help='Phone number')
    reg_parser.add_argument('--export', '-e', action='store_true', help='Export key')

    # identity show
    id_subparsers.add_parser('show', help='Show identity')

    # identity export
    id_subparsers.add_parser('export', help='Export public key')

    # Service mode
    svc_parser = subparsers.add_parser('service', help='Run API service')
    svc_parser.add_argument('--host', default='0.0.0.0', help='Host')
    svc_parser.add_argument('--port', '-p', type=int, default=8000, help='Port')

    # Parse and dispatch
    args = parser.parse_args()

    if args.mode == 'node':
        handle_node_mode(args)
    elif args.mode == 'proof':
        handle_proof_mode(args)
    elif args.mode == 'identity':
        handle_identity_mode(args)
    elif args.mode == 'service':
        handle_service_mode(args)
    else:
        parser.print_help()


def handle_node_mode(args):
    """Handle node commands."""
    if args.node_command == 'start':
        asyncio.run(node_start(args))
    elif args.node_command == 'status':
        asyncio.run(node_status(args))
    elif args.node_command == 'peers':
        asyncio.run(node_peers(args))
    elif args.node_command == 'connect':
        asyncio.run(node_connect(args))
    else:
        print("Usage: calldns node <start|status|peers|connect>")


async def node_start(args):
    """Start a CallDNS node."""
    import signal
    from ..network.async_node import AsyncDecentralizedNode
    from ..network.decentralized import NodeType
    from ..network.discovery import create_discovery_for_network
    from .transport import NodeTransport

    node_type = NodeType(args.type)
    print(f"Starting CallDNS {args.type} node: {args.id}")
    print(f"  Host: {args.host}:{args.port}")
    print(f"  Network: {args.network}")

    # Create node
    node = AsyncDecentralizedNode(
        node_id=args.id,
        node_type=node_type,
        data_dir=args.data_dir
    )
    await node.initialize()
    print(f"  Data: {node.data_dir}")

    # Create transport (TLS if certs provided)
    if args.cert and args.key:
        from .tls_transport import TLSNodeTransport
        transport = TLSNodeTransport(
            node, args.host, args.port,
            cert_file=args.cert,
            key_file=args.key,
            ca_file=args.ca
        )
    else:
        transport = NodeTransport(node, args.host, args.port)

    node.set_send_handler(transport.send_to_peer)
    await transport.start()

    # Setup discovery
    discovery = create_discovery_for_network(args.id, args.type, args.network)
    discovery.set_callbacks(transport.connect_to_peer, None)

    # Add bootstrap nodes
    for bootstrap in args.bootstrap:
        host, port = bootstrap.rsplit(':', 1)
        discovery.add_seed_node(f"bootstrap-{host}", host, int(port))

    # Connect to explicit peers
    for peer_spec in args.peer:
        try:
            peer_id, peer_addr = peer_spec.split('@')
            peer_host, peer_port = peer_addr.split(':')
            print(f"  Connecting to: {peer_id}@{peer_host}:{peer_port}")
            await transport.connect_to_peer(peer_id, peer_host, int(peer_port))
        except ValueError:
            print(f"  Invalid peer: {peer_spec}")

    # Start discovery
    await discovery.start()

    # Setup push service
    push_service = None
    if args.ws_port or args.mqtt_host:
        from ..network.push import PushService
        push_service = PushService()

        if args.ws_port:
            await push_service.start_websocket(args.host, args.ws_port)
            print(f"  WebSocket push: ws://{args.host}:{args.ws_port}")

        if args.mqtt_host:
            await push_service.start_mqtt(
                args.mqtt_host,
                args.mqtt_port,
                args.mqtt_user,
                args.mqtt_pass
            )
            print(f"  MQTT: {args.mqtt_host}:{args.mqtt_port}")

    # Start embedded API with commitment storage
    api_task = None
    commitment_storage = None
    if args.api_port:
        from ..network.embedded_api import run_embedded_api
        from ..network.commitment_storage import SQLiteCommitmentStorage

        # Initialize commitment storage
        commitment_db = str(node.data_dir / "commitments.db")
        commitment_storage = SQLiteCommitmentStorage(commitment_db)
        await commitment_storage.initialize()
        print(f"  Commitment DB: {commitment_db}")

        api_task = asyncio.create_task(
            run_embedded_api(node, args.host, args.api_port, push_service, commitment_storage)
        )
        print(f"  HTTP API: http://{args.host}:{args.api_port}")

    # Maintenance loop
    compaction_counter = 0
    async def maintenance():
        nonlocal compaction_counter
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await node.run_maintenance()

                # Periodic compaction every hour (12 * 5 min)
                compaction_counter += 1
                if compaction_counter >= 12:
                    compaction_counter = 0
                    await node.storage.vacuum()
            except asyncio.CancelledError:
                break

    maintenance_task = asyncio.create_task(maintenance())

    print(f"\nNode {args.id} running. Ctrl+C to stop.")

    # Wait for shutdown
    shutdown = asyncio.Event()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown.set)

    await shutdown.wait()

    print("\nShutting down...")
    maintenance_task.cancel()
    if api_task:
        api_task.cancel()
    if push_service:
        await push_service.stop()
    if commitment_storage:
        await commitment_storage.close()
    await discovery.stop()
    await transport.stop()
    await node.shutdown()
    print("Stopped.")


async def node_status(args):
    """Get node status."""
    import websockets
    uri = f"ws://{args.host}:{args.port}"

    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"type": "status_request"}))
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("type") == "status_response":
                stats = data.get("stats", {})
                print(f"Node: {stats.get('node_id', 'unknown')}")
                print(f"  Type: {stats.get('node_type')}")
                print(f"  Peers: {stats.get('peers', 0)}")
                print(f"  Subscriptions: {stats.get('subscriptions', 0)}")
                print(f"  Proofs: {stats.get('cached_proofs', 0)}")
                print(f"  Pending: {stats.get('pending_proofs', 0)}")
    except Exception as e:
        print(f"Error: {e}")


async def node_peers(args):
    """List connected peers."""
    import websockets
    uri = f"ws://{args.host}:{args.port}"

    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"type": "peers_request"}))
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("type") == "peers_response":
                peers = data.get("peers", [])
                if not peers:
                    print("No peers")
                else:
                    print(f"Peers ({len(peers)}):")
                    for p in peers:
                        print(f"  {p.get('peer_id')} - {p.get('host')}:{p.get('port')} ({p.get('node_type')})")
    except Exception as e:
        print(f"Error: {e}")


async def node_connect(args):
    """Connect to a peer."""
    import websockets

    try:
        peer_id, peer_addr = args.peer.split('@')
        peer_host, peer_port = peer_addr.split(':')
    except ValueError:
        print(f"Invalid format: {args.peer} (use: id@host:port)")
        return

    uri = f"ws://{args.host}:{args.port}"

    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({
                "type": "connect_request",
                "peer_id": peer_id,
                "peer_host": peer_host,
                "peer_port": int(peer_port)
            }))
            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            data = json.loads(response)

            if data.get("success"):
                print(f"Connected to {peer_id}")
            else:
                print(f"Failed: {data.get('error')}")
    except Exception as e:
        print(f"Error: {e}")


def handle_proof_mode(args):
    """Handle proof commands."""
    if args.proof_command == 'subscribe':
        asyncio.run(proof_subscribe(args))
    elif args.proof_command == 'broadcast':
        asyncio.run(proof_broadcast(args))
    elif args.proof_command == 'fetch':
        asyncio.run(proof_fetch(args))
    elif args.proof_command == 'watch':
        asyncio.run(proof_watch(args))
    elif args.proof_command == 'commitment':
        proof_commitment(args)
    elif args.proof_command == 'generate':
        proof_generate(args)
    else:
        print("Usage: calldns proof <subscribe|broadcast|fetch|watch|commitment|generate>")


async def proof_subscribe(args):
    """Subscribe to proofs."""
    import websockets

    commitment = bytes.fromhex(args.commitment)
    subscriber_id = args.subscriber_id or args.commitment[:16]
    bucket = int.from_bytes(commitment[:2], 'big') % 64

    # Create bloom filter
    bloom = bytearray(128)
    for i in range(3):
        h = hashlib.sha256(commitment + i.to_bytes(1, 'big')).digest()
        idx = int.from_bytes(h[:2], 'big') % 1024
        bloom[idx // 8] |= (1 << (idx % 8))

    subscription = {
        "bucket": bucket,
        "bloom_filter": base64.b64encode(bytes(bloom)).decode(),
        "org_hints": args.org_hints,
        "time_window": args.time_window
    }

    uri = f"ws://{args.node}"
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({
                "type": "subscribe",
                "subscriber_id": subscriber_id,
                "subscription": subscription
            }))
            print(f"Subscribed: {subscriber_id}")
            print(f"  Bucket: {bucket}")
    except Exception as e:
        print(f"Error: {e}")


async def proof_broadcast(args):
    """Broadcast a proof."""
    import websockets

    fingerprint = bytes.fromhex(args.fingerprint)
    ciphertext = bytes.fromhex(args.ciphertext)
    nonce = bytes.fromhex(args.nonce) if args.nonce else secrets.token_bytes(12)

    proof = {
        "bucket": args.bucket,
        "bloom_fingerprint": base64.b64encode(fingerprint).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "timestamp": int(time.time()),
        "org_hint": args.org_hint
    }

    uri = f"ws://{args.node}"
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"type": "proof", "proof": proof}))
            print(f"Broadcast to bucket {args.bucket}")

            # Decoys
            if args.decoys > 0:
                decoy_buckets = []
                while len(decoy_buckets) < args.decoys:
                    b = secrets.randbelow(64)
                    if b != args.bucket and b not in decoy_buckets:
                        decoy_buckets.append(b)

                for db in decoy_buckets:
                    decoy = {
                        "bucket": db,
                        "bloom_fingerprint": base64.b64encode(secrets.token_bytes(8)).decode(),
                        "ciphertext": base64.b64encode(secrets.token_bytes(len(ciphertext))).decode(),
                        "nonce": base64.b64encode(secrets.token_bytes(12)).decode(),
                        "timestamp": int(time.time()),
                        "org_hint": args.org_hint
                    }
                    await ws.send(json.dumps({"type": "proof", "proof": decoy}))
                print(f"Broadcast {args.decoys} decoys")
    except Exception as e:
        print(f"Error: {e}")


async def proof_fetch(args):
    """Fetch pending proofs."""
    import websockets

    uri = f"ws://{args.node}"
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({
                "type": "get_proofs",
                "subscriber_id": args.subscriber_id
            }))
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            proofs = data.get("proofs", [])
            if not proofs:
                print("No proofs")
            else:
                print(f"Proofs ({len(proofs)}):")
                for p in proofs:
                    print(f"  Bucket {p.get('bucket')} - {p.get('org_hint', 'none')}")
    except Exception as e:
        print(f"Error: {e}")


async def proof_watch(args):
    """Watch for proofs."""
    import websockets

    print(f"Watching as {args.subscriber_id}... (Ctrl+C to stop)")
    uri = f"ws://{args.node}"

    try:
        async with websockets.connect(uri) as ws:
            while True:
                await ws.send(json.dumps({
                    "type": "get_proofs",
                    "subscriber_id": args.subscriber_id
                }))
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)

                for p in data.get("proofs", []):
                    ts = time.strftime("%H:%M:%S", time.localtime(p.get("timestamp", 0)))
                    print(f"[{ts}] Bucket {p.get('bucket')} - {p.get('org_hint', 'none')}")

                await asyncio.sleep(2)
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"Error: {e}")


def proof_commitment(args):
    """Generate a commitment."""
    salt = args.salt.encode() if args.salt else secrets.token_bytes(16)
    data = args.input.encode() + salt
    commitment = hashlib.sha256(data).digest()
    bucket = int.from_bytes(commitment[:2], 'big') % 64

    print(f"Input: {args.input}")
    print(f"Salt: {salt.hex()}")
    print(f"Commitment: {commitment.hex()}")
    print(f"Bucket: {bucket}")


def proof_generate(args):
    """Generate a test proof."""
    proof = {
        "bucket": args.bucket,
        "bloom_fingerprint": base64.b64encode(secrets.token_bytes(8)).decode(),
        "ciphertext": base64.b64encode(secrets.token_bytes(128)).decode(),
        "nonce": base64.b64encode(secrets.token_bytes(12)).decode(),
        "timestamp": int(time.time()),
        "org_hint": args.org_hint
    }
    print(json.dumps(proof, indent=2))


def handle_identity_mode(args):
    """Handle identity commands."""
    if args.identity_command == 'register':
        identity_register(args)
    elif args.identity_command == 'show':
        identity_show()
    elif args.identity_command == 'export':
        identity_export()
    else:
        print("Usage: calldns identity <register|show|export>")


def identity_register(args):
    """Register identity."""
    print("Registering identity...")
    identity = IdentityManager()
    pubkey = identity.get_public_key().hex()

    print(f"Public Key: {pubkey[:32]}...")
    if args.export:
        print(f"\nFull: {pubkey}")
    if args.name:
        print(f"Name: {args.name}")


def identity_show():
    """Show identity."""
    identity = IdentityManager()
    pubkey = identity.get_public_key()
    print(f"Public Key: {pubkey.hex()[:32]}...")
    print(f"Length: {len(pubkey)} bytes")


def identity_export():
    """Export public key."""
    identity = IdentityManager()
    print(identity.get_public_key().hex())


def handle_service_mode(args):
    """Run API service."""
    from ..service.api import run
    print(f"Starting API service on {args.host}:{args.port}")
    run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
