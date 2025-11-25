# CallDNS

[![PyPI version](https://badge.fury.io/py/calldns.svg)](https://badge.fury.io/py/calldns)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Regulatory-Grade Caller Verification for Financial Services and Beyond**

A zero-knowledge caller verification system designed to help regulated industries meet compliance requirements while protecting against voice fraud, deepfakes, and caller ID spoofing.

## The Compliance Challenge

Financial institutions and regulated entities face increasing pressure from multiple fronts:

- **FCA Consumer Duty (UK)**: Firms must act to deliver good outcomes for retail customers, including protection from fraud
- **Reg E / CFPB (US)**: Financial institutions bear liability for unauthorized transactions, including those initiated via social engineering
- **GDPR/CCPA**: Privacy requirements conflict with traditional verification methods that expose personal data
- **PSD2/SCA**: Strong customer authentication requirements extend to all customer touchpoints
- **MiFID II**: Communication recording and verification requirements for financial advice
- **TCPA**: Compliance obligations around outbound calling and consent verification

Voice-based social engineering attacks cost financial services billions annually, yet traditional caller ID is trivially spoofed via SS7 vulnerabilities. CallDNS provides cryptographic caller verification that satisfies regulatory requirements while preserving customer privacy.

## Last-Mile Privacy

CallDNS is architected so that **no single party has complete knowledge** of a verification:

```
Bank → broadcasts proof → Core Network → routes by bucket → Customer
         (cannot confirm              (cannot identify        (only they
          delivery)                    customer)               can decrypt)
```

### Privacy Guarantees

| Party | Knows | Cannot Know |
|-------|-------|-------------|
| **Organization** | Customer's commitment | If/when proof received |
| **Core Nodes** | Bucket, bloom filter | Customer or org identity |
| **Customer** | Full proof details | Other customers' activity |

### Why This Matters

- **Banks cannot surveil customers** - no delivery confirmation, no "online" tracking
- **Core nodes cannot deanonymize** - route by bucket (1.5% of users), not identity
- **No central database** - cannot reconstruct caller-callee relationships
- **Structural privacy** - it's not policy, it's architecture

Customers register commitments with their bank (one-time), then connect to **any core node** for proof delivery. Even if core nodes are compromised or collude with banks, they cannot link customers to organizations or confirm specific deliveries.

See [Privacy Model](docs/privacy-model.md) for detailed threat analysis.

## How CallDNS Addresses Compliance

### Regulatory Alignment

| Regulation | Requirement | CallDNS Solution |
|------------|-------------|------------------|
| **FCA Consumer Duty** | Protect customers from foreseeable harm | Cryptographic proof prevents impersonation fraud |
| **GDPR Article 25** | Privacy by design | Zero-knowledge proofs verify without exposing PII |
| **PSD2 SCA** | Strong authentication for transactions | Adds cryptographic layer to voice channel |
| **MiFID II** | Audit trail for communications | Immutable proof records with timestamps |
| **SOX/GLBA** | Internal controls and data protection | Secure key management with rotation and audit logs |
| **HIPAA** | Patient data protection | No central registry of caller-callee relationships |

### Key Compliance Features

- **Audit Trail**: Cryptographic proofs provide non-repudiable evidence of caller identity
- **Privacy by Design**: GDPR-compliant verification without storing or transmitting PII
- **Key Management**: Enterprise-grade key rotation, HSM support, and secure backup
- **Monitoring & Logging**: Security event logging with sensitive data sanitization
- **Data Minimization**: System cannot reconstruct caller-callee relationship graphs
- **Consent Management**: Proof generation requires explicit caller action

## Industry Use Cases

### Financial Services

#### Bank-to-Customer Verification
Protect customers from vishing attacks while meeting FCA Consumer Duty:
```python
# Customer receives call claiming to be from bank
# Opens banking app → sees cryptographic verification status
# "Verified: NatWest Corporate Treasury called at 14:32"
```

#### Customer-to-Bank Verification
Streamline contact center authentication:
```kotlin
// Android app - verified call button
VerifiedCallButton(
    phoneNumber = "+44 800 123 4567",
    destinationId = "natwest-uk",
    destinationName = "NatWest Customer Service",
    onCallInitiated = { proof ->
        // Proof broadcast, dialer opens automatically
    }
)
// Contact center receives: "Verified customer: John Smith"
```

#### Investment Advice Calls (MiFID II)
Provide auditable proof for regulated communications:
```kotlin
// Financial advisor app - generate proof before call
val proof = CallDNS.generateProof(
    callContext = CallContext(
        callerId = advisorId,
        metadata = mapOf(
            "firm_reference" to "FCA123456",
            "call_purpose" to "investment_advice"
        )
    )
)
// Proof stored for 7-year MiFID II record retention
```

#### Fraud Prevention (Reg E Compliance)
Reduce liability exposure from social engineering:
```javascript
// Contact center integration
const verification = await callDNS.verifyIncomingCall(callerId);
if (!verification.isValid) {
  // Flag for enhanced authentication before processing transactions
  requireStepUpAuth();
}
```

### Healthcare (HIPAA)

Verify calls without exposing patient relationships:
```swift
// Healthcare provider app
CallVerificationView(
    callContext: CallContext(
        callerId: providerNPI,
        callType: .voipCall,
        metadata: ["hipaa_compliant": true]
    )
)
// No central log of provider-patient communications
```

### Insurance & Pensions

Support vulnerable customer protections:
```python
# Pension provider outbound call
# Customer can verify legitimacy via provider portal
# Meets TPR requirements for member communications
```

### Legal Services (SRA Compliance)

Verify solicitor identity for client communications:
```javascript
// Law firm client portal
const widget = new CallDNSWidget('#verification-panel');
await widget.show({
  callerId: solicitorSRANumber,
  callType: 'VOICE_CALL',
  displayText: 'Verified: Smith & Partners LLP'
});
```

## Installation

```bash
pip install calldns
```

## Quick Start

### Running a Network (Quickstart)

```bash
# Clone and setup
git clone https://github.com/dipankar/calldns.git
cd calldns
poetry install

# Run quickstart demo
./scripts/quickstart.sh
```

This starts a core node and organization node locally for testing.

### Node CLI Commands

```bash
# Start a core node (public, with rate limiting)
calldns-node start --type core --id core-1 --port 8100 --api-port 8101 --rate-limit 60

# Start an organization node (with JWT authentication)
export CALLDNS_JWT_SECRET="your-secret-key"
calldns-node start --type org --id acme-bank --port 8100 --api-port 8101 \
  --peer core-1@localhost:8100

# Start a customer node
calldns-node start --type customer --id device-123 --port 8102 \
  --peer core-1@localhost:8100

# Check node status
calldns-node status --port 8100

# List connected peers
calldns-node peers --port 8100
```

**Authentication Model:**
- **Core nodes** are public (no auth) with IP-based rate limiting
- **Org nodes** require JWT tokens for customer registration endpoints
- See [Authentication Documentation](docs/authentication.md) for details

### Proof Management CLI

```bash
# Generate a commitment from phone number
calldns-proof commitment +1234567890

# Subscribe to proofs
calldns-proof subscribe --commitment <hex> --node localhost:8101

# Broadcast a proof
calldns-proof broadcast --bucket 42 --fingerprint <hex> --ciphertext <hex> --node localhost:8101

# Fetch pending proofs
calldns-proof fetch --subscriber-id device-123 --node localhost:8101

# Watch for proofs in real-time
calldns-proof watch --subscriber-id device-123 --node localhost:8101
```

### FastAPI Service

```bash
# Start the API service
calldns-api

# Or with custom host/port
uvicorn calldns.service.api:app --host 0.0.0.0 --port 8000
```

API endpoints:
- `POST /proofs/broadcast` - Broadcast a proof
- `POST /subscriptions/{id}` - Register subscription
- `GET /subscriptions/{id}/proofs` - Fetch pending proofs
- `WS /ws/{id}` - WebSocket for real-time delivery
- `GET /docs` - Interactive API documentation

### Python SDK
```python
from calldns.sdk import Caller, Verifier

# Generate a zero-knowledge proof
caller = Caller()
proof = caller.generate_call_proof(metadata={"purpose": "verification"})

# Verify the proof
verifier = Verifier()
is_valid = verifier.verify_call_proof(proof)
```

### Async Node API
```python
import asyncio
from calldns.network.async_node import AsyncDecentralizedNode
from calldns.network.decentralized import NodeType

async def main():
    # Create and initialize node
    node = AsyncDecentralizedNode(
        node_id="my-node",
        node_type=NodeType.CORE,
        data_dir="./data/my-node"
    )
    await node.initialize()

    # Register subscription
    await node.register_subscription("sub-1", {
        "bucket": 42,
        "bloom_filter": "<base64>",
        "org_hints": ["bank-a"],
        "time_window": 600
    })

    # Route proof
    notified = await node.route_proof(proof)

    # Cleanup
    await node.shutdown()

asyncio.run(main())
```

## Documentation

For detailed documentation, see the [docs](docs/) directory:

- [Privacy Model](docs/privacy-model.md) - Last-mile privacy guarantees
- [Authentication](docs/authentication.md) - JWT and rate limiting configuration
- [Bidirectional Verification](docs/bidirectional-verification.md) - Customer↔Bank verification flows
- [Commitment Registration](docs/commitment-registration.md) - Customer onboarding flows
- [Decentralized Architecture](docs/decentralized-architecture.md) - Network design
- [Network Economics](docs/network-economics.md) - Consortium + fee model for sustainability
- [Node Management UI](docs/ui.md) - Web UI for node operators
- [Quick Start Guide](docs/quickstart.md)
- [API Reference](docs/api.md)
- [Architecture Overview](docs/architecture.md)

## Deployment

### Docker Compose (Development)

```bash
# Start the network
docker-compose up -d

# Scale core nodes
docker-compose up -d --scale core-1=3

# With monitoring (Prometheus + Grafana)
docker-compose --profile monitoring up -d

# View logs
docker-compose logs -f core-1
```

### Kubernetes (Production)

```bash
# Deploy to Kubernetes
kubectl apply -k deploy/kubernetes/

# Check status
kubectl -n calldns get pods

# View logs
kubectl -n calldns logs -f statefulset/calldns-core

# Scale API
kubectl -n calldns scale deployment/calldns-api --replicas=3
```

### Load Testing

```bash
# Run benchmarks
python scripts/benchmark.py --node ws://localhost:8100 --scale medium

# Scales: small (100 ops), medium (1000 ops), large (5000 ops)
```

### TLS Configuration

```bash
# Generate self-signed certificates
python -c "from calldns.cli.tls_transport import generate_self_signed_cert; generate_self_signed_cert('cert.pem', 'key.pem', 'my-node')"

# Start node with TLS
calldns-node start --type core --id core-1 --port 8100 --api-port 8101 \
  --cert cert.pem --key key.pem
```

### Core Components

1. **Zero-Knowledge Proofs**: Schnorr-based implementation for fast verification
2. **Privacy Layer**: Traffic padding, cover traffic, and commitment-based routing
3. **Network Layer**: Scalable proof matching with bloom filters
4. **Client SDK**: Easy integration for app developers
5. **Key Management**: Secure key storage, rotation, and backup
6. **Monitoring**: Comprehensive logging and security monitoring

### API Reference

#### Caller
```python
from calldns.sdk import Caller

caller = Caller()
proof = caller.generate_call_proof(metadata)
```

#### Verifier
```python
from calldns.sdk import Verifier

verifier = Verifier()
is_valid = verifier.verify_call_proof(proof)
```

## Security & Compliance Architecture

CallDNS provides enterprise-grade security designed for regulated environments:

### Cryptographic Foundation
- **SECP256k1 Elliptic Curve**: Same cryptographic standard as financial-grade systems
- **Schnorr Zero-Knowledge Proofs**: Verify identity without revealing sensitive data
- **AES-GCM Authenticated Encryption**: AEAD encryption for all sensitive data
- **PBKDF2 Key Derivation**: 100,000 iterations for password-based key protection

### Enterprise Security Features
- **Key Rotation**: Configurable automatic rotation (default: 30 days)
- **HSM Support**: Integration points for hardware security modules
- **Secure Backup/Recovery**: Encrypted key snapshots with audit trails
- **No Central Registry**: Architectural privacy - system cannot map relationships

### Compliance Controls
- **Audit Logging**: Security-focused logging with PII sanitization
- **Access Controls**: Role-based access to cryptographic operations
- **Data Retention**: Configurable proof retention for regulatory requirements
- **Incident Response**: Security event monitoring and alerting

## Performance

- **Proof Generation**: ~1-2ms
- **Proof Verification**: ~2-3ms
- **Proof Size**: ~96 bytes
- **Scalable Matching**: Efficient even with thousands of simultaneous calls

## Project Structure

```
calldns/
├── calldns/                # Main package
│   ├── sdk/               # Client SDK
│   ├── crypto/            # Cryptographic operations
│   ├── privacy/           # Privacy-preserving features
│   ├── network/           # Network layer
│   ├── service/           # Web service
│   ├── cli/               # Command-line interface
│   ├── keystore/          # Key management
│   ├── logging/           # Logging and monitoring
│   └── utils/             # Utilities and validation
├── ui/                    # Node Management UI (Vue 3 + TailwindCSS)
├── sdks/                  # Platform-specific SDKs
│   ├── android/           # Android SDK (Kotlin/Compose)
│   ├── ios/               # iOS SDK (Swift/SwiftUI)
│   ├── react-native/      # React Native SDK
│   ├── web/               # Web SDK (TypeScript)
│   ├── flutter/           # Flutter SDK (Dart)
│   └── examples/          # SDK integration examples
├── docs/                  # Documentation
├── examples/              # Code examples
├── scripts/               # Development scripts
└── tests/                 # Test suite
```

## Node Management UI

CallDNS includes a web-based management interface for node operators:

```bash
# Start the UI (development)
./scripts/start_ui.sh

# Or manually
cd ui && npm install && npm run dev
```

The UI is available at `http://localhost:3000` and provides:

### Regular Node Mode
- Real-time node health monitoring
- WebSocket connection status
- Proof verification dashboard
- Commitment management

### Organization Node Mode
- Customer management (search, pagination for millions of records)
- Device registration and management
- Commitment tracking per customer
- Live statistics with animated counters

### Scalability Features
- Server-side pagination (25-250 items per page)
- Debounced search with instant results
- Virtual scrolling for large lists
- Compact number formatting (1.2M, 450K)

See [ui/README.md](ui/README.md) for detailed documentation.

## Development

### Installation
```bash
git clone https://github.com/dipankar/calldns.git
cd calldns
./scripts/setup_dev.sh
```

### Running Tests
```bash
./scripts/run_tests.sh
```

### Starting the Service
```bash
./scripts/start_service.sh
```

## Roadmap

### Current Status
- ✅ Core cryptographic primitives (Schnorr ZK proofs)
- ✅ Decentralized network architecture
- ✅ Bidirectional verification (bank↔customer)
- ✅ Multi-platform SDKs (Android, iOS, Web, Flutter, React Native)
- ✅ JWT authentication and rate limiting

### Planned
- 🔲 **Billing layer** - Usage tracking and invoicing for non-consortium orgs
- 🔲 **Foundation dashboard** - Network monitoring and consortium management
- 🔲 **Commitment rotation** - Automatic rotation for enhanced privacy
- 🔲 **HSM integration** - Hardware security module support for production keys
- 🔲 **Geographic expansion** - EU and US core node deployments

See [Network Economics](docs/network-economics.md) for the consortium + fee model.

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on:

- Setting up the development environment
- Code style and testing requirements
- Submitting pull requests
- Security guidelines

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Regulatory Resources

- [FCA Consumer Duty](https://www.fca.org.uk/firms/consumer-duty) - UK financial conduct requirements
- [GDPR Article 25](https://gdpr-info.eu/art-25-gdpr/) - Privacy by design requirements
- [PSD2 SCA](https://www.eba.europa.eu/regulation-and-policy/payment-services-and-electronic-money/regulatory-technical-standards-on-strong-customer-authentication-and-secure-communication-under-psd2) - Strong customer authentication
- [MiFID II](https://www.esma.europa.eu/policy-rules/mifid-ii-and-mifir) - Investment services regulation

## Acknowledgments

- Schnorr signature scheme for zero-knowledge proofs
- ECDSA library for cryptographic operations
- Bloom filters for efficient proof matching

---

**CallDNS** - Helping regulated industries verify caller identity while preserving privacy and meeting compliance obligations.