# Customer Onboarding Guide

This guide explains how to set up CallDNS for both end-users (customers) and organizations (callers like banks, healthcare providers, etc.).

## Overview

CallDNS uses a **commitment-based registration** system that enables:
- **Multi-device support**: Verify calls on any registered device
- **Privacy preservation**: Organizations can only reach customers who have explicitly linked
- **Cryptographic security**: Each device has its own keypair and commitment

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         REGISTRATION FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Customer   │     │   CallDNS    │     │ Organization │
│   Device     │     │   Service    │     │   (Bank)     │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                     │
       │ 1. Register        │                     │
       │    Customer ──────►│                     │
       │                    │                     │
       │ 2. Register        │                     │
       │    Device ────────►│                     │
       │                    │                     │
       │ 3. Generate        │                     │
       │    Linking Token   │                     │
       │    ────────────────┼────────────────────►│
       │                    │                     │
       │ 4. Link            │                     │
       │    Organization ──►│◄──── 5. Verify ─────│
       │                    │         Link        │
       │                    │                     │
       │                    │   6. Get Customer   │
       │                    │◄──── Commitments ───│
       │                    │                     │
       │ 7. Receive         │   8. Broadcast      │
       │    Proof ◄─────────│◄──── Proof ─────────│
       │                    │                     │
```

---

## For End Users (Customers)

### Step 1: Install the App

Download the CallDNS-enabled app from your service provider (e.g., your bank's mobile app with CallDNS integration).

### Step 2: Register Your Device

```python
from calldns.sdk import DeviceRegistration
import requests

# Create device registration
device = DeviceRegistration(device_name="My iPhone 15")

# Generate commitment
commitment = device.generate_commitment()

# Get registration payload
payload = device.get_registration_payload()

# Register with CallDNS service
response = requests.post(
    "https://calldns.example.com/customers/register",
    json={"customer_id": "your_customer_id"}
)

response = requests.post(
    f"https://calldns.example.com/customers/your_customer_id/devices",
    json=payload
)

print(f"Device registered: {response.json()}")
```

### Step 3: Link to Your Bank

Generate a linking token and share it with your bank (via their app or website):

```python
# Generate linking token for your bank
token = device.generate_linking_token("org_barclays")

# This token is shared with the bank through their onboarding flow
# (e.g., scanning a QR code in their app, or entering it on their website)
print(f"Share this token with your bank: {token}")
```

### Step 4: Complete Linking

The bank submits your token to CallDNS to establish the link:

```python
# Bank's system calls this endpoint with your token
response = requests.post(
    f"https://calldns.example.com/customers/your_customer_id/link",
    json={
        "organization_id": "org_barclays",
        "linking_token": token
    }
)
```

### Step 5: Receive Verified Calls

When your bank calls, your device automatically verifies the proof:

```python
from calldns.sdk import Verifier

verifier = Verifier()

# When call comes in, app queries for matching proofs
# and verifies them
is_valid = verifier.verify_call_proof(proof)

if is_valid:
    print("✓ Verified call from Barclays")
else:
    print("⚠ Unverified caller - be cautious")
```

---

## For Organizations (Banks, Healthcare, etc.)

### Step 1: Register Your Organization

```python
import requests

# Register organization with CallDNS
response = requests.post(
    "https://calldns.example.com/organizations/register",
    json={
        "organization_id": "org_barclays",
        "organization_name": "Barclays Bank PLC",
        "metadata": {
            "fca_reference": "122702",
            "industry": "financial_services"
        }
    }
)

result = response.json()
api_key = result["api_key"]  # Store securely - used for API authentication
print(f"Organization registered. API Key: {api_key}")
```

### Step 2: Onboard Customers

Provide customers with a way to link their devices to your organization:

#### Option A: QR Code Flow
```python
# Customer scans QR code in your app
# Your app generates linking token on customer's device
# Customer's device sends token to your backend
# Your backend submits to CallDNS
```

#### Option B: Token Entry Flow
```python
# Customer generates token in their CallDNS app
# Customer enters token on your website
# Your backend submits to CallDNS

