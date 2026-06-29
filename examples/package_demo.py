"""
Complete example demonstrating Tessera package usage.
"""

import time
from tessera import Sender, Verifier


def demo_complete_flow():
    """Demonstrate a complete Tessera flow."""
    print("Tessera Complete Package Demo")
    print("=" * 30)

    # Create sender and verifier
    print("1. Initializing Sender and Verifier...")
    sender = Sender()
    verifier = Verifier()

    # Generate a call proof
    print("\n2. Generating call proof...")
    metadata = {
        "timestamp": int(time.time()),
        "purpose": "demo_call",
        "sender": "Alice",
        "recipient": "Bob",
    }

    proof = sender.generate_call_proof(metadata)
    print(
        f"   Generated proof with commitment: {sender.get_public_key().hex()[:16]}..."
    )

    # Verify the proof
    print("\n3. Verifying call proof...")
    is_valid = verifier.verify_call_proof(proof)
    print(f"   Proof verification: {'VALID' if is_valid else 'INVALID'}")

    # Demonstrate privacy features
    print("\n4. Demonstrating privacy features...")

    # Generate reception commitment
    commitment = verifier.generate_reception_commitment("demo_session")
    print(f"   Generated reception commitment: {commitment.hex()[:16]}...")

    # Show traffic padding
    encrypted_proof = sender.encrypt_proof_for_recipient(proof, commitment, metadata)
    padded_proof = sender.prepare_proof_for_transmission(encrypted_proof)
    print(f"   Padded proof size: {padded_proof['proof_size']} bytes")

    # Show cover traffic
    batch = sender.schedule_batch_transmission([padded_proof])
    print(f"   Batch with cover traffic: {len(batch)} proofs")

    print("\n5. Demo complete!")
    print("   Tessera successfully demonstrated:")
    print("   - Zero-knowledge proof generation")
    print("   - Cryptographic verification")
    print("   - Privacy-preserving features")
    print("   - Traffic padding and cover traffic")


if __name__ == "__main__":
    demo_complete_flow()
