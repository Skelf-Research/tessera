# Mutual Authentication

The base Tessera flow is one-way: a *sender* authenticates itself to a
*recipient*. Many applications want **mutual** authentication — both ends prove
identity to each other. Tessera supports that with two parallel one-way flows,
no new primitive needed.

## Setup

Both parties enrol mutually: each holds the other's public key and a shared
seed (the *same* seed works for both directions, since the per-delivery
session_id keeps the pseudonyms distinct).

```python
from tessera.crypto.crypto_utils import CryptoUtils
from tessera.crypto.blinding import BlindedSender, BlindedVerifier

# Long-term keypairs (each party generates their own)
x_A, Y_A, _ = CryptoUtils.generate_keypair()
x_B, Y_B, _ = CryptoUtils.generate_keypair()

# Pairwise enrolment (out-of-band) gives each party:
#   - the contact's public key
#   - a shared_seed (one shared between them)
seed_AB = b"seed-A-and-B-share"
record_at_A = {"contact_pubkey": Y_B, "shared_seed": seed_AB}  # about B
record_at_B = {"contact_pubkey": Y_A, "shared_seed": seed_AB}  # about A
```

## Mutual handshake (two proofs)

Each party assembles a `BlindedSender` for outbound and a `BlindedVerifier`
for inbound, then runs two one-way flows back-to-back, each with its own
`session_id`:

```python
A_sender, A_verifier = BlindedSender(x_A, Y_A), BlindedVerifier()
B_sender, B_verifier = BlindedSender(x_B, Y_B), BlindedVerifier()

# A → B
session_AB = "handshake-AB-001"
proof_AB = A_sender.prove(seed_AB, session_AB, metadata={"role": "init"})
assert B_verifier.authenticate(proof_AB, Y_A, seed_AB, session_AB)

# B → A  (different session_id; same seed)
session_BA = "handshake-BA-001"
proof_BA = B_sender.prove(seed_AB, session_BA, metadata={"role": "ack"})
assert A_verifier.authenticate(proof_BA, Y_B, seed_AB, session_BA)
```

After both authentications succeed, A and B have *mutually* authenticated.

## Properties

- **Authentication, both directions.** Theorem 1 in
  [`../research.md`](../research.md)
  applies independently to each direction.
- **Cross-recipient unlinkability still holds.** A's third party C (with a
  different `seed_AC`) cannot link any of A's deliveries to B based on the
  blinded pseudonyms it sees A use towards C.
- **Distinct session_ids matter.** Re-using a session_id across directions
  would produce the same `t` and hence the same `Y'` for both directions —
  not a soundness break, but conventionally a delivery's session_id should
  uniquely name *that* one delivery; pick `session_id` distinct per side.

## Use cases

- **Channel bootstrap before bulk traffic.** Mutual auth at handshake, then
  ordinary one-way Tessera flows for the message stream.
- **Application protocols where both ends are senders sometimes** (chat,
  collaborative tools): each side authenticates each of its outbound
  deliveries; the symmetric structure means no extra design beyond two
  parallel one-way flows.

## What this *isn't*

This is mutual *Tessera-style* authentication: each end binds to the other's
long-term key via the per-contact `shared_seed`. It is **not**:
- A key-exchange protocol (use Signal X3DH/Double-Ratchet or similar to
  produce the `shared_seed` if you don't already have one out-of-band).
- A non-interactive deniability primitive (the Schnorr signatures on
  `(Y', m)` are non-repudiable against the holder of the contact record).

## Related

- [`authentication.md`](authentication.md) — the single-direction primitive.
- [`commitment-registration.md`](commitment-registration.md) — per-delivery commitments and replay defence.