def complete_customer_linking(customer_id: str, linking_token: str):
    response = requests.post(
        f"https://calldns.example.com/customers/{customer_id}/link",
        json={
            "organization_id": "org_barclays",
            "linking_token": linking_token
        },
        headers={"Authorization": f"Bearer {api_key}"}
    )
    return response.json()
```

### Step 3: Get Customer Commitments Before Calling

Before making a call, retrieve all device commitments for the customer:

```python
def get_customer_commitments(customer_id: str) -> list:
    """Get all device commitments for a customer."""
    response = requests.get(
        f"https://calldns.example.com/organizations/org_barclays/customers/{customer_id}/commitments",
        headers={"Authorization": f"Bearer {api_key}"}
    )

    result = response.json()
    return result["commitments"]  # List of commitment strings
```

### Step 4: Generate and Broadcast Proof

```python
from calldns.sdk import Caller
import base64

def make_verified_call(customer_id: str, call_metadata: dict):
    """Make a verified call to a customer."""

    # Get customer's device commitments
    commitments = get_customer_commitments(customer_id)

    if not commitments:
        print("Customer has no registered devices")
        return

    # Generate proof
    caller = Caller()
    proof = caller.generate_call_proof(metadata=call_metadata)

    # Encrypt and broadcast for each device
    for commitment_b64 in commitments:
        commitment = base64.b64decode(commitment_b64)

        # Encrypt proof for this device
        encrypted = caller.encrypt_proof_for_callee(
            proof,
            commitment,
            metadata={"timestamp": int(time.time())}
        )

        # Broadcast to network
        requests.post(
            "https://calldns.example.com/proofs/broadcast",
            json={
                "proof": encrypted,
                "recipients": [customer_id],
                "metadata": call_metadata
            },
            headers={"Authorization": f"Bearer {api_key}"}
        )

    print(f"Proof broadcast to {len(commitments)} devices")

# Example usage
make_verified_call(
    customer_id="cust_123",
    call_metadata={
        "firm_reference": "FCA122702",
        "department": "fraud_prevention",
        "call_purpose": "security_alert",
        "agent_id": "AGT-4521"
    }
)
```

---

## Multi-Device Support

Customers can register multiple devices, and all will receive verification:

```python
# Customer registers iPhone
iphone = DeviceRegistration(device_name="iPhone 15")
iphone_payload = iphone.get_registration_payload()

# Customer registers iPad
ipad = DeviceRegistration(device_name="iPad Pro")
ipad_payload = ipad.get_registration_payload()

# Customer registers web browser
browser = DeviceRegistration(device_name="Chrome Browser")
browser_payload = browser.get_registration_payload()

# Register all devices
for payload in [iphone_payload, ipad_payload, browser_payload]:
    requests.post(
        f"https://calldns.example.com/customers/{customer_id}/devices",
        json=payload
    )

# When bank calls, proof is broadcast to ALL 3 devices
# Whichever device the customer is using shows the verification
```

---

## API Reference

### Customer Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/customers/register` | POST | Register a new customer |
| `/customers/{id}/devices` | POST | Register a device |
| `/customers/{id}/devices` | GET | List all devices |
| `/customers/{id}/devices/{device_id}` | DELETE | Unregister a device |
| `/customers/{id}/link` | POST | Link to an organization |
| `/customers/{id}/unlink/{org_id}` | DELETE | Unlink from organization |
| `/customers/{id}/commitments` | GET | Get all commitments |

### Organization Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/organizations/register` | POST | Register organization |
| `/organizations/{org}/customers/{cust}/commitments` | GET | Get customer commitments |

### Proof Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/proofs/broadcast` | POST | Broadcast a proof |
| `/proofs/verify` | POST | Verify a proof |
| `/proofs/recent` | GET | Get recent proofs |

---

## Security Considerations

### For Customers

1. **Protect your device**: Device private keys are stored locally
2. **Review linked organizations**: Regularly check which organizations have access
3. **Unlink old devices**: Remove devices you no longer use
4. **Verify before sharing**: Only share linking tokens with trusted organizations

### For Organizations

1. **Secure API keys**: Store API keys in secure vaults (e.g., AWS Secrets Manager)
2. **Validate customer identity**: Verify customer identity before accepting linking tokens
3. **Audit access**: Log all commitment retrievals and proof broadcasts
4. **Rotate keys**: Implement key rotation for long-term security

