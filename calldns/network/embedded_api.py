"""
Embedded HTTP API for CallDNS nodes.
Provides REST endpoints when a node is started with --api-port.
"""

import time
import base64
import asyncio
import hashlib
from typing import Dict, List, Optional
from collections import defaultdict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Response, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

from .async_node import AsyncDecentralizedNode
from .push import PushService
from .commitment_storage import CommitmentStorage, SQLiteCommitmentStorage


# Rate limiting for core nodes
class RateLimiter:
    """IP-based rate limiter for core node endpoints."""

    def __init__(self, requests_per_minute: int = 60, burst_size: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        minute_ago = now - 60

        # Clean old requests
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > minute_ago
        ]

        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return False

        # Check burst
        second_ago = now - 1
        recent = [t for t in self.requests[client_ip] if t > second_ago]
        if len(recent) >= self.burst_size:
            return False

        self.requests[client_ip].append(now)
        return True

    def get_retry_after(self, client_ip: str) -> int:
        if not self.requests[client_ip]:
            return 0
        oldest = min(self.requests[client_ip])
        return max(1, int(60 - (time.time() - oldest)))


# JWT validation for org nodes
class JWTValidator:
    """JWT validator for org node authentication."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate JWT token and return claims.
        """
        try:
            import jwt

            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return claims

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None


security = HTTPBearer(auto_error=False)


# Pydantic models
class Subscription(BaseModel):
    bucket: int
    bloom_filter: str
    org_hints: Optional[List[str]] = []
    time_window: Optional[int] = 600


class ProofBroadcast(BaseModel):
    proof: Dict
    decoys: Optional[int] = 3


class PushSubscription(BaseModel):
    commitments: List[str]
    device_token: Optional[str] = None


class CommitmentRegistration(BaseModel):
    customer_id: str
    commitment: str
    device_id: Optional[str] = None
    metadata: Optional[Dict] = None


class CustomerQuery(BaseModel):
    customer_id: str


class ProofLookup(BaseModel):
    commitment: str
    since: Optional[int] = None
    limit: Optional[int] = 10


class CallerVerification(BaseModel):
    customer_id: str
    caller_id: Optional[str] = None


