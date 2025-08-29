"""
Cryptographic utilities for CallDNS.
Implements Schnorr-based zero-knowledge proofs for fast verification using ECDSA library.
"""

import hashlib
import secrets
import ecdsa
from ecdsa import SECP256k1
from ecdsa.util import sigencode_string, sigdecode_string
from ecdsa.curves import Curve


class CryptoUtils:
    """Utility class for cryptographic operations."""
    
    @staticmethod
    def generate_keypair():
        """Generate a key pair using SECP256k1."""
        private_key = ecdsa.SigningKey.generate(curve=SECP256k1)
        public_key = private_key.get_verifying_key()
        
        # Get private key value as integer
        private_int = int.from_bytes(private_key.to_string(), 'big')
        public_bytes = public_key.to_string()
        
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
        self.curve = SECP256k1
        self.order = SECP256k1.order
    
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
        
        # Create ephemeral point for R = g^r
        R_point = self.curve.generator * r
        R = R_point.to_bytes()
        
        # Compute challenge c = H(R || Y || metadata)
        c_hash = CryptoUtils.hash_data(R, public_key_bytes, metadata or "")
        # Convert hash to integer mod order
        c = int.from_bytes(c_hash, byteorder='big') % self.order
        
        # Compute response s = r + c*x mod q
        s = (r + c * private_key_int) % self.order
        
        return {
            'R': R,
            's': s,
            'public_key': public_key_bytes,
            'metadata': metadata
        }


class ZKVerifier:
    """Implements Schnorr-based zero-knowledge proof verification."""
    
    def __init__(self):
        self.curve = SECP256k1
        self.order = SECP256k1.order
    
    def verify_proof(self, proof):
        """
        Verify a Schnorr zero-knowledge proof.
        
        Args:
            proof: The proof dictionary containing R, s, and public_key
            
        Returns:
            bool: True if proof is valid, False otherwise
        """
        try:
            R = proof['R']
            s = proof['s']
            Y = proof['public_key']
            metadata = proof.get('metadata', "")
            
            # Deserialize points
            R_point = ecdsa.ellipticcurve.Point(
                self.curve.curve, 
                int.from_bytes(R[:32], 'big'), 
                int.from_bytes(R[32:], 'big')
            )
            Y_point = ecdsa.ellipticcurve.Point(
                self.curve.curve, 
                int.from_bytes(Y[:32], 'big'), 
                int.from_bytes(Y[32:], 'big')
            )
            
            # Compute challenge c = H(R || Y || metadata)
            c_hash = CryptoUtils.hash_data(R, Y, metadata or "")
            c = int.from_bytes(c_hash, byteorder='big') % self.order
            
            # Compute g^s
            gs_point = self.curve.generator * s
            
            # Compute Y^c
            Yc_point = Y_point * c
            
            # Compute R' = g^s * Y^(-c)
            # Y^(-c) is the negation of Y^c
            Y_neg_c_point = ecdsa.ellipticcurve.Point(
                self.curve.curve,
                Yc_point.x(),
                -Yc_point.y() % self.curve.curve.p()
            )
            
            # R' = g^s * Y^(-c)
            Rp_point = gs_point + Y_neg_c_point
            
            # Check if R == R'
            return R_point.x() == Rp_point.x() and R_point.y() == Rp_point.y()
            
        except Exception as e:
            print(f"Verification error: {e}")
            return False