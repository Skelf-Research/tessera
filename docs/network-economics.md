# Tessera Network Economics

## Overview

Tessera uses a **Consortium + Fee Hybrid** model to incentivize core node operation while ensuring network sustainability and neutrality.

## The Challenge

Core nodes are essential infrastructure that:
- Route proofs between organizations and customers
- Maintain subscriptions and pending proof queues
- Provide high availability (24/7 operation)
- Cannot identify users (privacy by design)

Without incentives, operators have costs but no direct benefit, leading to free-rider problems.

## Consortium + Fee Hybrid Model

### Structure

```
┌─────────────────────────────────────────────────────────┐
│                   Tessera Foundation                     │
│                   (Non-profit governance)                │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ Bank A  │   │ Bank B  │   │ Bank C  │   Founding Consortium
   │ Core    │   │ Core    │   │ Core    │   (run core nodes)
   └─────────┘   └─────────┘   └─────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  Core Network │
              │  (shared)     │
              └───────┬───────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ Org D   │   │ Org E   │   │ Org F   │   Non-consortium orgs
   │ (pays)  │   │ (pays)  │   │ (pays)  │   (pay per-proof fees)
   └─────────┘   └─────────┘   └─────────┘
```

### Participant Roles

| Role | Contribution | Benefit |
|------|-------------|---------|
| **Founding Consortium** | Run 1+ core nodes | No per-proof fees, governance rights |
| **Foundation** | Governance, fee collection | Funds additional infrastructure |
| **Non-consortium Orgs** | Pay per-proof fees | Network access without node operation |
| **Customers** | None (free) | Verified call protection |

## Fee Structure

### Per-Proof Pricing

| Tier | Monthly Volume | Price per Proof |
|------|----------------|-----------------|
| Starter | 0 - 10,000 | £0.002 |
| Growth | 10,001 - 100,000 | £0.001 |
| Enterprise | 100,001 - 1,000,000 | £0.0005 |
| Custom | 1,000,000+ | Negotiated |

### Example Costs

| Organization Type | Monthly Calls | Monthly Cost |
|-------------------|---------------|--------------|
| Small credit union | 5,000 | £10 |
| Regional bank | 50,000 | £50 |
| National bank | 500,000 | £250 |
| Large enterprise | 2,000,000 | Negotiated |

### What's Included

- Proof broadcast to network
- Cover traffic (3 decoys per proof)
- 24-hour proof retention
- Push notification delivery
- Basic SLA (99.9% uptime)

### Additional Services (Optional)

| Service | Price |
|---------|-------|
| Extended retention (7 days) | +20% |
| Priority routing | +50% |
| Dedicated support | £500/month |
| Custom SLA (99.99%) | Negotiated |

## Founding Consortium

### Requirements

To join the founding consortium, organizations must:

1. **Run Infrastructure**
   - Minimum 2 core nodes (primary + failover)
   - 99.9% uptime SLA
   - Geographic distribution preferred

2. **Commit Resources**
   - Initial setup and ongoing operations
   - Participate in governance (quarterly meetings)
   - 2-year minimum commitment

3. **Meet Eligibility**
   - Regulated financial institution or equivalent
   - No competitive conflict of interest
   - Pass security audit

### Benefits

- **No per-proof fees** for own traffic
- **Governance voting rights** (1 vote per member)
- **Early adopter recognition**
- **Input on roadmap priorities**
- **Revenue share** from fee pool (optional)

### Governance

The consortium governs:
- Fee structure changes
- New consortium member admission
- Technical standards and protocols
- Foundation budget allocation
- Network upgrade decisions

Decisions require majority vote with quorum of 60%.

## Foundation Role

### Responsibilities

1. **Fee Collection & Distribution**
   - Collect fees from non-consortium orgs
   - Distribute to node operators (if applicable)
   - Fund additional infrastructure

2. **Network Operations**
   - Run additional core nodes as needed
   - Monitor network health
   - Coordinate incident response

3. **Governance Administration**
   - Facilitate consortium meetings
   - Maintain membership records
   - Publish transparency reports

4. **Ecosystem Development**
   - SDK maintenance
   - Documentation
   - Developer support

### Funding Allocation

| Category | Allocation |
|----------|------------|
| Infrastructure (additional nodes) | 40% |
| Development & maintenance | 30% |
| Operations & support | 20% |
| Reserve fund | 10% |

## Transition Path

### Phase 1: Bootstrap (Months 1-6)

