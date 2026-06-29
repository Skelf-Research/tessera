# Tessera

**Open-source privacy protocol for authenticated, metadata-private messaging.**

A sender proves identity to a recipient using a Schnorr zero-knowledge proof
under a per-recipient *blinded pseudonym*; the proof is AES-GCM encrypted and
routed over a bucketed broadcast network whose cover traffic is calibrated to
provide **(ε,δ)-differentially-private** sender↔recipient metadata.

[![Tests](https://github.com/Skelf-Research/tessera/actions/workflows/ci.yml/badge.svg)](https://github.com/Skelf-Research/tessera/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## Why Tessera

Existing secure-messaging systems force a trade-off:

- **Signed messaging** (Signal, WhatsApp) authenticates the sender but the
  central server sees the full social graph — who messages whom, when, and how
  often.
- **Metadata-private messaging** (Vuvuzela, Stadium, Talek) hides the graph but
  the recipient cannot identify the sender at all — no authentication.

**Tessera closes this gap.** Zero unintended metadata leaks, zero
authentication gaps, no central authority.

| | Routing observer | Network eavesdropper | Recipient | Colluding recipients | Sender auth |
|---|---|---|---|---|---|
| Signed messaging | 5 leaks | timing only | intended | none | yes |
| Metadata-private messaging | none | none | none | none | **missing** |
| **Tessera** | none | none | intended | none | **yes** |

## Install

```bash
# with uv (recommended)
uv pip install tessera

# or with pip
pip install tessera
```

For development:

```bash
git clone https://github.com/Skelf-Research/tessera.git
cd tessera
uv sync
uv run pytest tests/ -q                                # 151 passed
```

## Quick start

```python
from tessera.crypto.crypto_utils import CryptoUtils
from tessera.crypto.blinding import BlindedSender, BlindedVerifier

# One-time per sender: long-term keypair.
x, Y, _ = CryptoUtils.generate_keypair()

# Enrolment (pairwise, out-of-band): both ends agree on a contact seed.
seed = b"shared-with-this-recipient"

# Sender produces a delivery proof under a per-recipient blinded pseudonym.
sender = BlindedSender(x, Y)
proof = sender.prove(seed, session_id="msg-001",
                     metadata={"channel": "message"})

# Recipient authenticates the blinded pseudonym against the enrolment record.
verifier = BlindedVerifier()
ok = verifier.authenticate(proof, contact_public_key=Y,
                           shared_seed=seed, session_id="msg-001")
assert ok   # True
```

A different seed (any other recipient) cannot recompute the pseudonym, so the
sender's deliveries to *different* recipients are unlinkable.

## Run a node

```bash
uv run python -m tessera.network.ws_server --port 8100
```

## Local cluster (mesh or ring)

```bash
uv run python -m tessera.deploy.cluster --nodes 5 --topology ring
```

## Key properties

- **No central authority.** Pairwise local enrolment — the same out-of-band
  step Signal-style messengers already perform.
- **Cross-recipient unlinkability.** A recipient holds a per-contact
  `shared_seed` and recomputes `Y' = Y + t·G` to authenticate; any party without
  the seed sees a uniform `Y'` per delivery.
- **Metadata privacy.** Load-independent shifted-Laplace cover traffic gives
  the per-bucket count `C_b = R_b + D_b` `(ε,δ)`-DP w.r.t. a single delivery.
- **Replay resistance.** Per-delivery commitment freshness + receiver dedup.
- **Soundness.** FAR/FRR = 0 across tamper, swap-key, forge, and replay trials.

## Performance

| | Number |
|---|---|
| ZK proof generation | ~0.85 ms |
| ZK proof verification | ~13 ms |
| Subscribe throughput | **326 ops/s** (4.5× the naive design) |
| Route throughput (~75 subs/bucket) | **440 ops/s** |
| FAR / FRR over tamper, swap-key, forge, replay | **0 / 0** |
| Adversary linking AUC under DP cover, ε=0.1 | 0.526 (≤ ε-DP ceiling 0.548) |
| Churn delivery rate, full mesh, 50% nodes offline | **100%** |

## Repository layout

```
tessera/
  crypto/        Schnorr / Fiat-Shamir, AES-GCM, per-recipient key blinding
  sdk/           Sender, Verifier, commitment_manager, traffic_manager (DPCoverTraffic)
  network/       async_node + persistent SQLite, ws_server, WSPeerTransport, canonical routing
  deploy/        LocalCluster launcher (mesh / ring, runtime churn)
  keystore/      PBKDF2-encrypted keystore with rotation
  service/       Flask REST + WS service
scripts/         Experiment harnesses (E1–E7) and load-test driver
tests/           151 tests: crypto soundness, DP mechanism, routing, gossip, churn, transport
sdks/            Cross-platform clients (Android / iOS / RN / Web / Flutter) — auxiliary
docs/            Engineering documentation
```

## Documentation

| Doc | What |
|---|---|
| [Quickstart](docs/quickstart.md) | Install, run a node, send and verify a proof, run a local cluster. |
| [Architecture](docs/architecture.md) | The end-to-end picture: crypto / SDK / network / deploy layers. |
| [Authentication](docs/authentication.md) | How a sender proves identity: Schnorr ZK + per-recipient blinded pseudonym. |
| [Privacy Model](docs/privacy-model.md) | The (ε,δ)-DP cover-traffic guarantee, per-recipient pseudonyms, threat model. |
| [Commitment Registration](docs/commitment-registration.md) | Per-delivery commitment scheme and replay defence. |
| [Mutual Authentication](docs/mutual-authentication.md) | Running two Tessera flows in opposite directions. |
| [Decentralized Architecture](docs/decentralized-architecture.md) | Relay overlay, bucketed broadcast, gossip, churn behaviour. |
| [Network Economics](docs/network-economics.md) | Incentive design for a no-central-authority relay overlay. |
| [API Reference](docs/api.md) | Python SDK reference + WS wire protocol. |
| [Research](research.md) | Formal foundations, security proofs, experiment harnesses. |

## License

MIT. © Dipankar Sarkar.