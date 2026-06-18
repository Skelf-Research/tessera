"""
Async decentralized node for Tessera.
High-performance async implementation using aiosqlite.
"""

import hashlib
import secrets
import time
import json
import base64
import asyncio
from typing import Dict, List, Set, Optional
from pathlib import Path
from collections import defaultdict

from .async_storage import AsyncNodeStorage
from .decentralized import NodeType, BloomFilter, Subscription


class AsyncDecentralizedNode:
    """
    Async decentralized Tessera node.

    Can be run as:
    - Core node: High availability, routes proofs between nodes
    - Organization node: Broadcasts proofs for calls
    - Customer node: Subscribes to receive relevant proofs
    """

    def __init__(self, node_id: str, node_type: NodeType, data_dir: str = None):
        self.node_id = node_id
        self.node_type = node_type
        self.proof_ttl = 3600  # 1 hour

        # Setup data directory
        if data_dir is None:
            data_dir = f"./tessera_data/{node_id}"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize async storage
        db_path = str(self.data_dir / "node.db")
        self.storage = AsyncNodeStorage(db_path)

        # In-memory caches
        self.peers: Dict[str, dict] = {}
        self.bucket_subscribers: Dict[int, Set[str]] = defaultdict(set)
        # subscriber_id -> subscription data, so route_proof matches candidates in
        # memory instead of one storage read per candidate (fixes F9: O(occupancy) reads).
        self.subscription_cache: Dict[str, dict] = {}
        # subscriber_id -> parsed BloomFilter, so matching does not rebuild the 1024-bit
        # filter from bytes on every candidate of every proof (fixes F12: CPU per match).
        self._bloom_cache: Dict[str, BloomFilter] = {}

        # Local matching (for customer nodes)
        self.my_subscriptions: List[Subscription] = []
        self.matched_proofs: List[dict] = []

        # Peer connection handlers (set by transport layer)
        self._send_to_peer_handler = None

    async def initialize(self):
        """Initialize the node (must be called before use)."""
        await self.storage.initialize()

        # Store node configuration
        await self.storage.set_config("node_id", self.node_id)
        await self.storage.set_config("node_type", self.node_type.value)

        # Load state from storage
        await self._load_state()

    async def _load_state(self):
        """Load state from persistent storage."""
        # Load peers
        for peer in await self.storage.get_active_peers():
            self.peers[peer["peer_id"]] = peer

        # Load subscriptions and rebuild bucket index + in-memory cache
        for sub_data in await self.storage.get_all_subscriptions():
            bucket = sub_data["bucket"]
            subscriber_id = sub_data["subscriber_id"]
            self.bucket_subscribers[bucket].add(subscriber_id)
            self.subscription_cache[subscriber_id] = sub_data

    # ─────────────────────────────────────────────────────────────
    # Core Node Functions
    # ─────────────────────────────────────────────────────────────

    async def register_subscription(self, subscriber_id: str, subscription_data: dict):
        """Register a customer subscription."""
        bucket = subscription_data["bucket"]

        # Store in database
        await self.storage.store_subscription(subscriber_id, subscription_data)

        # Update in-memory indexes
        self.bucket_subscribers[bucket].add(subscriber_id)
        self.subscription_cache[subscriber_id] = subscription_data

        await self.storage.increment_stat("subscriptions_registered")

    async def unregister_subscription(self, subscriber_id: str):
        """Remove a customer subscription."""
        sub_data = await self.storage.get_subscription(subscriber_id)
        if not sub_data:
            return

        # Remove from in-memory indexes
        bucket = sub_data["bucket"]
        self.bucket_subscribers[bucket].discard(subscriber_id)
        self.subscription_cache.pop(subscriber_id, None)
        self._bloom_cache.pop(subscriber_id, None)

        # Remove from database
        await self.storage.delete_subscription(subscriber_id)

    async def route_proof(self, proof: dict, from_peer: str = None) -> int:
        """
        Route a proof to relevant subscribers.

        Returns:
            int: Number of subscribers notified
        """
        await self.storage.increment_stat("proofs_received")

        # Dedup check
        proof_id = self._hash_proof(proof)
        if await self.storage.proof_exists(proof_id):
            return 0

        # Store proof
        is_new = await self.storage.store_proof(proof_id, proof, from_peer, self.proof_ttl)
        if not is_new:
            return 0

        # Find matching subscribers by bucket
        bucket = proof.get("bucket")
        if bucket is None:
            return 0

        potential_subscribers = self.bucket_subscribers.get(bucket, set())
        notified = 0

        # Process subscribers concurrently
        tasks = []
        for subscriber_id in potential_subscribers:
            tasks.append(self._check_and_queue_proof(subscriber_id, proof, proof_id))

        results = await asyncio.gather(*tasks)
        notified = sum(results)

        # Gossip to peer core nodes
        await self._gossip_to_peers(proof, exclude=from_peer)

        await self.storage.increment_stat("proofs_forwarded")
        return notified

    async def _check_and_queue_proof(self, subscriber_id: str, proof: dict,
                                     proof_id: str) -> int:
        """Check if proof matches subscriber and queue it."""
        # In-memory lookup (fixes F9): avoid a storage read per candidate subscriber.
        sub_data = self.subscription_cache.get(subscriber_id)
        if not sub_data:
            sub_data = await self.storage.get_subscription(subscriber_id)
        if not sub_data:
            return 0

        bloom = self._get_cached_bloom(subscriber_id, sub_data)
        if not self._matches_subscription_data(proof, sub_data, bloom):
            return 0

        await self.storage.queue_proof_for_subscriber(subscriber_id, proof_id)
        return 1

    def _get_cached_bloom(self, subscriber_id: str, sub_data: dict) -> BloomFilter:
        """Parsed BloomFilter for a subscriber, built once and cached (fixes F12)."""
        bloom = self._bloom_cache.get(subscriber_id)
        if bloom is None:
            bloom = BloomFilter.from_bytes(base64.b64decode(sub_data["bloom_filter"]))
            self._bloom_cache[subscriber_id] = bloom
        return bloom

    def _matches_subscription_data(self, proof: dict, sub_data: dict,
                                   bloom: BloomFilter = None) -> bool:
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

        # Bloom filter check (use the cached filter when available)
        if bloom is None:
            bloom = BloomFilter.from_bytes(base64.b64decode(sub_data["bloom_filter"]))
        fingerprint = base64.b64decode(proof.get("bloom_fingerprint", ""))
        if not bloom.might_contain(fingerprint):
            return False

        return True

    async def get_pending_proofs(self, subscriber_id: str) -> List[dict]:
        """Get pending proofs for a subscriber."""
        await self.storage.update_subscriber_last_seen(subscriber_id)
        return await self.storage.get_pending_proofs(subscriber_id, delete_after=True)

    # ─────────────────────────────────────────────────────────────
    # Organization Node Functions
    # ─────────────────────────────────────────────────────────────

    async def broadcast_proof(self, proof: dict, decoy_buckets: List[int] = None):
        """Broadcast a proof with optional cover traffic."""
        # Broadcast real proof
        await self._send_to_core_nodes(proof)

        # Generate and broadcast decoys
        if decoy_buckets:
            tasks = []
            for bucket in decoy_buckets:
                decoy = self._generate_decoy_proof(bucket, proof.get("org_hint"))
                tasks.append(self._send_to_core_nodes(decoy))
            await asyncio.gather(*tasks)

    def _generate_decoy_proof(self, bucket: int, org_hint: str = None) -> dict:
        """Generate a decoy proof for cover traffic."""
        return {
            "bucket": bucket,
            "bloom_fingerprint": base64.b64encode(secrets.token_bytes(8)).decode(),
            "ciphertext": base64.b64encode(secrets.token_bytes(128)).decode(),
            "nonce": base64.b64encode(secrets.token_bytes(12)).decode(),
            "timestamp": int(time.time()),
            "org_hint": org_hint
        }

    async def _send_to_core_nodes(self, proof: dict):
        """Send proof to connected core nodes."""
        tasks = []
        for peer_id, peer_info in self.peers.items():
            if peer_info.get("node_type") == NodeType.CORE.value:
                tasks.append(self._send_to_peer(peer_id, proof))
        if tasks:
            await asyncio.gather(*tasks)

    # ─────────────────────────────────────────────────────────────
    # Customer Node Functions
    # ─────────────────────────────────────────────────────────────

    def subscribe(self, commitment: bytes, linked_orgs: List[str] = None) -> Subscription:
        """Create subscription for this customer node."""
        sub = Subscription(commitment, linked_orgs)
        self.my_subscriptions.append(sub)
        return sub

    async def receive_proof(self, proof: dict):
        """Receive a proof from network."""
        await self.storage.increment_stat("proofs_received")

        for sub in self.my_subscriptions:
            if sub.matches_proof(proof):
                self.matched_proofs.append(proof)
                await self.storage.increment_stat("proofs_matched")
                await self._notify_proof_received(proof)
                break

    async def _notify_proof_received(self, proof: dict):
        """Notify local application of received proof."""
        pass  # Override or set callback

    # ─────────────────────────────────────────────────────────────
    # Peer Management
    # ─────────────────────────────────────────────────────────────

    async def connect_peer(self, peer_id: str, peer_info: dict):
        """Connect to a peer node."""
        self.peers[peer_id] = peer_info
        await self.storage.store_peer(peer_id, peer_info)

    async def disconnect_peer(self, peer_id: str):
        """Disconnect from a peer node."""
        if peer_id in self.peers:
            del self.peers[peer_id]
        await self.storage.deactivate_peer(peer_id)

    async def _gossip_to_peers(self, proof: dict, exclude: str = None):
        """Gossip proof to peer nodes."""
        tasks = []
        for peer_id in self.peers:
            if peer_id != exclude:
                tasks.append(self._send_to_peer(peer_id, proof))
        if tasks:
            await asyncio.gather(*tasks)

    async def _send_to_peer(self, peer_id: str, proof: dict):
        """Send proof to specific peer."""
        if self._send_to_peer_handler:
            await self._send_to_peer_handler(peer_id, proof)

    def set_send_handler(self, handler):
        """Set the handler for sending to peers."""
        self._send_to_peer_handler = handler

    # ─────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────

    def _hash_proof(self, proof: dict) -> str:
        """Compute unique hash for proof deduplication."""
        data = proof.get("bloom_fingerprint", "") + str(proof.get("timestamp", 0))
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    async def cleanup_expired(self) -> int:
        """Remove expired proofs."""
        return await self.storage.cleanup_expired_proofs()

    async def get_stats(self) -> dict:
        """Get node statistics."""
        db_stats = await self.storage.get_database_stats()
        counter_stats = await self.storage.get_all_stats()

        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "peers": len(self.peers),
            "subscriptions": db_stats.get("total_subscriptions", 0),
            "cached_proofs": db_stats.get("total_proofs", 0),
            "pending_proofs": db_stats.get("total_pending", 0),
            "db_size_bytes": db_stats.get("db_size_bytes", 0),
            "counters": counter_stats
        }

    async def shutdown(self):
        """Gracefully shutdown the node."""
        await self.cleanup_expired()
        await self.storage.vacuum()
        await self.storage.close()

    async def run_maintenance(self):
        """Run periodic maintenance tasks."""
        deleted = await self.cleanup_expired()
        if deleted > 0:
            await self.storage.increment_stat("proofs_expired", deleted)


class AsyncPrivacyPreservingBroadcaster:
    """Async helper for broadcasting proofs with cover traffic."""

    def __init__(self, org_node: AsyncDecentralizedNode, num_decoys: int = 3):
        self.node = org_node
        self.num_decoys = num_decoys
        self.num_buckets = 64

    async def broadcast_with_cover(self, proof: dict) -> dict:
        """Broadcast proof with cover traffic."""
        real_bucket = proof.get("bucket")

        # Generate random decoy buckets
        decoy_buckets = []
        while len(decoy_buckets) < self.num_decoys:
            bucket = secrets.randbelow(self.num_buckets)
            if bucket != real_bucket and bucket not in decoy_buckets:
                decoy_buckets.append(bucket)

        # Broadcast
        await self.node.broadcast_proof(proof, decoy_buckets)

        return {
            "real_bucket": real_bucket,
            "decoy_buckets": decoy_buckets,
            "total_broadcasts": 1 + len(decoy_buckets),
            "privacy_ratio": len(decoy_buckets) / (1 + len(decoy_buckets))
        }
