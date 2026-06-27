# Architecture

Tessera is a one-to-one delivery protocol that gives sender authentication and
metadata privacy in the same primitive. This document is the engineer's tour of
how the parts fit together. The canonical spec lives in
[`../../tessera-paper-msg/spec/protocol_spec.md`](../../tessera-paper-msg/spec/protocol_spec.md).

## The 30-second picture

```
sender              network (relays)            recipient
 │                       │                          │
 │ blind:   Y'=Y+tG      │                          │
 │ prove:   π=(R,s)      │                          │
 │ commit:  H(Y'||…)     │                          │
 │ encrypt: AES-GCM      │                          │
 ├──────── bucket ───────► relays gossip ───────────►│
 │                       │ DP cover traffic added   │ match (bucket+bloom)
 │                       │                          │ decrypt → verify π
 │                       │                          │ authenticate Y' via seed
```

Three actors: **senders** (anyone who delivers), **recipients** (anyone who
receives, holding a per-contact `shared_seed`), and **relay nodes** (peer-to-peer,
no central authority). One-time pairwise enrolment is the same out-of-band step
Signal-style messengers already perform.

## Layers (Python package `tessera/`)

| Layer | Path | What it does |
|---|---|---|
| Crypto | `tessera/crypto/` | `ZKProver`/`ZKVerifier` (Schnorr Fiat–Shamir), `SecureEncryption` (AES-256-GCM AEAD), `blinding.py` (`BlindedSender`/`BlindedVerifier` — per-recipient pseudonyms). |
| SDK | `tessera/sdk/` | High-level `Sender`, `Verifier`, `commitment_manager` (`H(Y'‖ephemeral‖session_id)`), `traffic_manager` (incl. `DPCoverTraffic` mechanism). |
| Network | `tessera/network/` | `async_node.py` (in-memory subscription + parsed-bloom caches over `async_storage.py`'s single persistent SQLite connection), `ws_server.py` (WebSocket transport + `WSPeerTransport` gossip), `decentralized.py` (canonical routing functions: `compute_bucket`, `compute_fingerprint`, `make_routing_fields`), `dht.py` (Kademlia-style). |
| Deploy | `tessera/deploy/` | `LocalCluster` — N peered in-process nodes, mesh or ring, supports runtime `stop_node` / `start_node` for churn experiments. |
| Keystore | `tessera/keystore/` | PBKDF2-encrypted keystore (100 k iters), key rotation. |
| Service | `tessera/service/` | Flask REST + WS service (dev-grade). |

## End-to-end delivery (six steps)

1. **Enrol** (one-time, pairwise, out-of-band) — recipient stores sender's
   public key `Y` and a fresh `shared_seed`.
2. **Blind** — for each delivery, sender derives
   `t = H(seed ‖ session_id) mod q`, `Y' = Y + t·G`, `x' = x + t`.
3. **Commit** — sender registers `commit = H(Y' ‖ ephemeral ‖ session_id)` to
   the network.
4. **Encrypt** — sender encrypts `π = (R, s)` under a routing key derived from
   `commit`, and addresses it to `bucket = H(commit) mod 64`.
5. **Route** — relays gossip the encrypted proof, adding calibrated DP cover
   traffic per [`privacy-model.md`](privacy-model.md).
6. **Verify** — recipient matches by bloom fingerprint, decrypts, verifies `π`,
   and authenticates `Y' = Y + t·G` against `(Y, shared_seed, session_id)`.

## Key properties (and where each comes from)

| Property | Mechanism | Where |
|---|---|---|
| Sender authentication | Schnorr Fiat–Shamir proof of `x` | `crypto/crypto_utils.py` |
| Cross-recipient unlinkability | Per-recipient blinded pseudonym `Y'` | `crypto/blinding.py` |
| Replay resistance | Per-delivery commitment + receiver dedup | `sdk/commitment_manager.py` + `network/async_storage.py` |
| Network metadata privacy | (ε,δ)-DP cover traffic, load-independent | `sdk/traffic_manager.py::DPCoverTraffic` |
| Soundness over tamper / forge / swap-key | Schnorr binds (R, s, Y, m); FAR/FRR = 0 in tests | `tests/test_crypto.py`, `bench_security.py` |

## Why a persistent DB connection + caches

The naive design (one SQLite connection per op + per-candidate `get_subscription`
+ bloom-rebuild per candidate) was storage-bound at ~70 ops/s. The current code
holds **one long-lived `aiosqlite` connection serialised by a lock** (so
`synchronous=NORMAL` actually applies), keeps subscriptions and parsed
`BloomFilter` objects in memory, and lifts routing from O(occupancy) DB reads to
O(matches) in-memory checks + one queued INSERT per match. Result: subscribe
~326 ops/s, route ~440 ops/s. See `network/async_storage.py`,
`network/async_node.py`, and paper §Evaluation.

## What's not in scope here

- **Telephony binding** (PSTN / SIP / out-of-band call channel) — not in the
  current code; the messaging-pivot paper treats telephony as a possible
  application only.
- **Distributed DP-noise generation without a coordinator** — design space
  noted as future work in the paper.
- **Phase 3 (Tessera-Agent)** — delegation tokens, scope-bound blinding, and
  revocation will land after Paper A is submitted.

## Where to read next

- [`authentication.md`](authentication.md) — the proof-and-blinding mechanics in detail.
- [`privacy-model.md`](privacy-model.md) — the DP guarantee and threat model.
- [`decentralized-architecture.md`](decentralized-architecture.md) — the relay overlay.
- [`api.md`](api.md) — the Python SDK and the WS wire protocol.
