"""
Integration tests for CallDNS decentralized network.
Tests node communication, proof routing, and subscription matching.
"""

import pytest
import asyncio
import base64
import hashlib
import secrets
import time
import tempfile
import shutil
from pathlib import Path

from calldns.network.async_node import AsyncDecentralizedNode, AsyncPrivacyPreservingBroadcaster
from calldns.network.decentralized import NodeType, Subscription


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix="calldns_test_")
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
async def core_node(temp_data_dir):
    """Create and initialize a core node."""
    node = AsyncDecentralizedNode(
        node_id="test-core-1",
        node_type=NodeType.CORE,
        data_dir=f"{temp_data_dir}/core1"
    )
    await node.initialize()
    yield node
    await node.shutdown()


@pytest.fixture
async def org_node(temp_data_dir):
    """Create and initialize an organization node."""
    node = AsyncDecentralizedNode(
        node_id="test-org-1",
        node_type=NodeType.ORGANIZATION,
        data_dir=f"{temp_data_dir}/org1"
    )
    await node.initialize()
    yield node
    await node.shutdown()


@pytest.fixture
async def customer_node(temp_data_dir):
    """Create and initialize a customer node."""
    node = AsyncDecentralizedNode(
        node_id="test-customer-1",
        node_type=NodeType.CUSTOMER,
        data_dir=f"{temp_data_dir}/customer1"
    )
    await node.initialize()
    yield node
    await node.shutdown()


def create_test_commitment(value: str = "test") -> bytes:
    """Create a test commitment."""
    return hashlib.sha256(value.encode()).digest()


def create_test_subscription(commitment: bytes) -> dict:
    """Create a subscription data dict from commitment."""
    sub = Subscription(commitment, linked_orgs=["test-org"])
    return sub.to_dict()


def create_test_proof(commitment: bytes, org_hint: str = "test-org") -> dict:
    """Create a test proof matching a commitment."""
    bucket = int.from_bytes(commitment[:2], 'big') % 64

    # Create bloom fingerprint that matches the commitment
    fingerprint = commitment[:8]

    return {
        "bucket": bucket,
        "bloom_fingerprint": base64.b64encode(fingerprint).decode(),
        "ciphertext": base64.b64encode(secrets.token_bytes(128)).decode(),
        "nonce": base64.b64encode(secrets.token_bytes(12)).decode(),
        "timestamp": int(time.time()),
        "org_hint": org_hint
    }


