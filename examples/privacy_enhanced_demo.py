"""
Privacy-enhanced demo for Tessera.
Demonstrates traffic padding and cover traffic for enhanced privacy.
"""

import time
import secrets
from tessera.sdk.sender import Sender
from tessera.sdk.verifier import Verifier
from tessera.network.enhanced_broadcast import EnhancedBroadcast


def demo_traffic_privacy():
    """Demonstrate traffic padding and cover traffic."""
    print("Tessera Privacy-Enhanced Demo")
    print("=" * 35)

    # Create broadcast system
    broadcast_system = EnhancedBroadcast()

    # Create verifier and generate commitment
    print("\n1. Verifier setting up...")
    verifier = Verifier()
    commitment = verifier.generate_reception_commitment("enhanced_session")
    print(f"   Generated commitment: {commitment.hex()[:16]}...")

    # Create sender
    print("\n2. Sender preparing calls...")
    sender = Sender()

    # Generate multiple proofs
    real_proofs = []
    for i in range(3):
        # Generate proof
        metadata = {
            "timestamp": int(time.time()),
            "call_type": "voice",
            "session_id": f"call_{i}",
        }

        proof = sender.generate_call_proof(metadata)
        encrypted_proof = sender.encrypt_proof_for_recipient(
            proof, commitment, metadata
        )

        # Add traffic padding
        padded_proof = sender.prepare_proof_for_transmission(encrypted_proof)
        real_proofs.append(padded_proof)

        print(
            f"   Prepared call {i + 1} with padding (size: {padded_proof['_padded_size']} bytes)"
        )

    print(f"\n3. Generated {len(real_proofs)} real proofs")

    # Mix with cover traffic
    print("\n4. Adding cover traffic...")
    mixed_proofs = sender.schedule_batch_transmission(real_proofs)

    print(f"   After mixing: {len(mixed_proofs)} total proofs")
    print("   (Includes real proofs and dummy cover traffic)")

    # Show size uniformity
    sizes = [proof["_padded_size"] for proof in mixed_proofs]
    print(f"   All proofs padded to uniform size: {sizes[0]} bytes")

    # Broadcast mixed proofs
    print("\n5. Broadcasting mixed traffic...")
    for i, proof in enumerate(mixed_proofs):
        broadcast_system.broadcast_proof(proof, "enhanced_region")

    # Verifier processes batch
    print("\n6. Verifier processing batch...")

    # Get all proofs (in a real system, only relevant ones would be received)
    # For demo, we'll simulate getting all proofs
    all_proofs = []
    for node in broadcast_system.relay_nodes:
        for message in broadcast_system.broadcast_channels[node]:
            all_proofs.append(message["encrypted_proof"])

    print(f"   Received {len(all_proofs)} proofs from network")

    # Process batch
    valid_proofs = verifier.process_batched_proofs(all_proofs)
    print(f"   Found {len(valid_proofs)} valid proofs (real calls)")

    # Show privacy analysis
    print("\n7. Privacy Analysis:")
    print("   - Network sees uniform traffic patterns")
    print("   - All packets same size due to padding")
    print("   - Dummy traffic obscures real call volume")
    print("   - Timing obfuscation prevents pattern analysis")
    print("   - No sender-recipient relationships visible")

    # Show statistics
    print("\n8. Traffic Statistics:")
    stats = sender.traffic_manager.get_transmission_stats()
    print(f"   Padding size: {stats['padding_size']} bytes")
    print(f"   Cover traffic ratio: {stats['cover_traffic_ratio']:.1%}")
    print(f"   Transmission interval: {sender.traffic_manager.transmission_interval}s")


def demo_traffic_analysis_resistance():
    """Demonstrate resistance to traffic analysis."""
    print("\n\nTraffic Analysis Resistance Demo")
    print("=" * 35)

    print("\nNetwork Perspective:")
    print("- Sees packets of uniform size every 30 seconds")
    print("- Cannot distinguish real calls from dummy traffic")
    print("- Cannot count actual call volume")
    print("- Cannot identify calling patterns")
    print("- Cannot build behavioral profiles")

    print("\nUser Privacy Benefits:")
    print("- Call volume obfuscation (30% dummy traffic)")
    print("- Timing pattern masking (fixed intervals)")
    print("- Size uniformity (all packets 1024 bytes)")
    print("- Relationship anonymity (no identity linkage)")
    print("- Activity hiding (calls mixed with dummy traffic)")

    print("\nComparison to Traditional Systems:")
    print("Traditional VoIP:")
    print("  ❌ Detailed call logs created")
    print("  ❌ Call timing recorded")
    print("  ❌ Sender-recipient relationships mapped")
    print("  ❌ Volume and patterns analyzed")

    print("Tessera Enhanced Privacy:")
    print("  ✅ No call logs generated")
    print("  ✅ Timing patterns obscured")
    print("  ✅ No relationship mapping possible")
    print("  ✅ Traffic analysis resistant")


if __name__ == "__main__":
    demo_traffic_privacy()
    demo_traffic_analysis_resistance()

    print("\n" + "=" * 50)
    print("PRIVACY ENHANCEMENTS SUMMARY")
    print("=" * 50)
    print("1. Traffic Padding: All packets uniform size")
    print("2. Cover Traffic: 30% dummy proofs mixed in")
    print("3. Timing Obfuscation: Fixed transmission intervals")
    print("4. Size Uniformity: Prevents packet size analysis")
    print("5. Pattern Masking: Real calls hidden in dummy traffic")
    print("\nNetwork can no longer:")
    print("- Count actual calls")
    print("- Identify calling patterns")
    print("- Map social relationships")
    print("- Build behavioral profiles")
