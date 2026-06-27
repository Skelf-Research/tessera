# Decentralized Architecture

Tessera's relay overlay is a peer-to-peer network with **no central authority**.
This page describes the topology, the routing primitives, the gossip mechanism,
and the measured behaviour under churn.

## Roles

| Role | Implementation | What it does |
|---|---|---|
| Sender | `tessera.sdk.sender.Sender` | Produces blinded proofs, submits to any reachable relay. |
| Recipient (subscriber) | `tessera.network.decentralized.Subscription` registered against a relay | Subscribes to its bucket; matches incoming proofs by bloom filter; fetches matched proofs. |
| Relay node | `tessera.network.async_node.AsyncDecentralizedNode` served by `tessera.network.ws_server` | Stores proofs (TTL'd), indexes subscriptions by bucket, routes matched proofs to subscribers, gossips to peers. |

Any participant can run a relay. Relays know each other through pairwise
peer connections (`WSPeerTransport`).

## Routing primitives (canonical, shared)

All sender/recipient agreement runs through three functions in
`tessera/network/decentralized.py` — **these are the single source of truth**
for bucket and fingerprint derivation:

```python
compute_bucket(commit)        # → int in [0, 64)
compute_fingerprint(commit,t) # → 8 bytes, floored to a global 10s grid
make_routing_fields(commit)   # → {bucket, bloom_fingerprint, timestamp}
```

A proof's `bucket` is what the relays route on. The
`bloom_fingerprint` is what subscribers match on. Producers (senders) and
consumers (recipients) **must** derive both via the canonical functions or
they will silently miss each other (the routing bug that caused the project's
14-test regression in early development).

## Storage

`tessera/network/async_storage.py` uses **one long-lived aiosqlite connection
serialised by an asyncio lock** with `PRAGMA synchronous=NORMAL` (so commits
do *not* fsync per write — the fix that took subscribe throughput from ~70 to
~326 ops/s; see paper §Evaluation). Schema:

- `proofs(proof_id, bucket, bloom_fingerprint, proof_data, …, expires_at)` —
  TTL'd proof storage; indexed by bucket+timestamp and by expires_at.
- `subscriptions(subscriber_id, bucket, bloom_filter, org_hints, time_window, …)`
  — recipient registrations.
- `pending_proofs(subscriber_id, proof_id, queued_at)` — per-subscriber queues
  pre-fetch.
- `peers`, `stats`, `config`.

In addition, the node holds two in-memory caches: `subscription_cache` (so the
hot path does not hit storage per candidate) and `_bloom_cache` (parsed
`BloomFilter` objects so each match doesn't rebuild the 1024-bit filter).

## Gossip transport

`tessera/network/ws_server.py::WSPeerTransport` is the cross-node link:

- Each relay holds a (peer_id → uri) map.
- `node.set_send_handler(transport.send)` wires the node's
  `_gossip_to_peers` into the transport.
- `send(peer, proof)` opens a lazy persistent WebSocket to the peer, forwards
  `{"type":"proof", "proof":…, "from_peer": <me>}`, drains the `routed` ack,
  and reuses the connection on the next send. Dropped connections reconnect
  on next send.
- The receiving relay's `route_proof` excludes the `from_peer` when
  re-gossiping (and the protocol-level proof dedup terminates any
  remaining loops).

## Topology

| Topology | Use | Failure behaviour |
|---|---|---|
| **Mesh** (default) | Production / robust delivery | 100 % delivery up to 50 % nodes offline in our experiments — one hop to any live node. |
| **Ring** | Experiments / minimal overhead | Segments once ≥2 nodes are offline (50–60 % delivery at 25–50 % offline). |

Quantified by **E5** (`scripts/analysis/churn_sim.py`) and Figure E5 in the
paper. Implication: production deployments should default to mesh or
similarly-connected peering, or replicate subscriptions across more than one
relay.

## Local cluster (development / experiments)

`tessera/deploy/cluster.py::LocalCluster` brings up N peered in-process nodes
with one command:

```bash
poetry run python -m tessera.deploy.cluster --nodes 5 --topology mesh
```

Programmatically:

```python
from tessera.deploy.cluster import LocalCluster
cluster = LocalCluster(n=5, topology="mesh")
await cluster.start()
print(cluster.uris())          # {"node-0": "ws://127.0.0.1:..", …}
await cluster.stop_node("node-2")   # simulate churn
await cluster.start_node("node-2")  # bring it back
await cluster.stop()
```

This is the harness used by `tests/test_cluster.py` and the E5 experiment.

## WS wire protocol (one node)

JSON request → JSON response over a WebSocket:

| Request | Response |
|---|---|
| `{"type":"subscribe","subscriber_id":…,"subscription":{…}}` | `{"type":"subscribed","subscriber_id":…}` |
| `{"type":"proof","proof":{…},"from_peer":…?}` | `{"type":"routed","notified": <int>}` |
| `{"type":"fetch","subscriber_id":…}` | `{"type":"proofs","proofs":[…]}` |
| `{"type":"stats"}` | `{"type":"stats","stats":{…}}` |
| `{"type":"ping"}` | `{"type":"pong","timestamp":…}` |

Full Python-side API in [`api.md`](api.md).

## What's **not** here

- A real DHT-based peer-discovery protocol: a Kademlia scaffold exists in
  `tessera/network/dht.py` but the production overlay uses configured peer
  lists. Wiring DHT discovery into the live overlay is future work.
- Distributed DP-noise generation across relays without a coordinator —
  open design space called out in the paper.

## Related

- [`commitment-registration.md`](commitment-registration.md) — what relays route on.
- [`network-economics.md`](network-economics.md) — incentive model for running a relay.
- [`api.md`](api.md) — the Python and WS APIs.
- Paper §Evaluation: E4 (throughput) and E5 (churn) numbers.
