"""
Kademlia-style DHT for Tessera peer discovery.
Provides decentralized peer lookup without central coordination.
"""

import asyncio
import hashlib
import heapq
import random
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# DHT parameters
K = 20  # Bucket size (replication factor)
ALPHA = 3  # Parallel lookups
ID_BITS = 160  # Node ID size in bits


@dataclass
class DHTNode:
    """A node in the DHT network."""

    node_id: bytes
    host: str
    port: int
    node_type: str = "core"
    last_seen: float = 0
    rtt_ms: float = 0

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        return self.node_id == other.node_id

    def distance(self, other_id: bytes) -> int:
        """XOR distance to another node ID."""
        return int.from_bytes(
            bytes(a ^ b for a, b in zip(self.node_id, other_id)), "big"
        )

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id.hex(),
            "host": self.host,
            "port": self.port,
            "node_type": self.node_type,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DHTNode":
        return cls(
            node_id=bytes.fromhex(data["node_id"]),
            host=data["host"],
            port=data["port"],
            node_type=data.get("node_type", "core"),
            last_seen=data.get("last_seen", 0),
        )


class KBucket:
    """A k-bucket for storing nodes at a specific distance range."""

    def __init__(self, k: int = K):
        self.k = k
        self.nodes: List[DHTNode] = []
        self.replacement_cache: List[DHTNode] = []

    def add(self, node: DHTNode) -> bool:
        """Add a node to the bucket. Returns True if added."""
        # Check if node already exists
        for i, existing in enumerate(self.nodes):
            if existing.node_id == node.node_id:
                # Move to end (most recently seen)
                self.nodes.pop(i)
                self.nodes.append(node)
                return True

        # Bucket not full
        if len(self.nodes) < self.k:
            self.nodes.append(node)
            return True

        # Bucket full - add to replacement cache
        self.replacement_cache.append(node)
        if len(self.replacement_cache) > self.k:
            self.replacement_cache.pop(0)
        return False

    def remove(self, node_id: bytes):
        """Remove a node from the bucket."""
        self.nodes = [n for n in self.nodes if n.node_id != node_id]

        # Promote from replacement cache
        if self.replacement_cache and len(self.nodes) < self.k:
            self.nodes.append(self.replacement_cache.pop(0))

    def get_nodes(self) -> List[DHTNode]:
        """Get all nodes in the bucket."""
        return list(self.nodes)

    def __len__(self):
        return len(self.nodes)


class RoutingTable:
    """Kademlia routing table with k-buckets."""

    def __init__(self, local_id: bytes, k: int = K):
        self.local_id = local_id
        self.k = k
        self.buckets: List[KBucket] = [KBucket(k) for _ in range(ID_BITS)]

    def _bucket_index(self, node_id: bytes) -> int:
        """Get bucket index for a node ID based on XOR distance."""
        distance = int.from_bytes(
            bytes(a ^ b for a, b in zip(self.local_id, node_id)), "big"
        )
        if distance == 0:
            return 0
        return distance.bit_length() - 1

    def add_node(self, node: DHTNode) -> bool:
        """Add a node to the routing table."""
        if node.node_id == self.local_id:
            return False

        index = self._bucket_index(node.node_id)
        return self.buckets[index].add(node)

    def remove_node(self, node_id: bytes):
        """Remove a node from the routing table."""
        index = self._bucket_index(node_id)
        self.buckets[index].remove(node_id)

    def find_closest(self, target_id: bytes, count: int = K) -> List[DHTNode]:
        """Find the closest nodes to a target ID."""
        all_nodes = []
        for bucket in self.buckets:
            all_nodes.extend(bucket.get_nodes())

        # Sort by distance to target
        all_nodes.sort(key=lambda n: n.distance(target_id))
        return all_nodes[:count]

    def get_all_nodes(self) -> List[DHTNode]:
        """Get all nodes in the routing table."""
        nodes = []
        for bucket in self.buckets:
            nodes.extend(bucket.get_nodes())
        return nodes

    def get_stats(self) -> dict:
        """Get routing table statistics."""
        total_nodes = sum(len(b) for b in self.buckets)
        non_empty_buckets = sum(1 for b in self.buckets if len(b) > 0)
        return {
            "total_nodes": total_nodes,
            "non_empty_buckets": non_empty_buckets,
            "total_buckets": len(self.buckets),
        }


