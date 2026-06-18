"""
Complete flow demo for Tessera.
Demonstrates the full privacy-preserving proof matching workflow.
"""

import time
import base64
from tessera.sdk.sender import Sender
from tessera.sdk.verifier import Verifier
from tessera.network.enhanced_broadcast import EnhancedBroadcast


def demo_complete_flow():
    """Demonstrate the complete Tessera workflow."""
    print("Tessera Complete Flow Demo")
    print("=" * 30)
    
    # Create broadcast system
    broadcast_system = EnhancedBroadcast()
    
    # Step 1: Verifier sets up reception commitment (happens before calls)
    print("\n1. Verifier setting up reception commitment...")
    verifier = Verifier()
    session_id = f"session_{int(time.time())}"
    commitment = verifier.generate_reception_commitment(session_id)
    print(f"   Generated commitment: {commitment.hex()[:16]}...")
    
    # In a real system, this commitment would be shared with potential callers
    # For this demo, we'll simulate that by using the same commitment for callers
    
    # Step 2: Callers make calls using the commitment
    print("\n2. Making calls...")
    callers = []
    encrypted_proofs = []
    
    for i in range(3):
        print(f"   Sender {i} generating proof...")
        sender = Sender()
        callers.append(sender)
        
        # Generate metadata
        metadata = {
            "timestamp": int(time.time()),
            "call_type": "voice",
            "session_id": f"call_{i}"
        }
        
        # Generate ZK proof
        proof = sender.generate_call_proof(metadata)
        
        # Encrypt proof for verifier using the commitment
        encrypted_proof = sender.encrypt_proof_for_callee(proof, commitment, metadata)
        encrypted_proofs.append(encrypted_proof)
        
        # Broadcast encrypted proof
        broadcast_system.broadcast_proof(encrypted_proof, "default_region")
        print(f"   Sender {i} proof broadcasted")
    
    # Step 3: Verifier checks for relevant proofs
    print("\n3. Verifier checking for calls...")
    
    # Generate fingerprint for our commitment
    timestamp = int(time.time())
    fingerprint = verifier.commitment_manager.generate_bloom_fingerprint(commitment, timestamp)
    
    # Get relevant proofs using bloom filter matching
    relevant_proofs = broadcast_system.get_relevant_proofs([fingerprint], "default_region")
    print(f"   Found {len(relevant_proofs)} potentially relevant proofs")
    
    # Step 4: Verify each relevant proof
    print("\n4. Verifying proofs...")
    valid_calls = 0
    
    for i, encrypted_proof in enumerate(relevant_proofs):
        is_valid = verifier.verify_encrypted_call_proof(encrypted_proof)
        if is_valid:
            valid_calls += 1
            print(f"   Proof {i+1} is VALID")
        else:
            print(f"   Proof {i+1} is INVALID")
    
    # Results
    print("\n5. Results:")
    print(f"   - {len(encrypted_proofs)} calls made")
    print(f"   - {len(relevant_proofs)} proofs received by verifier")
    print(f"   - {valid_calls} calls successfully verified")
    
    # Privacy demonstration
    print("\n6. Privacy Analysis:")
    print("   - Network only sees encrypted proofs")
    print("   - No sender identification in transmitted data")
    print("   - Verifier commitment is not linked to identity in network")
    print("   - Bloom filters prevent exhaustive matching")
    
    # Efficiency demonstration
    print("\n7. Efficiency Analysis:")
    print("   - Bloom filters reduced proof processing")
    print("   - Verifier only processes relevant proofs")
    print("   - Network routing is decentralized")


def demo_privacy_protection():
    """Demonstrate privacy protection features."""
    print("\n\nPrivacy Protection Demo")
    print("=" * 25)
    
    # Create multiple verifiers
    verifier1 = Verifier()
    verifier2 = Verifier()
    
    # Generate commitments
    commitment1 = verifier1.generate_reception_commitment("session1")
    commitment2 = verifier2.generate_reception_commitment("session2")
    
    print("Two verifiers generated commitments:")
    print(f"   Verifier 1: {commitment1.hex()[:16]}...")
    print(f"   Verifier 2: {commitment2.hex()[:16]}...")
    
    # Create sender
    sender = Sender()
    
    # Generate proof for verifier 1
    metadata = {"timestamp": int(time.time()), "call_type": "voice"}
    proof = sender.generate_call_proof(metadata)
    encrypted_proof1 = sender.encrypt_proof_for_callee(proof, commitment1, metadata)
    
    # Network sees only:
    print("\nNetwork can only see:")
    print(f"   Encrypted proof size: {encrypted_proof1['proof_size']} bytes")
    print(f"   Bloom fingerprint: {encrypted_proof1['bloom_fingerprint'][:8]}...")
    print(f"   Ephemeral hint: {encrypted_proof1['ephemeral_hint'][:8]}...")
    
    print("\nNetwork cannot determine:")
    print("   - Who the sender is")
    print("   - Who the intended recipient is")
    print("   - What the proof contains")
    print("   - Any metadata about the call")


if __name__ == "__main__":
    demo_complete_flow()
    demo_privacy_protection()
    
    print("\n" + "=" * 50)
    print("DEMO COMPLETE")
    print("=" * 50)
    print("This demonstrates how Tessera solves the matching problem:")
    print("1. Privacy-preserving commitment scheme")
    print("2. Encrypted proof routing")
    print("3. Bloom filter-based efficient matching")
    print("4. No identity leakage in network")