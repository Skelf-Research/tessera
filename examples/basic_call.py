"""
Basic call example for Tessera.
Demonstrates the core functionality.
"""

import time
from tessera.sdk.sender import Sender
from tessera.sdk.verifier import Verifier
from tessera.network.broadcast import Broadcast


def main():
    # Create components
    sender = Sender()
    verifier = Verifier()
    broadcast = Broadcast()

    print("Tessera Demo")
    print("=" * 30)

    # Get sender's public key
    sender_public_key = sender.get_public_key()
    print(f"Sender public key: {sender_public_key.hex()[:32]}...")

    # Generate metadata for the delivery
    metadata = {
        "timestamp": int(time.time()),
        "call_type": "voice",
        "session_id": "demo_session",
    }

    # Generate ZK proof
    print("\nGenerating ZK proof...")
    proof = sender.generate_call_proof(metadata)
    print(f"Proof generated with R: {proof['R'][:16].hex()}...")

    # Broadcast the proof
    print("\nBroadcasting proof...")
    broadcast.broadcast_proof(proof, sender_public_key)

    # Verifier receives the broadcast
    print("\nVerifier receiving broadcast...")
    messages = broadcast.get_broadcast_messages()

    for message in messages:
        received_proof = message["proof"]
        received_public_key = bytes.fromhex(message["public_key"])

        # Add the public key to the proof for verification
        received_proof["public_key"] = received_public_key

        # Verify the proof
        print("\nVerifying proof...")
        is_valid = verifier.verify_call_proof(received_proof)

        if is_valid:
            print("✓ Proof verification successful - Delivery is valid")
        else:
            print("✗ Proof verification failed - Delivery is invalid")


if __name__ == "__main__":
    main()
