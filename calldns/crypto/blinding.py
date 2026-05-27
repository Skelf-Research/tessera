"""
Per-call key blinding for caller unlinkability (resolves finding F11).

The base ZK proof (crypto_utils.ZKProver) hides the caller's secret key x but transmits
the public key Y in the clear, so a callee that decrypts the proof could link every call
from the same caller by Y. This module makes the *statement* unlinkable too:

For each call the caller presents a blinded pseudonym
    Y' = Y + t*G,   t = H(shared_seed || session_id) mod q
and proves knowledge of the blinded secret x' = x + t (which it can compute). The callee,
holding the contact's registered key Y and the per-contact ``shared_seed`` established at
enrolment, recomputes t and checks Y' == Y + t*G — authenticating the caller as "the entity
I share this seed with" while:

  * a third party / the network sees a fresh, uniform Y' per call (unlinkable);
  * a *different* callee (with a different seed) cannot recompute Y' (no cross-callee linkage);
  * no central registry maps caller <-> callee — the binding is pairwise and local.

See ../../calldns-paper/formal/security_proofs.md (F11) and ../../calldns-paper/spec/protocol_spec.md.
"""

import hashlib
import hmac

from ecdsa import SECP256k1, VerifyingKey

from .crypto_utils import ZKProver, ZKVerifier

ORDER = SECP256k1.order
_G = SECP256k1.generator


def derive_blinding(shared_seed: bytes, session_id: str) -> int:
    """Per-call blinding scalar t = H(shared_seed || session_id) mod q."""
    h = hashlib.sha256(shared_seed + session_id.encode("utf-8")).digest()
    return int.from_bytes(h, "big") % ORDER


def blind_private_key(x: int, t: int) -> int:
    """x' = (x + t) mod q."""
    return (x + t) % ORDER


def blind_public_key(public_key_bytes: bytes, t: int) -> bytes:
    """Y' = Y + t*G, returned in the same 64-byte raw encoding as Y."""
    point = VerifyingKey.from_string(public_key_bytes, curve=SECP256k1).pubkey.point + (_G * t)
    return VerifyingKey.from_public_point(point, curve=SECP256k1).to_string()


class BlindedCaller:
    """Caller side: produce a per-call proof under a fresh blinded pseudonym."""

    def __init__(self, private_key_int: int, public_key_bytes: bytes):
        self.x = private_key_int
        self.Y = public_key_bytes
        self._prover = ZKProver()

    def prove(self, shared_seed: bytes, session_id: str, metadata: dict) -> dict:
        """Return a ZK proof carrying the blinded pseudonym Y' for this call."""
        t = derive_blinding(shared_seed, session_id)
        blinded_pub = blind_public_key(self.Y, t)
        blinded_priv = blind_private_key(self.x, t)
        return self._prover.generate_proof(blinded_priv, blinded_pub, metadata)


class BlindedVerifier:
    """Callee side: authenticate a blinded proof against a known contact (Y, shared_seed)."""

    def __init__(self):
        self._verifier = ZKVerifier()

    def authenticate(self, proof: dict, contact_public_key: bytes,
                     shared_seed: bytes, session_id: str) -> bool:
        """True iff the proof is valid AND its pseudonym matches the expected contact.

        Two independent checks must both pass:
          1. the ZK proof is cryptographically valid (knowledge of the blinded secret), and
          2. the blinded public key equals Y + t*G for this contact and session
             (so it is *this* contact, not just some valid key).
        """
        if not self._verifier.verify_proof(proof):
            return False
        t = derive_blinding(shared_seed, session_id)
        expected = blind_public_key(contact_public_key, t)
        return hmac.compare_digest(proof.get("public_key", b""), expected)
