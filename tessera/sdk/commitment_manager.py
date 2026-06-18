"""
Commitment manager for Tessera.
Handles cryptographic commitments for privacy-preserving proof routing.
"""

import hashlib
import secrets
from typing import Dict, Tuple, Optional


class CommitmentManager:
    """Manages cryptographic commitments for privacy-preserving routing."""
    
    def __init__(self):
        # Store local commitment mappings
        # In a real implementation, this would be encrypted and persisted securely
        self.commitments: Dict[bytes, Dict] = {}
    
    def generate_reception_commitment(self, callee_public_key: bytes, session_id: str) -> bytes:
        """
        Generate a reception commitment for a callee.
        
        Args:
            callee_public_key: The callee's public key
            session_id: Unique session identifier
            
        Returns:
            bytes: The reception commitment
        """
        # Generate ephemeral key for this commitment
        ephemeral_key = secrets.token_bytes(32)
        
        # Create commitment: H(callee_public_key || ephemeral_key || session_id)
        commitment_data = callee_public_key + ephemeral_key + session_id.encode('utf-8')
        commitment = hashlib.sha256(commitment_data).digest()
        
        # Store locally
        self.commitments[commitment] = {
            'ephemeral_key': ephemeral_key,
            'session_id': session_id,
            'created_at': __import__('time').time()
        }
        
        return commitment
    
    def derive_routing_key(self, commitment: bytes, ephemeral_hint: bytes) -> bytes:
        """
        Derive a routing key from a commitment and ephemeral hint.
        
        Args:
            commitment: The reception commitment
            ephemeral_hint: Ephemeral hint from sender
            
        Returns:
            bytes: The derived routing key
        """
        # Derive routing key: H(commitment || ephemeral_hint)
        routing_key_data = commitment + ephemeral_hint
        return hashlib.sha256(routing_key_data).digest()
    
    def get_commitment_info(self, commitment: bytes) -> Optional[Dict]:
        """
        Get information about a commitment.
        
        Args:
            commitment: The commitment to look up
            
        Returns:
            dict: Commitment information or None if not found
        """
        return self.commitments.get(commitment)
    
    def generate_bloom_fingerprint(self, commitment: bytes, timestamp: int) -> bytes:
        """
        Generate a bloom filter fingerprint for efficient routing.
        
        Args:
            commitment: The reception commitment
            timestamp: Timestamp for the call
            
        Returns:
            bytes: 8-byte bloom filter fingerprint
        """
        # Create fingerprint: H(commitment || timestamp)[:8]
        fingerprint_data = commitment + timestamp.to_bytes(8, byteorder='big')
        return hashlib.sha256(fingerprint_data).digest()[:8]
    
    def has_commitment_matching_fingerprint(self, fingerprint: bytes) -> bool:
        """
        Check if we have a commitment matching a bloom filter fingerprint.
        
        Args:
            fingerprint: The bloom filter fingerprint
            
        Returns:
            bool: True if we have a matching commitment
        """
        # In a real implementation, we'd have a more efficient lookup
        # For now, we'll check all commitments
        for commitment in self.commitments:
            # Recreate the fingerprint for this commitment
            commitment_info = self.commitments[commitment]
            timestamp = int(commitment_info.get('created_at', 0))
            test_fingerprint = self.generate_bloom_fingerprint(commitment, timestamp)
            if test_fingerprint == fingerprint:
                return True
        return False
    
    def cleanup_expired_commitments(self, expiration_time: int = 3600):
        """
        Clean up expired commitments.
        
        Args:
            expiration_time: Time in seconds after which commitments expire
        """
        current_time = __import__('time').time()
        expired_commitments = [
            commitment for commitment, info in self.commitments.items()
            if current_time - info['created_at'] > expiration_time
        ]
        
        for commitment in expired_commitments:
            del self.commitments[commitment]