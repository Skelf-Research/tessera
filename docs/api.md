# API Reference

## Core Modules

### tessera.sdk
Client SDK for integrating Tessera into applications.

#### Caller
```python
class Caller:
    def __init__(self)
    def generate_call_proof(self, metadata=None) -> dict
    def get_public_key(self) -> bytes
    def encrypt_proof_for_callee(self, proof: dict, reception_commitment: bytes, metadata=None) -> dict
    def prepare_proof_for_transmission(self, encrypted_proof: dict) -> dict
    def schedule_batch_transmission(self, proofs: list) -> list
```

#### Verifier
```python
class Verifier:
    def __init__(self)
    def verify_call_proof(self, proof) -> bool
    def generate_reception_commitment(self, session_id: str) -> bytes
    def verify_encrypted_call_proof(self, encrypted_proof_data: dict) -> bool
    def process_batched_proofs(self, encrypted_proofs: list) -> list
```

#### IdentityManager
```python
class IdentityManager:
    def __init__(self)
    def get_private_key(self) -> int
    def get_public_key(self) -> bytes
    def set_identity(self, private_key, public_key)
```

#### CommitmentManager
```python
class CommitmentManager:
    def __init__(self)
    def generate_reception_commitment(self, callee_public_key: bytes, session_id: str) -> bytes
    def derive_routing_key(self, commitment: bytes, ephemeral_hint: bytes) -> bytes
    def get_commitment_info(self, commitment: bytes) -> Optional[Dict]
    def generate_bloom_fingerprint(self, commitment: bytes, timestamp: int) -> bytes
    def has_commitment_matching_fingerprint(self, fingerprint: bytes) -> bool
    def cleanup_expired_commitments(self, expiration_time: int = 3600)
```

#### TrafficManager
```python
class TrafficManager:
    def __init__(self, padding_size: int = 1024, cover_traffic_ratio: float = 0.3)
    def pad_proof(self, encrypted_proof: Dict[str, Any]) -> Dict[str, Any]
    def generate_cover_traffic(self, count: int = 1) -> List[Dict[str, Any]]
    def mix_traffic(self, real_proofs: List[Dict[str, Any]]) -> List[Dict[str, Any]]
    def should_transmit(self) -> bool
    def schedule_transmission(self, proofs: List[Dict[str, Any]]) -> List[Dict[str, Any]]
    def get_transmission_stats(self) -> Dict[str, Any]
```

#### OutboundCaller (Customer → Bank)
```python
class OutboundCaller:
    def __init__(self, core_node_url: str, device_registration: Optional[DeviceRegistration] = None)
    async def prepare_verified_call(self, destination_id: str, destination_commitment: bytes, metadata: Optional[Dict] = None) -> OutboundCallProof
    async def broadcast_and_call(self, proof: OutboundCallProof, phone_number: str) -> Dict[str, Any]
    async def quick_verified_call(self, destination_id: str, destination_commitment: bytes, phone_number: str, metadata: Optional[Dict] = None) -> Dict[str, Any]
```

#### ContactCenterVerifier (Bank-side verification)
```python
class ContactCenterVerifier:
    def __init__(self, org_node_url: str)
    async def verify_incoming_caller(self, caller_commitment: str, caller_id: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]
    async def lookup_customer_commitment(self, customer_id: str) -> Optional[str]
```

### tessera.crypto
Cryptographic implementations for zero-knowledge proofs.

#### ZKProver
```python
class ZKProver:
    def __init__(self)
    def generate_proof(self, private_key_int, public_key_bytes, metadata=None) -> dict
```

#### ZKVerifier
```python
class ZKVerifier:
    def __init__(self)
    def verify_proof(self, proof) -> bool
```

#### CryptoUtils
```python
class CryptoUtils:
    @staticmethod
    def generate_keypair()
    @staticmethod
    def hash_data(*args)
```

### tessera.privacy
Privacy-preserving features for Tessera.

#### PrivacyPreserver
```python
class PrivacyPreserver:
    @staticmethod
    def anonymize_metadata(metadata)
    @staticmethod
    def generate_session_id()
    @staticmethod
    def obfuscate_timestamp(timestamp)
```

### tessera.network
Network functionality for Tessera.

#### EnhancedBroadcast
```python
class EnhancedBroadcast:
    def __init__(self)
    def broadcast_proof(self, encrypted_proof: Dict[str, Any], routing_hint: str = "default")
    def get_relevant_proofs(self, verifier_fingerprints: List[bytes], routing_hint: str = "default") -> List[Dict]
    def clear_expired_messages(self, expiration_time: int = 300)
```

#### BloomFilter
```python
class BloomFilter:
    def __init__(self, size: int = 10000, hash_count: int = 3)
    def add(self, item: bytes)
    def check(self, item: bytes) -> bool
```

## CLI Commands

### Main Commands
```bash
tessera <command> [args...]
```

#### verify
Verify an incoming call
```bash
tessera verify
```

#### register
Register your identity
```bash
tessera register
```

#### call
Make a verified call
```bash
tessera call <phone_number>
```

#### identity
Manage your identity
```bash
tessera identity show
tessera identity export
tessera identity import <file>
```

#### contacts
Manage contacts
```bash
tessera contacts list
tessera contacts add <name> <commitment>
tessera contacts remove <name>
```

## Web Service API

### Authentication

Tessera uses a split authentication model:

| Node Type | Authentication | Rate Limiting |
|-----------|----------------|---------------|
| **Core Node** | None (public) | IP-based (60 req/min) |
| **Org Node** | JWT token | Optional |

**Core node endpoints** are public to maintain customer anonymity. They are protected by IP-based rate limiting.