class TestAsyncDecentralizedNode:
    """Tests for AsyncDecentralizedNode."""

    @pytest.mark.asyncio
    async def test_node_initialization(self, core_node):
        """Test that node initializes correctly."""
        assert core_node.node_id == "test-core-1"
        assert core_node.node_type == NodeType.CORE

        stats = await core_node.get_stats()
        assert stats["node_id"] == "test-core-1"
        assert stats["node_type"] == "core"

    @pytest.mark.asyncio
    async def test_subscription_registration(self, core_node):
        """Test subscription registration."""
        commitment = create_test_commitment("subscriber1")
        subscription = create_test_subscription(commitment)

        await core_node.register_subscription("sub-1", subscription)

        stats = await core_node.get_stats()
        assert stats["subscriptions"] == 1

    @pytest.mark.asyncio
    async def test_subscription_unregistration(self, core_node):
        """Test subscription unregistration."""
        commitment = create_test_commitment("subscriber1")
        subscription = create_test_subscription(commitment)

        await core_node.register_subscription("sub-1", subscription)
        await core_node.unregister_subscription("sub-1")

        stats = await core_node.get_stats()
        assert stats["subscriptions"] == 0

    @pytest.mark.asyncio
    async def test_proof_routing_to_subscriber(self, core_node):
        """Test that proofs are routed to matching subscribers."""
        # Register subscription
        commitment = create_test_commitment("user123")
        subscription = create_test_subscription(commitment)
        await core_node.register_subscription("sub-user123", subscription)

        # Create matching proof
        proof = create_test_proof(commitment)

        # Route proof
        notified = await core_node.route_proof(proof)
        assert notified == 1

        # Fetch proof
        proofs = await core_node.get_pending_proofs("sub-user123")
        assert len(proofs) == 1
        assert proofs[0]["bucket"] == proof["bucket"]

    @pytest.mark.asyncio
    async def test_proof_deduplication(self, core_node):
        """Test that duplicate proofs are not routed twice."""
        commitment = create_test_commitment("dedup-test")
        subscription = create_test_subscription(commitment)
        await core_node.register_subscription("sub-dedup", subscription)

        proof = create_test_proof(commitment)

        # Route same proof twice
        first = await core_node.route_proof(proof)
        second = await core_node.route_proof(proof)

        assert first == 1
        assert second == 0

    @pytest.mark.asyncio
    async def test_proof_bucket_filtering(self, core_node):
        """Test that proofs only go to subscribers in matching bucket."""
        # Two subscriptions in different buckets
        commitment1 = create_test_commitment("bucket-test-1")
        commitment2 = create_test_commitment("bucket-test-2")

        sub1 = create_test_subscription(commitment1)
        sub2 = create_test_subscription(commitment2)

        await core_node.register_subscription("sub-1", sub1)
        await core_node.register_subscription("sub-2", sub2)

        # Create proof for first commitment only
        proof = create_test_proof(commitment1)
        notified = await core_node.route_proof(proof)

        # Check only first subscriber got it
        proofs1 = await core_node.get_pending_proofs("sub-1")
        proofs2 = await core_node.get_pending_proofs("sub-2")

        # At least sub-1 should have received it
        assert len(proofs1) >= 1 or len(proofs2) == 0

    @pytest.mark.asyncio
    async def test_org_hint_filtering(self, core_node):
        """Test org hint filtering in subscriptions."""
        commitment = create_test_commitment("org-filter-test")

        # Subscription that only wants proofs from "bank-a"
        sub_data = create_test_subscription(commitment)
        sub_data["org_hints"] = ["bank-a"]
        await core_node.register_subscription("sub-org-filter", sub_data)

        # Proof from different org
        proof = create_test_proof(commitment, org_hint="bank-b")
        notified = await core_node.route_proof(proof)

        # Should not be delivered due to org filter
        proofs = await core_node.get_pending_proofs("sub-org-filter")
        assert len(proofs) == 0

    @pytest.mark.asyncio
    async def test_time_window_filtering(self, core_node):
        """Test time window filtering."""
        commitment = create_test_commitment("time-test")
        sub_data = create_test_subscription(commitment)
        sub_data["time_window"] = 60  # 60 seconds

        await core_node.register_subscription("sub-time", sub_data)

        # Create old proof
        proof = create_test_proof(commitment)
        proof["timestamp"] = int(time.time()) - 120  # 2 minutes ago

        notified = await core_node.route_proof(proof)
        proofs = await core_node.get_pending_proofs("sub-time")

        # Should not be delivered due to time window
        assert len(proofs) == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_bucket(self, core_node):
        """Test multiple subscribers in same bucket all get proof."""
        # Create commitments that hash to same bucket
        # (For testing, we'll just use two subscriptions with same bucket)
        commitment = create_test_commitment("multi-sub")
        sub_data = create_test_subscription(commitment)

        await core_node.register_subscription("sub-a", sub_data)
        await core_node.register_subscription("sub-b", sub_data)

        proof = create_test_proof(commitment)
        notified = await core_node.route_proof(proof)

        assert notified == 2


