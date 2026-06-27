# Changelog

All notable changes to Tessera will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-27

### Changed (pivot away from telecom)
- **Project renamed CallDNS → Tessera.** The protocol is unchanged; only the
  framing moves. The repository is now `Skelf-Research/tessera`; the Python
  package is `tessera/`; the SDK class is `Sender` (formerly `Caller`); the
  blinded variant is `BlindedSender` (formerly `BlindedCaller`); cross-platform
  SDK packages renamed (`com.tessera.sdk`, iOS `Sources/Tessera`).
- **Framing pivoted to authenticated metadata-private messaging.** Telephony /
  caller-ID is no longer the primary domain; the protocol is positioned as a
  one-to-one delivery primitive that gives sender authentication *and*
  metadata privacy, between any two pre-enrolled parties. Telephony is one
  possible application, mentioned only in a single related-work footnote.
- All telephony-specific docs (industry-financial-services, industry-healthcare,
  industry-insurance-pensions, industry-legal-services, customer-onboarding,
  use_cases) removed. Architecture and API docs rewritten concise in the
  messaging framing.

### Added
- **Per-recipient key blinding** for cross-recipient unlinkability
  (`tessera/crypto/blinding.py`: `derive_blinding`, `blind_public_key`,
  `blind_private_key`, `BlindedSender`, `BlindedVerifier`; 7 tests).
- **Differentially-private cover traffic** (`tessera/sdk/traffic_manager.py::DPCoverTraffic`):
  load-independent shifted-Laplace noise giving (ε,δ)-DP on per-bucket counts.
  Replaces the previous load-proportional cover (which was *not* metadata-private).
- **Real multi-node networking**: `tessera/network/ws_server.py` (WebSocket
  transport + `WSPeerTransport` gossip), `tessera/deploy/cluster.py::LocalCluster`
  (N peered in-process nodes, mesh/ring, runtime churn).
- **Canonical routing functions** in `tessera/network/decentralized.py`
  (`compute_bucket`, `compute_fingerprint`, `make_routing_fields`) — single
  source of truth shared by producers and consumers; fixes a routing-field
  mismatch that previously broke 14 integration tests.
- Experiment harnesses E1–E7 in `scripts/` (crypto microbench, anonymity sim,
  linkability sim, throughput driver, churn sim, security FAR/FRR, leakage
  comparison) producing the paper's tables and figures.
- Paper draft + reproduction artefact in sibling repo
  `sarkar-dipankar/tessera-paper-msg` (target PoPETs 2027.2, 31 Aug 2026).

### Fixed
- `Subscription.__init__` referenced `self.time_window` before assignment —
  the class always raised. Fixed by reordering.
- Async test fixtures decorated `@pytest.fixture` under pytest-asyncio STRICT
  mode received un-awaited `async_generator`s. Fixed to `@pytest_asyncio.fixture`.
- Routing field derivation diverged between producer and consumer (bucket and
  bloom-fingerprint formulas didn't agree). Fixed via the canonical functions
  above.

### Performance
- `AsyncNodeStorage` rewritten to hold **one long-lived aiosqlite connection**
  serialised by a lock, so `synchronous=NORMAL` actually applies (previously,
  per-op connections reverted to `FULL` and fsync'd every commit).
- `AsyncDecentralizedNode` adds `subscription_cache` and parsed-`BloomFilter`
  cache so the route hot path is O(matches) in-memory checks rather than
  O(occupancy) DB reads + bloom rebuilds per candidate.
- Net effect: subscribe **73 → 326 ops/s** (4.5×, p99 1.8 s → 90 ms); route
  at ~75 subs/bucket from *did-not-finish-in-120 s* → 10.9 s @ 440 ops/s.

### Test suite
- 100 → **151 tests passing**. New: `test_blinding.py`, `test_multinode.py`,
  `test_cluster.py`, `test_ws_server.py`; extensions to `test_crypto.py`
  (TestProofRobustness) and `test_traffic.py` (TestDPCoverTraffic).

---

## [0.1.0] - 2024-09-23 (CallDNS)

Original release of the project under its prior name *CallDNS*, framed as a
zero-knowledge caller-verification system for telecom. Initial pieces:

- Schnorr / Fiat–Shamir zero-knowledge identity proof (SECP256k1).
- AES-GCM authenticated encryption for proof routing.
- Bloom-filter based proof matching.
- Padding + cover traffic for traffic-analysis resistance (load-proportional;
  later shown insufficient — superseded by the DP mechanism in 0.2.0).
- PBKDF2-encrypted keystore with rotation.
- Flask REST + WS service.
- 100 unit tests.

[0.2.0]: https://github.com/Skelf-Research/tessera/releases/tag/v0.2.0
[0.1.0]: https://github.com/Skelf-Research/tessera/releases/tag/v0.1.0
