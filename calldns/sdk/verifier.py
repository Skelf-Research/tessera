"""
Verifier component for CallDNS.
Handles proof verification on callee device.
"""

from ..crypto.crypto_utils import ZKVerifier


class Verifier:
    """Handles proof verification on callee device."""
    
    def __init__(self):
        self.zk_verifier = ZKVerifier()
    
    def verify_call_proof(self, proof, caller_public_key):
        """
        Verify incoming call proof.
        
        Args:
            proof: The ZK proof to verify
            caller_public_key: The caller's public key
            
        Returns:
            bool: True if proof is valid, False otherwise
        """
        return self.zk_verifier.verify_proof(proof, caller_public_key)