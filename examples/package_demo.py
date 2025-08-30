"""
Complete example demonstrating CallDNS package usage.
"""

import time
from calldns import Caller, Verifier


def demo_complete_flow():
    """Demonstrate a complete CallDNS flow."""
    print("CallDNS Complete Package Demo")
    print("=" * 30)
    
    # Create caller and verifier
    print("1. Initializing Caller and Verifier...")
    caller = Caller()
    verifier = Verifier()
    
    # Generate a call proof
    print("\n2. Generating call proof...")
    metadata = {
        "timestamp": int(time.time()),
        "purpose": "demo_call",
        "caller": "Alice",
        "recipient": "Bob"
    }
    
    proof = caller.generate_call_proof(metadata)
    print(f"   Generated proof with commitment: {caller.get_public_key().hex()[:16]}...")
    
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
    encrypted_proof = caller.encrypt_proof_for_callee(proof, commitment, metadata)
    padded_proof = caller.prepare_proof_for_transmission(encrypted_proof)
    print(f"   Padded proof size: {padded_proof['proof_size']} bytes")
    
    # Show cover traffic
    batch = caller.schedule_batch_transmission([padded_proof])
    print(f"   Batch with cover traffic: {len(batch)} proofs")
    
    print("\n5. Demo complete!")
    print("   CallDNS successfully demonstrated:")
    print("   - Zero-knowledge proof generation")
    print("   - Cryptographic verification")
    print("   - Privacy-preserving features")
    print("   - Traffic padding and cover traffic")


if __name__ == "__main__":
    demo_complete_flow()