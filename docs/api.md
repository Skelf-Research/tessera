# API Reference

## Core Modules

### calldns.sdk
Client SDK for integrating CallDNS into applications.

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

### calldns.crypto
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

### calldns.privacy
Privacy-preserving features for CallDNS.

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

### calldns.network
Network functionality for CallDNS.

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
calldns <command> [args...]
```

#### verify
Verify an incoming call
```bash
calldns verify
```

#### register
Register your identity
```bash
calldns register
```

#### call
Make a verified call
```bash
calldns call <phone_number>
```

#### identity
Manage your identity
```bash
calldns identity show
calldns identity export
calldns identity import <file>
```

#### contacts
Manage contacts
```bash
calldns contacts list
calldns contacts add <name> <commitment>
calldns contacts remove <name>
```

## Web Service API

### Endpoints

#### GET /health
Health check endpoint
```bash
curl http://localhost:8000/health
```
Response:
```json
{
  "status": "healthy",
  "service": "CallDNS"
}
```

#### POST /proofs/broadcast
Broadcast a proof to the network
```bash
curl -X POST http://localhost:8000/proofs/broadcast \
  -H "Content-Type: application/json" \
  -d '{"proof": {...}, "metadata": {...}}'
```

#### POST /proofs/verify
Verify a proof
```bash
curl -X POST http://localhost:8000/proofs/verify \
  -H "Content-Type: application/json" \
  -d '{"proof": {...}}'
```

#### POST /commitments/register
Register a commitment
```bash
curl -X POST http://localhost:8000/commitments/register \
  -H "Content-Type: application/json" \
  -d '{"commitment": "...", "metadata": {...}}'
```

#### GET /commitments/lookup/<commitment_id>
Lookup a commitment
```bash
curl http://localhost:8000/commitments/lookup/<commitment_id>
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
CALLDNS_KEY_STORAGE_PATH=~/.calldns/keys
```

### Configuration File
Create `~/.calldns/config.json`:
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
    "key_storage_path": "~/.calldns/keys"
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