**Org node endpoints** require JWT authentication via the `Authorization: Bearer <token>` header. Banks issue these tokens through their existing identity systems.

See [Authentication Documentation](authentication.md) for details.

### Core Node Endpoints

#### GET /health
Health check endpoint (rate limited)
```bash
curl http://localhost:8101/health
```
Response:
```json
{
  "status": "healthy",
  "service": "Tessera"
}
```

#### POST /proofs/broadcast
Broadcast a proof to the network
```bash
curl -X POST http://localhost:8101/proofs/broadcast \
  -H "Content-Type: application/json" \
  -d '{"proof": {...}, "metadata": {...}}'
```

#### POST /proofs/verify
Verify a proof
```bash
curl -X POST http://localhost:8101/proofs/verify \
  -H "Content-Type: application/json" \
  -d '{"proof": {...}}'
```

#### POST /commitments/register
Register a commitment
```bash
curl -X POST http://localhost:8101/commitments/register \
  -H "Content-Type: application/json" \
  -d '{"commitment": "...", "metadata": {...}}'
```

#### GET /commitments/lookup/<commitment_id>
Lookup a commitment
```bash
curl http://localhost:8101/commitments/lookup/<commitment_id>
```

### Org Node API (Contact Center Endpoints)

These endpoints are only available on organization nodes with commitment storage configured.

**All org node endpoints require JWT authentication.**

#### POST /customers/register
Register a customer's commitment
```bash
curl -X POST http://org-node:8101/customers/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{
    "customer_id": "CUST-12345",
    "commitment": "a1b2c3...",
    "device_id": "iphone-main",
    "metadata": {"registered_via": "mobile_app"}
  }'
```
Response:
```json
{
  "status": "registered",
  "customer_id": "CUST-12345",
  "commitment": "a1b2c3...",
  "device_id": "iphone-main",
  "registered_at": 1700000000,
  "total_devices": 2
}
```

#### GET /customers/{customer_id}/commitments
Get all commitments for a customer
```bash
curl http://org-node:8101/customers/CUST-12345/commitments \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```
Response:
```json
{
  "customer_id": "CUST-12345",
  "commitments": ["a1b2c3...", "d4e5f6..."],
  "devices": [
    {
      "commitment": "a1b2c3...",
      "device_id": "iphone-main",
      "registered_at": 1700000000
    }
  ]
}
```

#### POST /customers/{customer_id}/broadcast
Broadcast a proof to all devices of a customer
```bash
curl -X POST http://org-node:8101/customers/CUST-12345/broadcast \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{"proof": {...}, "decoys": 3}'
```

#### GET /proofs/lookup
Look up proofs by commitment (for contact center verification)
```bash
curl "http://org-node:8101/proofs/lookup?commitment=a1b2c3&since=1700000000" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```
Response:
```json
{
  "commitment": "a1b2c3...",
  "proofs": [
    {
      "timestamp": 1700000100,
      "metadata": {"direction": "outbound"}
    }
  ],
  "count": 1
}
```

#### POST /verify/incoming-caller
Verify an incoming caller by customer ID
```bash
curl -X POST http://org-node:8101/verify/incoming-caller \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{"customer_id": "CUST-12345"}'
```
Response (verified):
```json
{
  "verified": true,
  "customer_id": "CUST-12345",
  "proofs": [
    {
      "commitment": "a1b2c3...",
      "device_id": "iphone-main",
      "timestamp": 1700000100
    }
  ],
  "confidence": "high"
}
```
Response (not verified):
```json
{
  "verified": false,
  "customer_id": "CUST-12345",
  "reason": "no_recent_proof",
  "registered_devices": 2
}
```

## Configuration

### Environment Variables
```bash
# Network settings
CALLDNS_NETWORK_HOST=localhost
CALLDNS_NETWORK_PORT=8000

# Privacy settings
CALLDNS_PADDING_SIZE=1024
CALLDNS_COVER_TRAFFIC_RATIO=0.3

# Security settings
CALLDNS_KEY_STORAGE_PATH=~/.tessera/keys
```

### Configuration File
Create `~/.tessera/config.json`:
```json
{
  "network": {
    "host": "localhost",
    "port": 8000
  },
  "privacy": {
    "padding_size": 1024,
    "cover_traffic_ratio": 0.3
  },
  "security": {
    "key_storage_path": "~/.tessera/keys"
  }
}
```

## Error Handling

### Common Exceptions

#### InvalidProofError
Raised when a proof fails verification
```python
try:
    verifier.verify_call_proof(invalid_proof)
except InvalidProofError as e:
    print(f"Proof verification failed: {e}")
```

#### NetworkError
Raised when network operations fail
```python
try:
    broadcast.broadcast_proof(proof)
except NetworkError as e:
    print(f"Network error: {e}")
```

#### PrivacyError
Raised when privacy features encounter issues
```python
try:
    privacy_preserver.anonymize_metadata(sensitive_data)
except PrivacyError as e:
    print(f"Privacy error: {e}")
```

## Performance Considerations

### Proof Generation
- **Time**: ~1-2ms
- **CPU**: Minimal
- **Memory**: ~1KB

### Proof Verification
- **Time**: ~2-3ms
- **CPU**: Minimal
- **Memory**: ~1KB

### Network Operations
- **Bandwidth**: ~100 bytes per proof
- **Latency**: Real-time (sub-second)
- **Scalability**: Thousands of concurrent operations

### Privacy Features Overhead
- **Traffic Padding**: 30% bandwidth increase
- **Cover Traffic**: 43% bandwidth increase
- **Timing Obfuscation**: Max 30-second delay