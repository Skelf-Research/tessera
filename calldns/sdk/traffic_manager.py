"""
Traffic manager for CallDNS.
Handles traffic padding and cover traffic generation for enhanced privacy.
"""

import secrets
import hashlib
import json
import base64
import time
from typing import Dict, Any, List
from collections import deque


class TrafficManager:
    """Manages traffic padding and cover traffic for enhanced privacy."""
    
    def __init__(self, padding_size: int = 1024, cover_traffic_ratio: float = 0.3):
        """
        Initialize traffic manager.
        
        Args:
            padding_size: Target size for padded packets
            cover_traffic_ratio: Ratio of cover traffic to real traffic
        """
        self.padding_size = padding_size
        self.cover_traffic_ratio = cover_traffic_ratio
        self.transmission_queue = deque()
        self.last_transmission_time = 0
        self.transmission_interval = 30  # seconds
    
    def pad_proof(self, encrypted_proof: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add padding to an encrypted proof to fixed size.
        
        Args:
            encrypted_proof: The encrypted proof to pad
            
        Returns:
            dict: Padded encrypted proof
        """
        # Serialize the proof
        proof_json = json.dumps(encrypted_proof)
        proof_bytes = proof_json.encode('utf-8')
        
        # Calculate padding needed
        current_size = len(proof_bytes)
        padding_needed = max(0, self.padding_size - current_size)
        
        # Generate random padding
        padding = secrets.token_bytes(padding_needed)
        
        # Create padded proof
        padded_proof = encrypted_proof.copy()
        padded_proof['_padding'] = base64.b64encode(padding).decode('utf-8')
        padded_proof['_padded_size'] = self.padding_size
        
        return padded_proof
    
    def generate_cover_traffic(self, count: int = 1) -> List[Dict[str, Any]]:
        """
        Generate dummy proofs for cover traffic.
        
        Args:
            count: Number of dummy proofs to generate
            
        Returns:
            list: List of dummy encrypted proofs
        """
        dummy_proofs = []
        
        for _ in range(count):
            # Generate dummy proof data
            dummy_proof = {
                'R': base64.b64encode(secrets.token_bytes(65)).decode('utf-8'),  # EC point size
                's': secrets.randbelow(2**256),
                'metadata': {
                    'timestamp': int(time.time()) - secrets.randbelow(3600),  # Random past time
                    'call_type': ['voice', 'video', 'text'][secrets.randbelow(3)],  # Replace secrets.choice
                    'session_id': secrets.token_hex(16)
                },
                'is_dummy': True
            }
            
            # Convert to encrypted format (without actual encryption for dummy)
            dummy_encrypted = {
                'encrypted_proof': base64.b64encode(
                    json.dumps(dummy_proof).encode('utf-8')
                ).decode('utf-8'),
                'bloom_fingerprint': base64.b64encode(secrets.token_bytes(8)).decode('utf-8'),
                'ephemeral_hint': base64.b64encode(secrets.token_bytes(32)).decode('utf-8'),
                'proof_size': self.padding_size
            }
            
            # Add padding
            padded_dummy = self.pad_proof(dummy_encrypted)
            dummy_proofs.append(padded_dummy)
        
        return dummy_proofs
    
    def mix_traffic(self, real_proofs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Mix real proofs with cover traffic.
        
        Args:
            real_proofs: List of real encrypted proofs
            
        Returns:
            list: Mixed list of real and dummy proofs
        """
        # Calculate number of dummy proofs needed
        dummy_count = max(1, int(len(real_proofs) * self.cover_traffic_ratio))
        
        # Generate dummy proofs
        dummy_proofs = self.generate_cover_traffic(dummy_count)
        
        # Mix real and dummy proofs
        mixed_proofs = real_proofs + dummy_proofs
        
        # Shuffle to prevent ordering analysis
        import random
        random.shuffle(mixed_proofs)
        
        return mixed_proofs
    
    def should_transmit(self) -> bool:
        """
        Determine if it's time to transmit based on timing obfuscation.
        
        Returns:
            bool: True if transmission should occur
        """
        current_time = time.time()
        return current_time - self.last_transmission_time >= self.transmission_interval
    
    def schedule_transmission(self, proofs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Schedule proofs for transmission with timing obfuscation.
        
        Args:
            proofs: Proofs to schedule for transmission
            
        Returns:
            list: Proofs ready for transmission (may include queued proofs)
        """
        # Add proofs to queue
        for proof in proofs:
            self.transmission_queue.append(proof)
        
        # Check if it's time to transmit
        if self.should_transmit():
            # Mix queued proofs with cover traffic
            all_proofs = list(self.transmission_queue)
            self.transmission_queue.clear()
            self.last_transmission_time = time.time()
            
            # Apply traffic mixing
            return self.mix_traffic(all_proofs)
        
        # Return empty list if not time to transmit
        return []
    
    def get_transmission_stats(self) -> Dict[str, Any]:
        """
        Get statistics about traffic transmission.
        
        Returns:
            dict: Transmission statistics
        """
        return {
            'queue_size': len(self.transmission_queue),
            'last_transmission': self.last_transmission_time,
            'next_transmission': self.last_transmission_time + self.transmission_interval,
            'padding_size': self.padding_size,
            'cover_traffic_ratio': self.cover_traffic_ratio
        }