# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Development Commands

### Environment Setup
```bash
# Install Poetry first if not available
curl -sSL https://install.python-poetry.org | python3 -

# Setup development environment
./scripts/setup_dev.sh

# Install dependencies manually
poetry install
```

### Testing
```bash
# Run full test suite with coverage
./scripts/run_tests.sh

# Run specific test module
poetry run pytest tests/test_crypto.py -v

# Run single test
poetry run pytest tests/test_crypto.py::TestZKProver::test_generate_proof -v

# Run tests without coverage
poetry run pytest tests/ -v
```

### Service Operations
```bash
# Start web service (default: localhost:8000)
./scripts/start_service.sh

# Start with custom host/port
HOST=0.0.0.0 PORT=5000 ./scripts/start_service.sh

# Start service directly
poetry run calldns-service

# CLI operations
poetry run calldns register
poetry run calldns verify
poetry run calldns call +1234567890
```

### Code Quality
```bash
# Format code
poetry run black calldns/ tests/

# Lint code
poetry run flake8 calldns/ tests/
```

## Architecture Overview

### Core System Design
CallDNS is a zero-knowledge caller verification system built on Schnorr signatures and AES-GCM encryption. The architecture separates concerns into distinct layers:

**Cryptographic Layer** (`calldns/crypto/`):
- `crypto_utils.py`: Core cryptographic primitives using ECDSA library
- `ZKProver`: Generates Schnorr-based zero-knowledge proofs
- `ZKVerifier`: Verifies proofs without revealing caller identity
- `SecureEncryption`: AES-GCM AEAD encryption for proof routing

**Network Layer** (`calldns/network/`):
- `enhanced_broadcast.py`: Scalable proof distribution using bloom filters
- Implements traffic padding and cover traffic for privacy
- Commitment-based routing to prevent network analysis

**Privacy Layer** (`calldns/privacy/`):
- Traffic analysis resistance through timing obfuscation
- Padding mechanisms to hide proof metadata patterns
- Privacy-preserving proof matching algorithms

**Service Layer** (`calldns/service/`):
- `web.py`: Flask-based REST API service
- Endpoints: `/proofs/verify`, `/commitments/register`, `/health`
- Handles proof broadcast, verification, and commitment management

**SDK Layer** (`calldns/sdk/`):
- `Caller`: Generates proofs for outgoing calls
- `Verifier`: Verifies incoming call proofs
- `commitment_manager.py`: Manages proof commitments with lifecycle tracking

### Key Management Architecture
**Primary Storage** (`calldns/keystore/`):
- `key_manager.py`: Central key management with rotation support
- `FileBasedKeyStore`: Plain file storage for development
- `EncryptedKeyStore`: Production-ready encrypted storage with PBKDF2

**Security Features**:
- Automatic key rotation with configurable intervals
- Secure backup/recovery with encrypted snapshots
- Key derivation using PBKDF2 with 100,000 iterations
- Identity management with SECP256k1 keypairs

### Cross-Platform SDK Architecture
**Multi-Platform Support** (`sdks/`):
- **Android**: Kotlin/Jetpack Compose with Material 3 design
- **iOS**: Swift/SwiftUI with CallKit integration
- **React Native**: TypeScript with cross-platform hooks
- **Web**: TypeScript with WebRTC detection and React hooks
- **Flutter**: Dart with Material Design widgets

**Common SDK Patterns**:
- All SDKs implement identical `CallContext` and `VerificationResult` interfaces
- Widget-based architecture for easy integration
- Event-driven verification with caching
- Configurable UI themes and trust score display

## Security Implementation Notes

### Cryptographic Security
- Uses SECP256k1 elliptic curve for all key operations
- Schnorr signatures provide zero-knowledge properties
- AES-GCM provides authenticated encryption for sensitive data
- PBKDF2 key derivation with high iteration counts

### Privacy Mechanisms
- **Zero-Knowledge Proofs**: Callers prove identity without revealing phone numbers
- **Commitment Scheme**: Proofs are committed before calls to prevent replay attacks
- **Traffic Analysis Resistance**: Padding and cover traffic hide communication patterns
- **No Central Registry**: System cannot map caller-callee relationships

### Data Flow Architecture
1. **Proof Generation**: Caller creates ZK proof with metadata commitment
2. **Commitment Registration**: Proof commitment broadcast to network
3. **Call Initiation**: Actual call happens through existing infrastructure
4. **Verification**: Receiver looks up proof using commitment and verifies
5. **Result**: Verification result displayed without revealing caller details

## Testing Strategy

### Test Organization
- `tests/test_crypto.py`: Cryptographic primitives and proof generation/verification
- `tests/test_network.py`: Network layer, broadcast mechanisms, bloom filters
- `tests/test_privacy.py`: Privacy features, traffic analysis resistance
- `tests/test_service.py`: Web service endpoints and API functionality
- `tests/test_keystore.py`: Key management, storage, and rotation
- `tests/test_sdk.py`: SDK functionality and integration testing

### Critical Test Areas
- **Cryptographic Correctness**: Proof generation and verification accuracy
- **Key Security**: Proper key derivation, storage, and rotation
- **Privacy Preservation**: Traffic analysis resistance validation
- **Service Reliability**: API endpoint functionality and error handling
- **Cross-Platform Compatibility**: SDK behavior consistency

## Development Patterns

### Error Handling
- Custom exceptions in `calldns/utils/exceptions.py`
- `ProofError`, `EncryptionError`, `ValidationError` for domain-specific failures
- Comprehensive input validation in `calldns/utils/validation.py`

### Logging and Monitoring
- Security-focused logging in `calldns/logging/logger.py`
- Sensitive data sanitization (hashes instead of raw values)
- Performance metrics and verification statistics tracking
- Structured logging for security event monitoring

### Configuration Management
- Production vs development key storage strategies
- Configurable privacy parameters (padding intervals, cover traffic)
- SDK configuration for themes, trust score display, auto-verification

## Production Considerations

### Key Management
- Use `EncryptedKeyStore` for production deployments
- Implement regular key rotation (default: 30 days)
- Secure backup procedures with encrypted storage
- Monitor for key compromise indicators

### Service Deployment
- Web service runs on Flask (consider production WSGI server)
- Database integration needed for production (replace in-memory storage)
- Rate limiting and DDoS protection for public endpoints
- SSL/TLS termination for API security

### SDK Integration
- Each platform SDK includes comprehensive example applications
- Widget customization for brand consistency
- Event handling for verification state changes
- Caching mechanisms for performance optimization