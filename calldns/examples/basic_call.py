"""
Basic call example for CallDNS.
Demonstrates the core functionality.
"""

import time
from calldns.sdk.caller import Caller
from calldns.sdk.verifier import Verifier
from calldns.network.broadcast import Broadcast


def main():
    # Create components
    caller = Caller()
    verifier = Verifier()
    broadcast = Broadcast()
    
    print("CallDNS Demo")
    print("=" * 30)
    
    # Get caller's public key
    caller_public_key = caller.get_public_key()
    print(f"Caller public key: {caller_public_key.hex()[:32]}...")
    
    # Generate metadata for the call
    metadata = {
        "timestamp": int(time.time()),
        "call_type": "voice",
        "session_id": "demo_session"
    }
    
    # Generate ZK proof
    print("\nGenerating ZK proof...")
    proof = caller.generate_call_proof(metadata)
    print(f"Proof generated with R: {proof['R'][:16].hex()}...")
    
    # Broadcast the proof
    print("\nBroadcasting proof...")
    broadcast.broadcast_proof(proof, caller_public_key)
    
    # Verifier receives the broadcast
    print("\nVerifier receiving broadcast...")
    messages = broadcast.get_broadcast_messages()
    
    for message in messages:
        received_proof = message['proof']
        received_public_key = bytes.fromhex(message['public_key'])
        
        # Verify the proof
        print("\nVerifying proof...")
        is_valid = verifier.verify_call_proof(received_proof, received_public_key)
        
        if is_valid:
            print("✓ Proof verification successful - Call is valid")
        else:
            print("✗ Proof verification failed - Call is invalid")


if __name__ == "__main__":
    main()