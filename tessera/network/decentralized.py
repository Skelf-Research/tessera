"""
Decentralized network architecture for Tessera.
Implements privacy-preserving proof routing with bucketed subscriptions.
"""

import hashlib
import secrets
import time
import json
import base64
from typing import Dict, List, Set, Optional
from enum import Enum
from collections import defaultdict
from pathlib import Path

from .storage import NodeStorage


class NodeType(Enum):
    CORE = "core"  # High-availability, run by Tessera
    ORGANIZATION = "org"  # Run by banks, healthcare providers, etc.
    CUSTOMER = "customer"  # Run by end users (mobile/desktop app)


class BloomFilter:
    """Bloom filter for efficient proof matching."""

    def __init__(self, size: int = 1024, hash_count: int = 3):
        self.size = size
        self.hash_count = hash_count
        self.bit_array = [0] * size

    def _hashes(self, item: bytes) -> List[int]:
        """Generate multiple hash positions for an item."""
        positions = []
        for i in range(self.hash_count):
            h = hashlib.sha256(item + i.to_bytes(2, "big")).digest()
            pos = int.from_bytes(h[:4], "big") % self.size
            positions.append(pos)
        return positions

    def add(self, item: bytes):
        """Add an item to the filter."""
        for pos in self._hashes(item):
            self.bit_array[pos] = 1

    def might_contain(self, item: bytes) -> bool:
        """Check if item might be in filter (may have false positives)."""
        return all(self.bit_array[pos] for pos in self._hashes(item))

    def to_bytes(self) -> bytes:
        """Serialize bloom filter."""
        # Pack bits into bytes
        byte_array = bytearray((self.size + 7) // 8)
        for i, bit in enumerate(self.bit_array):
            if bit:
                byte_array[i // 8] |= 1 << (i % 8)
        return bytes(byte_array)

    @classmethod
    def from_bytes(
        cls, data: bytes, size: int = 1024, hash_count: int = 3
    ) -> "BloomFilter":
        """Deserialize bloom filter."""
        bf = cls(size=size, hash_count=hash_count)
        for i in range(min(size, len(data) * 8)):
            if data[i // 8] & (1 << (i % 8)):
                bf.bit_array[i] = 1
        return bf


# ─────────────────────────────────────────────────────────────────────
# Canonical routing functions — the single source of truth shared by proof
# *producers* (senders) and *consumers* (subscribers). A proof and a
# subscription only match if both derive bucket and fingerprint identically,
# so these MUST be the only place this logic lives.
# ─────────────────────────────────────────────────────────────────────

NUM_BUCKETS = 64
WINDOW_SECONDS = 10  # fingerprint time-window granularity
DEFAULT_TIME_WINDOW = 600  # 10 minutes of recent windows kept matchable


def compute_bucket(commitment: bytes, num_buckets: int = NUM_BUCKETS) -> int:
    """Map a commitment to a routing bucket: int(SHA256(commitment)[:2]) mod B."""
    h = hashlib.sha256(commitment).digest()
    return int.from_bytes(h[:2], "big") % num_buckets


def compute_fingerprint(commitment: bytes, timestamp: int) -> bytes:
    """Bloom fingerprint for a commitment in the time window containing ``timestamp``.

    The timestamp is floored to the global ``WINDOW_SECONDS`` grid so that a producer
    and a consumer independently compute the *same* fingerprint for the same window
    without coordinating clocks (beyond coarse agreement on wall-clock seconds).
    """
    window = int(timestamp) - (int(timestamp) % WINDOW_SECONDS)
    return hashlib.sha256(commitment + window.to_bytes(8, "big")).digest()[:8]


def make_routing_fields(
    commitment: bytes, timestamp: int = None, num_buckets: int = NUM_BUCKETS
) -> dict:
    """Routing fields a proof producer attaches so subscribers can match the proof.

    Returns ``{bucket, bloom_fingerprint (b64), timestamp}`` consistent with how
    :class:`Subscription` indexes itself.
    """
    ts = int(time.time()) if timestamp is None else int(timestamp)
    return {
        "bucket": compute_bucket(commitment, num_buckets),
        "bloom_fingerprint": base64.b64encode(
            compute_fingerprint(commitment, ts)
        ).decode(),
        "timestamp": ts,
    }


class Subscription:
    """Customer subscription for filtered proof delivery."""

    def __init__(self, commitment: bytes, linked_orgs: List[str] = None):
        self.commitment = commitment
        self.time_window = 600  # 10 minutes (must be set before _create_bloom_filter)
        self.linked_orgs = linked_orgs or []
        self.bucket = self._compute_bucket(commitment)
        self.bloom_filter = self._create_bloom_filter(commitment)

    def _compute_bucket(self, commitment: bytes, num_buckets: int = NUM_BUCKETS) -> int:
        """Compute bucket from commitment (delegates to the canonical function)."""
        return compute_bucket(commitment, num_buckets)

    def _create_bloom_filter(self, commitment: bytes) -> BloomFilter:
        """Create bloom filter holding fingerprints for recent time windows."""
        bf = BloomFilter(size=1024, hash_count=3)

        # Add a fingerprint for each WINDOW_SECONDS-aligned window over the lookback.
        current_time = int(time.time())
        for offset in range(0, self.time_window, WINDOW_SECONDS):
            bf.add(compute_fingerprint(commitment, current_time - offset))

        return bf

    def _compute_fingerprint(self, commitment: bytes, timestamp: int) -> bytes:
        """Compute bloom fingerprint (delegates to the canonical function)."""
        return compute_fingerprint(commitment, timestamp)

    def to_dict(self) -> dict:
        """Serialize subscription for transmission."""
        return {
            "bucket": self.bucket,
            "bloom_filter": base64.b64encode(self.bloom_filter.to_bytes()).decode(),
            "org_hints": self.linked_orgs,
            "since_timestamp": int(time.time()) - self.time_window,
        }

    def matches_proof(self, proof: dict) -> bool:
        """Check if proof might match this subscription (local verification)."""
        # Bucket check
        if proof.get("bucket") != self.bucket:
            return False

        # Time check
        if proof.get("timestamp", 0) < int(time.time()) - self.time_window:
            return False

        # Org hint check (if specified)
        if self.linked_orgs:
            proof_org = proof.get("org_hint")
            if proof_org and proof_org not in self.linked_orgs:
                return False

        # Bloom filter check
        fingerprint = base64.b64decode(proof.get("bloom_fingerprint", ""))
        if not self.bloom_filter.might_contain(fingerprint):
            return False

        return True


class DecentralizedNode:
    """
    Decentralized Tessera node.

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

        # Initialize SQLite storage
        db_path = str(self.data_dir / "node.db")
        self.storage = NodeStorage(db_path)

        # Store node configuration
        self.storage.set_config("node_id", node_id)
        self.storage.set_config("node_type", node_type.value)

        # In-memory caches (rebuilt from storage on startup)
        self.peers: Dict[str, dict] = {}
        self.bucket_subscribers: Dict[int, Set[str]] = defaultdict(set)

        # Local matching (for customer nodes)
        self.my_subscriptions: List[Subscription] = []
        self.matched_proofs: List[dict] = []

        # Load state from storage
        self._load_state()

    def _load_state(self):
        """Load state from persistent storage."""
        # Load peers
        for peer in self.storage.get_active_peers():
            self.peers[peer["peer_id"]] = peer

        # Load subscriptions and rebuild bucket index
        for sub_data in self.storage.get_all_subscriptions():
            bucket = sub_data["bucket"]
            subscriber_id = sub_data["subscriber_id"]
            self.bucket_subscribers[bucket].add(subscriber_id)

    def _get_stats(self) -> dict:
        """Get statistics from storage."""
        return self.storage.get_all_stats()

    # ─────────────────────────────────────────────────────────────
    # Core Node Functions
    # ─────────────────────────────────────────────────────────────

    def register_subscription(self, subscriber_id: str, subscription_data: dict):
        """
        Register a customer subscription (core node function).

        Args:
            subscriber_id: Unique subscriber identifier
            subscription_data: Subscription parameters
        """
        bucket = subscription_data["bucket"]

        # Store in database
        self.storage.store_subscription(subscriber_id, subscription_data)

        # Update in-memory bucket index
        self.bucket_subscribers[bucket].add(subscriber_id)

        self.storage.increment_stat("subscriptions_registered")

    def unregister_subscription(self, subscriber_id: str):
        """Remove a customer subscription."""
        # Get subscription to find bucket
        sub_data = self.storage.get_subscription(subscriber_id)
        if not sub_data:
            return

        # Remove from in-memory index
        bucket = sub_data["bucket"]
        self.bucket_subscribers[bucket].discard(subscriber_id)

        # Remove from database
        self.storage.delete_subscription(subscriber_id)

    def route_proof(self, proof: dict, from_peer: str = None) -> int:
        """
        Route a proof to relevant subscribers (core node function).

        Returns:
            int: Number of subscribers notified
        """
        self.storage.increment_stat("proofs_received")

        # Dedup check
        proof_id = self._hash_proof(proof)
        if self.storage.proof_exists(proof_id):
            return 0

        # Store proof
        is_new = self.storage.store_proof(proof_id, proof, from_peer, self.proof_ttl)
        if not is_new:
            return 0

        # Find matching subscribers by bucket
        bucket = proof.get("bucket")
        if bucket is None:
            return 0

        potential_subscribers = self.bucket_subscribers.get(bucket, set())
        notified = 0

        for subscriber_id in potential_subscribers:
            # Get subscription from storage
            sub_data = self.storage.get_subscription(subscriber_id)
            if not sub_data:
                continue

            # Apply filters
            if not self._matches_subscription_data(proof, sub_data):
                continue

            # Queue for delivery
            self.storage.queue_proof_for_subscriber(subscriber_id, proof_id)
            notified += 1

        # Gossip to peer core nodes (exclude sender)
        self._gossip_to_peers(proof, exclude=from_peer)

        self.storage.increment_stat("proofs_forwarded")
        return notified

    def _matches_subscription_data(self, proof: dict, sub_data: dict) -> bool:
        """Check if proof matches subscription filters using stored data."""
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

    def _matches_subscription(self, proof: dict, sub: Subscription) -> bool:
        """Check if proof matches subscription filters."""
        # Time check
        since_ts = int(time.time()) - sub.time_window
        if proof.get("timestamp", 0) < since_ts:
            return False

        # Org hint check
        if sub.linked_orgs:
            proof_org = proof.get("org_hint")
            if proof_org and proof_org not in sub.linked_orgs:
                return False

        # Bloom filter check
        fingerprint = base64.b64decode(proof.get("bloom_fingerprint", ""))
        if not sub.bloom_filter.might_contain(fingerprint):
            return False

        return True

    def get_pending_proofs(self, subscriber_id: str) -> List[dict]:
        """
        Get pending proofs for a subscriber (pull model).

        Args:
            subscriber_id: Subscriber to get proofs for

        Returns:
            list: Pending proofs
        """
        # Update last seen
        self.storage.update_subscriber_last_seen(subscriber_id)

        # Get and clear pending proofs from storage
        return self.storage.get_pending_proofs(subscriber_id, delete_after=True)

    # ─────────────────────────────────────────────────────────────
    # Organization Node Functions
    # ─────────────────────────────────────────────────────────────

    def broadcast_proof(self, proof: dict, decoy_buckets: List[int] = None):
        """
        Broadcast a proof with optional cover traffic (org node function).

        Args:
            proof: The real proof to broadcast
            decoy_buckets: Additional buckets for decoy proofs
        """
        # Broadcast real proof
        self._send_to_core_nodes(proof)

        # Generate and broadcast decoys
        if decoy_buckets:
            for bucket in decoy_buckets:
                decoy = self._generate_decoy_proof(bucket, proof.get("org_hint"))
                self._send_to_core_nodes(decoy)

    def _generate_decoy_proof(self, bucket: int, org_hint: str = None) -> dict:
        """Generate a decoy proof for cover traffic."""
        return {
            "bucket": bucket,
            "bloom_fingerprint": base64.b64encode(secrets.token_bytes(8)).decode(),
            "ciphertext": base64.b64encode(secrets.token_bytes(128)).decode(),
            "nonce": base64.b64encode(secrets.token_bytes(12)).decode(),
            "timestamp": int(time.time()),
            "org_hint": org_hint,
            "is_decoy": True,  # Only known to org, stripped before broadcast
        }

    def _send_to_core_nodes(self, proof: dict):
        """Send proof to connected core nodes."""
        # Strip internal flags
        proof_to_send = {k: v for k, v in proof.items() if k != "is_decoy"}

        for peer_id, peer_info in self.peers.items():
            if peer_info.get("node_type") == NodeType.CORE:
                self._send_to_peer(peer_id, proof_to_send)

    # ─────────────────────────────────────────────────────────────
    # Customer Node Functions
    # ─────────────────────────────────────────────────────────────

    def subscribe(
        self, commitment: bytes, linked_orgs: List[str] = None
    ) -> Subscription:
        """
        Create subscription for this customer node.

        Args:
            commitment: Customer's commitment
            linked_orgs: Organizations customer has linked with

        Returns:
            Subscription: The subscription object
        """
        sub = Subscription(commitment, linked_orgs)
        self.my_subscriptions.append(sub)
        return sub

    def receive_proof(self, proof: dict):
        """
        Receive a proof from network (customer node function).

        Args:
            proof: Proof to check
        """
        self.stats["proofs_received"] += 1

        # Check against all subscriptions
        for sub in self.my_subscriptions:
            if sub.matches_proof(proof):
                self.matched_proofs.append(proof)
                self.stats["proofs_matched"] += 1
                self._notify_proof_received(proof)
                break

    def pull_proofs(self, core_node_url: str) -> List[dict]:
        """
        Pull pending proofs from core node (pull model).

        Args:
            core_node_url: URL of core node to pull from

        Returns:
            list: Retrieved proofs
        """
        # In real implementation, this would be an HTTP/WebSocket call
        # For now, return local matched proofs
        proofs = self.matched_proofs.copy()
        self.matched_proofs = []
        return proofs

    def _notify_proof_received(self, proof: dict):
        """Notify local application of received proof."""
        # Override in subclass or set callback
        pass

    # ─────────────────────────────────────────────────────────────
    # Common Functions
    # ─────────────────────────────────────────────────────────────

    def connect_peer(self, peer_id: str, peer_info: dict):
        """Connect to a peer node."""
        self.peers[peer_id] = peer_info
        self.storage.store_peer(peer_id, peer_info)

    def disconnect_peer(self, peer_id: str):
        """Disconnect from a peer node."""
        if peer_id in self.peers:
            del self.peers[peer_id]
        self.storage.deactivate_peer(peer_id)

    def _gossip_to_peers(self, proof: dict, exclude: str = None):
        """Gossip proof to peer nodes."""
        for peer_id in self.peers:
            if peer_id != exclude:
                self._send_to_peer(peer_id, proof)

    def _send_to_peer(self, peer_id: str, proof: dict):
        """Send proof to specific peer (override for actual network)."""
        # In real implementation, this sends over network
        pass

    def _hash_proof(self, proof: dict) -> str:
        """Compute unique hash for proof deduplication."""
        # Use fingerprint + timestamp for uniqueness
        data = proof.get("bloom_fingerprint", "") + str(proof.get("timestamp", 0))
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def cleanup_expired(self) -> int:
        """Remove expired proofs from storage. Returns count deleted."""
        return self.storage.cleanup_expired_proofs()

    def get_stats(self) -> dict:
        """Get node statistics."""
        db_stats = self.storage.get_database_stats()
        counter_stats = self.storage.get_all_stats()

        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "peers": len(self.peers),
            "subscriptions": db_stats.get("total_subscriptions", 0),
            "cached_proofs": db_stats.get("total_proofs", 0),
            "pending_proofs": db_stats.get("total_pending", 0),
            "db_size_bytes": db_stats.get("db_size_bytes", 0),
            "counters": counter_stats,
        }

    def shutdown(self):
        """Gracefully shutdown the node."""
        # Cleanup expired data
        self.cleanup_expired()

        # Vacuum database
        self.storage.vacuum()

        # Close storage
        self.storage.close()

    def run_maintenance(self):
        """Run periodic maintenance tasks."""
        # Cleanup expired proofs
        deleted = self.cleanup_expired()
        if deleted > 0:
            self.storage.increment_stat("proofs_expired", deleted)

        # Could add: cleanup stale subscriptions, vacuum db, etc.


class PrivacyPreservingBroadcaster:
    """
    Helper for organizations to broadcast proofs with cover traffic.
    """

    def __init__(self, org_node: DecentralizedNode, num_decoys: int = 3):
        self.node = org_node
        self.num_decoys = num_decoys
        self.num_buckets = 64

    def broadcast_with_cover(self, proof: dict) -> dict:
        """
        Broadcast proof with cover traffic to random buckets.

        Args:
            proof: Real proof to broadcast

        Returns:
            dict: Broadcast statistics
        """
        real_bucket = proof.get("bucket")

        # Generate random decoy buckets (excluding real)
        decoy_buckets = []
        while len(decoy_buckets) < self.num_decoys:
            bucket = secrets.randbelow(self.num_buckets)
            if bucket != real_bucket and bucket not in decoy_buckets:
                decoy_buckets.append(bucket)

        # Broadcast
        self.node.broadcast_proof(proof, decoy_buckets)

        return {
            "real_bucket": real_bucket,
            "decoy_buckets": decoy_buckets,
            "total_broadcasts": 1 + len(decoy_buckets),
            "privacy_ratio": len(decoy_buckets) / (1 + len(decoy_buckets)),
        }


class CustomerNodeClient:
    """
    Lightweight customer node client for mobile/desktop apps.
    """

    def __init__(self, commitment: bytes, linked_orgs: List[str] = None):
        self.commitment = commitment
        self.subscription = Subscription(commitment, linked_orgs)
        self.core_node_urls = [
            "core1.tessera.network",
            "core2.tessera.network",
            "core3.tessera.network",
        ]

    def get_subscription_data(self) -> dict:
        """Get subscription data to send to core node."""
        return self.subscription.to_dict()

    def verify_proof_locally(self, proof: dict) -> bool:
        """
        Verify if proof matches our subscription locally.

        Args:
            proof: Proof to verify

        Returns:
            bool: True if proof might be for us
        """
        return self.subscription.matches_proof(proof)

    def filter_proofs(self, proofs: List[dict]) -> List[dict]:
        """
        Filter list of proofs to only those matching our subscription.

        Args:
            proofs: List of proofs from core node

        Returns:
            list: Filtered proofs
        """
        return [p for p in proofs if self.verify_proof_locally(p)]
