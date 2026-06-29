"""
Tests for Tessera SDK components.
"""

import unittest
from tessera.sdk.sender import Sender
from tessera.sdk.verifier import Verifier


class TestSender(unittest.TestCase):
    """Test sender SDK."""

    def setUp(self):
        """Set up test fixtures."""
        self.sender = Sender()

    def test_sender_creation(self):
        """Test sender creation."""
        self.assertIsNotNone(self.sender.identity_manager)
        self.assertIsNotNone(self.sender.zk_prover)

    def test_generate_call_proof(self):
        """Test generating call proof."""
        proof = self.sender.generate_call_proof({"test": "data"})
        self.assertIn("R", proof)
        self.assertIn("s", proof)
        self.assertIsInstance(proof["R"], bytes)
        self.assertIsInstance(proof["s"], int)


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
