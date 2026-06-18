"""
Local multi-node cluster launcher for Tessera (Workstream D2).

Spins up ``n`` AsyncDecentralizedNodes in one process, each served over WebSocket and
wired to peers (mesh or ring) with real WSPeerTransport gossip. Intended for local
demos, end-to-end testing, and the churn/resilience experiment (E5) — nodes can be
stopped and restarted at runtime.

As a library:
    cluster = LocalCluster(n=5, topology="mesh")
    await cluster.start()
    uris = cluster.uris()            # {"node-0": "ws://127.0.0.1:..", ...}
    await cluster.stop_node("node-2")   # simulate churn
    await cluster.start_node("node-2")
    await cluster.stop()

As a launcher:
    poetry run python -m tessera.deploy.cluster --nodes 5 --topology ring
"""

import argparse
import asyncio
import shutil
import tempfile
from pathlib import Path

import websockets

from ..network.async_node import AsyncDecentralizedNode
from ..network.decentralized import NodeType
from ..network.ws_server import NodeWebSocketServer, WSPeerTransport


class _NodeHandle:
    def __init__(self, name: str, data_dir: str):
        self.name = name
        self.data_dir = data_dir
        self.node = None
        self.server = None
        self.transport = None
        self.uri = None


class LocalCluster:
    """A set of peered Tessera nodes running in the current event loop."""

    def __init__(self, n: int = 3, topology: str = "mesh",
                 host: str = "127.0.0.1", base_dir: str = None):
        if topology not in ("mesh", "ring"):
            raise ValueError("topology must be 'mesh' or 'ring'")
        self.n = n
        self.topology = topology
        self.host = host
        self._owns_base = base_dir is None
        self.base_dir = base_dir or tempfile.mkdtemp(prefix="tessera_cluster_")
        self.handles: dict = {}

    def _peers_of(self, idx: int):
        names = [f"node-{i}" for i in range(self.n)]
        if self.topology == "mesh":
            return [names[j] for j in range(self.n) if j != idx]
        # ring: connect to next neighbour (bidirectional ring)
        return [names[(idx + 1) % self.n], names[(idx - 1) % self.n]] if self.n > 1 else []

    async def start_node(self, name: str):
        """Start (or restart) a single node and (re)wire its peer links."""
        h = self.handles[name]
        h.node = AsyncDecentralizedNode(name, NodeType.CORE, data_dir=h.data_dir)
        await h.node.initialize()
        server = await websockets.serve(NodeWebSocketServer(h.node).handler, self.host, 0)
        h.server = server
        h.uri = f"ws://{self.host}:{server.sockets[0].getsockname()[1]}"

    async def _wire_peers(self):
        names = [f"node-{i}" for i in range(self.n)]
        for idx, name in enumerate(names):
            h = self.handles[name]
            if h.node is None:
                continue
            h.transport = WSPeerTransport(name)
            for peer in self._peers_of(idx):
                ph = self.handles[peer]
                if ph.uri:
                    h.transport.add_peer(peer, ph.uri)
                    await h.node.connect_peer(peer, {"node_type": "core"})
            h.node.set_send_handler(h.transport.send)

    async def start(self):
        for i in range(self.n):
            name = f"node-{i}"
            self.handles[name] = _NodeHandle(name, f"{self.base_dir}/{name}")
            await self.start_node(name)
        await self._wire_peers()
        return self

    async def stop_node(self, name: str):
        """Simulate a node going offline (keeps its data dir for restart)."""
        h = self.handles[name]
        if h.transport:
            await h.transport.close()
        if h.server:
            h.server.close()
            await h.server.wait_closed()
        if h.node:
            await h.node.shutdown()
        h.node = h.server = h.transport = None
        h.uri = None

    async def stop(self):
        for name in list(self.handles):
            await self.stop_node(name)
        if self._owns_base:
            shutil.rmtree(self.base_dir, ignore_errors=True)

    def uris(self) -> dict:
        return {name: h.uri for name, h in self.handles.items() if h.uri}


async def _run_forever(args):
    cluster = LocalCluster(n=args.nodes, topology=args.topology,
                           base_dir=str(Path(args.data_dir).resolve()) if args.data_dir else None)
    await cluster.start()
    print(f"Tessera local cluster up ({args.nodes} nodes, {args.topology}):")
    for name, uri in cluster.uris().items():
        print(f"  {name}: {uri}")
    try:
        await asyncio.Future()
    finally:
        await cluster.stop()


def main():
    ap = argparse.ArgumentParser(description="Run a local Tessera cluster")
    ap.add_argument("--nodes", type=int, default=3)
    ap.add_argument("--topology", default="mesh", choices=["mesh", "ring"])
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args()
    try:
        asyncio.run(_run_forever(args))
    except KeyboardInterrupt:
        print("\nshutting down cluster")


if __name__ == "__main__":
    main()
