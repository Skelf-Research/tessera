"""
Tests for CallDNS cryptographic components.
"""

import unittest
from calldns.crypto.crypto_utils import CryptoUtils, ZKProver, ZKVerifier
from calldns.sdk.identity_manager import IdentityManager


class TestCryptoUtils(unittest.TestCase):
    """Test cryptographic utilities."""
    
    def test_key_generation(self):
        """Test key generation."""
        private_int, public_bytes, private_obj = CryptoUtils.generate_keypair()
        self.assertIsInstance(private_int, int)
        self.assertIsInstance(public_bytes, bytes)
        self.assertIsNotNone(private_obj)
    
    def test_hash_data(self):
        """Test data hashing."""
        result = CryptoUtils.hash_data("test", b"data", 123)
        self.assertIsInstance(result, bytes)
        self.assertEqual(len(result), 32)  # SHA-256 produces 32 bytes


class TestZKProofs(unittest.TestCase):
    """Test zero-knowledge proofs."""
    
    def setUp(self):
        """Set up test fixtures."""
        private_int, public_bytes, private_obj = CryptoUtils.generate_keypair()
        self.private_key = private_int
        self.public_key = public_bytes
        self.prover = ZKProver()
        self.verifier = ZKVerifier()
    
    def test_proof_generation(self):
        """Test proof generation."""
        proof = self.prover.generate_proof(self.private_key, self.public_key, "test")
        self.assertIn('R', proof)
        self.assertIn('s', proof)
        self.assertIn('public_key', proof)
        self.assertIsInstance(proof['R'], bytes)
        self.assertIsInstance(proof['s'], int)
        self.assertIsInstance(proof['public_key'], bytes)
    
    def test_proof_verification(self):
        """Test proof verification."""
        proof = self.prover.generate_proof(self.private_key, self.public_key, "test")
        # Now we have a proper verification implementation
        result = self.verifier.verify_proof(proof)
        self.assertTrue(result)
    
    def test_invalid_proof_verification(self):
        """Test verification of invalid proof."""
        # Create a valid proof first
        proof = self.prover.generate_proof(self.private_key, self.public_key, "test")
        
        # Tamper with the proof
        proof['s'] = proof['s'] + 1
        
        # Verification should fail
        result = self.verifier.verify_proof(proof)
        self.assertFalse(result)


class TestIdentityManager(unittest.TestCase):
    """Test identity manager."""
    
    def test_identity_generation(self):
        """Test identity generation."""
        identity_manager = IdentityManager()
        private_key = identity_manager.get_private_key()
        public_key = identity_manager.get_public_key()
        
        self.assertIsNotNone(private_key)
        self.assertIsNotNone(public_key)
        self.assertIsInstance(private_key, int)
        self.assertIsInstance(public_key, bytes)


if __name__ == "__main__":
    unittest.main()