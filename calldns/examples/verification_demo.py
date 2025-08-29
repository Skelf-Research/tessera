"""
Verification demo for CallDNS.
Shows how privacy is preserved in the system.
"""

import time
from calldns.sdk.caller import Caller
from calldns.sdk.verifier import Verifier
from calldns.privacy.privacy_preserver import PrivacyPreserver
from calldns.network.broadcast import Broadcast


def demo_privacy_features():
    """Demonstrate privacy preservation features."""
    print("CallDNS Privacy Demo")
    print("=" * 30)
    
    # Create components
    caller = Caller()
    verifier = Verifier()
    privacy_preserver = PrivacyPreserver()
    broadcast = Broadcast()
    
    # Generate metadata with potentially identifying information
    original_metadata = {
        "caller_id": "1234567890",
        "callee_id": "0987654321",
        "phone_number": "+1234567890",
        "ip_address": "192.168.1.100",
        "device_id": "device-12345",
        "location": "New York, NY",
        "timestamp": int(time.time()),
        "call_type": "voice",
        "session_id": "demo_session"
    }
    
    print("Original metadata (with identifying info):")
    for key, value in original_metadata.items():
        print(f"  {key}: {value}")
    
    # Anonymize metadata
    anonymized_metadata = privacy_preserver.anonymize_metadata(original_metadata)
    print("\nAnonymized metadata (identifying info removed):")
    for key, value in anonymized_metadata.items():
        print(f"  {key}: {value}")
    
    # Generate session ID
    session_id = privacy_preserver.generate_session_id()
    print(f"\nGenerated session ID: {session_id}")
    
    # Obfuscate timestamp
    original_timestamp = original_metadata["timestamp"]
    obfuscated_timestamp = privacy_preserver.obfuscate_timestamp(original_timestamp)
    print(f"\nOriginal timestamp: {original_timestamp}")
    print(f"Obfuscated timestamp: {obfuscated_timestamp}")
    print(f"Difference: {original_timestamp - obfuscated_timestamp} seconds")
    
    # Generate ZK proof with anonymized metadata
    print("\nGenerating ZK proof with anonymized metadata...")
    proof = caller.generate_call_proof(anonymized_metadata)
    print(f"Proof generated successfully")
    
    # Broadcast and verify
    print("\nBroadcasting proof...")
    broadcast.broadcast_proof(proof, caller.get_public_key())
    
    print("\nVerifying proof...")
    messages = broadcast.get_broadcast_messages()
    for message in messages:
        received_proof = message['proof']
        received_public_key = bytes.fromhex(message['public_key'])
        is_valid = verifier.verify_call_proof(received_proof, received_public_key)
        
        if is_valid:
            print("✓ Proof verification successful - Call is valid")
        else:
            print("✗ Proof verification failed - Call is invalid")
    
    print("\nPrivacy Summary:")
    print("- Original identifying information has been removed")
    print("- Timestamps are obfuscated to reduce precision")
    print("- Session IDs are ephemeral and random")
    print("- CallDNS cannot identify originator or receiver")
    print("- Zero-knowledge proofs verify authenticity without revealing sensitive data")


if __name__ == "__main__":
    demo_privacy_features()