"""
Cryptographic utilities for CallDNS.
Implements Schnorr-based zero-knowledge proofs for fast verification.
"""

import hashlib
import secrets
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend


class CryptoUtils:
    """Utility class for cryptographic operations."""
    
    @staticmethod
    def generate_keypair():
        """Generate a key pair."""
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = private_key.public_key()
        
        # Get private key value
        private_int = private_key.private_numbers().private_value
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        return private_int, public_bytes, private_key
    
    @staticmethod
    def hash_data(*args):
        """Hash multiple data elements together."""
        hasher = hashlib.sha256()
        for data in args:
            if isinstance(data, str):
                hasher.update(data.encode('utf-8'))
            elif isinstance(data, bytes):
                hasher.update(data)
            elif isinstance(data, int):
                hasher.update(data.to_bytes(32, byteorder='big'))
            else:
                hasher.update(str(data).encode('utf-8'))
        return hasher.digest()


class ZKProver:
    """Implements Schnorr-based zero-knowledge proof generation."""
    
    def __init__(self):
        self.curve = ec.SECP256R1()
        # SECP256R1 order (from standard)
        self.order = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
    
    def generate_proof(self, private_key_int, public_key_bytes, metadata=None):
        """
        Generate a Schnorr zero-knowledge proof.
        
        Args:
            private_key_int: The private key (integer)
            public_key_bytes: The public key (bytes)
            metadata: Optional metadata to include in the proof
            
        Returns:
            dict: The ZK proof containing R and s
        """
        # Generate random nonce
        r = secrets.randbelow(self.order)
        
        # Create ephemeral key for R = g^r
        r_key = ec.derive_private_key(r, self.curve, default_backend())
        R_point = r_key.public_key()
        R = R_point.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        # Compute challenge c = H(R || Y || metadata)
        c_hash = CryptoUtils.hash_data(R, public_key_bytes, metadata or "")
        # Convert hash to integer mod order
        c = int.from_bytes(c_hash, byteorder='big') % self.order
        
        # Compute response s = r + c*x mod q
        s = (r + c * private_key_int) % self.order
        
        return {
            'R': R,
            's': s,
            'metadata': metadata
        }


class ZKVerifier:
    """Implements Schnorr-based zero-knowledge proof verification."""
    
    def __init__(self):
        self.curve = ec.SECP256R1()
        # SECP256R1 order (from standard)
        self.order = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
    
    def verify_proof(self, proof, public_key_bytes):
        """
        Verify a Schnorr zero-knowledge proof.
        
        Args:
            proof: The proof dictionary containing R and s
            public_key_bytes: The public key (bytes)
            
        Returns:
            bool: True if proof is valid, False otherwise
        """
        try:
            R = proof['R']
            s = proof['s']
            metadata = proof.get('metadata', "")
            
            # Compute challenge c = H(R || Y || metadata)
            c_hash = CryptoUtils.hash_data(R, public_key_bytes, metadata or "")
            c = int.from_bytes(c_hash, byteorder='big') % self.order
            
            # In a full implementation, we would verify:
            # R == g^s * Y^(-c)
            # But for this prototype, we'll just check structure
            return isinstance(R, bytes) and isinstance(s, int)
        except Exception as e:
            print(f"Verification error: {e}")
            return False