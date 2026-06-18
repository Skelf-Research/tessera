"""
Tessera Proof CLI.
Commands for managing proofs, subscriptions, and broadcasts.
"""

import argparse
import asyncio
import json
import base64
import time
import hashlib
import secrets
from typing import List

import websockets


def main():
    """Main entry point for the Tessera proof CLI."""
    parser = argparse.ArgumentParser(
        prog='tessera-proof',
        description='Tessera Proof Management - Broadcast and subscribe to proofs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Subscribe to proofs (customer)
  tessera-proof subscribe --commitment <hex> --node localhost:8100

  # Broadcast a proof (organization)
  tessera-proof broadcast --bucket 42 --fingerprint <hex> --ciphertext <hex> --node localhost:8100

  # Generate a test proof
  tessera-proof generate --bucket 42

  # Fetch pending proofs
  tessera-proof fetch --subscriber-id device-123 --node localhost:8100

  # Watch for proofs in real-time
  tessera-proof watch --subscriber-id device-123 --node localhost:8100
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Subscribe command
    sub_parser = subparsers.add_parser('subscribe', help='Subscribe to proofs')
    sub_parser.add_argument('--commitment', '-c', required=True,
                           help='Commitment hash (hex)')
    sub_parser.add_argument('--subscriber-id', '-s',
                           help='Subscriber ID (default: commitment[:16])')
    sub_parser.add_argument('--org-hints', nargs='*', default=[],
                           help='Organization IDs to filter by')
    sub_parser.add_argument('--time-window', type=int, default=600,
                           help='Time window in seconds (default: 600)')
    sub_parser.add_argument('--node', default='localhost:8100',
                           help='Node address (default: localhost:8100)')

    # Unsubscribe command
    unsub_parser = subparsers.add_parser('unsubscribe', help='Unsubscribe from proofs')
    unsub_parser.add_argument('--subscriber-id', '-s', required=True,
                             help='Subscriber ID')
    unsub_parser.add_argument('--node', default='localhost:8100',
                             help='Node address')

    # Broadcast command
    broadcast_parser = subparsers.add_parser('broadcast', help='Broadcast a proof')
    broadcast_parser.add_argument('--bucket', '-b', type=int, required=True,
                                  help='Target bucket (0-63)')
    broadcast_parser.add_argument('--fingerprint', '-f', required=True,
                                  help='Bloom fingerprint (hex)')
    broadcast_parser.add_argument('--ciphertext', required=True,
                                  help='Encrypted proof data (hex)')
    broadcast_parser.add_argument('--nonce', help='Encryption nonce (hex)')
    broadcast_parser.add_argument('--org-hint', help='Organization hint')
    broadcast_parser.add_argument('--decoys', type=int, default=3,
                                  help='Number of decoy proofs (default: 3)')
    broadcast_parser.add_argument('--node', default='localhost:8100',
                                  help='Node address')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate a test proof')
    gen_parser.add_argument('--bucket', '-b', type=int, default=0,
                           help='Target bucket (default: 0)')
    gen_parser.add_argument('--org-hint', help='Organization hint')
    gen_parser.add_argument('--output', '-o', choices=['json', 'hex'], default='json',
                           help='Output format')

    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch pending proofs')
    fetch_parser.add_argument('--subscriber-id', '-s', required=True,
                             help='Subscriber ID')
    fetch_parser.add_argument('--node', default='localhost:8100',
                             help='Node address')

    # Watch command
    watch_parser = subparsers.add_parser('watch', help='Watch for proofs in real-time')
    watch_parser.add_argument('--subscriber-id', '-s', required=True,
                             help='Subscriber ID')
    watch_parser.add_argument('--node', default='localhost:8100',
                             help='Node address')

    # Commitment command (generate commitment from phone number)
    commit_parser = subparsers.add_parser('commitment', help='Generate a commitment')
    commit_parser.add_argument('input', help='Input value (e.g., phone number)')
    commit_parser.add_argument('--salt', help='Salt value (optional)')

    args = parser.parse_args()

    if args.command == 'subscribe':
        asyncio.run(handle_subscribe(args))
    elif args.command == 'unsubscribe':
        asyncio.run(handle_unsubscribe(args))
    elif args.command == 'broadcast':
        asyncio.run(handle_broadcast(args))
    elif args.command == 'generate':
        handle_generate(args)
    elif args.command == 'fetch':
        asyncio.run(handle_fetch(args))
    elif args.command == 'watch':
        asyncio.run(handle_watch(args))
    elif args.command == 'commitment':
        handle_commitment(args)
    else:
        parser.print_help()


async def handle_subscribe(args):
    """Subscribe to proofs."""
    commitment = bytes.fromhex(args.commitment)
    subscriber_id = args.subscriber_id or args.commitment[:16]

    # Compute bucket from commitment
    bucket = int.from_bytes(commitment[:2], 'big') % 64

    # Create bloom filter
    bloom = create_bloom_filter(commitment, 1024, 3)

    subscription = {
        "bucket": bucket,
        "bloom_filter": base64.b64encode(bloom).decode(),
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

            print(f"Subscribed as: {subscriber_id}")
            print(f"  Bucket: {bucket}")
            print(f"  Org hints: {args.org_hints or 'any'}")
            print(f"  Time window: {args.time_window}s")

    except Exception as e:
        print(f"Failed to subscribe: {e}")


async def handle_unsubscribe(args):
    """Unsubscribe from proofs."""
    uri = f"ws://{args.node}"

    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({
                "type": "unsubscribe",
                "subscriber_id": args.subscriber_id
            }))

            print(f"Unsubscribed: {args.subscriber_id}")

    except Exception as e:
        print(f"Failed to unsubscribe: {e}")


async def handle_broadcast(args):
    """Broadcast a proof."""
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
            # Broadcast real proof
            await ws.send(json.dumps({
                "type": "proof",
                "proof": proof
            }))

            print(f"Broadcast proof to bucket {args.bucket}")

            # Generate decoys
            if args.decoys > 0:
                decoy_buckets = []
                while len(decoy_buckets) < args.decoys:
                    b = secrets.randbelow(64)
                    if b != args.bucket and b not in decoy_buckets:
                        decoy_buckets.append(b)

                for decoy_bucket in decoy_buckets:
                    decoy = {
                        "bucket": decoy_bucket,
                        "bloom_fingerprint": base64.b64encode(secrets.token_bytes(8)).decode(),
                        "ciphertext": base64.b64encode(secrets.token_bytes(len(ciphertext))).decode(),
                        "nonce": base64.b64encode(secrets.token_bytes(12)).decode(),
                        "timestamp": int(time.time()),
                        "org_hint": args.org_hint
                    }
                    await ws.send(json.dumps({
                        "type": "proof",
                        "proof": decoy
                    }))

                print(f"Broadcast {args.decoys} decoy proofs to buckets: {decoy_buckets}")

    except Exception as e:
        print(f"Failed to broadcast: {e}")


def handle_generate(args):
    """Generate a test proof."""
    fingerprint = secrets.token_bytes(8)
    ciphertext = secrets.token_bytes(128)
    nonce = secrets.token_bytes(12)

    proof = {
        "bucket": args.bucket,
        "bloom_fingerprint": base64.b64encode(fingerprint).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "timestamp": int(time.time()),
        "org_hint": args.org_hint
    }

    if args.output == 'json':
        print(json.dumps(proof, indent=2))
    else:
        # Hex output for command line use
        print(f"Bucket: {args.bucket}")
        print(f"Fingerprint: {fingerprint.hex()}")
        print(f"Ciphertext: {ciphertext.hex()}")
        print(f"Nonce: {nonce.hex()}")


async def handle_fetch(args):
    """Fetch pending proofs."""
    uri = f"ws://{args.node}"

    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({
                "type": "get_proofs",
                "subscriber_id": args.subscriber_id
            }))

            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("type") == "proofs":
                proofs = data.get("proofs", [])
                if not proofs:
                    print("No pending proofs")
                else:
                    print(f"Received {len(proofs)} proofs:")
                    for i, proof in enumerate(proofs):
                        print(f"\n  [{i+1}] Bucket: {proof.get('bucket')}")
                        print(f"      Timestamp: {proof.get('timestamp')}")
                        print(f"      Org: {proof.get('org_hint', 'none')}")
            else:
                print(f"Unexpected response: {data}")

    except Exception as e:
        print(f"Failed to fetch proofs: {e}")


