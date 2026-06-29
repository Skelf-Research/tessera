# Tessera Documentation

Tessera is a one-to-one delivery protocol providing **sender authentication and
metadata privacy together** (see top-level [`README.md`](../README.md) for the
elevator pitch). These docs are for engineers building on or contributing to
the implementation.

## Start here

| Doc | What |
|---|---|
| [`quickstart.md`](quickstart.md) | Install, run a node, send and verify a proof, run a local cluster. |
| [`architecture.md`](architecture.md) | The end-to-end picture: crypto / SDK / network / deploy layers. |
| [`specs.md`](specs.md) | Pointers to the authoritative protocol spec, formal proofs, and paper. |

## Protocol and security

| Doc | What |
|---|---|
| [`authentication.md`](authentication.md) | How a sender proves identity to a recipient: Schnorr ZK + per-recipient blinded pseudonym. |
| [`commitment-registration.md`](commitment-registration.md) | The per-delivery commitment scheme that binds proof to delivery and prevents replay. |
| [`mutual-authentication.md`](mutual-authentication.md) | Running two Tessera flows in opposite directions for mutual sender↔recipient authentication. |
| [`privacy-model.md`](privacy-model.md) | The (ε,δ)-DP cover-traffic guarantee, per-recipient pseudonyms, threat model. |

## Network

| Doc | What |
|---|---|
| [`decentralized-architecture.md`](decentralized-architecture.md) | Relay overlay, bucketed broadcast, gossip, churn behaviour. |
| [`network-economics.md`](network-economics.md) | Incentive design for a no-central-authority relay overlay. |

## Integration

| Doc | What |
|---|---|
| [`api.md`](api.md) | Python SDK reference: `Sender`, `Verifier`, `BlindedSender`, `BlindedVerifier`, `LocalCluster`. |
| [`ui.md`](ui.md) | Cross-platform SDK UI components (Android / iOS / RN / Web / Flutter). |

## Research artifacts

Formal foundations, security proofs, and experiment harness summaries live in
[`research.md`](../research.md). The experiment harnesses themselves are in
[`scripts/`](../scripts/) and emit results to [`results/`](../results/).
