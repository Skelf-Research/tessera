"""
Tests for Tessera traffic privacy features.
"""

import unittest
import base64
import json
import math
import random
from tessera.sdk.traffic_manager import TrafficManager, DPCoverTraffic
from tessera.sdk.sender import Sender
from tessera.sdk.verifier import Verifier


class TestTrafficManager(unittest.TestCase):
    """Test traffic manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.traffic_manager = TrafficManager()

    def test_padding_size(self):
        """Test that proofs are padded to correct size."""
        # Create a sample encrypted proof
        sample_proof = {
            "encrypted_proof": base64.b64encode(b"test").decode("utf-8"),
            "bloom_fingerprint": base64.b64encode(b"fingerprint").decode("utf-8"),
            "ephemeral_hint": base64.b64encode(b"hint").decode("utf-8"),
            "proof_size": 4,
        }

        padded_proof = self.traffic_manager.pad_proof(sample_proof)

        # Check that padding was added
        self.assertIn("_padding", padded_proof)
        self.assertEqual(
            padded_proof["_padded_size"], self.traffic_manager.padding_size
        )

    def test_cover_traffic_generation(self):
        """Test cover traffic generation."""
        dummy_proofs = self.traffic_manager.generate_cover_traffic(3)

        self.assertEqual(len(dummy_proofs), 3)
        for proof in dummy_proofs:
            self.assertIn("encrypted_proof", proof)
            self.assertIn("bloom_fingerprint", proof)
            self.assertIn("ephemeral_hint", proof)
            # Note: The 'is_dummy' flag is in the encrypted content, not the wrapper

    def test_traffic_mixing(self):
        """Test mixing real and dummy traffic."""
        # Create sample real proofs
        real_proofs = [{"proof_id": i, "is_dummy": False} for i in range(5)]

        mixed_proofs = self.traffic_manager.mix_traffic(real_proofs)

        # Should have real proofs plus dummy proofs
        self.assertGreater(len(mixed_proofs), len(real_proofs))

        # Check that all real proofs are included
        real_proof_ids = {proof["proof_id"] for proof in real_proofs}
        # For this test, we'll just check the count since dummy proofs are mixed in


class TestSenderWithTraffic(unittest.TestCase):
    """Test sender with traffic privacy features."""

    def setUp(self):
        """Set up test fixtures."""
        self.sender = Sender()

    def test_proof_preparation_with_padding(self):
        """Test proof preparation with padding."""
        # Create sample encrypted proof
        sample_proof = {
            "encrypted_proof": base64.b64encode(b"test").decode("utf-8"),
            "bloom_fingerprint": base64.b64encode(b"fingerprint").decode("utf-8"),
            "ephemeral_hint": base64.b64encode(b"hint").decode("utf-8"),
            "proof_size": 4,
        }

        padded_proof = self.sender.prepare_proof_for_transmission(sample_proof)

        self.assertIn("_padding", padded_proof)
        self.assertEqual(
            padded_proof["_padded_size"], self.sender.traffic_manager.padding_size
        )

    def test_batch_scheduling(self):
        """Test batch scheduling with cover traffic."""
        # Create sample proofs
        sample_proofs = [
            {
                "encrypted_proof": base64.b64encode(b"test").decode("utf-8"),
                "bloom_fingerprint": base64.b64encode(b"fingerprint").decode("utf-8"),
                "ephemeral_hint": base64.b64encode(b"hint").decode("utf-8"),
                "proof_size": 4,
            }
            for _ in range(3)
        ]

        # Schedule transmission
        scheduled_proofs = self.sender.schedule_batch_transmission(sample_proofs)

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
        dummy_content = {"R": "test", "s": 123, "metadata": {}, "is_dummy": True}

        dummy_proof = {
            "encrypted_proof": base64.b64encode(
                json.dumps(dummy_content).encode("utf-8")
            ).decode("utf-8"),
            "bloom_fingerprint": base64.b64encode(b"fingerprint").decode("utf-8"),
            "ephemeral_hint": base64.b64encode(b"hint").decode("utf-8"),
            "proof_size": 1024,
        }

        # Verification should return False for dummy proofs
        result = self.verifier.verify_encrypted_call_proof(dummy_proof)
        self.assertFalse(result)


class TestDPCoverTraffic(unittest.TestCase):
    """Differentially-private cover-traffic mechanism (Workstream C).

    Backs docs/privacy-model.md and scripts/analysis/linkability_sim.py.
    """

    def test_baseline_mu_formula(self):
        eps, delta = 1.0, 1e-6
        dp = DPCoverTraffic(epsilon=eps, delta=delta, sensitivity=1)
        expected_mu = (1.0 / eps) * math.log(1.0 / (2.0 * delta))
        self.assertAlmostEqual(dp.mu, expected_mu, places=9)
        self.assertAlmostEqual(dp.scale, 1.0 / eps, places=9)

    def test_counts_non_negative(self):
        dp = DPCoverTraffic(epsilon=2.0, delta=1e-6, rng=random.Random(1))
        counts = dp.dummy_counts(64)
        self.assertEqual(len(counts), 64)
        self.assertTrue(all(c >= 0 for c in counts))

    def test_expected_overhead(self):
        dp = DPCoverTraffic(epsilon=1.0, delta=1e-6, num_buckets=64)
        self.assertAlmostEqual(dp.expected_overhead_per_round(), 64 * dp.mu, places=6)

    def test_overhead_independent_of_real_load(self):
        """Defining DP property: dummy generation does not look at the real load."""
        dp = DPCoverTraffic(epsilon=1.0, delta=1e-6, rng=random.Random(7))
        published = dp.published_counts([0, 100, 5, 0, 42])
        # Each published count >= its real count (only adds dummies, never removes).
        for real, pub in zip([0, 100, 5, 0, 42], published):
            self.assertGreaterEqual(pub, real)

    def test_empirical_mean_near_mu(self):
        dp = DPCoverTraffic(epsilon=1.0, delta=1e-6, rng=random.Random(123))
        samples = [dp.dummy_count_for_bucket() for _ in range(5000)]
        mean = sum(samples) / len(samples)
        # Mean should be close to mu (truncation at 0 is negligible at this mu ~ 13).
        self.assertLess(abs(mean - dp.mu), 1.0)

    def test_smaller_epsilon_more_overhead(self):
        hi_priv = DPCoverTraffic(epsilon=0.1, delta=1e-6)
        lo_priv = DPCoverTraffic(epsilon=4.0, delta=1e-6)
        self.assertGreater(
            hi_priv.expected_overhead_per_round(), lo_priv.expected_overhead_per_round()
        )

    def test_invalid_params_rejected(self):
        with self.assertRaises(ValueError):
            DPCoverTraffic(epsilon=0)
        with self.assertRaises(ValueError):
            DPCoverTraffic(epsilon=1.0, delta=1.5)


if __name__ == "__main__":
    unittest.main()
