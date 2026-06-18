# Tessera Privacy Model

This document describes the privacy guarantees provided by Tessera's decentralized architecture, focusing on the "last mile privacy" that protects customers even from the organizations they interact with.

## Core Principle: Separation of Knowledge

Tessera is designed so that **no single party has complete knowledge** of a call verification:

| Party | Knows | Does NOT Know |
|-------|-------|---------------|
| **Organization (Bank)** | Customer's commitment, proof content | If/when proof was received, customer's core node |
| **Core Nodes** | Bucket, bloom filter, routing | Customer identity, org identity, proof content |
| **Customer** | Everything about their own proofs | Other customers' activity |

## Architecture for Privacy

### Connection Pattern

```
┌─────────────┐                              ┌─────────────┐
│    Bank     │                              │  Customer   │
│  Org Node   │                              │   Mobile    │
└──────┬──────┘                              └──────┬──────┘
       │                                            │
       │  One-time registration                     │  Ongoing subscription
       │  (HTTPS to bank's API)                     │  (WebSocket to ANY core)
       │                                            │
       ▼                                            ▼
┌─────────────┐                              ┌─────────────┐
│  Bank's     │                              │    Core     │
│  API Port   │                              │    Nodes    │
└─────────────┘                              └─────────────┘
       │                                            ▲
       │                                            │
       │         Broadcast to network               │
       └────────────────────────────────────────────┘
                  (No direct connection)
```

**Critical design choice**: Customers connect to **core nodes**, not to their bank's node, for proof delivery. This ensures:

1. Bank cannot observe customer's connection patterns
2. Bank cannot confirm proof delivery
3. Bank cannot track when customer is "online"

### Why Not Direct Bank-to-Customer?

If customers connected directly to their bank's node for proofs:

❌ Bank sees when customer connects
❌ Bank can correlate connection times with calls
❌ Bank can confirm proof delivery
❌ Bank has full surveillance capability

With core node routing:

✅ Bank broadcasts blindly - no feedback
✅ Core nodes route by bucket - no identity
✅ Customer receives privately - unobservable
✅ No party has complete picture

## Privacy Guarantees

### For Customers

