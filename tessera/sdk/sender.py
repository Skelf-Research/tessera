"""
Sender component for Tessera.
Handles ZK proof generation on sender device with commitment-based routing and traffic privacy.
"""

import hashlib
import secrets
import json
import base64
from .identity_manager import IdentityManager
from .traffic_manager import TrafficManager
from ..crypto.crypto_utils import ZKProver, SecureEncryption


class Sender:
    """Handles ZK proof generation on sender device."""
    
    def __init__(self):
        self.identity_manager = IdentityManager()
        self.zk_prover = ZKProver()
        self.traffic_manager = TrafficManager()
    
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
        """Get the sender's public key."""
        return self.identity_manager.get_public_key()
    
    def encrypt_proof_for_callee(self, proof: dict, reception_commitment: bytes, metadata=None) -> dict:
        """
        Encrypt proof for a specific callee using commitment-based routing.
        
        Args:
            proof: The ZK proof to encrypt
            reception_commitment: The callee's reception commitment
            metadata: Optional metadata for bloom filter
            
        Returns:
            dict: Encrypted proof with routing information
        """
        # Convert bytes to base64 for JSON serialization
        proof_serializable = {}
        for key, value in proof.items():
            if isinstance(value, bytes):
                proof_serializable[key] = base64.b64encode(value).decode('utf-8')
            else:
                proof_serializable[key] = value
        
        # Generate ephemeral hint for key derivation
        ephemeral_hint = secrets.token_bytes(32)
        
        # Derive routing key: H(commitment || ephemeral_hint)
        routing_key_data = reception_commitment + ephemeral_hint
        routing_key = hashlib.sha256(routing_key_data).digest()

        # Use secure AES-GCM encryption for production security
        proof_json = json.dumps(proof_serializable).encode('utf-8')

        # Additional authenticated data includes routing metadata
        aad = reception_commitment[:16]  # First 16 bytes of commitment as AAD

        # Encrypt using secure AEAD
        encrypted_data = SecureEncryption.encrypt(proof_json, routing_key, aad)
        
        # Generate bloom filter fingerprint
        timestamp = metadata.get('timestamp', 0) if metadata else 0
        fingerprint_data = reception_commitment + timestamp.to_bytes(8, byteorder='big')
        bloom_fingerprint = hashlib.sha256(fingerprint_data).digest()[:8]
        
        return {
            'nonce': base64.b64encode(encrypted_data['nonce']).decode('utf-8'),
            'ciphertext': base64.b64encode(encrypted_data['ciphertext']).decode('utf-8'),
            'aad': base64.b64encode(encrypted_data['additional_data']).decode('utf-8'),
            'bloom_fingerprint': base64.b64encode(bloom_fingerprint).decode('utf-8'),
            'ephemeral_hint': base64.b64encode(ephemeral_hint).decode('utf-8'),
            'proof_size': len(encrypted_data['ciphertext'])
        }
    
    def prepare_proof_for_transmission(self, encrypted_proof: dict) -> dict:
        """
        Prepare proof for transmission with traffic padding.
        
        Args:
            encrypted_proof: The encrypted proof
            
        Returns:
            dict: Padded encrypted proof ready for transmission
        """
        return self.traffic_manager.pad_proof(encrypted_proof)
    
    def schedule_batch_transmission(self, proofs: list) -> list:
        """
        Schedule proofs for batch transmission with cover traffic.
        
        Args:
            proofs: List of encrypted proofs
            
        Returns:
            list: Proofs ready for transmission (mixed with cover traffic)
        """
        return self.traffic_manager.schedule_transmission(proofs)