# Network Economics

The Tessera relay overlay has **no central operator**. This page sketches the
incentive structure that makes a peer-to-peer relay viable, what we measure /
have decided in the code, and what is left to design.

## Why this matters

Metadata-private routing has real costs:
- **CPU / I/O.** Each relay stores TTL'd encrypted proofs, indexes them by
  bucket, matches subscriptions, gossips to peers, and emits calibrated DP
  cover traffic.
- **Bandwidth.** Cover traffic is the dominant cost in steady state; the
  expected per-round overhead is ≈ B·μ dummy proofs where μ = (1/ε)·ln(1/(2δ)).
  At B=64, ε=1, δ=1e-6 this is ≈ 840 dummy proofs per 30 s round per relay.
- **Disk.** A single SQLite file holds proofs for their TTL (1 h default) plus
  subscriptions and pending queues. Modest at small scale.

So someone has to run the relays. The design space is who, and why.

## Who runs relays

Tessera makes the relay overlay symmetric — anyone can run one. The
realistic deployment modes (none mutually exclusive):

| Mode | Relay operator | Why they bear the cost |
|---|---|---|
| **Self-hosted** | The sender or recipient organisation | Direct control; no third-party dependency; the cost is just operating one more service. |
| **Federated (NGO / consortium)** | Privacy-focused NGOs, universities, foundations | Mission alignment; the cost is amortised across a community. |
| **Paid relay providers** | Commercial operators | Recipients pay for SLA-backed, geo-distributed relays. The market resembles email / push-notification relays today. |
| **Embedded in user devices** | End-user device acting as its own relay | For small groups / personal use; the device only sees its own buckets. |

A user is free to subscribe to one or many relays simultaneously (different
relays for different contacts, for redundancy, or for jurisdictional
diversity).

## What discourages free-riding

- Per-relay bookkeeping is local (subscriptions, proofs, peers) — a relay
  cannot extract identity information from the traffic it carries, so it
  cannot monetise the metadata it has access to.
- Refusing to gossip a proof is detectable by the recipient (it simply does
  not arrive); a recipient subscribed to more than one relay routes around
  unresponsive ones.
- Cover-traffic generation is decentralised; a relay that under-contributes
  noise degrades only its own bucket's privacy locally (until cover from other
  relays / participants compensates). A robust **distributed noise generation
  protocol that tolerates a malicious minority** is open future work (called
  out in the paper).

## What discourages bad behaviour

- **No central authority to bribe.** The recipient's authentication check
  rests on the per-contact `shared_seed`, not on anything the network knows.
- **Dropped or delayed proofs are visible.** Recipients can detect persistent
  failure-to-deliver from a particular relay and switch.
- **Forgery is impossible.** A relay cannot synthesise a valid Schnorr proof
  for a contact it doesn't have the secret for (Theorem 1 in
  [`../../tessera-paper-msg/formal/security_proofs.md`](../../tessera-paper-msg/formal/security_proofs.md));
  the relay's role is transport, not minting.

## Reputation and discovery

The current code uses configured peer lists and pairwise peer connections
(`tessera/network/ws_server.py::WSPeerTransport`). A reputation overlay
(uptime, gossip-correctness, freshness of state) is a natural addition; the
`tessera/network/dht.py` Kademlia scaffold is the obvious substrate for
discovery once it's wired into the production overlay. Both are deferred to
future work.

## Measured costs (single node, dev laptop)

From paper §Evaluation:

| Op | Throughput | p99 latency |
|---|---|---|
| Subscribe | ~326 ops/s | ~90 ms |
| Route (~75 subs/bucket) | ~440 ops/s | ~128 ms |
| ZK proof verify (the receiver hot path) | ~77 ops/s | not yet optimised |

The optimised storage layer (one persistent connection, `synchronous=NORMAL`,
in-memory subscription + bloom caches) is what makes a relay's per-op cost
small enough that the bandwidth cost of DP cover traffic dominates.

## What we have **not** built

- A real reputation system.
- An incentive token / payment layer.
- A discovery DHT that lives.
- A distributed noise-generation protocol robust to a malicious minority.

These are all reasonable future-work directions; the protocol is designed so
they can be added without changing the core authentication and privacy
guarantees.

## Related

- [`decentralized-architecture.md`](decentralized-architecture.md) — relay topology, gossip, churn behaviour.
- [`privacy-model.md`](privacy-model.md) — DP cover-traffic bandwidth cost.
- Paper §Limitations — distributed noise generation as open work.
