# Tessera Scalable Architecture with Privacy-Preserving Matching

## Overview
This document outlines an enhanced architecture for Tessera that addresses the scalability challenge of matching proofs to callees in a privacy-preserving manner.

## The Matching Problem

In a real-world deployment with thousands of simultaneous calls:
1. How does a callee know which proof to verify?
2. How do we avoid privacy leaks through indexing?
3. How do we efficiently route proofs without compromising anonymity?

## Solution: Privacy-Preserving Proof Routing

We'll implement a hybrid approach using cryptographic commitments and bloom filters:

### 1. Commitment-Based Routing

Each callee generates a unique "reception commitment" for each communication session:
```
# Callee generates:
reception_key = random_scalar()
reception_commitment = H(callee_public_key || reception_key || session_id)
```

### 2. Encrypted Proof Routing

Callers encrypt proofs using the reception commitment:
```
# Caller generates:
routing_key = H(reception_commitment || ephemeral_key)
encrypted_proof = AEAD_encrypt(routing_key, proof_data)
```

### 3. Decentralized Matching

The network uses bloom filters to efficiently distribute proofs without revealing recipient information.

## Updated System Components

### 1. Enhanced Device SDK

#### 1.1 Caller Enhancements
- Generate reception commitments from callee information
- Encrypt proofs with routing keys
- Include bloom filter fingerprints for efficient distribution

#### 1.2 Verifier Enhancements
- Generate and manage reception keys
- Decrypt incoming proofs
- Verify authenticity

### 2. Privacy-Preserving Network Layer

#### 2.1 Commitment Registry
- Stores temporary, encrypted commitment mappings
- Automatically expires after session timeout
- No plaintext callee identification

#### 2.2 Routing Protocol
- Uses bloom filters for efficient proof distribution
- Implements onion routing for additional anonymity
- Supports multicast for group communication scenarios

#### 2.3 Proof Distribution Network
- Decentralized nodes for proof relay
- Rate limiting to prevent DoS attacks
- Proof expiration to limit replay attacks

## Detailed Design

### 3. Cryptographic Commitments

#### 3.1 Reception Commitment Generation (Callee Side)
```
def generate_reception_commitment(callee_public_key, session_id):
    # Generate ephemeral key for this session
    ephemeral_key = generate_random_scalar()
    
    # Create commitment
    commitment = H(callee_public_key || ephemeral_key || session_id)
    
    # Store locally (never transmitted in plaintext)
    store_local_mapping(commitment, ephemeral_key)
    
    return commitment
```

#### 3.2 Proof Encryption (Caller Side)
```
def encrypt_proof_for_callee(proof, reception_commitment, metadata):
    # Generate ephemeral key for encryption
    ephemeral_encryption_key = generate_random_scalar()
    
    # Derive routing key
    routing_key = H(reception_commitment || ephemeral_encryption_key)
    
    # Encrypt proof
    encrypted_proof = AEAD_encrypt(routing_key, serialize_proof(proof))
    
    # Generate bloom filter entry
    bloom_entry = H(reception_commitment || metadata.timestamp)[:8]  # 8-byte fingerprint
    
    return {
        'encrypted_proof': encrypted_proof,
        'bloom_fingerprint': bloom_entry,
        'ephemeral_hint': ephemeral_encryption_key  # Not secret, just for derivation
    }
```

### 4. Privacy-Preserving Distribution

#### 4.1 Bloom Filter Distribution
- Network nodes maintain bloom filters for efficient routing
- Filters contain fingerprints of active reception commitments
- Size dynamically adjusts based on network load

#### 4.2 Proof Relay Nodes
- Decentralized proof relay with onion routing
- Nodes only know immediate neighbors
- Automatic proof expiration and cleanup

### 5. Verification Process

#### 5.1 Callee Verification Flow
```
def verify_incoming_call(encrypted_proof_data):
    # Extract bloom fingerprint
    fingerprint = encrypted_proof_data['bloom_fingerprint']
    
    # Check if we have a matching commitment
    if not has_local_commitment_matching_fingerprint(fingerprint):
        return False  # Not for us
    
    # Retrieve the commitment and decryption key
    commitment, decryption_key = get_local_commitment_and_key(fingerprint)
    
    # Derive decryption key
    routing_key = H(commitment || encrypted_proof_data['ephemeral_hint'])
    
    # Decrypt proof
    try:
        proof_bytes = AEAD_decrypt(routing_key, encrypted_proof_data['encrypted_proof'])
        proof = deserialize_proof(proof_bytes)
    except:
        return False  # Decryption failed
    
    # Verify proof
    return verify_zk_proof(proof, proof['public_key'])
```

## Implementation Plan

### 6. Enhanced Python Package Structure

```
tessera/
├── sdk/
│   ├── caller.py          # Enhanced with commitment handling
│   ├── verifier.py        # Enhanced with reception commitment management
│   ├── identity_manager.py
│   └── commitment_manager.py  # NEW: Handles commitments
├── crypto/
│   ├── crypto_utils.py
│   ├── zk_prover.py
│   ├── zk_verifier.py
│   └── commitment_crypto.py   # NEW: Commitment cryptography
├── privacy/
│   ├── privacy_preserver.py
│   └── anonymous_router.py    # NEW: Anonymous routing
├── network/
│   ├── broadcast.py
│   ├── registry.py
│   ├── protocol.py
│   ├── commitment_registry.py # NEW: Commitment registry
│   └── relay_node.py          # NEW: Proof relay nodes
├── tests/
│   ├── test_crypto.py
│   ├── test_sdk.py
│   ├── test_privacy.py
│   └── test_network.py
└── examples/
    ├── basic_call.py
    ├── verification_demo.py
    └── scalable_demo.py       # NEW: Demonstrates scalable matching
```

## Security Considerations

### 7. Enhanced Privacy Guarantees
1. **Recipient Anonymity**: Network cannot identify who is receiving calls
2. **Sender Anonymity**: Network cannot identify who is making calls
3. **Metadata Protection**: Minimal information leakage in routing
4. **Forward Secrecy**: Compromised keys don't reveal past communications

### 8. Cryptographic Security
1. **Post-Quantum Preparation**: Can upgrade to PQ algorithms
2. **Resistance to Side-Channels**: Constant-time implementations
3. **Key Derivation Security**: Proper use of HKDF for key derivation

## Performance Optimization

### 9. Scalable Matching
1. **Bloom Filter Efficiency**: Sub-linear lookup time
2. **Batch Processing**: Handle multiple proofs simultaneously
3. **Caching**: Cache commitment derivations
4. **Load Distribution**: Decentralized relay network

## Next Steps

1. Implement commitment-based cryptography
2. Build privacy-preserving routing protocol
3. Create decentralized proof relay network
4. Develop scalable matching mechanisms
5. Comprehensive testing and security audit