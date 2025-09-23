# CallDNS

[![PyPI version](https://badge.fury.io/py/calldns.svg)](https://badge.fury.io/py/calldns)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A zero-knowledge caller verification system that works above existing VoIP/communication layers to verify callers while maintaining privacy.

## Overview

CallDNS addresses the challenges of deepfakes and SS7 issues in communications infrastructure by providing a way for callers to generate zero-knowledge proofs that can be verified by receivers in near real-time. The system ensures that CallDNS cannot identify the originator or receiver, maintaining client-side privacy.

## Key Features

- **Zero-Knowledge Proofs**: Cryptographically secure verification without revealing sensitive information
- **Privacy Preservation**: No central registry of caller-callee relationships
- **Scalable Architecture**: Efficient proof matching even with thousands of simultaneous calls
- **Traffic Privacy**: Padding, cover traffic, and timing obfuscation to prevent network analysis
- **Fast Verification**: Sub-millisecond proof generation and verification
- **Cross-Platform SDK**: Easy integration with existing communication systems
- **Production Ready**: Comprehensive logging, monitoring, and key management
- **Secure Encryption**: AES-GCM authenticated encryption for all sensitive data
- **Enterprise Features**: Key rotation, backup/recovery, and security monitoring

## Use Cases

### 1. Bank Website Verification
Users can verify if an incoming call is actually from their bank:
```python
# User receives suspicious call
# Visits bank website and enters phone number
# Website confirms: "Yes, Bank called you 5 minutes ago"
```

### 2. Mobile App Integration
Integrate CallDNS verification into any mobile app:
```kotlin
// Android - Show verification widget
CallVerificationWidget(
    callContext = CallContext(
        callerId = "+1234567890",
        callType = CallType.VOICE_CALL
    )
)
```

### 3. WebRTC Call Verification
Verify browser-based calls automatically:
```javascript
// Web - Auto-verify WebRTC calls
const widget = new CallDNSWidget('#call-interface');
await widget.show({
  callerId: 'user@example.com',
  callType: 'WEBRTC_CALL'
});
```

### 4. VoIP Service Integration
Protect VoIP services from spoofing:
```swift
// iOS - Verify WhatsApp/Telegram calls
CallVerificationView(
    callContext: CallContext(
        callerId: "+1234567890",
        callType: .voipCall,
        appContext: "WhatsApp"
    )
)
```

## Installation

```bash
pip install calldns
```

## Quick Start

### CLI Usage
```bash
# Register your identity
calldns register

# Verify an incoming call
calldns verify

# Make a verified call
calldns call +1234567890
```

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

## Documentation

For detailed documentation, see the [docs](docs/) directory:

- [Quick Start Guide](docs/quickstart.md)
- [API Reference](docs/api.md)
- [Architecture Overview](docs/architecture.md)
- [Use Cases](docs/use_cases.md)

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

## Security

CallDNS provides strong security guarantees:
- **Cryptographic Security**: Based on elliptic curve discrete logarithm problem
- **Forward Secrecy**: Ephemeral keys protect past communications
- **Zero-Knowledge**: Verification without revealing sensitive data
- **Privacy Preservation**: No caller-callee relationship mapping

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

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on:

- Setting up the development environment
- Code style and testing requirements
- Submitting pull requests
- Security guidelines

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Schnorr signature scheme for zero-knowledge proofs
- ECDSA library for cryptographic operations
- Bloom filters for efficient proof matching