class KademliaDHT:
    """
    Kademlia DHT implementation for peer discovery.

    Features:
    - XOR-based distance metric
    - Iterative node lookup
    - Bootstrap from seed nodes
    - Periodic refresh
    """

    def __init__(self, node_id: str, host: str, port: int, node_type: str = "core"):
        # Generate 160-bit node ID from string ID
        self.node_id = hashlib.sha1(node_id.encode()).digest()
        self.host = host
        self.port = port
        self.node_type = node_type

        self.routing_table = RoutingTable(self.node_id)
        self.bootstrap_nodes: List[DHTNode] = []

        # RPC callbacks
        self._ping_callback = None
        self._find_node_callback = None
        self._store_callback = None

        # State
        self._running = False
        self._refresh_task = None

    def set_callbacks(self, ping_fn, find_node_fn, store_fn=None):
        """Set RPC callbacks."""
        self._ping_callback = ping_fn
        self._find_node_callback = find_node_fn
        self._store_callback = store_fn

    def add_bootstrap_node(self, host: str, port: int, node_id: str = None):
        """Add a bootstrap node."""
        if node_id:
            nid = hashlib.sha1(node_id.encode()).digest()
        else:
            nid = hashlib.sha1(f"{host}:{port}".encode()).digest()

        node = DHTNode(node_id=nid, host=host, port=port, node_type="core")
        self.bootstrap_nodes.append(node)

    async def start(self):
        """Start the DHT."""
        self._running = True

        # Bootstrap
        await self._bootstrap()

        # Start refresh task
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def stop(self):
        """Stop the DHT."""
        self._running = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

    async def _bootstrap(self):
        """Bootstrap from seed nodes."""
        if not self.bootstrap_nodes:
            return

        print(f"DHT: Bootstrapping from {len(self.bootstrap_nodes)} nodes...")

        # Add bootstrap nodes to routing table
        for node in self.bootstrap_nodes:
            self.routing_table.add_node(node)

        # Look up our own ID to populate routing table
        await self.find_node(self.node_id)

    async def _refresh_loop(self):
        """Periodically refresh buckets."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Every hour
                await self._refresh_buckets()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"DHT refresh error: {e}")

    async def _refresh_buckets(self):
        """Refresh stale buckets by looking up random IDs."""
        for i, bucket in enumerate(self.routing_table.buckets):
            if len(bucket) == 0:
                continue

            # Check if bucket is stale (no recent activity)
            if all(n.last_seen < time.time() - 3600 for n in bucket.nodes):
                # Generate random ID in bucket's range
                random_id = self._random_id_in_bucket(i)
                await self.find_node(random_id)

    def _random_id_in_bucket(self, bucket_index: int) -> bytes:
        """Generate a random ID that would fall in the given bucket."""
        # XOR with our ID to get target distance
        distance = random.getrandbits(bucket_index + 1)
        distance |= 1 << bucket_index  # Ensure it's in the right bucket

        local_int = int.from_bytes(self.node_id, "big")
        target_int = local_int ^ distance
        return target_int.to_bytes(20, "big")

    async def find_node(self, target_id: bytes) -> List[DHTNode]:
        """
        Iterative node lookup.

        Returns the K closest nodes to target_id.
        """
        # Get initial closest nodes
        closest = self.routing_table.find_closest(target_id, K)
        if not closest:
            return []

        # Track queried nodes
        queried = set()
        queried.add(self.node_id)

        # Iterative lookup
        while True:
            # Find unqueried nodes
            unqueried = [n for n in closest if n.node_id not in queried]
            if not unqueried:
                break

            # Query ALPHA nodes in parallel
            to_query = unqueried[:ALPHA]
            tasks = []

            for node in to_query:
                queried.add(node.node_id)
                if self._find_node_callback:
                    tasks.append(self._query_node(node, target_id))

            if not tasks:
                break

            # Wait for responses
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, list):
                    for node_data in result:
                        try:
                            node = DHTNode.from_dict(node_data)
                            if node.node_id not in queried:
                                self.routing_table.add_node(node)
                                closest.append(node)
                        except Exception:
                            pass

            # Re-sort by distance
            closest.sort(key=lambda n: n.distance(target_id))
            closest = closest[:K]

        return closest

    async def _query_node(self, node: DHTNode, target_id: bytes) -> List[dict]:
        """Query a node for closer nodes."""
        if not self._find_node_callback:
            return []

        try:
            start = time.time()
            result = await asyncio.wait_for(
                self._find_node_callback(node.host, node.port, target_id.hex()),
                timeout=5.0,
            )
            node.rtt_ms = (time.time() - start) * 1000
            node.last_seen = time.time()
            return result
        except Exception:
            # Mark node as failed
            self.routing_table.remove_node(node.node_id)
            return []

    def add_node(self, host: str, port: int, node_id: str, node_type: str = "core"):
        """Add a discovered node to the DHT."""
        nid = hashlib.sha1(node_id.encode()).digest()
        node = DHTNode(
            node_id=nid,
            host=host,
            port=port,
            node_type=node_type,
            last_seen=time.time(),
        )
        self.routing_table.add_node(node)

    def get_peers(self, count: int = 10) -> List[DHTNode]:
        """Get random peers from the DHT."""
        all_nodes = self.routing_table.get_all_nodes()
        if len(all_nodes) <= count:
            return all_nodes
        return random.sample(all_nodes, count)

    def get_closest_peers(self, target: str, count: int = K) -> List[DHTNode]:
        """Get peers closest to a target."""
        target_id = hashlib.sha1(target.encode()).digest()
        return self.routing_table.find_closest(target_id, count)

    def handle_find_node(self, target_id_hex: str) -> List[dict]:
        """Handle incoming FIND_NODE RPC."""
        target_id = bytes.fromhex(target_id_hex)
        closest = self.routing_table.find_closest(target_id, K)
        return [n.to_dict() for n in closest]

    def get_stats(self) -> dict:
        """Get DHT statistics."""
        rt_stats = self.routing_table.get_stats()
        return {
            "node_id": self.node_id.hex(),
            "host": self.host,
            "port": self.port,
            "bootstrap_nodes": len(self.bootstrap_nodes),
            **rt_stats,
        }


def create_dht(
    node_id: str,
    host: str,
    port: int,
    node_type: str = "core",
    bootstrap_nodes: List[Tuple[str, int]] = None,
) -> KademliaDHT:
    """Create and configure a DHT instance."""
    dht = KademliaDHT(node_id, host, port, node_type)

    if bootstrap_nodes:
        for host, port in bootstrap_nodes:
            dht.add_bootstrap_node(host, port)

    return dht
