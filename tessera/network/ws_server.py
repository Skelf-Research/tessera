"""
WebSocket transport server for a Tessera decentralized node.

Exposes an :class:`AsyncDecentralizedNode` over a real network socket so callers,
organizations, and customer devices can subscribe, broadcast proofs, and fetch
matched proofs across process / host boundaries. This is the transport that turns
the in-process node into a deployable network node (Workstream D).

Wire protocol (newline-free JSON request -> JSON response, one per message):

    subscribe : {"type":"subscribe","subscriber_id":str,"subscription":{...}}
                -> {"type":"subscribed","subscriber_id":str}
    proof     : {"type":"proof","proof":{bucket,bloom_fingerprint,timestamp,...}}
                -> {"type":"routed","notified":int}
    fetch     : {"type":"fetch","subscriber_id":str}
                -> {"type":"proofs","proofs":[...]}
    stats     : {"type":"stats"} -> {"type":"stats","stats":{...}}
    ping      : {"type":"ping"}  -> {"type":"pong","timestamp":int}

Run a node:
    poetry run python -m tessera.network.ws_server --port 8765
"""

import argparse
import asyncio
import json
import time
from collections import defaultdict

import websockets

from .async_node import AsyncDecentralizedNode
from .decentralized import NodeType


class NodeWebSocketServer:
    """Serve a single AsyncDecentralizedNode over WebSocket."""

    def __init__(self, node: AsyncDecentralizedNode):
        self.node = node

    async def _dispatch(self, data: dict) -> dict:
        mtype = data.get("type")

        if mtype == "subscribe":
            subscriber_id = data["subscriber_id"]
            await self.node.register_subscription(subscriber_id, data["subscription"])
            return {"type": "subscribed", "subscriber_id": subscriber_id}

        if mtype == "proof":
            # from_peer lets route_proof exclude the sender when gossiping, avoiding loops.
            notified = await self.node.route_proof(data["proof"], from_peer=data.get("from_peer"))
            return {"type": "routed", "notified": notified}

        if mtype == "fetch":
            proofs = await self.node.get_pending_proofs(data["subscriber_id"])
            return {"type": "proofs", "proofs": proofs}

        if mtype == "stats":
            return {"type": "stats", "stats": await self.node.get_stats()}

        if mtype == "ping":
            return {"type": "pong", "timestamp": int(time.time())}

        return {"type": "error", "message": f"unknown message type: {mtype!r}"}

    async def handler(self, websocket, path=None):
        """Per-connection message loop (path kept optional for websockets<12)."""
        try:
            async for message in websocket:
                try:
                    response = await self._dispatch(json.loads(message))
                except Exception as e:  # never let one bad message kill the connection
                    response = {"type": "error", "message": str(e)}
                await websocket.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosed:
            # Normal: client sent a request and closed without reading the reply.
            pass


class WSPeerTransport:
    """Cross-node gossip transport over WebSocket.

    Wire it into a node with ``node.set_send_handler(transport.send)`` and register
    peers via :meth:`add_peer`. When the node gossips a proof, it is forwarded to each
    peer's WS server tagged with ``from_peer`` so the receiver can avoid loops; node-level
    proof deduplication guarantees gossip terminates.

    Connections are lazily established and transparently reconnected on failure.
    """

    def __init__(self, my_node_id: str):
        self.my_node_id = my_node_id
        self.peers: dict = {}            # peer_id -> ws uri
        self._conns: dict = {}           # peer_id -> websocket connection
        self._locks = defaultdict(asyncio.Lock)

    def add_peer(self, peer_id: str, uri: str):
        self.peers[peer_id] = uri

    async def _connection(self, peer_id: str):
        async with self._locks[peer_id]:
            ws = self._conns.get(peer_id)
            if ws is None or ws.closed:
                ws = await websockets.connect(self.peers[peer_id])
                self._conns[peer_id] = ws
            return ws

    async def send(self, peer_id: str, proof: dict):
        """Forward a proof to a peer (fire-and-forget; drains the routed ack)."""
        if peer_id not in self.peers:
            return
        try:
            ws = await self._connection(peer_id)
            await ws.send(json.dumps({"type": "proof", "proof": proof,
                                      "from_peer": self.my_node_id}))
            await ws.recv()  # drain the {"type":"routed"} ack to keep the socket clean
        except Exception:
            # Drop the (possibly dead) connection; next send reconnects.
            self._conns.pop(peer_id, None)

    async def close(self):
        for ws in list(self._conns.values()):
            try:
                await ws.close()
            except Exception:
                pass
        self._conns.clear()


async def serve(host: str, port: int, node_id: str, node_type: NodeType,
                data_dir: str = None) -> None:
    import websockets

    node = AsyncDecentralizedNode(node_id=node_id, node_type=node_type, data_dir=data_dir)
    await node.initialize()
    server_obj = NodeWebSocketServer(node)

    async with websockets.serve(server_obj.handler, host, port):
        print(f"Tessera node '{node_id}' ({node_type.value}) on ws://{host}:{port}")
        try:
            await asyncio.Future()  # run until cancelled
        finally:
            await node.shutdown()


def main():
    ap = argparse.ArgumentParser(description="Run a Tessera WebSocket node")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--node-id", default="node-1")
    ap.add_argument("--node-type", default="core", choices=[t.value for t in NodeType])
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args()

    try:
        asyncio.run(serve(args.host, args.port, args.node_id,
                          NodeType(args.node_type), args.data_dir))
    except KeyboardInterrupt:
        print("\nshutting down")


if __name__ == "__main__":
    main()
