# API Reference

This is the engineering reference for Tessera's Python API and the
WebSocket wire protocol exposed by `tessera.network.ws_server`. For the
end-to-end protocol see [`architecture.md`](architecture.md); for the
underlying primitives see [`authentication.md`](authentication.md).

---

## Python API

### `tessera.crypto.crypto_utils`

| Symbol | Purpose |
|---|---|
| `CryptoUtils.generate_keypair() → (int, bytes, SigningKey)` | SECP256k1 keypair. Returns `(x, Y, sk)` — long-term secret as int, public key as 64-byte raw point, ecdsa SigningKey object. |
| `CryptoUtils.hash_data(*args) → bytes` | SHA-256 over a sequence of strings / bytes / ints. |
| `ZKProver().generate_proof(x: int, Y: bytes, metadata: dict) → dict` | Produces `{"R": bytes, "s": int, "public_key": bytes, "metadata": dict}` (Schnorr / Fiat–Shamir over SECP256k1). |
| `ZKVerifier().verify_proof(proof: dict) → bool` | Returns True iff the Schnorr equation holds. |
| `SecureEncryption.encrypt(plaintext, key, additional_data=b"") → dict` | AES-256-GCM AEAD; returns `{"nonce", "ciphertext", "additional_data"}`. |
| `SecureEncryption.decrypt(encrypted_data: dict, key) → bytes` | Authenticated decryption (raises `EncryptionError` on tag failure). |

### `tessera.crypto.blinding` — per-recipient pseudonyms

| Symbol | Purpose |
|---|---|
| `derive_blinding(shared_seed: bytes, session_id: str) → int` | `t = H(seed ‖ session_id) mod q`. |
| `blind_public_key(Y: bytes, t: int) → bytes` | `Y' = Y + t·G`, 64-byte raw point. |
| `blind_private_key(x: int, t: int) → int` | `(x + t) mod q`. |
| `BlindedSender(x, Y).prove(seed, session_id, metadata) → dict` | One-call helper producing the blinded proof. |
| `BlindedVerifier().authenticate(proof, contact_public_key, shared_seed, session_id) → bool` | Verifies the Schnorr proof *and* checks the pseudonym matches the expected contact. Constant-time comparison. |

### `tessera.sdk.traffic_manager`

| Symbol | Purpose |
|---|---|
| `TrafficManager(padding_size=1024, cover_traffic_ratio=0.3)` | Legacy padding + proportional cover (kept for backward-compat; *not* metadata-private). |
| `DPCoverTraffic(epsilon=1.0, delta=1e-6, sensitivity=1, num_buckets=64, rng=None)` | Load-independent (ε,δ)-DP cover-traffic policy. Methods: `dummy_count_for_bucket()`, `dummy_counts(num_buckets)`, `expected_overhead_per_round()`, `published_counts(real_by_bucket)`. |

### `tessera.sdk.commitment_manager`

Manages the per-delivery commitment lifecycle
(`commit = H(Y' ‖ ephemeral ‖ session_id)`) — TTL'd records, fingerprint
generation for routing, matching against incoming proofs. See
[`commitment-registration.md`](commitment-registration.md).

### `tessera.network.decentralized` — canonical routing functions

**These are the single source of truth for routing-field derivation. Use them
on both the producer and consumer side or proofs will silently miss.**

| Symbol | Purpose |
|---|---|
| `compute_bucket(commitment, num_buckets=64) → int` | `int(SHA256(commitment)[:2]) mod num_buckets`. |
| `compute_fingerprint(commitment, timestamp) → bytes` | `SHA256(commitment ‖ window_start)[:8]` where `window_start = ⌊timestamp / 10⌋·10`. |
| `make_routing_fields(commitment, timestamp=None) → dict` | The producer's helper: returns `{bucket, bloom_fingerprint (b64), timestamp}`. |
| `class Subscription(commitment, linked_orgs=None)` | Builds the subscription a recipient registers with a relay (bucket, bloom filter, org hints, time window). `.to_dict()` for transport. |
| `class BloomFilter(size=1024, hash_count=3)` | Used by `Subscription` to make the per-call match efficient. |

