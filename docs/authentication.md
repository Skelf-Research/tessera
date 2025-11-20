# CallDNS Authentication Model

CallDNS uses a split authentication model that preserves privacy while enabling secure operations.

## Design Principles

1. **Core nodes are public** - No authentication for proof routing (privacy)
2. **Org nodes require auth** - Bank-issued JWT tokens for customer registration
3. **Rate limiting** - IP-based throttling prevents abuse without tracking identity

## Authentication by Node Type

| Node Type | Authentication | Rate Limiting |
|-----------|----------------|---------------|
| **Core Node** | None (public) | IP-based (60 req/min) |
| **Org Node** | JWT token | Optional |

## Core Node Endpoints (Public)

Core nodes don't require authentication to maintain customer anonymity:

```bash
# No auth header needed
curl -X POST https://core.calldns.network/proofs/broadcast \
  -H "Content-Type: application/json" \
  -d '{"proof": {...}, "decoys": 3}'

# Rate limited by IP
curl https://core.calldns.network/proofs/{subscriber_id}
```

### Rate Limiting

- **60 requests per minute** per IP address
- **10 burst** per second
- Returns `429 Too Many Requests` with `Retry-After` header

```json
{
  "detail": "Rate limit exceeded"
}
```

Headers:
```
Retry-After: 45
```

## Org Node Endpoints (JWT Required)

Org nodes require JWT authentication for customer registration and verification:

```bash
# JWT token required
curl -X POST https://bank-node.example.com/customers/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{
    "customer_id": "CUST-12345",
    "commitment": "a1b2c3...",
    "device_id": "iphone-main"
  }'
```

### JWT Token Structure

```json
{
  "sub": "customer_id",
  "iss": "bank-identity-service",
  "aud": "calldns-org-node",
  "exp": 1700000000,
  "iat": 1699996400,
  "scope": ["register", "verify"]
}
```

### Token Issuance

Banks issue JWT tokens through their existing identity systems:

1. **Mobile App Login** → Bank's OAuth/OIDC service
2. **Token Exchange** → Bank issues CallDNS-scoped JWT
3. **SDK Usage** → Token passed to `orgAuthToken` config

Example integration with bank's OAuth:

```python
# Bank's backend service
@app.post("/calldns/token")
async def issue_calldns_token(user_id: str):
    # Verify user is authenticated
    user = await get_authenticated_user()

    # Issue CallDNS-scoped token
    token = jwt.encode({
        "sub": user.customer_id,
        "iss": "natwest-identity",
        "aud": "calldns-org-node",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "scope": ["register", "verify"]
    }, JWT_SECRET, algorithm="HS256")

    return {"token": token}
```

## SDK Configuration

### No API Key for Core Nodes

SDKs connect to core nodes without authentication:

```typescript
// Web SDK
const client = CallDNSClient.initialize({
  coreNodeUrl: 'https://core.calldns.network',
  // No auth needed for core node
});

// Broadcast proof (public endpoint)
await client.prepareVerifiedCall({
  destinationId: 'natwest-uk',
  phoneNumber: '+44 800 123 4567'
});
```

### JWT for Org Node Registration

```typescript
const client = CallDNSClient.initialize({
  coreNodeUrl: 'https://core.calldns.network',
  orgNodeUrl: 'https://org.natwest.com:8101',
  orgAuthToken: 'eyJhbGciOiJIUzI1NiIs...' // From bank's auth
});

// Register commitment (requires JWT)
await client.registerCommitment(
  'CUST-12345',
  'commitment-hex',
  'device-id'
);
```

### Android Example

```kotlin
val config = CallDNSConfig(
    coreNodeUrl = "https://core.calldns.network",
    orgNodeUrl = "https://org.natwest.com:8101",
    orgAuthToken = bankAuthService.getCallDNSToken()
)

val client = CallDNSClient.initialize(context, config)
```

### iOS Example

```swift
let config = CallDNSConfig(
    coreNodeUrl: "https://core.calldns.network",
    orgNodeUrl: "https://org.natwest.com:8101",
    orgAuthToken: bankAuthService.getCallDNSToken()
)

CallDNSClient.shared.initialize(config: config)
```

## Node Configuration

### Core Node (Public)

```bash
# Start with rate limiting (default: 60 req/min)
calldns-node start \
  --type core \
  --id core-1 \
  --port 8100 \
  --api-port 8101 \
  --rate-limit 60
```

### Org Node (JWT Required)

```bash
# Start with JWT validation
calldns-node start \
  --type org \
  --id natwest-uk \
  --port 8100 \
  --api-port 8101 \
  --jwt-secret "your-secret-key" \
  --peer core-1@core.calldns.network:8100
```

For production, use environment variables:

```bash
export CALLDNS_JWT_SECRET="your-production-secret"
calldns-node start --type org --id natwest-uk --port 8100 --api-port 8101
```

### CLI Reference

| Argument | Description | Default |
|----------|-------------|---------|
| `--type` | Node type: `core`, `org`, or `customer` | Required |
| `--id` | Node identifier | Required |
| `--port` | P2P network port | 8100 |
| `--api-port` | HTTP API port | None |
| `--jwt-secret` | JWT secret for org node auth | None |
| `--rate-limit` | Requests per minute | 60 |
| `--peer` | Initial peer (format: `id@host:port`) | None |
| `--data-dir` | Data directory | `./calldns_data/<id>` |

## Security Considerations

### Core Nodes

- **No identity tracking** - Can't correlate requests to users
- **Rate limiting only** - Prevents DoS without auth
- **IP-based** - May affect users behind NAT

### Org Nodes

- **Bank controls tokens** - Revoke on account closure
- **Short expiry** - 1 hour recommended
- **Scope limiting** - Only grant necessary permissions

### Token Security

- Store tokens securely (Keychain/Keystore)
- Rotate regularly
- Don't log tokens
- Use HTTPS only

## Development Mode

For local development, org nodes can run without JWT:

```bash
# Dev mode - no auth required
calldns node start --type org --id test-bank --api-port 8101
# Warning: Commitment storage configured without JWT secret
```

**Never run production without JWT validation.**

## Error Responses

### 401 Unauthorized

Missing or invalid token:

```json
{
  "detail": "Authorization required"
}
```

```json
{
  "detail": "Invalid or expired token"
}
```

### 429 Too Many Requests

Rate limit exceeded:

```json
{
  "detail": "Rate limit exceeded"
}
```

### 503 Service Unavailable

Endpoint not available on this node type:

```json
{
  "detail": "Contact center endpoints only available on org nodes"
}
```

## Best Practices

### For Banks

1. **Integrate with existing auth** - Use your OAuth/OIDC system
2. **Short-lived tokens** - 1 hour expiry
3. **Rotate secrets** - Change JWT signing key periodically
4. **Audit logs** - Log all registration requests
5. **Revocation** - Have process for token invalidation

### For SDK Developers

1. **Don't hardcode tokens** - Fetch from auth service
2. **Handle 401** - Refresh token and retry
3. **Handle 429** - Respect Retry-After header
4. **Secure storage** - Use platform secure storage

### For Network Operators

1. **Monitor rate limits** - Adjust based on traffic
2. **IP allowlists** - For known good actors
3. **DDoS protection** - Use CDN/WAF for public endpoints
4. **JWT key management** - HSM for production