async def handle_watch(args):
    """Watch for proofs in real-time."""
    uri = f"ws://{args.node}"

    print(f"Watching for proofs as {args.subscriber_id}...")
    print("Press Ctrl+C to stop")

    try:
        async with websockets.connect(uri) as ws:
            while True:
                # Poll for proofs
                await ws.send(json.dumps({
                    "type": "get_proofs",
                    "subscriber_id": args.subscriber_id
                }))

                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)

                if data.get("type") == "proofs":
                    proofs = data.get("proofs", [])
                    for proof in proofs:
                        timestamp = time.strftime(
                            "%H:%M:%S",
                            time.localtime(proof.get("timestamp", 0))
                        )
                        print(f"[{timestamp}] Proof received - Bucket: {proof.get('bucket')}, "
                              f"Org: {proof.get('org_hint', 'none')}")

                await asyncio.sleep(2)

    except KeyboardInterrupt:
        print("\nStopped watching")
    except Exception as e:
        print(f"Error: {e}")


def handle_commitment(args):
    """Generate a commitment from input."""
    salt = args.salt.encode() if args.salt else secrets.token_bytes(16)
    data = args.input.encode() + salt

    commitment = hashlib.sha256(data).digest()
    bucket = int.from_bytes(commitment[:2], 'big') % 64

    print(f"Input: {args.input}")
    print(f"Salt: {salt.hex()}")
    print(f"Commitment: {commitment.hex()}")
    print(f"Bucket: {bucket}")


def create_bloom_filter(data: bytes, size: int = 1024, num_hashes: int = 3) -> bytes:
    """Create a simple bloom filter."""
    bits = bytearray(size // 8)

    for i in range(num_hashes):
        h = hashlib.sha256(data + i.to_bytes(1, 'big')).digest()
        idx = int.from_bytes(h[:2], 'big') % size
        bits[idx // 8] |= (1 << (idx % 8))

    return bytes(bits)


if __name__ == '__main__':
    main()
