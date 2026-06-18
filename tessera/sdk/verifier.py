"""
Verifier component for Tessera.
Handles proof verification on callee device with commitment management and traffic privacy.
"""

import hashlib
import json
import base64
from ..crypto.crypto_utils import ZKVerifier, SecureEncryption
from .commitment_manager import CommitmentManager
from .traffic_manager import TrafficManager
from cryptography.exceptions import InvalidTag


class Verifier:
    """Handles proof verification on callee device."""
    
    def __init__(self):
        self.zk_verifier = ZKVerifier()
        self.commitment_manager = CommitmentManager()
        self.traffic_manager = TrafficManager()
    
    def verify_call_proof(self, proof):
        """
        Verify incoming call proof.
        
        Args:
            proof: The ZK proof to verify
            
        Returns:
            bool: True if proof is valid, False otherwise
        """
        return self.zk_verifier.verify_proof(proof)
    
    def generate_reception_commitment(self, session_id: str) -> bytes:
        """
        Generate a reception commitment for this verifier.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            bytes: The reception commitment
        """
        # For this prototype, we'll use a dummy public key
        # In a real implementation, this would be the verifier's actual public key
        dummy_public_key = b"verifier_public_key_placeholder"
        return self.commitment_manager.generate_reception_commitment(
            dummy_public_key, session_id
        )
    
    def verify_encrypted_call_proof(self, encrypted_proof_data: dict) -> bool:
        """
        Verify an encrypted call proof.
        
        Args:
            encrypted_proof_data: Encrypted proof with routing information
            
        Returns:
            bool: True if proof is valid, False otherwise
        """
        # Decode base64 data
        try:
            bloom_fingerprint = base64.b64decode(encrypted_proof_data['bloom_fingerprint'])
            ephemeral_hint = base64.b64decode(encrypted_proof_data['ephemeral_hint'])
            nonce = base64.b64decode(encrypted_proof_data['nonce'])
            ciphertext = base64.b64decode(encrypted_proof_data['ciphertext'])
            aad = base64.b64decode(encrypted_proof_data['aad'])
        except Exception as e:
            print(f"Decoding error: {e}")
            return False
        
        # Check if we have a matching commitment using bloom filter fingerprint
        if not self.commitment_manager.has_commitment_matching_fingerprint(bloom_fingerprint):
            return False  # Not for us
        
        # Derive decryption key
        # We need to find the right commitment - in a real implementation we'd have a more efficient way
        # For this prototype, we'll use the first matching commitment
        commitment = None
        for comm in self.commitment_manager.commitments:
            commitment_info = self.commitment_manager.commitments[comm]
            timestamp = int(commitment_info.get('created_at', 0))
            test_fingerprint = self.commitment_manager.generate_bloom_fingerprint(comm, timestamp)
            if test_fingerprint == bloom_fingerprint:
                commitment = comm
                break
        
        if not commitment:
            return False
        
        # Derive routing key
        routing_key_data = commitment + ephemeral_hint
        routing_key = hashlib.sha256(routing_key_data).digest()

        # Decrypt proof using secure AES-GCM
        try:
            encrypted_data = {
                'nonce': nonce,
                'ciphertext': ciphertext,
                'additional_data': aad
            }
            proof_json_bytes = SecureEncryption.decrypt(encrypted_data, routing_key)

            # Deserialize proof
            proof_str = proof_json_bytes.decode('utf-8')
            proof_data = json.loads(proof_str)
        except InvalidTag:
            print("Authentication failed: Proof has been tampered with")
            return False
        except Exception as e:
            print(f"Decryption error: {e}")
            return False

        try:
            # Check if this is a dummy proof
            if proof_data.get('is_dummy', False):
                return False  # Dummy proof, not a real call
            
            # Convert base64 strings back to bytes
            proof = {}
            for key, value in proof_data.items():
                if isinstance(value, str) and key in ['R', 'public_key']:  # These should be bytes
                    try:
                        proof[key] = base64.b64decode(value)
                    except:
                        proof[key] = value
                else:
                    proof[key] = value
            
            # Verify proof
            return self.verify_call_proof(proof)
        except Exception as e:
            print(f"Verification error: {e}")
            return False
    
    def process_batched_proofs(self, encrypted_proofs: list) -> list:
        """
        Process a batch of encrypted proofs, filtering out valid ones.
        
        Args:
            encrypted_proofs: List of encrypted proofs
            
        Returns:
            list: List of valid proof results
        """
        valid_proofs = []
        
        for proof in encrypted_proofs:
            is_valid = self.verify_encrypted_call_proof(proof)
            if is_valid:
                valid_proofs.append(proof)
        
        return valid_proofs