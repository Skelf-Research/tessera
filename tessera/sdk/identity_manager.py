"""
Identity management for CallDNS.
Handles cryptographic identities locally on the device.
"""

from ..crypto.crypto_utils import CryptoUtils


class IdentityManager:
    """Manages cryptographic identities for the device."""
    
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.private_key_obj = None
        self._generate_identity()
    
    def _generate_identity(self):
        """Generate a new identity (key pair)."""
        private_int, public_bytes, private_obj = CryptoUtils.generate_keypair()
        self.private_key = private_int
        self.public_key = public_bytes
        self.private_key_obj = private_obj
    
    def get_private_key(self):
        """Get the private key."""
        return self.private_key
    
    def get_private_key_obj(self):
        """Get the private key object."""
        return self.private_key_obj
    
    def get_public_key(self):
        """Get the public key."""
        return self.public_key
    
    def set_identity(self, private_key, public_key):
        """Set an existing identity."""
        self.private_key = private_key
        self.public_key = public_key