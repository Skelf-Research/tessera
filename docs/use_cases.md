# CallDNS Use Cases

## 1. Bank Website Verification

### Problem
Users receive suspicious calls claiming to be from their bank. How can they verify the call is legitimate?

### Solution
CallDNS enables banks and users to cryptographically verify calls without compromising privacy.

### How It Works

#### Bank Side (One-time Setup)
1. Bank generates cryptographic identity key pair
2. Bank registers commitment with CallDNS network
3. Bank publishes public commitment for users to reference

#### User Verification Process
1. User receives incoming call from suspected bank
2. User visits bank's official website/app
3. User enters their phone number in verification section
4. Website queries CallDNS network for recent proofs to that number
5. Website verifies proofs against bank's registered commitment
6. Website displays: "Yes, we called you 5 minutes ago about account verification"

### Technical Implementation
```python
# Bank generates proof when initiating call
metadata = {
    "caller_type": "financial_institution",
    "institution_id": "bank_public_commitment_hash",
    "purpose": "account_verification",
    "session_id": "user_phone_hash",
    "timestamp": int(time.time())
}

proof = bank_caller.generate_call_proof(metadata)
broadcast_proof(proof)

# User verification on website
def verify_recent_call(user_phone, bank_commitment):
    recent_proofs = get_proofs_for_recipient(
        hash_phone_number(user_phone),
        time_window=3600  # Last hour
    )
    
    for proof in recent_proofs:
        if verify_proof_against_commitment(proof, bank_commitment):
            return {
                "verified": True,
                "timestamp": proof.metadata["timestamp"],
                "purpose": proof.metadata["purpose"]
            }
    
    return {"verified": False}
```

### Privacy Benefits
- **User Privacy**: Phone number hashed, not exposed
- **Bank Privacy**: Identified by cryptographic commitment, not name
- **No Call Logs**: No persistent records of calls
- **Time-limited**: Only recent calls are verifiable

## 2. User-to-User Verification

### Problem
Alice calls Bob, but Bob wants to verify it's actually Alice (not an impersonator).

### Solution
CallDNS app enables real-time caller verification between users with installed apps.

### How It Works

#### Setup Phase
1. Both Alice and Bob install CallDNS app
2. Each generates long-term identity key pairs
3. Each registers commitments with CallDNS network
4. Users optionally exchange contact commitments for enhanced UX

#### Call Process
1. Alice opens CallDNS app and selects "Verified Call" to Bob
2. Alice's app generates ZK proof with her identity
3. Proof is broadcast to CallDNS network
4. Bob's app receives/queries the proof
5. Bob's app verifies proof against Alice's known commitment
6. Bob sees "Verified: Alice Johnson" on his phone display

### Technical Implementation
```python
# Alice's App - Call Initiation
def initiate_verified_call(bob_phone):
    metadata = {
        "caller_id": "alice_commitment_hash",
        "recipient": hash_phone_number(bob_phone),
        "call_type": "voice",
        "timestamp": int(time.time())
    }
    
    proof = generate_call_proof(metadata)
    broadcast_proof(proof)
    make_voice_call(bob_phone)

# Bob's App - Incoming Call Handler
def handle_incoming_call(caller_phone):
    recent_proofs = get_recent_proofs_for_recipient(
        hash_phone_number(caller_phone),
        time_window=300  # Last 5 minutes
    )
    
    for proof in recent_proofs:
        contact_name = match_commitment_to_contact(
            proof.metadata["caller_id"]
        )
        if contact_name:
            show_verified_caller(contact_name, proof.metadata["timestamp"])
            return contact_name
    
    show_unverified_caller("Unknown Caller")
    return None
```

### Enhanced Features

#### Contact List Integration
- Contacts synced with CallDNS commitments
- Automatic verification for known contacts
- Visual indicators for verified callers
- Warning alerts for unverified calls

#### User Experience
```python
# Contact verification setup
def share_contact_verification():
    # Generate QR code or shareable link
    qr_code = generate_qr_code(my_commitment_hash)
    return qr_code

def add_verified_contact(qr_code):
    # Scan QR code to add verified contact
    commitment_hash = scan_qr_code(qr_code)
    store_contact_commitment(commitment_hash)
```

### Privacy & Security Benefits
- **No Phone Number Exposure**: Only cryptographic hashes used
- **Ephemeral Proofs**: Proofs expire quickly (5-30 minutes)
- **User-controlled Sharing**: Contacts decide who to verify
- **No Call Content**: Only metadata for verification
- **Real-time Verification**: Happens during call setup
- **Cryptographic Proof**: Mathematical guarantee
- **Impersonation Detection**: Immediate fraud detection

## Technical Architecture

### Zero-Knowledge Proofs
CallDNS uses Schnorr-based zero-knowledge proofs:
```
Proof Generation:
1. Choose random nonce: r ← Z_q
2. Compute commitment: R = g^r
3. Compute challenge: c = H(R || Y || metadata)
4. Compute response: s = r + c·x mod q
5. Proof π = (R, s)

Verification:
Check that R = g^s · Y^(-c)
```

### Privacy Features
1. **Traffic Padding**: All packets uniform size (1024 bytes)
2. **Cover Traffic**: 30% dummy traffic mixed with real calls
3. **Timing Obfuscation**: Fixed transmission intervals
4. **Commitment-based Routing**: Cryptographic addressing
5. **Bloom Filter Matching**: Efficient proof distribution

### Performance
- **Proof Generation**: ~1-2ms
- **Proof Verification**: ~2-3ms
- **Proof Size**: ~96 bytes
- **Verification**: Real-time during call setup
- **Scalability**: Thousands of simultaneous calls