---

## Troubleshooting

### Customer Issues

**"Device not receiving verification"**
- Check device is registered: `GET /customers/{id}/devices`
- Check organization is linked: Verify linking was successful
- Check network connectivity to CallDNS service

**"Cannot link to organization"**
- Token may be expired (1 hour validity)
- Organization ID may be incorrect
- Generate a new linking token

### Organization Issues

**"Cannot get customer commitments"**
- Verify customer has linked to your organization
- Check authorization: customer must have granted `get_commitments` permission
- Verify API key is correct

**"Proof not reaching customer"**
- Verify commitments are current (devices may have been unregistered)
- Check broadcast was successful
- Verify proof encryption is correct

---

## Example: Complete Bank Integration

```python
"""
Complete example: Bank calling customer with verification
"""

from calldns.sdk import Caller, DeviceRegistration
import requests
import base64
import time

CALLDNS_URL = "https://calldns.example.com"
API_KEY = "your_org_api_key"
ORG_ID = "org_barclays"

class BankCallerService:
    def __init__(self):
        self.caller = Caller()

    def call_customer(self, customer_id: str, purpose: str, agent_id: str):
        """Make a verified call to a customer."""

        # 1. Get customer commitments
        response = requests.get(
            f"{CALLDNS_URL}/organizations/{ORG_ID}/customers/{customer_id}/commitments",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )

        if response.status_code != 200:
            print(f"Failed to get commitments: {response.json()}")
            return False

        commitments = response.json()["commitments"]

        if not commitments:
            print("Customer has no registered devices - cannot verify call")
            return False

        # 2. Generate proof
        metadata = {
            "firm_reference": "FCA122702",
            "organization": "Barclays Bank",
            "call_purpose": purpose,
            "agent_id": agent_id,
            "timestamp": int(time.time())
        }

        proof = self.caller.generate_call_proof(metadata=metadata)

        # 3. Broadcast to all customer devices
        for commitment_b64 in commitments:
            commitment = base64.b64decode(commitment_b64)

            encrypted = self.caller.encrypt_proof_for_callee(
                proof, commitment, metadata
            )

            requests.post(
                f"{CALLDNS_URL}/proofs/broadcast",
                json={
                    "proof": encrypted,
                    "recipients": [customer_id],
                    "metadata": metadata
                },
                headers={"Authorization": f"Bearer {API_KEY}"}
            )

        print(f"✓ Proof broadcast to {len(commitments)} device(s)")
        print(f"  Customer: {customer_id}")
        print(f"  Purpose: {purpose}")
        print(f"  Agent: {agent_id}")

        return True


# Usage
service = BankCallerService()
service.call_customer(
    customer_id="cust_john_doe_123",
    purpose="fraud_alert",
    agent_id="AGT-4521"
)
```

---

---

## Real-Time Proof Delivery (WebSocket)

For instant notification when proofs arrive, devices can connect via WebSocket instead of polling.

### JavaScript/Web Client

```javascript
// Connect to WebSocket
const socket = io('https://calldns.example.com');

// Subscribe to device commitments
socket.emit('subscribe', {
  device_id: 'dev_123',
  commitments: ['commitment_abc', 'commitment_def']
});

// Handle subscription confirmation
socket.on('subscribed', (data) => {
  console.log(`Subscribed to ${data.count} commitments`);
});

// Handle incoming proofs
socket.on('proof_received', (data) => {
  console.log('Proof received!', data);

  // Verify the proof
  const isValid = verifyProof(data.proof);

  if (isValid) {
    showVerificationBanner({
      organization: data.proof.metadata.organization,
      purpose: data.proof.metadata.call_purpose,
      timestamp: data.timestamp
    });
  }
});

// Keepalive ping
setInterval(() => {
  socket.emit('ping');
}, 30000);
```

### Python Client

```python
import socketio

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected to CallDNS')
    sio.emit('subscribe', {
        'device_id': device.device_id,
        'commitments': [device.get_registration_payload()['commitment']]
    })

@sio.on('proof_received')
def on_proof(data):
    print(f"Proof received: {data}")

    # Verify proof
    from calldns.sdk import Verifier
    verifier = Verifier()

    if verifier.verify_call_proof(data['proof']):
        print(f"✓ Verified call from {data['proof']['metadata']['organization']}")
    else:
        print("⚠ Invalid proof")

@sio.on('subscribed')
def on_subscribed(data):
    print(f"Subscribed to {data['count']} commitments")

# Connect
sio.connect('https://calldns.example.com')
sio.wait()
```

