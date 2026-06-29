# Specifications

This page indexes the authoritative spec material. The formal foundations
and protocol specification live in [`research.md`](../research.md):

| Document | Location | Covers |
|---|---|---|
| Protocol & threat model | [`research.md`](../research.md) | Notation, primitives, per-recipient pseudonym, full delivery flow, threat model. |
| Metadata-privacy guarantee | [`research.md`](../research.md) | Adversary model, the (ε,δ)-DP cover-traffic mechanism, overhead, distributed-noise considerations. |
| Security properties | [`research.md`](../research.md) | Unforgeability (EUF-CMA ⇐ DLog), HVZK / Fiat–Shamir privacy, replay resistance. |
| Experiment harnesses | [`research.md`](../research.md) | E1–E7 reproduction instructions and headline numbers. |

For implementation-side documentation see [`architecture.md`](architecture.md)
and the Python SDK reference in [`api.md`](api.md).
