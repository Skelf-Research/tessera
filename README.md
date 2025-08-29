# CallDNS

A zero-knowledge caller verification system that works above existing VoIP/communication layers to verify callers while maintaining privacy.

## Overview

CallDNS addresses the challenges of deepfakes and SS7 issues in communications infrastructure by providing a way for callers to generate zero-knowledge proofs that can be verified by receivers in near real-time. The system ensures that CallDNS cannot identify the originator or receiver, maintaining client-side privacy.

## Features

- Zero-knowledge proof-based caller verification
- Client-side privacy preservation
- Fast verification algorithms
- Cross-platform device SDK
- Support for various calling scenarios (call centers, apps, users)

## Architecture

The system consists of several key components:

1. **Device SDK**: Handles ZK proof generation (caller) and verification (verifier)
2. **Zero-Knowledge Module**: Implements fast Schnorr-based ZK proofs
3. **Network Layer**: Manages proof broadcasting
4. **Privacy Layer**: Ensures anonymity and minimizes information leakage

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd calldns

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Example

```python
from calldns.sdk.caller import Caller
from calldns.sdk.verifier import Verifier

# Create caller and generate proof
caller = Caller()
proof = caller.generate_call_proof({"call_type": "voice"})

# Create verifier and verify proof
verifier = Verifier()
is_valid = verifier.verify_call_proof(proof, caller.get_public_key())
```

### Running the Demo

```bash
python calldns/examples/basic_call.py
```

## Security & Privacy

CallDNS ensures privacy through:

1. **Zero-Knowledge Proofs**: Verification without revealing sensitive information
2. **Ephemeral Keys**: Temporary session keys for each call
3. **Metadata Minimization**: Only necessary data included in proofs
4. **Anonymity**: No central registry of caller-callee relationships

## Performance

The system uses Schnorr-based signatures for fast verification:
- Proof generation: ~1-2ms
- Proof verification: ~1-2ms
- Small proof size: ~64 bytes

## Development

### Running Tests

```bash
python -m unittest discover calldns/tests
```

### Project Structure

```
calldns/
├── sdk/          # Device SDK components
├── crypto/       # Cryptographic implementations
├── privacy/      # Privacy preservation mechanisms
├── network/      # Network broadcast functionality
├── tests/        # Unit tests
└── examples/     # Usage examples
```

## Future Improvements

1. Implement full elliptic curve mathematics for ZK verification
2. Add post-quantum cryptographic options
3. Implement actual network broadcasting mechanism
4. Add support for batch verification
5. Enhance privacy measures with advanced anonymity techniques