### `tessera.network.async_node`

| Symbol | Purpose |
|---|---|
| `class AsyncDecentralizedNode(node_id, node_type, data_dir=None)` | The relay implementation. `await initialize()`, `await register_subscription(sid, sub_dict)`, `await route_proof(proof, from_peer=None)`, `await get_pending_proofs(sid)`, `await get_stats()`, `await shutdown()`. Holds in-memory `subscription_cache` and `_bloom_cache` for hot-path performance. |

### `tessera.network.ws_server`

| Symbol | Purpose |
|---|---|
| `class NodeWebSocketServer(node)` | Wraps an `AsyncDecentralizedNode` and exposes the WS wire protocol below. |
| `class WSPeerTransport(my_node_id)` | Cross-node gossip transport (peer_id → uri map, persistent connections, automatic reconnect). Wire with `node.set_send_handler(transport.send)`. |
| `serve(host, port, node_id, node_type, data_dir=None)` | Coroutine that starts the WS server. Also available as `python -m tessera.network.ws_server`. |

### `tessera.deploy.cluster`

```python
from tessera.deploy.cluster import LocalCluster

cluster = LocalCluster(n=5, topology="mesh")    # or "ring"
await cluster.start()
print(cluster.uris())            # {"node-0": "ws://...", ...}
await cluster.stop_node("node-2")
await cluster.start_node("node-2")
await cluster.stop()
```

CLI: `poetry run python -m tessera.deploy.cluster --nodes 5 --topology mesh`.

### `tessera.keystore`

PBKDF2-encrypted keystore (100 k iters), key rotation, file or encrypted
backends. Use the `EncryptedKeyStore` in any non-dev deployment.

---

## WebSocket wire protocol

Each message is one JSON object; responses are one JSON object per request.

| Request | Response |
|---|---|
| `{"type":"subscribe","subscriber_id":str,"subscription":<Subscription.to_dict()>}` | `{"type":"subscribed","subscriber_id":str}` |
| `{"type":"proof","proof":{...bucket, bloom_fingerprint, timestamp, ciphertext, nonce, org_hint?},"from_peer":?str}` | `{"type":"routed","notified":int}` |
| `{"type":"fetch","subscriber_id":str}` | `{"type":"proofs","proofs":[{...},...]}` |
| `{"type":"stats"}` | `{"type":"stats","stats":{...}}` |
| `{"type":"ping"}` | `{"type":"pong","timestamp":int}` |

Errors come back as `{"type":"error","message":str}`.

A reference Python client lives in `scripts/bench_throughput.py`. The
benchmark driver opens persistent connections (`websockets.connect` reused
across many requests) — opening one connection per op is the **wrong** way to
drive Tessera at load (caps you at ~30–70 ops/s).

---

## Tests as executable spec

The most current contract for the API is the test suite:

| File | What it pins |
|---|---|
| `tests/test_crypto.py` | ZK soundness across forge/tamper/swap-key. |
| `tests/test_blinding.py` | Per-recipient pseudonyms; cross-recipient unlinkability. |
| `tests/test_traffic.py` | `DPCoverTraffic` parameters, non-negativity, expected overhead, load-independence. |
| `tests/test_network_integration.py` | Subscribe / route / fetch on the in-process node. |
| `tests/test_ws_server.py` | The WS wire protocol round-trip. |
| `tests/test_multinode.py` | Two-node gossip end-to-end. |
| `tests/test_cluster.py` | 3-node mesh + churn resilience. |

```bash
poetry run pytest tests/ -q     # expect: 151 passed
```

## Related

- [`architecture.md`](architecture.md) — module-by-module tour.
- [`quickstart.md`](quickstart.md) — copy-paste examples.
- [`decentralized-architecture.md`](decentralized-architecture.md) — relay overlay design.
