"""
Tests for per-call key blinding (resolves F11): caller unlinkability with callee
authentication. See calldns/crypto/blinding.py.
"""

import unittest

from calldns.crypto.crypto_utils import CryptoUtils
from calldns.crypto.blinding import (
    BlindedCaller, BlindedVerifier, blind_public_key, derive_blinding,
)


class TestBlindedIdentity(unittest.TestCase):
    def setUp(self):
        self.x, self.Y, _ = CryptoUtils.generate_keypair()
        self.caller = BlindedCaller(self.x, self.Y)
        self.verifier = BlindedVerifier()
        self.seed = b"enrolment-shared-seed-with-bank"
        self.meta = {"call_type": "voice"}

    def test_callee_authenticates_blinded_proof(self):
        proof = self.caller.prove(self.seed, "session-1", self.meta)
        self.assertTrue(
            self.verifier.authenticate(proof, self.Y, self.seed, "session-1"))

    def test_blinded_key_is_not_the_longterm_key(self):
        proof = self.caller.prove(self.seed, "session-1", self.meta)
        self.assertNotEqual(proof["public_key"], self.Y)

    def test_cross_call_unlinkability(self):
        p1 = self.caller.prove(self.seed, "session-1", self.meta)
        p2 = self.caller.prove(self.seed, "session-2", self.meta)
        # Same caller, different calls -> different pseudonyms.
        self.assertNotEqual(p1["public_key"], p2["public_key"])

    def test_different_callee_cannot_link(self):
        # A different callee holds a different shared seed and cannot recompute the
        # pseudonym, so it cannot authenticate (or link) the caller.
        proof = self.caller.prove(self.seed, "session-1", self.meta)
        other_seed = b"some-other-callees-seed"
        self.assertFalse(
            self.verifier.authenticate(proof, self.Y, other_seed, "session-1"))

    def test_wrong_session_id_fails(self):
        proof = self.caller.prove(self.seed, "session-1", self.meta)
        self.assertFalse(
            self.verifier.authenticate(proof, self.Y, self.seed, "session-2"))

    def test_tampered_proof_fails(self):
        proof = self.caller.prove(self.seed, "session-1", self.meta)
        proof["s"] = proof["s"] + 1
        self.assertFalse(
            self.verifier.authenticate(proof, self.Y, self.seed, "session-1"))

    def test_blinding_is_deterministic_for_seed_session(self):
        t1 = derive_blinding(self.seed, "session-1")
        t2 = derive_blinding(self.seed, "session-1")
        self.assertEqual(t1, t2)
        self.assertEqual(blind_public_key(self.Y, t1), blind_public_key(self.Y, t2))


if __name__ == "__main__":
    unittest.main()
