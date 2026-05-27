"""
Multi-node gossip test (Workstream D2).

Proves the decentralization claim: a proof submitted to node A is gossiped over a real
WebSocket peer link to node B, where a subscriber registered only on B receives it.
"""

import json
import shutil
import tempfile

import pytest
import pytest_asyncio
import websockets

from calldns.network.async_node import AsyncDecentralizedNode
from calldns.network.decentralized import NodeType, Subscription, make_routing_fields
from calldns.network.ws_server import NodeWebSocketServer, WSPeerTransport


class _Node:
    def __init__(self, node):
        self.node = node
        self.server = None
        self.transport = None
        self.uri = None


@pytest_asyncio.fixture
async def cluster():
    """Two peered nodes (A, B) each served over WS and gossiping to each other."""
    tmp = tempfile.mkdtemp(prefix="calldns_cluster_")
    nodes = {}
    for name in ("A", "B"):
        n = AsyncDecentralizedNode(name, NodeType.CORE, data_dir=f"{tmp}/{name}")
        await n.initialize()
        server = await websockets.serve(NodeWebSocketServer(n).handler, "127.0.0.1", 0)
        w = _Node(n)
        w.server = server
        w.uri = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
        nodes[name] = w

    # Wire mutual peer transports.
    for name, other in (("A", "B"), ("B", "A")):
        w = nodes[name]
        w.transport = WSPeerTransport(name)
        w.transport.add_peer(other, nodes[other].uri)
        await w.node.connect_peer(other, {"node_type": "core"})
        w.node.set_send_handler(w.transport.send)

    try:
        yield nodes
    finally:
        for w in nodes.values():
            await w.transport.close()
            w.server.close()
            await w.server.wait_closed()
            await w.node.shutdown()
        shutil.rmtree(tmp)


@pytest.mark.asyncio
async def test_proof_gossips_to_peer_subscriber(cluster):
    commitment = b"\x2a" * 32

    # Subscriber exists ONLY on node B.
    await cluster["B"].node.register_subscription(
        "sub-on-B", Subscription(commitment, linked_orgs=["org"]).to_dict())

    # Proof is submitted to node A (which has no local subscriber for it).
    proof = {**make_routing_fields(commitment), "org_hint": "org"}
    async with websockets.connect(cluster["A"].uri) as ws:
        await ws.send(json.dumps({"type": "proof", "proof": proof}))
        ack = json.loads(await ws.recv())
        assert ack["type"] == "routed"
        assert ack["notified"] == 0  # no local subscriber on A

    # After gossip, B's subscriber must have received the proof.
    async with websockets.connect(cluster["B"].uri) as ws:
        await ws.send(json.dumps({"type": "fetch", "subscriber_id": "sub-on-B"}))
        resp = json.loads(await ws.recv())
        assert resp["type"] == "proofs"
        assert len(resp["proofs"]) == 1
        assert resp["proofs"][0]["org_hint"] == "org"
