# Quick Start Guide

## Installation

```bash
pip install tessera
```

## Basic Usage

### Command Line Interface

```bash
# Register your identity
tessera register

# Verify an incoming call
tessera verify

# Make a verified call
tessera call +1234567890

# Manage contacts
tessera contacts add "Alice" <commitment_hash>

# Check your identity
tessera identity show
```

### Python SDK

#### Making Verified Calls

```python
from tessera import Caller

# Initialize caller
caller = Caller()

# Generate metadata for the call
metadata = {
    "purpose": "business_meeting",
    "timestamp": int(time.time()),
    "recipient": "bob_commitment_hash"
}

# Generate zero-knowledge proof
proof = caller.generate_call_proof(metadata)

# Broadcast proof (in real implementation, this would go to network)
print(f"Generated proof with commitment: {caller.get_public_key()[:16].hex()}...")
```

#### Verifying Incoming Calls

```python
from tessera import Verifier

# Initialize verifier
verifier = Verifier()

# Generate a reception commitment (for this session)
commitment = verifier.generate_reception_commitment("meeting_session_123")

# When you receive a proof (in real implementation, from network)
# received_proof = get_proof_from_network()

# For demo, let's create a test proof
test_caller = Caller()  # Simulate another user
test_proof = test_caller.generate_call_proof({"test": "call"})

# Verify the proof
is_valid = verifier.verify_call_proof(test_proof)
print(f"Call verification: {'VALID' if is_valid else 'INVALID'}")
```

#### Contact Management

```python
from tessera import Caller, Verifier

# Add a verified contact
def add_verified_contact(name, commitment_hash):
    """Add a verified contact to your address book."""
    # In a real app, this would be stored securely
    contacts = {}
    contacts[name] = commitment_hash
    return contacts

# Example usage
alice_commitment = "example_commitment_hash_for_alice"
contacts = add_verified_contact("Alice", alice_commitment)
```

## Running Nodes

### Start a Core Node

```bash
# Core nodes are public and handle proof routing
tessera-node start \
  --type core \
  --id core-1 \
  --port 8100 \
  --api-port 8101 \
  --rate-limit 60
```

### Start an Org Node (Bank/Enterprise)

```bash
# Org nodes require JWT authentication for customer registration
export CALLDNS_JWT_SECRET="your-secret-key"
tessera-node start \
  --type org \
  --id mybank-uk \
  --port 8100 \
  --api-port 8101 \
  --peer core-1@localhost:8100
```

### Check Node Status

```bash
tessera-node status --port 8100
tessera-node peers --port 8100
```

## Web Service

### Starting the Service

```bash
tessera-service
```

### API Endpoints

```python
import requests

# Health check
response = requests.get("http://localhost:8101/health")
print(response.json())

# Broadcast a proof
proof_data = {
    "proof": {"R": "example", "s": 123},
    "metadata": {"timestamp": 1234567890}
}
response = requests.post("http://localhost:8101/proofs/broadcast", json=proof_data)
print(response.json())
```

## Advanced Features

### Privacy Enhancement

```python
from tessera import Caller

caller = Caller()

# Enable traffic padding
proof = caller.generate_call_proof({"private": "call"})
padded_proof = caller.prepare_proof_for_transmission(proof)

# Mix with cover traffic
batch = caller.schedule_batch_transmission([padded_proof])
print(f"Batch size with cover traffic: {len(batch)}")
```

### Commitment Management

```python
from tessera import Verifier

verifier = Verifier()

# Generate multiple commitments for different purposes
meeting_commitment = verifier.generate_reception_commitment("business_meeting")
personal_commitment = verifier.generate_reception_commitment("personal_call")
emergency_commitment = verifier.generate_reception_commitment("emergency_contact")

print(f"Meeting commitment: {meeting_commitment.hex()[:16]}...")
```

## Integration Examples

### Bank Website Integration

```python
from tessera import Verifier
import requests

def verify_bank_call(user_phone_number, bank_commitment_hash):
    """
    Verify if a bank recently called the user.
    This would be implemented on the bank's website.
    """
    # In a real implementation, query the Tessera network
    # network_response = requests.post(
    #     "https://tessera-network/proofs/verify",
    #     json={
    #         "phone_hash": hash_phone(user_phone_number),
    #         "commitment": bank_commitment_hash,
    #         "time_window": 3600  # Last hour
    #     }
    # )
    
    # Simulate response
    return {
        "verified": True,
        "timestamp": int(time.time()) - 300,  # 5 minutes ago
        "purpose": "account_verification"
    }

# Usage on bank website
user_phone = "+1234567890"
bank_commitment = "bank_public_commitment_hash"

verification = verify_bank_call(user_phone, bank_commitment)
if verification["verified"]:
    print(f"✓ We called you {int(time.time() - verification['timestamp'])} seconds ago")
else:
    print("⚠ No recent verified calls from us")
```

### Mobile App Integration

```python
from tessera import Caller, Verifier
import time

class TesseraApp:
    def __init__(self):
        self.caller = Caller()
        self.verifier = Verifier()
        self.contacts = {}
    
    def make_verified_call(self, contact_name, phone_number):
        """Make a verified call to a contact."""
        # Get contact commitment
        commitment = self.contacts.get(contact_name)
        if not commitment:
            print(f"Contact {contact_name} not verified")
            return
        
        # Generate proof
        metadata = {
            "caller": self.caller.get_public_key().hex(),
            "recipient": commitment,
            "timestamp": int(time.time()),
            "type": "verified_call"
        }
        
        proof = self.caller.generate_call_proof(metadata)
        print(f"Generated verified call proof for {contact_name}")
        
        # In real app, broadcast proof and then make actual call
        # make_phone_call(phone_number)
    
    def add_contact(self, name, commitment_hash):
        """Add a verified contact."""
        self.contacts[name] = commitment_hash
        print(f"Added verified contact: {name}")

# Usage
app = TesseraApp()
app.add_contact("Alice", "alice_commitment_hash")
app.make_verified_call("Alice", "+1234567890")
```

## Testing

### Running Unit Tests

```bash
# Run all tests
poetry run pytest

# Run specific test module
poetry run pytest tests/test_crypto.py

# Run with coverage
poetry run pytest --cov=tessera
```

### Example Test

```python
import pytest
from tessera import Caller, Verifier

def test_verified_call():
    """Test that verified calls work correctly."""
    caller = Caller()
    verifier = Verifier()
    
    # Generate proof
    proof = caller.generate_call_proof({"test": "verification"})
    
    # Verify proof
    is_valid = verifier.verify_call_proof(proof)
    
    assert is_valid, "Verified call proof should be valid"

def test_invalid_proof_rejection():
    """Test that invalid proofs are rejected."""
    caller = Caller()
    verifier = Verifier()
    
    # Generate valid proof
    proof = caller.generate_call_proof({"test": "verification"})
    
    # Tamper with proof
    proof["s"] = proof["s"] + 1
    
    # Verify tampered proof
    is_valid = verifier.verify_call_proof(proof)
    
    assert not is_valid, "Tampered proof should be invalid"
```

## Next Steps

1. **Explore the API**: Check out the full API documentation
2. **Run Examples**: Try the example scripts in the `examples/` directory
3. **Build Integration**: Integrate Tessera into your communication app
4. **Contribute**: Help improve Tessera by contributing code or documentation