# Tessera

**Authenticated, metadata-private one-to-one delivery.** A sender proves identity
to a recipient with a Schnorr zero-knowledge proof under a per-recipient *blinded
pseudonym*; the proof is AES-GCM encrypted and routed over a bucketed broadcast
network whose cover traffic is calibrated to provide
**(ε,δ)-differentially-private** sender↔recipient metadata.

- **No central authority.** Pairwise local enrolment.
- **Cross-recipient unlinkability.** A recipient holds a per-contact `shared_seed`
  and recomputes the blinded pseudonym `Y' = Y + t·G` to authenticate; any party
  without the seed sees a uniform `Y'` per delivery.
- **Metadata privacy.** Load-independent shifted-Laplace cover traffic gives
  the per-bucket count `C_b = R_b + D_b` `(ε,δ)`-DP w.r.t. a single delivery event.

The protocol backs two papers (see `~/.claude/projects/-home-dipankar-Code-tessera/memory/tessera-paper-strategy.md`):

| Paper | Repo | Venue | Deadline |
|---|---|---|---|
| **A** — Authenticated, Metadata-Private Messaging | `../tessera-paper-msg/` | PoPETs 2027.2 | 31 Aug 2026 |
| **B** — Tessera-Agent (Verifiable AI-Agent Identity) | `../tessera-paper-agent/` *(Phase 3)* | USENIX Sec 2027 C2 | 26 Jan 2027 |

## Quick start

```bash
poetry install
poetry run pytest tests/ -q                                # 151 passed
poetry run python -m tessera.network.ws_server --port 8100 # serve a node
poetry run python -m tessera.deploy.cluster --nodes 5      # local cluster (mesh)
```

## Headline numbers (single-laptop, single node — see paper §Eval)

| | Number |
|---|---|
| ZK proof generation | ~0.85 ms |
| ZK proof verification | ~13 ms |
| Subscribe throughput | **326 ops/s** (4.5× the naive design) |
| Route throughput (~75 subs/bucket) | **440 ops/s** (vs. naive: did not complete in 120 s) |
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
```

## Status

- **Phase 1** *(this commit)* — code/SDK rename CallDNS → Tessera, 151 tests pass,
  live node serves over WebSocket.
- **Phase 2** *(next)* — Paper A reframe to messaging; submit PoPETs 2027.2.
- **Phase 3** — Tessera-Agent (delegation, scope-bound blinding, revocation);
  submit USENIX Security.

## Licence

MIT. © Dipankar Sarkar.
