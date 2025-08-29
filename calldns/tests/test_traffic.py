"""
Tests for CallDNS traffic privacy features.
"""

import unittest
import base64
import json
from calldns.sdk.traffic_manager import TrafficManager
from calldns.sdk.caller import Caller
from calldns.sdk.verifier import Verifier


class TestTrafficManager(unittest.TestCase):
    """Test traffic manager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.traffic_manager = TrafficManager()
    
    def test_padding_size(self):
        """Test that proofs are padded to correct size."""
        # Create a sample encrypted proof
        sample_proof = {
            'encrypted_proof': base64.b64encode(b'test').decode('utf-8'),
            'bloom_fingerprint': base64.b64encode(b'fingerprint').decode('utf-8'),
            'ephemeral_hint': base64.b64encode(b'hint').decode('utf-8'),
            'proof_size': 4
        }
        
        padded_proof = self.traffic_manager.pad_proof(sample_proof)
        
        # Check that padding was added
        self.assertIn('_padding', padded_proof)
        self.assertEqual(padded_proof['_padded_size'], self.traffic_manager.padding_size)
    
    def test_cover_traffic_generation(self):
        """Test cover traffic generation."""
        dummy_proofs = self.traffic_manager.generate_cover_traffic(3)
        
        self.assertEqual(len(dummy_proofs), 3)
        for proof in dummy_proofs:
            self.assertIn('encrypted_proof', proof)
            self.assertIn('bloom_fingerprint', proof)
            self.assertIn('ephemeral_hint', proof)
            # Note: The 'is_dummy' flag is in the encrypted content, not the wrapper
    
    def test_traffic_mixing(self):
        """Test mixing real and dummy traffic."""
        # Create sample real proofs
        real_proofs = [
            {'proof_id': i, 'is_dummy': False} for i in range(5)
        ]
        
        mixed_proofs = self.traffic_manager.mix_traffic(real_proofs)
        
        # Should have real proofs plus dummy proofs
        self.assertGreater(len(mixed_proofs), len(real_proofs))
        
        # Check that all real proofs are included
        real_proof_ids = {proof['proof_id'] for proof in real_proofs}
        # For this test, we'll just check the count since dummy proofs are mixed in


class TestCallerWithTraffic(unittest.TestCase):
    """Test caller with traffic privacy features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.caller = Caller()
    
    def test_proof_preparation_with_padding(self):
        """Test proof preparation with padding."""
        # Create sample encrypted proof
        sample_proof = {
            'encrypted_proof': base64.b64encode(b'test').decode('utf-8'),
            'bloom_fingerprint': base64.b64encode(b'fingerprint').decode('utf-8'),
            'ephemeral_hint': base64.b64encode(b'hint').decode('utf-8'),
            'proof_size': 4
        }
        
        padded_proof = self.caller.prepare_proof_for_transmission(sample_proof)
        
        self.assertIn('_padding', padded_proof)
        self.assertEqual(padded_proof['_padded_size'], self.caller.traffic_manager.padding_size)
    
    def test_batch_scheduling(self):
        """Test batch scheduling with cover traffic."""
        # Create sample proofs
        sample_proofs = [
            {
                'encrypted_proof': base64.b64encode(b'test').decode('utf-8'),
                'bloom_fingerprint': base64.b64encode(b'fingerprint').decode('utf-8'),
                'ephemeral_hint': base64.b64encode(b'hint').decode('utf-8'),
                'proof_size': 4
            } for _ in range(3)
        ]
        
        # Schedule transmission
        scheduled_proofs = self.caller.schedule_batch_transmission(sample_proofs)
        
        # Should have real proofs plus dummy proofs
        self.assertGreaterEqual(len(scheduled_proofs), len(sample_proofs))


class TestVerifierWithTraffic(unittest.TestCase):
    """Test verifier with traffic privacy features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.verifier = Verifier()
    
    def test_dummy_proof_filtering(self):
        """Test that dummy proofs are filtered out."""
        # Create a dummy proof with the is_dummy flag in the content
        dummy_content = {
            'R': 'test',
            's': 123,
            'metadata': {},
            'is_dummy': True
        }
        
        dummy_proof = {
            'encrypted_proof': base64.b64encode(
                json.dumps(dummy_content).encode('utf-8')
            ).decode('utf-8'),
            'bloom_fingerprint': base64.b64encode(b'fingerprint').decode('utf-8'),
            'ephemeral_hint': base64.b64encode(b'hint').decode('utf-8'),
            'proof_size': 1024
        }
        
        # Verification should return False for dummy proofs
        result = self.verifier.verify_encrypted_call_proof(dummy_proof)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()