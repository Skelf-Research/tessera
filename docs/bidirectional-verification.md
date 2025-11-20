# Bidirectional Call Verification

CallDNS supports verification in both directions:

1. **Bank → Customer**: Bank proves identity when calling customer
2. **Customer → Bank**: Customer proves identity when calling bank

Both flows use the same cryptographic primitives but with reversed roles.

## Use Cases

### Bank Calling Customer (Inbound to Customer)

Protects against vishing attacks where fraudsters impersonate the bank:

```
Bank generates proof → Broadcasts to network → Customer verifies in app
```

**Customer sees**: "Verified call from NatWest at 14:32"

### Customer Calling Bank (Outbound from Customer)

Enables streamlined authentication at contact centers:

```
Customer taps "Verified Call" → Proof broadcasts → Dials bank → Contact center verifies
```

**Contact center sees**: "Verified customer: John Smith (account ***4521)"

## Customer → Bank Flow

### Mobile App Integration

#### Android (Kotlin/Compose)

```kotlin
import com.calldns.sdk.ui.VerifiedCallButton

@Composable
fun BankContactScreen() {
    VerifiedCallButton(
        phoneNumber = "+44 800 123 4567",
        destinationId = "natwest-uk",
        destinationName = "NatWest Customer Service",
        onCallInitiated = { proof ->
            // Proof has been broadcast, call is being placed
            Log.d("CallDNS", "Verified call initiated: ${proof.id}")
        },
        onError = { error ->
            // Handle error - offer fallback unverified call
            Toast.makeText(context, "Verification failed: $error", Toast.LENGTH_SHORT).show()
        }
    )
}
```

#### iOS (SwiftUI)

```swift
import CallDNS

struct BankContactView: View {
    var body: some View {
        VerifiedCallButton(
            phoneNumber: "+44 800 123 4567",
            destinationId: "natwest-uk",
            destinationName: "NatWest Customer Service",
            onCallInitiated: { proof in
                print("Verified call initiated: \(proof.id)")
            },
            onError: { error in
                print("Verification failed: \(error)")
            }
        )
    }
}
```

### UX Flow

1. **User taps button** → "Call with Verification"
2. **Generating** → SDK creates ZK proof (< 50ms)
3. **Broadcasting** → Proof sent to core network
4. **Ready to dial** → Phone dialer opens automatically
5. **Call connected** → Contact center verifies proof

### Button States

| State | Visual | Duration |
|-------|--------|----------|
| Ready | Shield icon + "Call with Verification" | - |
| Generating | Spinner + "Generating proof..." | ~50ms |
| Broadcasting | Spinner + "Broadcasting..." | ~200ms |
| Ready to Dial | Checkmark + "Opening dialer..." | 500ms |
| Error | Warning + error message | 3s then reset |

## Contact Center Integration

### API Endpoints

The org node exposes endpoints for contact center verification:

#### Look Up Proofs by Commitment

```bash
curl "http://org-node:8101/proofs/lookup?commitment=<hex>&since=<timestamp>" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

Response:
```json
{
  "commitment": "a1b2c3...",
  "proofs": [
    {
      "timestamp": 1700000000,
      "metadata": {
        "direction": "outbound",
        "destination": "natwest-uk"
      }
    }
  ],
  "count": 1
}
```

#### Verify Incoming Caller

```bash
curl -X POST http://org-node:8101/verify/incoming-caller \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{
    "customer_id": "CUST-12345",
    "caller_id": "+447700900123"
  }'
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
      "timestamp": 1700000000
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

### Python Integration

```python
from calldns.sdk import ContactCenterVerifier

verifier = ContactCenterVerifier("http://org-node:8101")

# When call comes in
async def on_incoming_call(customer_id: str, caller_id: str):
    # Look up customer's commitment
    commitment = await verifier.lookup_customer_commitment(customer_id)

    if commitment:
        # Check for recent proof
        result = await verifier.verify_incoming_caller(
            caller_commitment=commitment,
            caller_id=caller_id,
            timeout=30
        )

        if result["verified"]:
            # Fast-track authentication
            return "verified", result["metadata"]
        else:
            # Require standard authentication
            return "unverified", None
    else:
        # Customer not registered for verified calls
        return "not_enrolled", None
```

### IVR Integration Example

```python
# Genesys/Twilio/Amazon Connect integration
async def ivr_verification_check(call_sid: str, customer_id: str):
    result = await verifier.verify_incoming_caller(customer_id)

    if result["verified"]:
        # Skip "please enter your account number" prompts
        # Route directly to agent with verified context
        return {
            "action": "route_to_agent",
            "context": {
                "verified": True,
                "customer_id": customer_id,
                "verification_time": result["proofs"][0]["timestamp"]
            }
        }
    else:
        # Standard IVR flow
        return {
            "action": "standard_authentication"
        }
```

