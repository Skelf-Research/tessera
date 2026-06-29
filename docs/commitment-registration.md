# Commitment Registration

The per-delivery **commitment** binds a proof to one specific delivery, drives
the routing fingerprint, and is the lever for replay defence. This page
explains what a commitment is, how it is registered, and how the receiver uses
it.

## What a commitment is

For each delivery the sender computes

```
commit = H(Y' ‖ ephemeral_key ‖ session_id)
```

where `Y'` is the per-recipient blinded pseudonym
(see [`authentication.md`](authentication.md)), `ephemeral_key` is a fresh
random scalar, and `session_id` identifies the delivery. The commitment is
**fresh per delivery** (fresh `ephemeral_key` + `session_id` → unique with
overwhelming probability) and **bound to the pseudonym** (changing `Y'` after
the fact breaks the commitment).

## Routing fields derived from the commitment

Both sides agree on the routing by deriving these from `commit` via the
**canonical functions** in `tessera/network/decentralized.py`
(`compute_bucket`, `compute_fingerprint`, `make_routing_fields`):

| Field | Definition | Used by |
|---|---|---|
| `bucket` | `int(SHA256(commit)[:2]) mod 64` | relay routing |
| `bloom_fingerprint` | `SHA256(commit ‖ window_start)[:8]`, where `window_start = ⌊timestamp / 10⌋·10` | recipient matching |
| `timestamp` | wall-clock seconds at send time | freshness check |

Producers (the sender) and consumers (the subscribing recipient) **must** use
the same canonical functions — the routing field mismatch that caused the
14-test regression early in the project was exactly the failure of this
invariant. `make_routing_fields(commitment)` is the producer helper.

## Subscription side

A recipient builds a `Subscription` (`tessera/network/decentralized.py`) that
combines the commitment's `bucket`, a per-subscription `BloomFilter`
(1024 bits, 3 hashes) populated with `compute_fingerprint(commit, t)` for each
10-second window in the last `time_window` seconds (default 600), and the
recipient's listed `linked_orgs`. The subscription is registered with one or
more relays (e.g. via the WS `subscribe` message); the relay indexes it under
its `bucket`.

When a proof arrives in that bucket, `AsyncDecentralizedNode._matches_subscription_data`
checks (a) the delivery is within the time window, (b) the org-hint matches
(if any), and (c) the proof's `bloom_fingerprint` is in the cached parsed
filter.

## Replay defence

Replay reduces to two requirements, both met:

1. **Commitment freshness.** Fresh `ephemeral_key` and `session_id` per
   delivery make `commit` unique with overwhelming probability. A replayed
   `π` carries an already-consumed `commit`.
2. **Receiver-side dedup.** `AsyncNodeStorage` keeps a TTL'd record of every
   `proof_id` it has stored; `route_proof` rejects already-seen proofs in
   constant time. Outside the time window the recipient's freshness check
   rejects regardless.

Formally: see Theorem 3 in [`../research.md`](../research.md).

## Lifecycle

```
sender                                  relay(s)                     recipient
  │ commit = H(Y'||eph||sid)              │                              │
  │ make_routing_fields(commit) →         │                              │
  │   {bucket, bloom_fingerprint, ts}     │                              │
  │ encrypted π carries those             │                              │
  ├──── proof ──────────────────────────► │                              │
  │                                       │  store (TTL); index bucket   │
  │                                       │  gossip to peers             │
  │                                       │  match subscribers in bucket │
  │                                       │ ──────── matched proof ──────► fetch
  │                                       │                              │ decrypt π
  │                                       │                              │ verify Schnorr
  │                                       │                              │ BlindedVerifier check
```

`commit` is therefore both the routing key and the freshness anchor.

## Related

- [`authentication.md`](authentication.md) — Schnorr proof + per-recipient pseudonym.
- [`decentralized-architecture.md`](decentralized-architecture.md) — relay bucketing and gossip.
- Canonical functions: `tessera/network/decentralized.py::{compute_bucket, compute_fingerprint, make_routing_fields}`.
