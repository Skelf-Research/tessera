# Commitment Registration

This document explains how customers register their commitments with organizations in Tessera, enabling verified call delivery.

## Overview

In Tessera, a **commitment** is a cryptographic hash derived from the customer's phone number (plus salt). Organizations need to know customer commitments to broadcast proofs to them. There are two approaches:

1. **Out-of-band registration** - Commitment shared through existing channels
2. **Direct registration** - Commitment registered directly to org's node API

## Out-of-Band Registration

The simplest and most privacy-preserving approach. The commitment exchange happens through the organization's existing customer relationship.

### Flow

```
┌─────────────┐                     ┌─────────────┐
│   Customer  │                     │     Org     │
│   (Mobile)  │                     │   (Bank)    │
└──────┬──────┘                     └──────┬──────┘
       │                                   │
       │  1. Generate commitment           │
       │  tessera proof commitment         │
       │  +1234567890                       │
       │                                   │
       │  2. Share via banking app         │
       │  ─────────────────────────────►   │
       │  "Register for verified calls"    │
       │                                   │
       │                                   │  3. Store in CRM
       │                                   │  customer_id → commitment
       │                                   │
       │  4. Subscribe to network          │
       │  tessera node start ...           │
       │                                   │
       │                                   │  5. Broadcast proof
       │  ◄─────────────────────────────   │  to commitment
       │  6. Receive proof                 │
       │                                   │
```

### Example

**Customer side:**

```bash
# Generate commitment
$ tessera proof commitment +1234567890
Input: +1234567890
Salt: a1b2c3d4e5f6...
Commitment: 7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d8c9b0a1f2e3d4c5b6a7f8e
Bucket: 42

# Subscribe to network
$ tessera-node start --type customer --id my-device --port 8102 \
    --peer core-1@seed.tessera.network:8100
```

**Customer shares commitment** via:
- Banking app settings ("Enable verified calls")
- Customer portal
- Phone call to support
- QR code scan

**Organization side:**

```python
# Bank's backend stores the commitment
customer_commitments = {
    "cust-12345": {
        "commitment": "7f8e9d0c1b2a...",
        "phone": "+1234567890",
        "registered_at": "2024-01-15"
    }
}

# When making a call, broadcast proof
proof = generate_proof_for_commitment(commitment)
broadcast_to_network(proof)
```

### Advantages

- **Privacy-preserving**: Tessera network never sees customer-org relationship
- **Simple**: Uses existing customer channels
- **Flexible**: Works with any org's existing systems

### Disadvantages

- Requires integration with org's customer portal/app
- Manual step for customer

---

## Direct Registration

Customer registers commitment directly with the org's node via HTTP API. The org must run at least one node with `--api-port`.

### Flow

```
┌─────────────┐                     ┌─────────────┐
│   Customer  │                     │  Org Node   │
│   (Mobile)  │                     │  (--api-port)│
└──────┬──────┘                     └──────┬──────┘
       │                                   │
       │  1. Generate commitment           │
       │                                   │
       │  2. POST /customers/register      │
       │  ─────────────────────────────►   │
       │  {customer_id, commitment}        │
       │                                   │
       │  ◄─────────────────────────────   │
       │  {status: "registered"}           │
       │                                   │
       │  3. Subscribe to network          │
       │  (with matching bucket/bloom)     │
       │                                   │
       │                                   │  4. POST /customers/{id}/broadcast
       │  ◄─────────────────────────────   │
       │  5. Receive proof                 │
       │                                   │
```

### API Endpoints

**Register commitment:**

```bash
POST /customers/register
{
  "customer_id": "cust-12345",
  "commitment": "7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d8c9b0a1f2e3d4c5b6a7f8e",
  "device_id": "iphone-abc123",
  "metadata": {
    "phone": "+1234567890",
    "name": "John Doe"
  }
}

Response:
{
  "status": "registered",
  "customer_id": "cust-12345",
  "commitment": "7f8e9d0c...",
  "device_id": "iphone-abc123",
  "total_devices": 1
}
```

**Get customer commitments:**

```bash
GET /customers/cust-12345/commitments

Response:
{
  "customer_id": "cust-12345",
  "commitments": ["7f8e9d0c..."],
  "devices": [
    {
      "commitment": "7f8e9d0c...",
      "device_id": "iphone-abc123",
      "registered_at": 1705334400
    }
  ]
}
```

**Broadcast to customer:**

