"""
Integration test for the WebSocket node transport (Workstream D).

Validates that an AsyncDecentralizedNode served over a real WebSocket socket
performs subscribe -> route -> fetch correctly, using the canonical routing fields.
"""

import json
import tempfile
import shutil

import pytest
import pytest_asyncio
import websockets

from calldns.network.async_node import AsyncDecentralizedNode
from calldns.network.decentralized import NodeType, Subscription, make_routing_fields, compute_bucket
from calldns.network.ws_server import NodeWebSocketServer


@pytest_asyncio.fixture
async def ws_node():
    """Start a node WS server on an ephemeral port; yield (uri, node)."""
    tmp = tempfile.mkdtemp(prefix="calldns_ws_test_")
    node = AsyncDecentralizedNode("ws-test", NodeType.CORE, data_dir=f"{tmp}/n")
    await node.initialize()
    server = await websockets.serve(NodeWebSocketServer(node).handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield f"ws://127.0.0.1:{port}", node
    finally:
        server.close()
        await server.wait_closed()
        await node.shutdown()
        shutil.rmtree(tmp)


async def _roundtrip(ws, message):
    await ws.send(json.dumps(message))
    return json.loads(await ws.recv())


@pytest.mark.asyncio
async def test_subscribe_route_fetch(ws_node):
    uri, _node = ws_node
    commitment = b"\x11" * 32

    async with websockets.connect(uri) as ws:
        # Subscribe using the canonical Subscription serialization.
        sub = Subscription(commitment, linked_orgs=["test-org"]).to_dict()
        resp = await _roundtrip(ws, {"type": "subscribe",
                                     "subscriber_id": "dev-1", "subscription": sub})
        assert resp["type"] == "subscribed"

        # Route a proof produced with the canonical routing fields.
        proof = {**make_routing_fields(commitment), "org_hint": "test-org"}
        resp = await _roundtrip(ws, {"type": "proof", "proof": proof})
        assert resp["type"] == "routed"
        assert resp["notified"] == 1

        # Fetch delivers exactly the matched proof, then drains.
        resp = await _roundtrip(ws, {"type": "fetch", "subscriber_id": "dev-1"})
        assert resp["type"] == "proofs"
        assert len(resp["proofs"]) == 1
        assert resp["proofs"][0]["bucket"] == compute_bucket(commitment)

        resp = await _roundtrip(ws, {"type": "fetch", "subscriber_id": "dev-1"})
        assert len(resp["proofs"]) == 0


@pytest.mark.asyncio
async def test_ping_and_unknown(ws_node):
    uri, _ = ws_node
    async with websockets.connect(uri) as ws:
        assert (await _roundtrip(ws, {"type": "ping"}))["type"] == "pong"
        assert (await _roundtrip(ws, {"type": "bogus"}))["type"] == "error"
