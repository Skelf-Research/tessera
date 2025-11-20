# CallDNS Decentralized Architecture

## Overview

CallDNS uses a decentralized network architecture that provides **privacy by design** - no single node can determine who is calling whom. This document explains how the system achieves both privacy and scalability.

## Privacy Guarantees

### Core Claim

> **CallDNS cannot identify the specific recipient of a call.** Organizations broadcast proofs with cover traffic to multiple buckets, and customers subscribe to buckets containing their commitment. No node in the network can correlate callers to callees.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PROOF BROADCAST FLOW                             │
└─────────────────────────────────────────────────────────────────────┘

Organization calls Customer
         │
         ▼
┌─────────────────┐
│  Generate Proof │
│  Bucket: 42     │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Add Cover       │  Generate decoy proofs for buckets 17, 63, 8
│ Traffic         │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Broadcast ALL   │  Core nodes receive 4 proofs
│ to Network      │  Cannot tell which is real
└─────────────────┘
         │
         ▼
    Core Nodes
    ┌─────┬─────┬─────┬─────┐
    │ B42 │ B17 │ B63 │ B8  │  Route to bucket subscribers
    └──┬──┴──┬──┴──┬──┴──┬──┘
       │     │     │     │
       ▼     ▼     ▼     ▼
    Subs   Subs   Subs   Subs   Each bucket has ~1000 subscribers
       │
       ▼
   Customer matches bloom filter → Decrypts → Verified call!
```

### What Each Party Knows

| Party | Knows | Does NOT Know |
|-------|-------|---------------|
| **Organization** | Customer's commitment, bucket | Other subscribers in bucket |
| **Core Node** | Proof went to bucket 42 (and decoys to 17, 63, 8) | Which bucket has real proof, which subscriber matched |
| **Customer** | Proof matched their commitment | Other proofs in their bucket |
| **Network Observer** | Traffic patterns | Any relationships (all encrypted + cover traffic) |

---

## Traffic Reduction Layers

Customer devices receive only a tiny fraction of global traffic through layered filtering:

```
Global Traffic (100%)
         │
         ▼
┌─────────────────────┐
│ Layer 1: Bucket     │  64 buckets → 1.5% of traffic
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Layer 2: Org Hints  │  3 linked orgs → 0.0045%
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Layer 3: Time       │  Last 10 min → 0.00075%
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Layer 4: Bloom      │  1% false positive → 0.0000075%
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Layer 5: Pull Model │  Fetch only when notified
└─────────────────────┘
         │
         ▼
    ~1-2 proofs to verify locally
```

### Scalability Numbers

| Global Scale | Proofs/Hour | Per Customer (Pull Model) |
|--------------|-------------|---------------------------|
| 10,000 calls/hour | 10,000 | 1-2 when notified |
| 100,000 calls/hour | 100,000 | 1-2 when notified |
| 1,000,000 calls/hour | 1,000,000 | 1-2 when notified |

---

## Node Types

### Core Nodes

Run by CallDNS. High-availability nodes that:
- Route proofs between network participants
- Manage customer subscriptions
- Store pending proofs for pull model
- Gossip proofs to peer core nodes

```python
from calldns.network.decentralized import DecentralizedNode, NodeType

core = DecentralizedNode(
    node_id="core1.calldns.network",
    node_type=NodeType.CORE
)
```

### Organization Nodes

Run by banks, healthcare providers, etc. These nodes:
- Generate and broadcast proofs
- Add cover traffic (decoy proofs)
- Connect to multiple core nodes

```python
from calldns.network.decentralized import DecentralizedNode, NodeType, PrivacyPreservingBroadcaster

org_node = DecentralizedNode(
    node_id="org_barclays",
    node_type=NodeType.ORGANIZATION
)

broadcaster = PrivacyPreservingBroadcaster(org_node, num_decoys=3)
```

### Customer Nodes

Lightweight clients for mobile/desktop apps:
- Subscribe to buckets matching their commitment
- Provide bloom filter for fine-grained filtering
- Pull proofs when notified
- Verify proofs locally

```python
from calldns.network.decentralized import CustomerNodeClient

