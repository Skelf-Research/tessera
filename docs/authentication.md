# Sender Authentication

How a sender proves identity to a recipient with no central authority and no
cross-recipient linkability. The formal proofs live in [`../research.md`](../research.md);
this doc is the engineer-facing summary of the flow and where each piece lives
in the code.

## What we want

| Property | Meaning |
|---|---|
| Authentication | The recipient is convinced the delivery came from this specific contact. |
| Witness privacy | The recipient learns nothing about the sender's secret key beyond its existence. |
| Cross-recipient unlinkability | Two recipients cannot tell that a sender's two deliveries came from the same sender. |
| Replay resistance | A captured proof cannot be re-presented as a new delivery. |
| No central registry | No party other than the two endpoints learns about the binding. |

## Primitives

**Schnorr / Fiat–Shamir identity proof** (`tessera/crypto/crypto_utils.py::ZKProver`,
`ZKVerifier`). Group SECP256k1, generator `G`, order `q`, hash `H` (SHA-256).
Sender key `(x, Y=xG)`.

```
Prove(x, Y, m):
    r  ←$ Z_q
    R  = rG
    c  = H(R ‖ Y ‖ m) mod q
    s  = (r + c·x) mod q
    return π = (R, s)

Verify(Y, m, π):
    c  = H(R ‖ Y ‖ m) mod q
    accept iff  sG == R + cY
```

Standard Schnorr signature on `(Y, m)`. Unforgeability reduces to discrete log
in `G` (forking lemma); the proof is HVZK and, in the ROM under Fiat–Shamir,
non-interactive zero-knowledge.

**Per-recipient key blinding** (`tessera/crypto/blinding.py`). The base proof
reveals `Y`, so presenting the long-term `Y` would let a recipient link a
sender's deliveries. Instead, for each delivery the sender presents a
**blinded pseudonym**:

```
t   = H(shared_seed ‖ session_id) mod q
Y'  = Y + t·G
x'  = x + t  mod q
π   = Prove(x', Y', m)
```

The recipient (who holds the per-contact `shared_seed` from enrolment)
recomputes `t` and checks `Y' = Y + t·G` to **authenticate** that the proof
came from this contact. Anyone without the seed sees a uniform `Y'` per
delivery → cross-recipient unlinkability.

## Flow

```python
from tessera.crypto.crypto_utils import CryptoUtils
from tessera.crypto.blinding import BlindedSender, BlindedVerifier

# Sender setup (long-term)
x, Y, _ = CryptoUtils.generate_keypair()
sender  = BlindedSender(x, Y)

# Enrolment record stored at the recipient (per-contact)
record = {"contact_pubkey": Y, "shared_seed": b"recipient-bound-seed"}

# Per delivery
proof = sender.prove(record["shared_seed"], session_id="m-001",
                     metadata={"channel": "message"})

# Recipient authentication
verifier = BlindedVerifier()
assert verifier.authenticate(
    proof,
    contact_public_key=record["contact_pubkey"],
    shared_seed=record["shared_seed"],
    session_id="m-001",
)
```

`BlindedVerifier.authenticate` enforces *both* checks:
1. `ZKVerifier.verify_proof(π)` — Schnorr soundness.
2. `proof['public_key'] == Y + t·G` (constant-time via `hmac.compare_digest`)
   — the pseudonym matches the expected contact for this session.

## Why both checks matter

A valid Schnorr proof on its own only attests "*some* party knows the secret
behind the key in this proof". The per-recipient pseudonym check binds the
proof to the *expected* contact. A different sender producing a perfectly
valid Schnorr proof under a different `Y'` will fail check 2.

## Threat-model summary

| Adversary | Defence |
|---|---|
| Malicious sender (impersonation) | Theorem 1 (unforgeability ⇐ DLog). |
| Honest-but-curious recipient (link this sender's deliveries) | Per-recipient blinding — `Y'` is uniform across deliveries to that recipient as `session_id` varies. |
| Colluding recipients (link across recipients) | Distinct `shared_seed`s → distinct `Y'` distributions; without a seed, `Y'` is uniform. |
| Global passive network observer | `(ε,δ)`-DP cover traffic — see [`privacy-model.md`](privacy-model.md). |
| Replay | Per-delivery commitment + receiver dedup — see [`commitment-registration.md`](commitment-registration.md). |

## Tests and benchmarks

- Unit tests: `tests/test_crypto.py`, `tests/test_blinding.py` (7 tests covering
  cross-recipient unlinkability, wrong-seed rejection, session mismatch,
  tampered-proof rejection).
- Quantitative FAR/FRR over forge / tamper / swap-key trials:
  `scripts/bench_security.py` (currently 0/0).
- Latency / sizes: `scripts/bench_crypto.py` (ZK gen ~0.85 ms, verify ~13 ms,
  proof ~216 B; see paper §Eval).

## Related

- [`commitment-registration.md`](commitment-registration.md) — per-delivery commitment + replay defence.
- [`mutual-authentication.md`](mutual-authentication.md) — running Tessera bidirectionally for mutual auth.
- [`privacy-model.md`](privacy-model.md) — the network-level (ε,δ)-DP guarantee.