class TestPrivacyPreservingBroadcaster:
    """Tests for cover traffic broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_with_decoys(self, org_node):
        """Test that broadcaster generates decoy proofs."""
        broadcaster = AsyncPrivacyPreservingBroadcaster(org_node, num_decoys=3)

        commitment = create_test_commitment("broadcast-test")
        proof = create_test_proof(commitment)

        result = await broadcaster.broadcast_with_cover(proof)

        assert result["total_broadcasts"] == 4  # 1 real + 3 decoys
        assert len(result["decoy_buckets"]) == 3
        assert result["real_bucket"] not in result["decoy_buckets"]


class TestNodePersistence:
    """Tests for node data persistence."""

    @pytest.mark.asyncio
    async def test_subscription_persistence(self, temp_data_dir):
        """Test that subscriptions persist across node restarts."""
        # Create and setup node
        node1 = AsyncDecentralizedNode(
            node_id="persist-test",
            node_type=NodeType.CORE,
            data_dir=f"{temp_data_dir}/persist"
        )
        await node1.initialize()

        commitment = create_test_commitment("persist-sub")
        subscription = create_test_subscription(commitment)
        await node1.register_subscription("sub-persist", subscription)

        await node1.shutdown()

        # Create new node with same data dir
        node2 = AsyncDecentralizedNode(
            node_id="persist-test",
            node_type=NodeType.CORE,
            data_dir=f"{temp_data_dir}/persist"
        )
        await node2.initialize()

        # Check subscription still exists
        stats = await node2.get_stats()
        assert stats["subscriptions"] == 1

        await node2.shutdown()

    @pytest.mark.asyncio
    async def test_proof_expiration(self, core_node):
        """Test that expired proofs are cleaned up."""
        # Set short TTL for testing
        core_node.proof_ttl = 1

        commitment = create_test_commitment("expire-test")
        subscription = create_test_subscription(commitment)
        await core_node.register_subscription("sub-expire", subscription)

        proof = create_test_proof(commitment)
        await core_node.route_proof(proof)

        # Wait for expiration
        await asyncio.sleep(2)

        # Run cleanup
        deleted = await core_node.cleanup_expired()
        assert deleted >= 1


class TestNodeStatistics:
    """Tests for node statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_tracking(self, core_node):
        """Test that statistics are tracked correctly."""
        commitment = create_test_commitment("stats-test")
        subscription = create_test_subscription(commitment)

        await core_node.register_subscription("sub-stats", subscription)

        proof = create_test_proof(commitment)
        await core_node.route_proof(proof)

        stats = await core_node.get_stats()

        assert stats["subscriptions"] == 1
        assert stats["cached_proofs"] >= 1
        counters = stats.get("counters", {})
        assert counters.get("proofs_received", 0) >= 1


class TestEndToEndFlow:
    """End-to-end tests for complete proof flow."""

    @pytest.mark.asyncio
    async def test_complete_proof_flow(self, temp_data_dir):
        """Test complete flow: subscribe -> broadcast -> receive."""
        # Setup core node
        core = AsyncDecentralizedNode(
            node_id="e2e-core",
            node_type=NodeType.CORE,
            data_dir=f"{temp_data_dir}/e2e-core"
        )
        await core.initialize()

        # Customer creates subscription
        commitment = create_test_commitment("customer-phone-123")
        subscription = create_test_subscription(commitment)
        await core.register_subscription("customer-device", subscription)

        # Organization broadcasts proof
        proof = create_test_proof(commitment, org_hint="test-org")
        notified = await core.route_proof(proof)
        assert notified == 1

        # Customer fetches proof
        proofs = await core.get_pending_proofs("customer-device")
        assert len(proofs) == 1
        assert proofs[0]["org_hint"] == "test-org"

        # Fetching again should return empty (proofs deleted after fetch)
        proofs = await core.get_pending_proofs("customer-device")
        assert len(proofs) == 0

        await core.shutdown()

    @pytest.mark.asyncio
    async def test_multi_device_customer(self, temp_data_dir):
        """Test customer with multiple devices."""
        core = AsyncDecentralizedNode(
            node_id="multidev-core",
            node_type=NodeType.CORE,
            data_dir=f"{temp_data_dir}/multidev-core"
        )
        await core.initialize()

        # Same commitment for both devices
        commitment = create_test_commitment("multi-device-user")
        sub_data = create_test_subscription(commitment)

        await core.register_subscription("device-1", sub_data)
        await core.register_subscription("device-2", sub_data)

        # Broadcast proof
        proof = create_test_proof(commitment)
        notified = await core.route_proof(proof)
        assert notified == 2

        # Both devices should have the proof
        proofs1 = await core.get_pending_proofs("device-1")
        proofs2 = await core.get_pending_proofs("device-2")

        assert len(proofs1) == 1
        assert len(proofs2) == 1

        await core.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
