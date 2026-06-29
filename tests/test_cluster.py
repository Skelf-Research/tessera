"""
LocalCluster tests (Workstream D2): multi-node gossip across a 3-node cluster and
basic churn resilience (delivery continues after a peer goes offline).
"""

import json

import pytest
import pytest_asyncio
import websockets

from tessera.deploy.cluster import LocalCluster
from tessera.network.decentralized import Subscription, make_routing_fields


@pytest_asyncio.fixture
async def cluster():
    c = LocalCluster(n=3, topology="mesh")
    await c.start()
    try:
        yield c
    finally:
        await c.stop()


async def _subscribe(uri, sub_id, commitment):
    async with websockets.connect(uri) as ws:
        await ws.send(
            json.dumps(
                {
                    "type": "subscribe",
                    "subscriber_id": sub_id,
                    "subscription": Subscription(commitment, ["org"]).to_dict(),
                }
            )
        )
        await ws.recv()


async def _route(uri, commitment):
    async with websockets.connect(uri) as ws:
        await ws.send(
            json.dumps(
                {
                    "type": "proof",
                    "proof": {**make_routing_fields(commitment), "org_hint": "org"},
                }
            )
        )
        return json.loads(await ws.recv())


async def _fetch(uri, sub_id):
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"type": "fetch", "subscriber_id": sub_id}))
        return json.loads(await ws.recv())["proofs"]


@pytest.mark.asyncio
async def test_gossip_across_three_nodes(cluster):
    uris = cluster.uris()
    commitment = b"\x07" * 32
    # Subscriber on node-2; proof submitted to node-0 -> must arrive via gossip.
    await _subscribe(uris["node-2"], "s2", commitment)
    await _route(uris["node-0"], commitment)
    assert len(await _fetch(uris["node-2"], "s2")) == 1


@pytest.mark.asyncio
async def test_delivery_survives_peer_churn(cluster):
    commitment = b"\x09" * 32
    await _subscribe(cluster.uris()["node-1"], "s1", commitment)

    # node-2 goes offline; node-0 should still gossip to the live node-1.
    await cluster.stop_node("node-2")
    ack = await _route(cluster.uris()["node-0"], commitment)
    assert ack["type"] == "routed"
    assert len(await _fetch(cluster.uris()["node-1"], "s1")) == 1