## Architecture

### Proof Flow (Customer → Bank)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Customer   │     │    Core      │     │   Bank Org   │
│   Mobile     │     │   Network    │     │    Node      │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │  1. Generate proof │                    │
       │─────────────────►  │                    │
       │                    │                    │
       │  2. Broadcast      │                    │
       │───────────────────►│                    │
       │                    │                    │
       │                    │  3. Route by bucket│
       │                    │───────────────────►│
       │                    │                    │
       │  4. Open dialer    │                    │
       │◄───────────────────│                    │
       │                    │                    │
       │        5. Phone call (PSTN)             │
       │────────────────────────────────────────►│
       │                    │                    │
       │                    │  6. Verify proof   │
       │                    │◄───────────────────│
       │                    │                    │
```

### Privacy Preservation

Even in customer → bank flow, privacy is maintained:

| Party | Knows | Cannot Know |
|-------|-------|-------------|
| **Customer** | Their own proof, destination | Other customers' activity |
| **Core Nodes** | Bucket, routing | Customer or bank identity |
| **Bank** | Proof content, customer ID | If customer will call |

The key difference from bank → customer:
- Bank **does** receive the proof (that's the point)
- But cannot know **when** customer will call until they do
- Cannot track customers who don't call

## Compliance Benefits

### Reduced Authentication Friction

- **Before**: "Please enter your 16-digit card number, then your date of birth, then your security code..."
- **After**: "Welcome back, Mr. Smith. How can I help you today?"

### Audit Trail

Every verified call creates a cryptographic record:
- Timestamp
- Proof validity
- Device used
- Call purpose (if provided)

Meets MiFID II and FCA record-keeping requirements.

### Fraud Reduction

- Validates customer identity before sensitive operations
- Detects account takeover (different device, no proof)
- Integrates with fraud scoring systems

## Configuration

### Button Customization

#### Android

```kotlin
VerifiedCallButton(
    phoneNumber = "+44 800 123 4567",
    destinationId = "natwest-uk",
    destinationName = "NatWest",
    config = VerifiedCallButtonConfig(
        buttonText = "Secure Call",
        buttonColor = Color(0xFF006D3B),  // Brand color
        buttonHeight = 48,
        cornerRadius = 8,
        showInfoText = true,
        showDestination = false
    )
)
```

#### iOS

```swift
VerifiedCallButton(
    phoneNumber: "+44 800 123 4567",
    destinationId: "natwest-uk",
    destinationName: "NatWest",
    config: VerifiedCallButtonConfig(
        buttonText: "Secure Call",
        buttonColor: Color(hex: "006D3B"),
        buttonHeight: 48,
        cornerRadius: 8,
        showInfoText: true,
        showDestination: false
    )
)
```

### Timeout Configuration

```python
# Contact center side
verifier = ContactCenterVerifier("http://org-node:8101")

# Wait up to 60 seconds for proof
# (customer may be slow to dial)
result = await verifier.verify_incoming_caller(
    customer_commitment=commitment,
    timeout=60
)
```

## Error Handling

### Customer Side

| Error | User Message | Action |
|-------|-------------|--------|
| Network failure | "Verification failed" | Offer unverified call option |
| SDK not initialized | "Please set up the app first" | Guide to registration |
| Timeout | "Verification timed out" | Retry or unverified call |

### Contact Center Side

| Scenario | Action |
|----------|--------|
| No proof found | Standard authentication |
| Proof expired (> TTL) | Standard authentication |
| Customer not enrolled | Standard authentication |
| Multiple proofs | Use most recent |

## Best Practices

### For Mobile App Developers

1. **Pre-register commitment** during app onboarding
2. **Cache destination commitments** for faster proof generation
3. **Offer fallback** if verification fails
4. **Show clear status** during proof generation

### For Contact Centers

1. **Set reasonable timeout** (30-60 seconds)
2. **Log all verification attempts** for audit
3. **Graceful degradation** to standard auth
4. **Train agents** on verified call handling

### For Security Teams

1. **Monitor verification rates** by channel
2. **Alert on** sudden drops in verification
3. **Integrate with** fraud scoring
4. **Regular key rotation** on org nodes

## Summary

Bidirectional verification enables:

- **Customers** to prove identity when calling sensitive services
- **Organizations** to streamline authentication
- **Both parties** to maintain cryptographic audit trails

The "Verified Call" button provides a simple UX that handles the complex cryptographic operations behind the scenes.
