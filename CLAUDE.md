# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repo.

## What Tessera is

Tessera is the protocol implementation behind two papers (see strategy memo
`~/.claude/projects/-home-dipankar-Code-tessera/memory/`). The core primitive is
**authenticated, metadata-private, one-to-one delivery**: a sender proves identity
to a recipient using a Schnorr / Fiat–Shamir zero-knowledge proof under a per-call
*blinded pseudonym* `Y' = Y + tG` (`t = H(seed ‖ session_id) mod q`); the proof is
AES-GCM encrypted and routed over a bucketed broadcast network with calibrated
**(ε,δ)-differentially-private cover traffic**. No central authority; pairwise
local enrolment.

Two papers, same protocol:
- **Paper A** (`../tessera-paper-msg`): authenticated, metadata-private messaging
  → PoPETs 2027.2 (Aug 31, 2026).
- **Paper B** (`../tessera-paper-agent`, created Phase 3): verifiable AI-agent
  identity with cross-service unlinkability → USENIX Sec 2027 C2 (Jan 26, 2027).

The project was previously called CallDNS and framed for telecom; it has been
pivoted away from that domain (see memory).

## Dev commands

```bash
poetry install
poetry run pytest tests/ -q                       # expect: 151 passed
poetry run pytest tests/test_crypto.py -v
poetry run black tessera/ tests/                  # format
poetry run flake8 tessera/ tests/                 # lint
```

```bash
# run a node over WebSocket
poetry run python -m tessera.network.ws_server --port 8100

# multi-node cluster (mesh or ring)
poetry run python -m tessera.deploy.cluster --nodes 5 --topology ring
```

## Architecture

| Layer | Path | What |
|---|---|---|
| Crypto | `tessera/crypto/` | `ZKProver`/`ZKVerifier` (Schnorr FS), `SecureEncryption` (AES-GCM), `blinding.py` (per-call pseudonyms, `BlindedSender`/`BlindedVerifier`) |
| SDK | `tessera/sdk/` | `Sender`, `Verifier`, `commitment_manager`, `traffic_manager` (incl. `DPCoverTraffic`) |
| Network | `tessera/network/` | `async_node.py` (in-memory cache + persistent SQLite via `async_storage.py`), `ws_server.py` (WS transport + `WSPeerTransport` gossip), `decentralized.py` (canonical routing: `compute_bucket`, `compute_fingerprint`, `make_routing_fields`), `dht.py` |
| Deploy | `tessera/deploy/` | `LocalCluster` (N peered in-process nodes, mesh/ring, runtime churn) |
| Keystore | `tessera/keystore/` | PBKDF2-encrypted keystore, key rotation |
| Service | `tessera/service/` | Flask REST + WS service |

## Experiment harnesses (Paper A artifact)

Live under `scripts/` and emit results to `../tessera-paper-msg/results/` (will be
renamed `../tessera-paper-msg/results/` in Phase 2):

- `bench_crypto.py` (E1) — proof gen/verify/AES latency + sizes
- `bench_security.py` (E6) — verifier FAR/FRR
- `bench_throughput.py` (E4) — persistent-connection node throughput
- `analysis/anonymity_sim.py` (E2) — bucket k-anonymity + bloom FPR
- `analysis/linkability_sim.py` (E3) — DP cover-traffic privacy/overhead
- `analysis/churn_sim.py` (E5) — mesh vs ring delivery under churn
- `analysis/leakage_compare.py` (E7) — comparative leakage matrix (will be
  reworked for messaging observers in Phase 2)

## Domain conventions

- The protocol uses **sender / recipient** terminology. The SDK class is
  `Sender` (formerly `Caller`); `Verifier` is unchanged. Avoid telecom-flavoured
  terms (caller, callee, PSTN, SIP, STIR/SHAKEN) in new code/docs.
- Cross-platform SDKs in `sdks/` are auxiliary; the paper artifact is the Python
  package + scripts + tests.

## Testing strategy

Tests under `tests/` exercise crypto soundness (incl. tamper/forge regression),
the DP cover-traffic mechanism, key blinding, the routing layer end-to-end (incl.
multi-node gossip and churn), and the WS transport. Adding new mechanisms should
add: (a) a fast unit-test in `tests/test_*.py`, and (b) where applicable a
quantitative harness in `scripts/`.

## Production-grade notes

- `EncryptedKeyStore` for prod; PBKDF2 with 100k iters; configurable rotation.
- Flask web service is dev-grade; behind a real WSGI server for prod.
- The single-writer SQLite design (one persistent connection + lock,
  `synchronous=NORMAL`) is the verified bottleneck mitigation (see paper §Eval).
