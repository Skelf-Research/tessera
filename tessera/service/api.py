"""
FastAPI-based Tessera service.
High-performance async API for the decentralized network.
"""

import time
import base64
import asyncio
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..network.async_storage import AsyncNodeStorage
from ..network.decentralized import NodeType, BloomFilter
from ..sdk import Sender, Verifier


# ─────────────────────────────────────────────────────────────
# Prometheus Metrics
# ─────────────────────────────────────────────────────────────

class PrometheusMetrics:
    """Simple Prometheus metrics collector."""

    def __init__(self):
        self.counters: Dict[str, int] = {
            "proofs_received_total": 0,
            "proofs_verified_total": 0,
            "proofs_routed_total": 0,
            "subscriptions_created_total": 0,
            "websocket_connections_total": 0,
            "api_requests_total": 0,
        }
        self.gauges: Dict[str, float] = {
            "active_subscriptions": 0,
            "active_websocket_connections": 0,
            "cached_proofs": 0,
            "pending_proofs": 0,
        }
        self.histograms: Dict[str, List[float]] = {
            "request_duration_seconds": [],
        }

    def inc(self, name: str, value: int = 1):
        if name in self.counters:
            self.counters[name] += value

    def set_gauge(self, name: str, value: float):
        if name in self.gauges:
            self.gauges[name] = value

    def observe(self, name: str, value: float):
        if name in self.histograms:
            self.histograms[name].append(value)
            # Keep only last 1000 observations
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]

    def format_prometheus(self) -> str:
        lines = []

        # Counters
        for name, value in self.counters.items():
            lines.append(f"# TYPE tessera_{name} counter")
            lines.append(f"tessera_{name} {value}")

        # Gauges
        for name, value in self.gauges.items():
            lines.append(f"# TYPE tessera_{name} gauge")
            lines.append(f"tessera_{name} {value}")

        # Histograms (simplified - just show count and sum)
        for name, values in self.histograms.items():
            if values:
                lines.append(f"# TYPE tessera_{name} summary")
                lines.append(f"tessera_{name}_count {len(values)}")
                lines.append(f"tessera_{name}_sum {sum(values):.6f}")

        return "\n".join(lines) + "\n"


metrics = PrometheusMetrics()


# ─────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────

class CustomerRegistration(BaseModel):
    customer_id: str
    metadata: Optional[Dict] = None


class DeviceRegistration(BaseModel):
    device_id: str
    device_name: Optional[str] = None
    commitment: str
    public_key: str


class Subscription(BaseModel):
    bucket: int
    bloom_filter: str
    org_hints: Optional[List[str]] = []
    time_window: Optional[int] = 600


class OrganizationRegistration(BaseModel):
    organization_id: str
    organization_name: Optional[str] = None
    metadata: Optional[Dict] = None


class LinkRequest(BaseModel):
    organization_id: str
    linking_token: str


class ProofBroadcast(BaseModel):
    proof: Dict
    recipients: Optional[List[str]] = []
    commitments: Optional[List[str]] = []
    metadata: Optional[Dict] = None


class ProofVerify(BaseModel):
    proof: Dict


# ─────────────────────────────────────────────────────────────
# WebSocket Connection Manager
# ─────────────────────────────────────────────────────────────