- 3-5 founding consortium members
- Foundation operates 2-3 additional nodes
- Free tier for early adopters (first 1,000 proofs/month)
- Focus on onboarding and stability

### Phase 2: Growth (Months 7-18)

- Expand consortium to 10+ members
- Introduce fee structure
- Geographic expansion (EU, US nodes)
- Enterprise features

### Phase 3: Maturity (Month 19+)

- Self-sustaining fee revenue
- Consortium governance fully operational
- Consider additional incentive models
- International expansion

## Joining the Network

### For Organizations (Non-Consortium)

Non-consortium organizations run their own **org node** but connect to the consortium's core network. They don't need to run core nodes.

```
Small Org (e.g., credit union)
         │
         ▼
    ┌─────────┐
    │ Org Node │  ← They run this (with JWT auth for their customers)
    └────┬────┘
         │
         ▼
    Core Network   ← Consortium runs this (small org pays per-proof)
```

#### Setup Steps

```bash
# 1. Register with foundation
curl -X POST https://foundation.tessera.network/orgs/register \
  -d '{"name": "Acme Credit Union", "contact": "tech@acme-cu.com"}'

# 2. Receive network API key for billing
# 3. Configure and start org node
export CALLDNS_JWT_SECRET="your-jwt-secret"
export CALLDNS_NETWORK_API_KEY="key-from-foundation"

tessera-node start --type org --id acme-creditunion \
  --port 8100 --api-port 8101 \
  --peer core-1@network.tessera.org:8100 \
  --peer core-2@network.tessera.org:8100

# 4. Billing starts on first proof broadcast
```

#### Customer Registration

Customers register with the small org's org node (same as consortium orgs):

```python
# Customer's mobile app calls the org's API
import httpx

response = httpx.post(
    "https://api.acme-creditunion.com:8101/customers/register",
    headers={"Authorization": f"Bearer {jwt_token}"},
    json={
        "customer_id": "member-5678",
        "commitment": "abc123...",
        "device_id": "iphone-main"
    }
)
```

The org node stores commitments locally and handles all customer interactions.

#### What's Billed

| Action | Cost |
|--------|------|
| Customer registration | Free |
| Receiving proofs (customer → org) | Free |
| Broadcasting proofs (org → customer) | Per-proof fee |
| Cover traffic (decoys) | Included in per-proof fee |

Small orgs only pay when they broadcast proofs to customers (e.g., when the bank calls the customer).

### For Consortium Membership

1. **Expression of Interest**
   - Contact foundation@tessera.network
   - Provide organization details

2. **Technical Assessment**
   - Infrastructure review
   - Security audit
   - Capacity planning

3. **Legal Agreement**
   - Consortium membership agreement
   - SLA commitments
   - Governance participation

4. **Onboarding**
   - Node setup support
   - Integration testing
   - Go-live coordination

## Comparison with Alternatives

| Model | Pros | Cons |
|-------|------|------|
| **Consortium + Fee (chosen)** | Balanced, sustainable, neutral | Requires founding members |
| Pure fee-based | Simple economics | Central operator, trust issues |
| Pure consortium | No fees for members | Limited to consortium |
| Token/staking | Cryptoeconomic incentives | Regulatory complexity |
| Public good | No fees | Funding uncertainty |

## FAQ

### Why not make it completely free?

Infrastructure costs are real. Without sustainable funding:
- Node operators have no incentive
- Quality degrades over time
- Network becomes unreliable

The fee structure is designed to be minimal while ensuring sustainability.

### Why consortium instead of single operator?

- **Neutrality**: No single party controls the network
- **Trust**: Distributed operation reduces single point of failure
- **Governance**: Stakeholders have voice in decisions

### Can small organizations afford it?

Yes. At £0.002/proof:
- 1,000 calls/month = £2
- 5,000 calls/month = £10

This is negligible compared to fraud losses prevented.

### What prevents consortium from raising fees?

- **Governance**: Fee changes require majority vote
- **Competition**: Members can fork if fees unreasonable
- **Transparency**: All financials published quarterly

### How do customers benefit?

Customers pay nothing. They benefit from:
- Verified call protection
- Reduced fraud risk
- Better service (faster authentication)

Organizations pay because they benefit from:
- Reduced fraud losses
- Regulatory compliance
- Customer trust

## Contact

- **Consortium inquiries**: consortium@tessera.network
- **Organization signup**: onboarding@tessera.network
- **Technical support**: support@tessera.network
- **Foundation**: foundation@tessera.network