**What's protected:**
- Which organizations you're registered with (core nodes don't know)
- When you receive proofs (banks don't know)
- Your connection patterns (neither party knows)
- Proof contents (only you can decrypt)

**Practical meaning:**
- Your bank cannot build a profile of when you check calls
- A compromised core node cannot identify you
- No central log of caller-callee relationships exists

### For Organizations

**What's protected:**
- Customer lists (core nodes don't know who's registered)
- Call patterns to specific customers (routing is by bucket)
- Business relationships (hidden in bucket anonymity sets)

**Practical meaning:**
- Competitors cannot analyze your call patterns
- Regulators see compliance without customer lists
- Data breaches don't expose customer relationships

### Against Adversaries

**Compromised core node:**
- Sees: bucket numbers, bloom filters, encrypted proofs
- Cannot: identify customers, decrypt proofs, link to orgs

**Compromised org node:**
- Sees: their own customer commitments
- Cannot: confirm delivery, track customer activity

**Colluding core + org:**
- Even together they cannot confirm specific deliveries
- Bucket anonymity (1.5% of users) provides cover
- Decoy traffic adds noise

**Network observer:**
- Sees: encrypted WebSocket traffic
- Cannot: distinguish real proofs from decoys
- Cover traffic ratio: 3 decoys per real proof

## Technical Mechanisms

### 1. Bucket-Based Routing

Commitments are hashed into 64 buckets:
```python
bucket = int.from_bytes(commitment[:2], 'big') % 64
```

- Each bucket contains ~1.5% of all users
- Proofs are routed to buckets, not individuals
- Provides k-anonymity within bucket

### 2. Bloom Filter Matching

Within a bucket, bloom filters provide probabilistic matching:
```python
bloom = BloomFilter(commitment, size=1024, hashes=3)
```

- False positive rate ~1%
- Customer receives ~1-2 proofs per real call
- Cannot reverse bloom filter to commitment

### 3. End-to-End Encryption

Proofs are encrypted for the recipient's commitment:
```python
ciphertext = encrypt(proof_data, derive_key(commitment))
```

- Only commitment holder can decrypt
- Core nodes route encrypted blobs
- Bank cannot read after broadcast

### 4. Cover Traffic

Organizations broadcast decoy proofs:
```python
real_proof → bucket 42
decoy_1    → bucket 17  (random)
decoy_2    → bucket 55  (random)
decoy_3    → bucket 8   (random)
```

- 3 decoys per real proof (configurable)
- Indistinguishable from real proofs
- Prevents traffic analysis

### 5. Pull Model

Customers poll for proofs rather than receiving push:
```python
proofs = await fetch_pending_proofs(subscriber_id)
```

- Customer controls when to check
- No "online" indicator to network
- Proofs queued until fetched

## Threat Model

### What Tessera Protects Against

✅ **Mass surveillance** - No central database of calls
✅ **Bank overreach** - Cannot track customer behavior
✅ **Data breaches** - Commitments don't reveal phone numbers
✅ **Traffic analysis** - Cover traffic obscures patterns
✅ **Correlation attacks** - Bucket anonymity sets
✅ **Insider threats** - Separation of knowledge

### What Tessera Does NOT Protect Against

❌ **Targeted attacks on specific customer** - If adversary knows commitment, they can watch that bucket
❌ **Long-term statistical analysis** - Patterns may emerge over months
❌ **Endpoint compromise** - If phone is hacked, proofs are exposed
❌ **Org-side logging** - Bank knows they called you (outside Tessera)

### Mitigations for Known Limitations

**Targeted attacks:**
- Commitments are salted, not guessable from phone number
- Customer can rotate commitment periodically

**Statistical analysis:**
- Increase decoy ratio for high-security users
- Rotate buckets periodically (re-register with new salt)

**Endpoint security:**
- Proofs have TTL, auto-expire
- Secure enclave storage on mobile (platform-dependent)

## Comparison to Alternatives

### vs. Centralized Verification Service

| Aspect | Centralized | Tessera |
|--------|-------------|---------|
| Single point of failure | Yes | No |
| Operator sees all calls | Yes | No |
| Data breach impact | Catastrophic | Limited |
| Regulatory target | Yes | Distributed |

### vs. Direct Bank-to-Customer

| Aspect | Direct | Tessera |
|--------|--------|---------|
| Bank tracks customer | Yes | No |
| Delivery confirmation | Yes | No |
| Connection surveillance | Possible | Not possible |
| Requires bank online | Yes | No (async) |

### vs. Blockchain-Based

| Aspect | Blockchain | Tessera |
|--------|------------|---------|
| Public ledger | Yes | No |
| Permanent record | Yes | TTL expiry |
| Scalability | Limited | High |
| Privacy | Pseudonymous | Unlinkable |

## Regulatory Compliance

Tessera's privacy model supports compliance with:

**GDPR (EU):**
- Privacy by design (Article 25)
- Data minimization
- No processing beyond verification

**CCPA (California):**
- No sale of personal information
- Right to deletion (TTL expiry)

**FCA Consumer Duty (UK):**
- Protects customers from harm
- Doesn't create new surveillance risks

**HIPAA (US Healthcare):**
- No central PHI repository
- Cannot reconstruct patient-provider relationships

## Implementation Checklist

For organizations deploying Tessera:

- [ ] Run org node with `--api-port` for registration only
- [ ] Do NOT expose org node for proof delivery
- [ ] Use core network for all proof routing
- [ ] Enable decoy traffic (default: 3 per proof)
- [ ] Set appropriate proof TTL (default: 1 hour)
- [ ] Document privacy model for customers
- [ ] Regular security audits of node configuration

For customers:

- [ ] Generate commitment with random salt
- [ ] Connect to core nodes, not bank nodes
- [ ] Use pull model (fetch when needed)
- [ ] Rotate commitment periodically for high security
- [ ] Verify app connects to legitimate core nodes

## Summary

Tessera provides **last-mile privacy** through architectural separation:

1. **Banks broadcast but cannot observe** - no delivery confirmation
2. **Core nodes route but cannot identify** - only see buckets
3. **Customers receive but are unlinkable** - encrypted, anonymous

This ensures that even in adversarial conditions - compromised nodes, colluding parties, network surveillance - no single entity can fully deanonymize a customer or confirm specific call verifications.

The privacy is **structural**, not policy-based. It's not that we promise not to log - it's that the system is designed so logging wouldn't help.