def create_embedded_api(
    node: AsyncDecentralizedNode,
    push_service: Optional[PushService] = None,
    commitment_storage: Optional[CommitmentStorage] = None,
    jwt_secret: Optional[str] = None,
    rate_limit_rpm: int = 60
) -> FastAPI:
    """Create FastAPI app embedded in a node.

    Args:
        node: The decentralized node instance
        push_service: Optional push notification service
        commitment_storage: Optional commitment storage (org nodes only)
        jwt_secret: Secret key for JWT validation (org nodes only)
        rate_limit_rpm: Requests per minute for rate limiting (core nodes)
    """

    app = FastAPI(
        title=f"CallDNS Node API - {node.node_id}",
        description="Embedded HTTP API for CallDNS node",
        version="0.4.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store references
    app.state.node = node
    app.state.push = push_service
    app.state.commitment_storage = commitment_storage

    # Rate limiter for core nodes (public endpoints)
    rate_limiter = RateLimiter(requests_per_minute=rate_limit_rpm)

    # JWT validator for org nodes
    jwt_validator = JWTValidator(jwt_secret or "default-secret") if jwt_secret else None

    # Helper to check rate limit
    async def check_rate_limit(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(client_ip):
            retry_after = rate_limiter.get_retry_after(client_ip)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)}
            )

    # Helper to validate JWT for org endpoints
    async def validate_jwt(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Optional[Dict]:
        if not commitment_storage:
            # Not an org node, no auth needed
            return None

        if not jwt_validator:
            # Org node without JWT configured - allow all (dev mode)
            return {"sub": "anonymous"}

        if not credentials:
            raise HTTPException(status_code=401, detail="Authorization required")

        claims = jwt_validator.validate_token(credentials.credentials)
        if not claims:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return claims

    # Metrics
    metrics = {
        "requests": 0,
        "proofs_broadcast": 0,
        "subscriptions": 0,
        "registrations": 0,
        "rate_limited": 0
    }

    # Health & Stats
    @app.get("/health")
    async def health():
        stats = await node.get_stats()
        return {
            "status": "healthy",
            "node_id": node.node_id,
            "node_type": node.node_type.value,
            "timestamp": int(time.time()),
            "stats": stats
        }

    @app.get("/stats")
    async def get_stats():
        stats = await node.get_stats()
        push_stats = push_service.get_stats() if push_service else {}
        return {
            "node": stats,
            "push": push_stats,
            "api_metrics": metrics
        }

    @app.get("/metrics")
    async def prometheus_metrics():
        stats = await node.get_stats()
        lines = [
            f"# TYPE calldns_peers gauge",
            f"calldns_peers {stats.get('peers', 0)}",
            f"# TYPE calldns_subscriptions gauge",
            f"calldns_subscriptions {stats.get('subscriptions', 0)}",
            f"# TYPE calldns_cached_proofs gauge",
            f"calldns_cached_proofs {stats.get('cached_proofs', 0)}",
            f"# TYPE calldns_pending_proofs gauge",
            f"calldns_pending_proofs {stats.get('pending_proofs', 0)}",
            f"# TYPE calldns_api_requests counter",
            f"calldns_api_requests {metrics['requests']}",
        ]
        return Response(
            content="\n".join(lines) + "\n",
            media_type="text/plain"
        )

    # Proof endpoints (public, rate-limited)
    @app.post("/proofs/broadcast")
    async def broadcast_proof(request: ProofBroadcast, req: Request):
        # Rate limit check for core nodes
        await check_rate_limit(req)

        metrics["requests"] += 1
        metrics["proofs_broadcast"] += 1

        proof = request.proof

        # Route through node
        notified = await node.route_proof(proof)

        # Push to mobile clients
        push_sent = {}
        if push_service:
            commitment = proof.get("commitment_id")
            if commitment:
                push_sent = await push_service.push_proof(commitment, proof)

        return {
            "status": "broadcast",
            "notified": notified,
            "push": push_sent,
            "timestamp": int(time.time())
        }

    @app.get("/proofs/{subscriber_id}")
    async def get_proofs(subscriber_id: str):
        metrics["requests"] += 1
        proofs = await node.get_pending_proofs(subscriber_id)
        return {
            "subscriber_id": subscriber_id,
            "proofs": proofs,
            "count": len(proofs)
        }

    # Subscription endpoints
    @app.post("/subscriptions/{subscriber_id}")
    async def register_subscription(subscriber_id: str, subscription: Subscription):
        metrics["requests"] += 1
        metrics["subscriptions"] += 1

        await node.register_subscription(subscriber_id, subscription.model_dump())

        return {
            "status": "subscribed",
            "subscriber_id": subscriber_id,
            "bucket": subscription.bucket
        }

    @app.delete("/subscriptions/{subscriber_id}")
    async def unsubscribe(subscriber_id: str):
        metrics["requests"] += 1
        await node.unregister_subscription(subscriber_id)
        return {"status": "unsubscribed", "subscriber_id": subscriber_id}

    # Push subscription (for mobile apps)
    @app.post("/push/subscribe/{subscriber_id}")
    async def push_subscribe(subscriber_id: str, sub: PushSubscription):
        """Register for push notifications (MQTT topic subscription)."""
        metrics["requests"] += 1

        if not push_service or not push_service.mqtt_bridge:
            raise HTTPException(503, "MQTT push not available")

        # Return MQTT topics to subscribe to
        topics = [
            f"calldns/proofs/{c}" for c in sub.commitments
        ]

        return {
            "status": "push_registered",
            "subscriber_id": subscriber_id,
            "mqtt_topics": topics,
            "broker": {
                "host": push_service.mqtt_bridge.broker_host,
                "port": push_service.mqtt_bridge.broker_port
            }
        }

    # WebSocket for real-time updates
    @app.websocket("/ws/{subscriber_id}")
    async def websocket_endpoint(websocket: WebSocket, subscriber_id: str):
        await websocket.accept()

        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "subscribe":
                    commitments = data.get("commitments", [])
                    # Register with push service WebSocket
                    if push_service and push_service.ws_server:
                        push_service.ws_server.subscriptions[subscriber_id] = commitments

                    await websocket.send_json({
                        "type": "subscribed",
                        "commitments": commitments
                    })

                elif msg_type == "fetch":
                    proofs = await node.get_pending_proofs(subscriber_id)
                    await websocket.send_json({
                        "type": "proofs",
                        "proofs": proofs
                    })

                elif msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": int(time.time())
                    })

        except WebSocketDisconnect:
            pass

    # Customer commitment registration (for org nodes, JWT required)
    @app.post("/customers/register")
    async def register_commitment(
        reg: CommitmentRegistration,
        claims: Optional[Dict] = Depends(validate_jwt)
    ):
        """
        Register a customer's commitment with this org node.

        This allows the org to broadcast proofs to this customer.
        The customer should have already subscribed to the network
        with a matching bucket/bloom filter.

        Requires JWT authentication.
        """
        metrics["requests"] += 1
        metrics["registrations"] += 1

        if not commitment_storage:
            raise HTTPException(503, "Commitment storage not configured")

        try:
            result = await commitment_storage.register_commitment(
                customer_id=reg.customer_id,
                commitment=reg.commitment,
                device_id=reg.device_id,
                metadata=reg.metadata
            )
        except ValueError as e:
            raise HTTPException(400, str(e))

        return {
            "status": "registered",
            **result
        }

    @app.get("/customers/{customer_id}/commitments")
    async def get_customer_commitments_endpoint(customer_id: str):
        """Get all commitments for a customer."""
        metrics["requests"] += 1

        if not commitment_storage:
            raise HTTPException(503, "Commitment storage not configured")

        commitments = await commitment_storage.get_customer_commitments(customer_id)

        if not commitments:
            raise HTTPException(404, "Customer not found")

        return {
            "customer_id": customer_id,
            "commitments": [c["commitment"] for c in commitments],
            "devices": commitments
        }

    @app.delete("/customers/{customer_id}/commitments/{commitment}")
    async def remove_commitment_endpoint(customer_id: str, commitment: str):
        """Remove a specific commitment for a customer."""
        metrics["requests"] += 1

        if not commitment_storage:
            raise HTTPException(503, "Commitment storage not configured")

        removed = await commitment_storage.remove_commitment(customer_id, commitment)

        if not removed:
            raise HTTPException(404, "Commitment not found")

        return {
            "status": "removed",
            "customer_id": customer_id,
            "commitment": commitment
        }

    @app.post("/customers/{customer_id}/broadcast")
    async def broadcast_to_customer(customer_id: str, request: ProofBroadcast):
        """
        Broadcast a proof to all devices of a specific customer.

        The org uses this to send proofs to a known customer.
        """
        metrics["requests"] += 1
        metrics["proofs_broadcast"] += 1

        if not commitment_storage:
            raise HTTPException(503, "Commitment storage not configured")

        commitments = await commitment_storage.get_customer_commitments(customer_id)

        if not commitments:
            raise HTTPException(404, "Customer not found")

        proof = request.proof

        results = []
        for device in commitments:
            # Add commitment to proof for routing
            proof_copy = proof.copy()
            proof_copy["commitment_id"] = device["commitment"]

            # Route through node
            notified = await node.route_proof(proof_copy)

            # Push to mobile
            push_sent = {}
            if push_service:
                push_sent = await push_service.push_proof(device["commitment"], proof_copy)

            results.append({
                "device_id": device.get("device_id"),
                "commitment": device["commitment"][:16] + "...",
                "notified": notified,
                "push": push_sent
            })

        return {
            "status": "broadcast",
            "customer_id": customer_id,
            "devices": len(results),
            "results": results
        }

    # Contact center verification endpoints (org nodes only)
    @app.get("/proofs/lookup")
    async def lookup_proofs(commitment: str, since: Optional[int] = None, limit: int = 10):
        """
        Look up proofs by commitment for contact center verification.

        Used by banks to verify incoming customer calls.
        Only available on org nodes with commitment storage configured.
        """
        metrics["requests"] += 1

        if not commitment_storage:
            raise HTTPException(503, "Contact center endpoints only available on org nodes")

        # Get proofs from node's cache that match this commitment
        matching_proofs = []
        since_time = since or (int(time.time()) - 300)  # Default: last 5 minutes

        # Search through cached proofs
        for proof in node.proof_cache.values():
            if proof.get("commitment_id") == commitment:
                if proof.get("timestamp", 0) >= since_time:
                    matching_proofs.append(proof)

        # Sort by timestamp descending and limit
        matching_proofs.sort(key=lambda p: p.get("timestamp", 0), reverse=True)
        matching_proofs = matching_proofs[:limit]

        return {
            "commitment": commitment,
            "proofs": matching_proofs,
            "count": len(matching_proofs)
        }

    @app.post("/verify/incoming-caller")
    async def verify_incoming_caller(verification: CallerVerification):
        """
        Verify an incoming caller using their registered commitment.

        Contact centers use this to verify customer identity.
        """
        metrics["requests"] += 1

        if not commitment_storage:
            raise HTTPException(503, "Commitment storage not configured")

        # Look up customer's commitment
        commitments = await commitment_storage.get_customer_commitments(verification.customer_id)

        if not commitments:
            return {
                "verified": False,
                "customer_id": verification.customer_id,
                "reason": "customer_not_registered"
            }

        # Check for recent proofs from any of customer's commitments
        since_time = int(time.time()) - 300  # Last 5 minutes
        found_proofs = []

        for device in commitments:
            commitment = device["commitment"]
            for proof in node.proof_cache.values():
                if proof.get("commitment_id") == commitment:
                    if proof.get("timestamp", 0) >= since_time:
                        found_proofs.append({
                            "commitment": commitment[:16] + "...",
                            "device_id": device.get("device_id"),
                            "timestamp": proof.get("timestamp"),
                            "metadata": proof.get("metadata", {})
                        })

        if found_proofs:
            return {
                "verified": True,
                "customer_id": verification.customer_id,
                "proofs": found_proofs,
                "confidence": "high"
            }

        return {
            "verified": False,
            "customer_id": verification.customer_id,
            "reason": "no_recent_proof",
            "registered_devices": len(commitments)
        }

    # Peers endpoint
    @app.get("/peers")
    async def get_peers():
        metrics["requests"] += 1
        peers = []
        for peer_id, info in node.peers.items():
            peers.append({
                "peer_id": peer_id,
                **info
            })
        return {"peers": peers, "count": len(peers)}

    return app


async def run_embedded_api(
    node: AsyncDecentralizedNode,
    host: str,
    port: int,
    push_service: Optional[PushService] = None,
    commitment_storage: Optional[CommitmentStorage] = None,
    jwt_secret: Optional[str] = None,
    rate_limit_rpm: int = 60
):
    """Run the embedded API server.

    Args:
        node: The decentralized node instance
        host: Host to bind to
        port: Port to listen on
        push_service: Optional push notification service
        commitment_storage: Optional commitment storage (org nodes only)
        jwt_secret: Secret key for JWT validation (org nodes only)
        rate_limit_rpm: Requests per minute for rate limiting
    """
    app = create_embedded_api(
        node,
        push_service,
        commitment_storage,
        jwt_secret,
        rate_limit_rpm
    )

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning"
    )
    server = uvicorn.Server(config)
    await server.serve()
