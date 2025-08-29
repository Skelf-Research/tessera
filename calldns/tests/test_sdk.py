"""
Tests for CallDNS SDK components.
"""

import unittest
from calldns.sdk.caller import Caller
from calldns.sdk.verifier import Verifier


class TestCaller(unittest.TestCase):
    """Test caller SDK."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.caller = Caller()
    
    def test_caller_creation(self):
        """Test caller creation."""
        self.assertIsNotNone(self.caller.identity_manager)
        self.assertIsNotNone(self.caller.zk_prover)
    
    def test_generate_call_proof(self):
        """Test generating call proof."""
        proof = self.caller.generate_call_proof({"test": "data"})
        self.assertIn('R', proof)
        self.assertIn('s', proof)
        self.assertIsInstance(proof['R'], bytes)
        self.assertIsInstance(proof['s'], int)


class TestVerifier(unittest.TestCase):
    """Test verifier SDK."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.verifier = Verifier()
    
    def test_verifier_creation(self):
        """Test verifier creation."""
        self.assertIsNotNone(self.verifier.zk_verifier)


if __name__ == "__main__":
    unittest.main()