client = CustomerNodeClient(
    commitment=my_commitment,
    linked_orgs=["org_barclays", "org_nhs"]
)

# Get subscription data to send to core node
subscription = client.get_subscription_data()
```

---

## Subscription Model

### Customer Subscription

```python
subscription = {
    "bucket": 42,                    # Coarse routing (1 of 64)
    "bloom_filter": "base64...",     # Fine filtering (1% FP rate)
    "org_hints": ["org_barclays"],   # Only these orgs (optional)
    "since_timestamp": 1699900000    # Only recent proofs
}
```

### Privacy Analysis

| Field | Privacy Implication |
|-------|---------------------|
| `bucket` | Core node knows customer is in 1 of 64 groups (~1.5% of users) |
| `bloom_filter` | Cannot reverse to commitment (false positives provide cover) |
| `org_hints` | Core node knows customer's service providers (acceptable trade-off) |
| `since_timestamp` | Core node knows customer is active |

---

## Cover Traffic

Organizations add decoy proofs to prevent traffic analysis:

```python
broadcaster = PrivacyPreservingBroadcaster(org_node, num_decoys=3)

# Real proof goes to bucket 42
# Decoys go to random buckets (e.g., 17, 63, 8)
result = broadcaster.broadcast_with_cover(proof)

# result:
# {
#     "real_bucket": 42,
#     "decoy_buckets": [17, 63, 8],
#     "total_broadcasts": 4,
#     "privacy_ratio": 0.75  # 75% are decoys
# }
```

### Privacy Levels

| Decoys | Guess Probability | Bandwidth Cost |
|--------|-------------------|----------------|
| 1 | 50% | 2x |
| 3 | 25% | 4x |
| 7 | 12.5% | 8x |
| 15 | 6.25% | 16x |

Recommended: **3 decoys** (25% guess probability, 4x bandwidth)

---

## Pull Model

For mobile efficiency, customers use a pull model:

### Flow

```
1. Org broadcasts proof to network
2. Core node matches to subscriber's bucket + bloom filter
3. Core node queues proof for subscriber
4. Core node sends push notification: "You have a verified call"
5. Customer app wakes, pulls pending proofs
6. Customer verifies locally
```

### Implementation

```python
# Core node side
pending = core_node.get_pending_proofs(subscriber_id)

# Customer side
proofs = client.pull_proofs(core_node_url)
for proof in proofs:
    if client.verify_proof_locally(proof):
        # Decrypt and verify signature
        show_verification_ui(proof)
```

### Benefits

- **Zero idle traffic**: Customer only connects when needed
- **Battery efficient**: No persistent WebSocket
- **Works offline**: Proofs queued until customer pulls

---

## Network Topology

### Core Network

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│ Core 1  │◄───►│ Core 2  │◄───►│ Core 3  │
└────┬────┘     └────┬────┘     └────┬────┘
     │               │               │
     └───────────────┼───────────────┘
                     │
              Fully connected mesh
              (all cores see all proofs)
```

### Organization Connection

```
Organization Node
      │
      ├──► Core 1
      ├──► Core 2
      └──► Core 3

(Connect to multiple cores for reliability)
```

### Customer Connection

```
Customer Node
      │
      └──► Core 1 (primary)
           Core 2 (fallback)

(Minimal connections, pull model)
```

---

## Commitment Exchange

The organization still needs the customer's commitment to encrypt proofs. This happens **out-of-band**:

### Option 1: Via Bank App

```
1. Customer opens bank app
2. App generates commitment
3. App sends commitment to bank's backend
4. Bank stores commitment locally

Privacy: Bank knows commitment, network doesn't know mapping
```

### Option 2: QR Code

```
1. Customer generates commitment + QR code
2. Customer shows QR to bank (in branch or via app)
3. Bank scans and stores

Privacy: Same as above
```

