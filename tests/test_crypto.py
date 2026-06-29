"""
Tests for Tessera cryptographic components.
"""

import unittest
from tessera.crypto.crypto_utils import CryptoUtils, ZKProver, ZKVerifier
from tessera.sdk.identity_manager import IdentityManager
from tessera.utils.exceptions import ProofError, ValidationError


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
        metadata = {"test": "data", "call_type": "voice"}
        proof = self.prover.generate_proof(self.private_key, self.public_key, metadata)
        self.assertIn("R", proof)
        self.assertIn("s", proof)
        self.assertIn("public_key", proof)
        self.assertIsInstance(proof["R"], bytes)
        self.assertIsInstance(proof["s"], int)
        self.assertIsInstance(proof["public_key"], bytes)

    def test_proof_verification(self):
        """Test proof verification."""
        metadata = {"test": "data", "call_type": "voice"}
        proof = self.prover.generate_proof(self.private_key, self.public_key, metadata)
        # Now we have a proper verification implementation
        result = self.verifier.verify_proof(proof)
        self.assertTrue(result)

    def test_invalid_proof_verification(self):
        """Test verification of invalid proof."""
        # Create a valid proof first
        metadata = {"test": "data", "call_type": "voice"}
        proof = self.prover.generate_proof(self.private_key, self.public_key, metadata)

        # Tamper with the proof
        proof["s"] = proof["s"] + 1

        # Verification should fail
        result = self.verifier.verify_proof(proof)
        self.assertFalse(result)


class TestProofRobustness(unittest.TestCase):
    """Soundness regression tests (fast counterparts of scripts/bench_security.py / E6).

    Every category of tampered/forged proof must be rejected. A regression here
    is a soundness break — the central correctness claim of the paper.
    """

    def setUp(self):
        priv, pub, _ = CryptoUtils.generate_keypair()
        self.private_key = priv
        self.public_key = pub
        self.prover = ZKProver()
        self.verifier = ZKVerifier()
        self.metadata = {"call_type": "voice", "region": "US"}

    def _valid_proof(self):
        return self.prover.generate_proof(
            self.private_key, self.public_key, self.metadata
        )

    def test_valid_proof_accepted(self):
        self.assertTrue(self.verifier.verify_proof(self._valid_proof()))

    def test_tampered_R_rejected(self):
        proof = self._valid_proof()
        R = bytearray(proof["R"])
        R[0] ^= 0x01
        proof["R"] = bytes(R)
        self.assertFalse(self.verifier.verify_proof(proof))

    def test_swapped_public_key_rejected(self):
        proof = self._valid_proof()
        _, other_pub, _ = CryptoUtils.generate_keypair()
        proof["public_key"] = other_pub
        self.assertFalse(self.verifier.verify_proof(proof))

    def test_tampered_metadata_rejected(self):
        proof = self._valid_proof()
        proof["metadata"] = {"call_type": "voice", "region": "GB"}
        self.assertFalse(self.verifier.verify_proof(proof))

    def test_random_forgery_rejected(self):
        proof = self._valid_proof()
        # Well-formed random point R from an unrelated proof, with a real public key.
        forged = {
            "R": self.prover.generate_proof(
                *CryptoUtils.generate_keypair()[:2], self.metadata
            )["R"],
            "s": proof["s"],
            "public_key": self.public_key,
            "metadata": self.metadata,
        }
        self.assertFalse(self.verifier.verify_proof(forged))


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
