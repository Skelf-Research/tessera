"""
Node discovery service for CallDNS network.
Supports seed nodes, peer exchange, and automatic reconnection.
"""

import asyncio
import json
import random
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class PeerInfo:
    """Information about a peer node."""
    peer_id: str
    host: str
    port: int
    node_type: str
    last_seen: float = 0
    failures: int = 0
    connected: bool = False

    def to_dict(self) -> dict:
        return {
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
            "node_type": self.node_type,
            "last_seen": self.last_seen,
            "connected": self.connected
        }


class NodeDiscovery:
    """
    Handles peer discovery for CallDNS nodes.

    Features:
    - Seed node bootstrap
    - Peer exchange protocol
    - Automatic reconnection
    - Peer scoring and pruning
    """

    def __init__(
        self,
        node_id: str,
        node_type: str,
        max_peers: int = 50,
        min_peers: int = 3
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.max_peers = max_peers
        self.min_peers = min_peers

        # Known peers
        self.peers: Dict[str, PeerInfo] = {}
        self.seed_nodes: List[PeerInfo] = []

        # Connection callbacks
        self._connect_callback = None
        self._disconnect_callback = None

        # State
        self._running = False
        self._discovery_task = None

    def set_callbacks(self, connect_fn, disconnect_fn):
        """Set connection callbacks."""
        self._connect_callback = connect_fn
        self._disconnect_callback = disconnect_fn

    def add_seed_node(self, peer_id: str, host: str, port: int, node_type: str = "core"):
        """Add a seed node for initial bootstrap."""
        peer = PeerInfo(
            peer_id=peer_id,
            host=host,
            port=port,
            node_type=node_type
        )
        self.seed_nodes.append(peer)
        self.peers[peer_id] = peer

    def add_peer(self, peer_id: str, host: str, port: int, node_type: str) -> bool:
        """Add a discovered peer."""
        if peer_id == self.node_id:
            return False

        if len(self.peers) >= self.max_peers and peer_id not in self.peers:
            # Prune worst peer to make room
            self._prune_worst_peer()

        if peer_id not in self.peers:
            self.peers[peer_id] = PeerInfo(
                peer_id=peer_id,
                host=host,
                port=port,
                node_type=node_type
            )
            return True
        else:
            # Update existing peer info
            self.peers[peer_id].host = host
            self.peers[peer_id].port = port
            self.peers[peer_id].node_type = node_type
            return False

    def mark_connected(self, peer_id: str):
        """Mark a peer as connected."""
        if peer_id in self.peers:
            self.peers[peer_id].connected = True
            self.peers[peer_id].last_seen = time.time()
            self.peers[peer_id].failures = 0

    def mark_disconnected(self, peer_id: str):
        """Mark a peer as disconnected."""
        if peer_id in self.peers:
            self.peers[peer_id].connected = False

    def mark_failed(self, peer_id: str):
        """Mark a connection attempt as failed."""
        if peer_id in self.peers:
            self.peers[peer_id].failures += 1
            # Remove peer after too many failures
            if self.peers[peer_id].failures > 5:
                del self.peers[peer_id]

    def get_connected_peers(self) -> List[PeerInfo]:
        """Get list of connected peers."""
        return [p for p in self.peers.values() if p.connected]

    def get_disconnected_peers(self) -> List[PeerInfo]:
        """Get list of disconnected peers to try connecting."""
        return [
            p for p in self.peers.values()
            if not p.connected and p.failures < 5
        ]

    def get_peers_for_exchange(self, limit: int = 10) -> List[dict]:
        """Get peer list for peer exchange protocol."""
        # Prefer recently seen, connected peers
        peers = sorted(
            self.peers.values(),
            key=lambda p: (p.connected, p.last_seen),
            reverse=True
        )
        return [p.to_dict() for p in peers[:limit]]

    def process_peer_exchange(self, peers: List[dict]):
        """Process peer list from peer exchange."""
        for peer_data in peers:
            peer_id = peer_data.get("peer_id")
            if peer_id and peer_id != self.node_id:
                self.add_peer(
                    peer_id=peer_id,
                    host=peer_data.get("host", ""),
                    port=peer_data.get("port", 0),
                    node_type=peer_data.get("node_type", "unknown")
                )

    def _prune_worst_peer(self):
        """Remove the worst performing peer."""
        if not self.peers:
            return

        # Score peers: lower is worse
        def score(peer: PeerInfo) -> float:
            s = 0
            if peer.connected:
                s += 100
            s += peer.last_seen / 1000  # Recency
            s -= peer.failures * 10  # Penalize failures
            return s

        worst = min(self.peers.values(), key=score)
        if not worst.connected:
            del self.peers[worst.peer_id]

    async def start(self):
        """Start the discovery service."""
        self._running = True
        self._discovery_task = asyncio.create_task(self._discovery_loop())

    async def stop(self):
        """Stop the discovery service."""
        self._running = False
        if self._discovery_task:
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass

    async def _discovery_loop(self):
        """Main discovery loop."""
        # Initial bootstrap from seed nodes
        await self._bootstrap()

        while self._running:
            try:
                # Check if we need more peers
                connected = len(self.get_connected_peers())

                if connected < self.min_peers:
                    # Try to connect to more peers
                    await self._connect_to_peers()

                # Periodic peer exchange
                await self._peer_exchange()

                # Sleep before next round
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Discovery error: {e}")
                await asyncio.sleep(5)

    async def _bootstrap(self):
        """Bootstrap from seed nodes."""
        if not self.seed_nodes:
            return

        print(f"Bootstrapping from {len(self.seed_nodes)} seed nodes...")

        for seed in self.seed_nodes:
            if self._connect_callback:
                try:
                    success = await self._connect_callback(
                        seed.peer_id,
                        seed.host,
                        seed.port
                    )
                    if success:
                        self.mark_connected(seed.peer_id)
                    else:
                        self.mark_failed(seed.peer_id)
                except Exception as e:
                    self.mark_failed(seed.peer_id)

    async def _connect_to_peers(self):
        """Try to connect to disconnected peers."""
        disconnected = self.get_disconnected_peers()
        if not disconnected:
            return

        # Shuffle to avoid always trying same peers
        random.shuffle(disconnected)

        # Try to connect to a few peers
        for peer in disconnected[:3]:
            if self._connect_callback:
                try:
                    success = await self._connect_callback(
                        peer.peer_id,
                        peer.host,
                        peer.port
                    )
                    if success:
                        self.mark_connected(peer.peer_id)
                    else:
                        self.mark_failed(peer.peer_id)
                except Exception as e:
                    self.mark_failed(peer.peer_id)

    async def _peer_exchange(self):
        """Exchange peer lists with connected peers."""
        connected = self.get_connected_peers()
        if not connected:
            return

        # Pick a random connected peer
        peer = random.choice(connected)

        # For now, just update last_seen
        # Full peer exchange would be implemented in transport layer
        peer.last_seen = time.time()

    def get_stats(self) -> dict:
        """Get discovery statistics."""
        return {
            "total_peers": len(self.peers),
            "connected_peers": len(self.get_connected_peers()),
            "seed_nodes": len(self.seed_nodes),
            "max_peers": self.max_peers,
            "min_peers": self.min_peers
        }


class SeedNodeRegistry:
    """
    Registry of known seed nodes for different networks.
    """

    # Default seed nodes for mainnet
    MAINNET_SEEDS = [
        {"peer_id": "seed-1", "host": "seed1.calldns.network", "port": 8100},
        {"peer_id": "seed-2", "host": "seed2.calldns.network", "port": 8100},
        {"peer_id": "seed-3", "host": "seed3.calldns.network", "port": 8100},
    ]

    # Seed nodes for testnet
    TESTNET_SEEDS = [
        {"peer_id": "seed-test-1", "host": "testnet1.calldns.network", "port": 8100},
        {"peer_id": "seed-test-2", "host": "testnet2.calldns.network", "port": 8100},
    ]

    # Local development seeds
    LOCAL_SEEDS = [
        {"peer_id": "local-seed", "host": "localhost", "port": 8100},
    ]

    @classmethod
    def get_seeds(cls, network: str = "mainnet") -> List[dict]:
        """Get seed nodes for a network."""
        if network == "mainnet":
            return cls.MAINNET_SEEDS
        elif network == "testnet":
            return cls.TESTNET_SEEDS
        elif network == "local":
            return cls.LOCAL_SEEDS
        else:
            return []


def create_discovery_for_network(
    node_id: str,
    node_type: str,
    network: str = "mainnet"
) -> NodeDiscovery:
    """Create a NodeDiscovery instance configured for a network."""
    discovery = NodeDiscovery(node_id, node_type)

    seeds = SeedNodeRegistry.get_seeds(network)
    for seed in seeds:
        discovery.add_seed_node(
            peer_id=seed["peer_id"],
            host=seed["host"],
            port=seed["port"]
        )

    return discovery