### Option 3: Derived Commitment (Advanced)

```python
# Both parties derive from shared secret
commitment = derive_commitment(
    shared_secret,      # Established during onboarding
    timestamp,          # Current hour
    sequence_number     # Call count
)

# Commitment rotates, preventing long-term correlation
```

---

## Security Considerations

### Threat Model

| Threat | Mitigation |
|--------|------------|
| Core node logs all traffic | Cover traffic + bloom filters prevent correlation |
| Network observer monitors traffic | All proofs encrypted, decoys indistinguishable |
| Bucket intersection attack | Large buckets (1000+ users), org hints are optional |
| Long-term statistical analysis | Commitment rotation (advanced), cover traffic ratio |

### What We DON'T Protect Against

- Customer voluntarily revealing their commitment
- Organization revealing their customer list
- Compromise of customer's device

### Honest Privacy Claim

> CallDNS provides **practical privacy** through layered defenses: bucket anonymity sets, bloom filter ambiguity, cover traffic, and pull-based retrieval. A motivated adversary with access to core node logs could narrow possibilities but cannot definitively identify specific caller-callee relationships without additional information.

---

## Deployment

### Running a Core Node

```bash
# Install dependencies
pip install calldns

# Start core node
python -c "
from calldns.network.decentralized import DecentralizedNode, NodeType

node = DecentralizedNode('core1', NodeType.CORE)
# Add peer connections, start listening...
"
```

### Organization Integration

```python
from calldns.network.decentralized import (
    DecentralizedNode,
    NodeType,
    PrivacyPreservingBroadcaster
)
from calldns.sdk import Caller

# Setup
org_node = DecentralizedNode("org_barclays", NodeType.ORGANIZATION)
broadcaster = PrivacyPreservingBroadcaster(org_node, num_decoys=3)
caller = Caller()

# Make verified call
def make_call(customer_commitment: bytes, metadata: dict):
    # Generate proof
    proof = caller.generate_call_proof(metadata=metadata)

    # Encrypt for customer
    encrypted = caller.encrypt_proof_for_callee(
        proof, customer_commitment, metadata
    )

    # Add bucket info
    encrypted["bucket"] = compute_bucket(customer_commitment)
    encrypted["org_hint"] = "org_barclays"
    encrypted["timestamp"] = int(time.time())

    # Broadcast with cover traffic
    broadcaster.broadcast_with_cover(encrypted)
```

### Customer App Integration

```python
from calldns.network.decentralized import CustomerNodeClient
from calldns.sdk import Verifier

# Setup
client = CustomerNodeClient(
    commitment=my_commitment,
    linked_orgs=["org_barclays", "org_nhs"]
)
verifier = Verifier()

# Register subscription with core node
subscription = client.get_subscription_data()
requests.post(f"{CORE_URL}/subscribe", json={
    "subscriber_id": my_device_id,
    "subscription": subscription
})

# When push notification received, pull proofs
proofs = requests.get(f"{CORE_URL}/proofs/{my_device_id}").json()

# Filter and verify locally
for proof in client.filter_proofs(proofs):
    if verifier.verify_encrypted_call_proof(proof):
        show_verification_banner(proof)
```

---

## Comparison: Centralized vs Decentralized

| Aspect | Centralized | Decentralized |
|--------|-------------|---------------|
| **Privacy** | Service can see relationships | No node sees relationships |
| **Trust** | Trust the service operator | Trust no single party |
| **Scalability** | Vertical (bigger servers) | Horizontal (more nodes) |
| **Complexity** | Simpler | More complex |
| **Latency** | Lower | Slightly higher (gossip) |

---

## Future Enhancements

1. **Commitment rotation**: Automatic rotation per time period
2. **Mixnet routing**: Onion routing for even stronger privacy
3. **Customer-run relays**: Customers contribute bandwidth
4. **Zero-knowledge proofs of bucket membership**: Prove you're in a bucket without revealing which

---

*CallDNS Decentralized - Privacy by architecture, not policy*