class ConnectionManager:
    """Manages WebSocket connections for real-time proof delivery."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, List[str]] = {}  # subscriber_id -> commitments
        self.commitment_to_subscribers: Dict[str, set] = {}  # commitment -> subscriber_ids

    async def connect(self, websocket: WebSocket, subscriber_id: str):
        await websocket.accept()
        self.active_connections[subscriber_id] = websocket

    def disconnect(self, subscriber_id: str):
        if subscriber_id in self.active_connections:
            del self.active_connections[subscriber_id]

        # Clean up subscriptions
        if subscriber_id in self.subscriptions:
            for commitment in self.subscriptions[subscriber_id]:
                if commitment in self.commitment_to_subscribers:
                    self.commitment_to_subscribers[commitment].discard(subscriber_id)
            del self.subscriptions[subscriber_id]

    def subscribe(self, subscriber_id: str, commitments: List[str]):
        self.subscriptions[subscriber_id] = commitments
        for commitment in commitments:
            if commitment not in self.commitment_to_subscribers:
                self.commitment_to_subscribers[commitment] = set()
            self.commitment_to_subscribers[commitment].add(subscriber_id)

    async def broadcast_to_commitment(self, commitment: str, message: dict):
        """Send message to all subscribers of a commitment."""
        subscribers = self.commitment_to_subscribers.get(commitment, set())
        for subscriber_id in subscribers:
            websocket = self.active_connections.get(subscriber_id)
            if websocket:
                try:
                    await websocket.send_json(message)
                except:
                    self.disconnect(subscriber_id)

    def get_stats(self) -> dict:
        return {
            "active_connections": len(self.active_connections),
            "total_subscriptions": sum(len(s) for s in self.subscriptions.values())
        }


# ─────────────────────────────────────────────────────────────
# Application State
# ─────────────────────────────────────────────────────────────

class AppState:
    """Application state container."""

    def __init__(self):
        self.storage: Optional[AsyncNodeStorage] = None
        self.verifier = Verifier()
        self.ws_manager = ConnectionManager()

        # In-memory caches
        self.customers: Dict[str, Dict] = {}
        self.organizations: Dict[str, Dict] = {}
        self.bucket_subscribers: Dict[int, set] = {}

    async def initialize(self, db_path: str = "tessera_api.db"):
        self.storage = AsyncNodeStorage(db_path)
        await self.storage.initialize()

        # Load subscriptions into memory
        subscriptions = await self.storage.get_all_subscriptions()
        for sub in subscriptions:
            bucket = sub["bucket"]
            if bucket not in self.bucket_subscribers:
                self.bucket_subscribers[bucket] = set()
            self.bucket_subscribers[bucket].add(sub["subscriber_id"])


# Global state
state = AppState()


# ─────────────────────────────────────────────────────────────
# Lifespan Management
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    await state.initialize()
    print("Tessera API initialized")

    # Start background tasks
    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield

    # Shutdown
    cleanup_task.cancel()
    if state.storage:
        await state.storage.vacuum()
    print("Tessera API shutdown")


async def periodic_cleanup():
    """Periodically clean up expired data."""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            if state.storage:
                deleted = await state.storage.cleanup_expired_proofs()
                if deleted > 0:
                    await state.storage.increment_stat("proofs_expired", deleted)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Cleanup error: {e}")


# ─────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Tessera API",
    description="Decentralized sender verification network",
    version="0.2.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# Health & Stats
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_stats = await state.storage.get_database_stats()
    ws_stats = state.ws_manager.get_stats()

    return {
        "status": "healthy",
        "service": "Tessera",
        "version": "0.2.0",
        "timestamp": int(time.time()),
        "database": db_stats,
        "websocket": ws_stats,
        "customers": len(state.customers),
        "organizations": len(state.organizations)
    }


@app.get("/stats")
async def get_stats():
    """Get detailed statistics."""
    db_stats = await state.storage.get_database_stats()
    counter_stats = await state.storage.get_all_stats()

    return {
        "status": "success",
        "database": db_stats,
        "counters": counter_stats,
        "timestamp": int(time.time())
    }


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    # Update gauges
    db_stats = await state.storage.get_database_stats()
    metrics.set_gauge("active_subscriptions", db_stats.get("total_subscriptions", 0))
    metrics.set_gauge("cached_proofs", db_stats.get("total_proofs", 0))
    metrics.set_gauge("pending_proofs", db_stats.get("total_pending", 0))
    metrics.set_gauge("active_websocket_connections", len(state.ws_manager.active_connections))

    return Response(
        content=metrics.format_prometheus(),
        media_type="text/plain; charset=utf-8"
    )


# ─────────────────────────────────────────────────────────────
# Proof Endpoints
# ─────────────────────────────────────────────────────────────

@app.post("/proofs/broadcast")
async def broadcast_proof(request: ProofBroadcast):
    """Broadcast a proof to the network."""
    start_time = time.time()
    proof = request.proof
    recipients = request.recipients
    commitments = request.commitments

    await state.storage.increment_stat("proofs_received")
    metrics.inc("proofs_received_total")
    metrics.inc("api_requests_total")

    # Get commitments for recipients if not provided
    if recipients and not commitments:
        for recipient_id in recipients:
            if recipient_id in state.customers:
                for device in state.customers[recipient_id].get("devices", {}).values():
                    commitments.append(device["commitment"])

    # Generate proof ID
    import hashlib
    proof_data = f"{proof.get('bloom_fingerprint', '')}{proof.get('timestamp', 0)}"
    proof_id = hashlib.sha256(proof_data.encode()).hexdigest()[:16]

    # Store proof
    await state.storage.store_proof(proof_id, proof, ttl=3600)

    # Route to subscribers
    bucket = proof.get("bucket")
    ws_delivered = 0

    if bucket is not None:
        subscribers = state.bucket_subscribers.get(bucket, set())

        for subscriber_id in subscribers:
            sub_data = await state.storage.get_subscription(subscriber_id)
            if not sub_data:
                continue

            # Apply filters
            if not await _matches_subscription(proof, sub_data):
                continue

            # Queue for pull model
            await state.storage.queue_proof_for_subscriber(subscriber_id, proof_id)

            # WebSocket delivery
            commitment = sub_data.get("commitment_id")
            if commitment:
                await state.ws_manager.broadcast_to_commitment(commitment, {
                    "type": "proof_received",
                    "proof": proof,
                    "timestamp": int(time.time())
                })
                ws_delivered += 1

    await state.storage.increment_stat("proofs_routed")
    metrics.inc("proofs_routed_total")
    metrics.observe("request_duration_seconds", time.time() - start_time)

    return {
        "status": "proof_broadcasted",
        "proof_id": proof_id,
        "recipients": len(recipients),
        "commitments_targeted": len(commitments),
        "websocket_delivered": ws_delivered,
        "timestamp": int(time.time())
    }


@app.post("/proofs/verify")
async def verify_proof(request: ProofVerify):
    """Verify a proof."""
    proof = request.proof

    # Convert base64 to bytes if needed
    if isinstance(proof.get('R'), str):
        proof_bytes = {}
        for key, value in proof.items():
            if key in ['R', 'public_key'] and isinstance(value, str):
                try:
                    proof_bytes[key] = base64.b64decode(value)
                except:
                    proof_bytes[key] = value
            else:
                proof_bytes[key] = value
        proof = proof_bytes

    is_valid = state.verifier.verify_call_proof(proof)

    await state.storage.increment_stat("proofs_verified")

    return {
        "status": "verified",
        "valid": is_valid,
        "timestamp": int(time.time())
    }


async def _matches_subscription(proof: dict, sub_data: dict) -> bool:
    """Check if proof matches subscription filters."""
    # Time check
    time_window = sub_data.get("time_window", 600)
    since_ts = int(time.time()) - time_window
    if proof.get("timestamp", 0) < since_ts:
        return False

    # Org hint check
    org_hints = sub_data.get("org_hints", [])
    if org_hints:
        proof_org = proof.get("org_hint")
        if proof_org and proof_org not in org_hints:
            return False

    # Bloom filter check
    bloom_bytes = base64.b64decode(sub_data["bloom_filter"])
    bloom = BloomFilter.from_bytes(bloom_bytes)
    fingerprint = base64.b64decode(proof.get("bloom_fingerprint", ""))
    if not bloom.might_contain(fingerprint):
        return False

    return True


# ─────────────────────────────────────────────────────────────
# Subscription Endpoints
# ─────────────────────────────────────────────────────────────

@app.post("/subscriptions/{subscriber_id}")
async def register_subscription(subscriber_id: str, subscription: Subscription):
    """Register a subscription for proof delivery."""
    sub_data = subscription.model_dump()

    # Store in database
    await state.storage.store_subscription(subscriber_id, sub_data)

    # Update in-memory index
    bucket = subscription.bucket
    if bucket not in state.bucket_subscribers:
        state.bucket_subscribers[bucket] = set()
    state.bucket_subscribers[bucket].add(subscriber_id)

    await state.storage.increment_stat("subscriptions_registered")

    return {
        "status": "subscription_registered",
        "subscriber_id": subscriber_id,
        "bucket": bucket,
        "timestamp": int(time.time())
    }


@app.get("/subscriptions/{subscriber_id}")
async def get_subscription(subscriber_id: str):
    """Get a subscription."""
    sub_data = await state.storage.get_subscription(subscriber_id)

    if not sub_data:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {
        "status": "success",
        "subscription": sub_data
    }


@app.delete("/subscriptions/{subscriber_id}")
async def delete_subscription(subscriber_id: str):
    """Delete a subscription."""
    sub_data = await state.storage.get_subscription(subscriber_id)

    if sub_data:
        bucket = sub_data["bucket"]
        if bucket in state.bucket_subscribers:
            state.bucket_subscribers[bucket].discard(subscriber_id)

    deleted = await state.storage.delete_subscription(subscriber_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {
        "status": "subscription_deleted",
        "subscriber_id": subscriber_id
    }


@app.get("/subscriptions/{subscriber_id}/proofs")
async def get_pending_proofs(subscriber_id: str):
    """Get pending proofs for a subscriber (pull model)."""
    await state.storage.update_subscriber_last_seen(subscriber_id)

    proofs = await state.storage.get_pending_proofs(subscriber_id, delete_after=True)

    return {
        "status": "success",
        "subscriber_id": subscriber_id,
        "proofs": proofs,
        "count": len(proofs),
        "timestamp": int(time.time())
    }


# ─────────────────────────────────────────────────────────────
# Customer Endpoints
# ─────────────────────────────────────────────────────────────

@app.post("/customers")
async def register_customer(request: CustomerRegistration):
    """Register a new customer."""
    customer_id = request.customer_id

    if customer_id in state.customers:
        return {
            "status": "customer_exists",
            "customer_id": customer_id
        }

    state.customers[customer_id] = {
        "customer_id": customer_id,
        "created_at": int(time.time()),
        "devices": {},
        "organization_links": {},
        "metadata": request.metadata or {}
    }

    return {
        "status": "customer_registered",
        "customer_id": customer_id,
        "created_at": state.customers[customer_id]["created_at"]
    }


@app.post("/customers/{customer_id}/devices")
async def register_device(customer_id: str, device: DeviceRegistration):
    """Register a device for a customer."""
    if customer_id not in state.customers:
        # Auto-create customer
        state.customers[customer_id] = {
            "customer_id": customer_id,
            "created_at": int(time.time()),
            "devices": {},
            "organization_links": {},
            "metadata": {}
        }

    device_data = {
        "device_id": device.device_id,
        "device_name": device.device_name or f"Device-{device.device_id[:8]}",
        "commitment": device.commitment,
        "public_key": device.public_key,
        "registered_at": int(time.time()),
        "last_seen": int(time.time()),
        "active": True
    }

    state.customers[customer_id]["devices"][device.device_id] = device_data

    return {
        "status": "device_registered",
        "customer_id": customer_id,
        "device_id": device.device_id,
        "device_name": device_data["device_name"]
    }


@app.get("/customers/{customer_id}/devices")
async def get_customer_devices(customer_id: str):
    """Get all devices for a customer."""
    if customer_id not in state.customers:
        raise HTTPException(status_code=404, detail="Customer not found")

    devices = list(state.customers[customer_id]["devices"].values())

    return {
        "status": "success",
        "customer_id": customer_id,
        "devices": devices,
        "count": len(devices)
    }


@app.get("/customers/{customer_id}/commitments")
async def get_customer_commitments(customer_id: str):
    """Get all commitments for a customer."""
    if customer_id not in state.customers:
        raise HTTPException(status_code=404, detail="Customer not found")

    commitments = [
        device["commitment"]
        for device in state.customers[customer_id]["devices"].values()
        if device.get("active", True)
    ]

    return {
        "status": "success",
        "customer_id": customer_id,
        "commitments": commitments,
        "count": len(commitments)
    }


# ─────────────────────────────────────────────────────────────
# Organization Endpoints
# ─────────────────────────────────────────────────────────────

@app.post("/organizations")
async def register_organization(request: OrganizationRegistration):
    """Register an organization."""
    org_id = request.organization_id

    import secrets
    api_key = secrets.token_urlsafe(32)

    state.organizations[org_id] = {
        "organization_id": org_id,
        "organization_name": request.organization_name or org_id,
        "api_key": api_key,
        "created_at": int(time.time()),
        "metadata": request.metadata or {}
    }

    return {
        "status": "organization_registered",
        "organization_id": org_id,
        "api_key": api_key,
        "created_at": state.organizations[org_id]["created_at"]
    }


@app.get("/organizations/{org_id}/customers/{customer_id}/commitments")
async def org_get_customer_commitments(org_id: str, customer_id: str):
    """Get customer commitments for an organization."""
    if org_id not in state.organizations:
        raise HTTPException(status_code=404, detail="Organization not found")

    if customer_id not in state.customers:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Check authorization
    customer = state.customers[customer_id]
    if org_id not in customer.get("organization_links", {}):
        raise HTTPException(
            status_code=403,
            detail="Organization not authorized for this customer"
        )

    commitments = [
        device["commitment"]
        for device in customer["devices"].values()
        if device.get("active", True)
    ]

    return {
        "status": "success",
        "organization_id": org_id,
        "customer_id": customer_id,
        "commitments": commitments,
        "count": len(commitments)
    }


# ─────────────────────────────────────────────────────────────
# WebSocket Endpoint
# ─────────────────────────────────────────────────────────────

@app.websocket("/ws/{subscriber_id}")
async def websocket_endpoint(websocket: WebSocket, subscriber_id: str):
    """WebSocket endpoint for real-time proof delivery."""
    await state.ws_manager.connect(websocket, subscriber_id)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "subscribe":
                commitments = data.get("commitments", [])
                state.ws_manager.subscribe(subscriber_id, commitments)

                # Send pending proofs
                proofs = await state.storage.get_pending_proofs(
                    subscriber_id, delete_after=True
                )
                if proofs:
                    await websocket.send_json({
                        "type": "pending_proofs",
                        "proofs": proofs,
                        "count": len(proofs)
                    })

                await websocket.send_json({
                    "type": "subscribed",
                    "commitments": commitments
                })

            elif msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": int(time.time())
                })

    except WebSocketDisconnect:
        state.ws_manager.disconnect(subscriber_id)


# ─────────────────────────────────────────────────────────────
# Run Application
# ─────────────────────────────────────────────────────────────

def run(host: str = "0.0.0.0", port: int = 8000):
    """Run the FastAPI application."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
