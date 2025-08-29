"""
Caller component for CallDNS.
Handles ZK proof generation on caller device.
"""

from .identity_manager import IdentityManager
from ..crypto.crypto_utils import ZKProver


class Caller:
    """Handles ZK proof generation on caller device."""
    
    def __init__(self):
        self.identity_manager = IdentityManager()
        self.zk_prover = ZKProver()
    
    def generate_call_proof(self, metadata=None):
        """
        Generate ZK proof for outgoing call.
        
        Args:
            metadata: Optional metadata to include in the proof
            
        Returns:
            dict: The ZK proof
        """
        return self.zk_prover.generate_proof(
            self.identity_manager.get_private_key(),
            self.identity_manager.get_public_key(),
            metadata
        )
    
    def get_public_key(self):
        """Get the caller's public key."""
        return self.identity_manager.get_public_key()