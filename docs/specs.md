# Specifications

This page is an index of the authoritative spec material. The canonical specs
and proofs live in the **paper repo** (`../../tessera-paper-msg/`):

| Document | Location | Covers |
|---|---|---|
| Protocol & threat model | [`spec/protocol_spec.md`](../../tessera-paper-msg/spec/protocol_spec.md) | Notation, primitives, per-recipient pseudonym, full delivery flow, threat model, resolved design decisions. |
| Metadata-privacy guarantee | [`spec/metadata_privacy.md`](../../tessera-paper-msg/spec/metadata_privacy.md) | Adversary model, the (ε,δ)-DP cover-traffic mechanism, overhead, distributed-noise considerations. |
| Game-based proofs | [`formal/security_proofs.md`](../../tessera-paper-msg/formal/security_proofs.md) | Unforgeability (EUF-CMA ⇐ DLog), HVZK / Fiat–Shamir privacy, replay resistance. |
| Symbolic model | [`formal/tessera.pv`](../../tessera-paper-msg/formal/tessera.pv) | ProVerif Dolev–Yao model (Q1 key secrecy, Q2 injective agreement). |
| Paper draft | [`main.tex`](../../tessera-paper-msg/main.tex) | Full assembled paper (PoPETs 2027.2 target). |

For implementation-side documentation see [`architecture.md`](architecture.md)
and the Python SDK reference in [`api.md`](api.md).