```bash
POST /customers/cust-12345/broadcast
{
  "proof": {
    "bucket": 42,
    "bloom_fingerprint": "base64...",
    "ciphertext": "base64...",
    "nonce": "base64...",
    "timestamp": 1705334500,
    "org_hint": "acme-bank"
  }
}

Response:
{
  "status": "broadcast",
  "customer_id": "cust-12345",
  "devices": 1,
  "results": [
    {
      "device_id": "iphone-abc123",
      "commitment": "7f8e9d0c1b2a...",
      "notified": 1,
      "push": {"websocket": 1, "mqtt": true}
    }
  ]
}
```

**Remove commitment:**

```bash
DELETE /customers/cust-12345/commitments/7f8e9d0c...

Response:
{
  "status": "removed",
  "customer_id": "cust-12345",
  "commitment": "7f8e9d0c..."
}
```

### Example

**Start org node with API:**

```bash
export CALLDNS_JWT_SECRET="your-secret-key"
tessera-node start --type org --id acme-bank --port 8100 \
    --api-port 8101 \
    --peer core-1@seed.tessera.network:8100
```

**Customer registers (from mobile app):**

```python
import httpx

# Generate commitment locally
commitment = generate_commitment("+1234567890", salt)

# Register with org (JWT required)
response = httpx.post(
    "https://api.acme-bank.com:8101/customers/register",
    headers={"Authorization": f"Bearer {jwt_token}"},
    json={
        "customer_id": "cust-12345",
        "commitment": commitment.hex(),
        "device_id": get_device_id()
    }
)

# Subscribe to network
# (handled by mobile SDK)
```

**Org broadcasts proof:**

```python
# When agent calls customer
response = httpx.post(
    "http://localhost:8101/customers/cust-12345/broadcast",
    headers={"Authorization": f"Bearer {jwt_token}"},
    json={
        "proof": generate_proof(commitment)
    }
)
```

### Advantages

- **Automated**: No manual customer steps after initial setup
- **Multi-device**: Easy to register multiple devices
- **Real-time**: Immediate registration

### Disadvantages

- Org node stores customer-commitment mapping
- Requires org to run node with API port exposed

---

## Multi-Device Support

Both approaches support customers with multiple devices:

```bash
# Register phone
POST /customers/register
{"customer_id": "cust-12345", "commitment": "abc...", "device_id": "phone"}

# Register tablet
POST /customers/register
{"customer_id": "cust-12345", "commitment": "def...", "device_id": "tablet"}

# Broadcast reaches both devices
POST /customers/cust-12345/broadcast
```

Each device generates its own commitment (different salt), but they're all linked to the same customer ID.

---

## Security Considerations

### Commitment Generation

- Always use a random salt (minimum 16 bytes)
- Store salt securely on device
- Never transmit phone number directly

```python
import hashlib
import secrets

salt = secrets.token_bytes(16)
commitment = hashlib.sha256(phone.encode() + salt).digest()
```

### Registration Security

For direct registration:
- Use HTTPS for API calls
- Authenticate customer (OAuth, JWT, etc.)
- Rate limit registration endpoints
- Validate customer_id against org's customer database

### Privacy

- Commitments are one-way hashes - cannot reverse to phone number
- Org cannot see which other orgs a customer is registered with
- Network cannot see org-customer relationships (only bucket routing)

---

## Choosing an Approach

| Factor | Out-of-Band | Direct Registration |
|--------|-------------|---------------------|
| Privacy | Higher | Lower (org stores mapping) |
| Automation | Lower | Higher |
| Integration effort | Higher | Lower |
| Customer friction | Higher | Lower |
| Multi-device | Manual | Automatic |

**Recommendation:**

- **Banks/Financial services**: Out-of-band (regulatory preference for existing channels)
- **Healthcare**: Out-of-band (HIPAA considerations)
- **Telcos/Tech companies**: Direct registration (better UX)
- **Hybrid**: Offer both options to customers

---

## Mobile SDK Integration

The mobile SDKs handle most of this automatically:

```swift
// iOS example
let tessera = Tessera(orgNode: "https://api.acme-bank.com:8000")

// Generates commitment and registers
tessera.register(phone: "+1234567890", customerId: "cust-12345")

// Subscribes to network automatically
tessera.startListening { proof in
    // Handle incoming verified call
    showVerificationBadge(proof)
}
```

See the [SDK documentation](../sdks/) for platform-specific details.
