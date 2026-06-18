"""
Network broadcast for Tessera.
Handles proof broadcasting mechanism.
"""

import json
from typing import Dict, Any


class Broadcast:
    """Handles proof broadcasting mechanism."""
    
    def __init__(self):
        # In a real implementation, this would connect to a network layer
        self.broadcast_channel = []
    
    def broadcast_proof(self, proof: Dict[str, Any], caller_public_key: bytes):
        """
        Broadcast proof via network layer.
        
        Args:
            proof: The ZK proof to broadcast
            caller_public_key: The sender's public key
        """
        # In a real implementation, this would send over network
        # For now, we'll just store it in memory
        broadcast_message = {
            'proof': proof,
            'public_key': caller_public_key.hex()  # Convert to hex for JSON serialization
        }
        self.broadcast_channel.append(broadcast_message)
        print(f"Broadcasting proof for verification")
    
    def get_broadcast_messages(self):
        """
        Get all broadcast messages.
        
        Returns:
            list: List of broadcast messages
        """
        return self.broadcast_channel[:]
    
    def clear_broadcast_channel(self):
        """Clear the broadcast channel."""
        self.broadcast_channel.clear()