### Kotlin/Android Client

```kotlin
// Add to build.gradle: implementation 'io.socket:socket.io-client:2.1.0'

import io.socket.client.IO
import io.socket.client.Socket

class CallDNSWebSocket(private val serverUrl: String) {
    private lateinit var socket: Socket

    fun connect(deviceId: String, commitments: List<String>) {
        socket = IO.socket(serverUrl)

        socket.on(Socket.EVENT_CONNECT) {
            // Subscribe to commitments
            val data = JSONObject().apply {
                put("device_id", deviceId)
                put("commitments", JSONArray(commitments))
            }
            socket.emit("subscribe", data)
        }

        socket.on("proof_received") { args ->
            val data = args[0] as JSONObject
            handleProofReceived(data)
        }

        socket.on("subscribed") { args ->
            val data = args[0] as JSONObject
            Log.d("CallDNS", "Subscribed to ${data.getInt("count")} commitments")
        }

        socket.connect()
    }

    private fun handleProofReceived(data: JSONObject) {
        val proof = data.getJSONObject("proof")
        val metadata = proof.getJSONObject("metadata")

        // Show verification UI
        showVerificationNotification(
            organization = metadata.getString("organization"),
            purpose = metadata.getString("call_purpose")
        )
    }

    fun disconnect() {
        socket.disconnect()
    }
}
```

### Swift/iOS Client

```swift
// Add to Podfile: pod 'Socket.IO-Client-Swift'

import SocketIO

class CallDNSWebSocket {
    private var manager: SocketManager!
    private var socket: SocketIOClient!

    func connect(deviceId: String, commitments: [String]) {
        manager = SocketManager(
            socketURL: URL(string: "https://calldns.example.com")!,
            config: [.log(true), .compress]
        )

        socket = manager.defaultSocket

        socket.on(clientEvent: .connect) { [weak self] _, _ in
            self?.socket.emit("subscribe", [
                "device_id": deviceId,
                "commitments": commitments
            ])
        }

        socket.on("proof_received") { [weak self] data, _ in
            guard let proofData = data[0] as? [String: Any] else { return }
            self?.handleProofReceived(proofData)
        }

        socket.on("subscribed") { data, _ in
            if let response = data[0] as? [String: Any],
               let count = response["count"] as? Int {
                print("Subscribed to \(count) commitments")
            }
        }

        socket.connect()
    }

    private func handleProofReceived(_ data: [String: Any]) {
        guard let proof = data["proof"] as? [String: Any],
              let metadata = proof["metadata"] as? [String: Any] else { return }

        // Show verification UI
        DispatchQueue.main.async {
            self.showVerificationBanner(
                organization: metadata["organization"] as? String ?? "",
                purpose: metadata["call_purpose"] as? String ?? ""
            )
        }
    }

    func disconnect() {
        socket.disconnect()
    }
}
```

### Server Deployment with WebSocket

```bash
# Start service with WebSocket support
poetry run python -c "
from calldns.service.web import service
service.run(host='0.0.0.0', port=8000, websocket=True)
"

# Or use the standalone async WebSocket server
poetry run python -c "
import asyncio
from calldns.service.websocket import run_websocket_server
asyncio.run(run_websocket_server(port=8001))
"
```

### Connection Management

The WebSocket server handles:
- **Automatic reconnection**: Clients can reconnect and resubscribe
- **Pending proofs**: Proofs sent while device is offline are queued (1 hour retention)
- **Keepalive**: Ping/pong to detect stale connections
- **Multi-device**: Each device maintains its own WebSocket connection

---

## Next Steps

1. **Push Notifications**: Alert customers when proofs arrive (even when app is closed)
2. **SDK Packages**: Pre-built SDKs for iOS, Android, Web, Flutter, React Native
3. **Compliance Dashboards**: Organization reporting and analytics

---

*CallDNS - Verified caller identity for regulated industries*
