"""
Node transport layer using WebSockets.
Handles peer-to-peer communication between Tessera nodes.
"""

import asyncio
import json
from typing import Dict, Optional
import websockets
from websockets.server import WebSocketServerProtocol

from ..network.async_node import AsyncDecentralizedNode


class NodeTransport:
    """WebSocket-based transport layer for node communication."""

    def __init__(self, node: AsyncDecentralizedNode, host: str, port: int):
        self.node = node
        self.host = host
        self.port = port

        # Active connections: peer_id -> websocket
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.connection_info: Dict[str, dict] = {}

        self.server = None
        self._running = False

    async def start(self):
        """Start the WebSocket server."""
        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
            max_size=10 * 1024 * 1024,  # 10MB max message size
        )
        self._running = True
        print(f"  Transport listening on ws://{self.host}:{self.port}")

    async def stop(self):
        """Stop the WebSocket server."""
        self._running = False

        # Close all connections
        for peer_id in list(self.connections.keys()):
            await self._close_connection(peer_id)

        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def connect_to_peer(self, peer_id: str, host: str, port: int) -> bool:
        """Connect to a peer node."""
        if peer_id in self.connections:
            return True

        uri = f"ws://{host}:{port}"

        try:
            ws = await websockets.connect(uri, ping_interval=30, ping_timeout=10)

            # Send handshake
            await ws.send(
                json.dumps(
                    {
                        "type": "handshake",
                        "node_id": self.node.node_id,
                        "node_type": self.node.node_type.value,
                        "host": self.host,
                        "port": self.port,
                    }
                )
            )

            # Wait for handshake response
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("type") == "handshake_ack":
                self.connections[peer_id] = ws
                self.connection_info[peer_id] = {
                    "host": host,
                    "port": port,
                    "node_type": data.get("node_type", "unknown"),
                }

                # Register peer in node
                await self.node.connect_peer(
                    peer_id,
                    {"node_type": data.get("node_type"), "host": host, "port": port},
                )

                # Start receiving messages
                asyncio.create_task(self._receive_loop(peer_id, ws))

                return True
            else:
                await ws.close()
                return False

        except Exception as e:
            print(f"  Failed to connect to {peer_id}@{host}:{port}: {e}")
            return False

    async def send_to_peer(self, peer_id: str, proof: dict):
        """Send a proof to a specific peer."""
        if peer_id not in self.connections:
            return

        try:
            ws = self.connections[peer_id]
            await ws.send(json.dumps({"type": "proof", "proof": proof}))
        except Exception as e:
            print(f"  Failed to send to {peer_id}: {e}")
            await self._close_connection(peer_id)

    async def _handle_connection(
        self, websocket: WebSocketServerProtocol, path: str = ""
    ):
        """Handle incoming WebSocket connection."""
        peer_id = None

        try:
            # Wait for handshake
            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(message)

            if data.get("type") == "handshake":
                peer_id = data.get("node_id")

                if peer_id:
                    # Send handshake acknowledgment
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "handshake_ack",
                                "node_id": self.node.node_id,
                                "node_type": self.node.node_type.value,
                            }
                        )
                    )

                    # Store connection
                    self.connections[peer_id] = websocket
                    self.connection_info[peer_id] = {
                        "host": data.get("host", "unknown"),
                        "port": data.get("port", 0),
                        "node_type": data.get("node_type", "unknown"),
                    }

                    # Register peer in node
                    await self.node.connect_peer(
                        peer_id,
                        {
                            "node_type": data.get("node_type"),
                            "host": data.get("host"),
                            "port": data.get("port"),
                        },
                    )

                    print(f"  Peer connected: {peer_id} ({data.get('node_type')})")

                    # Handle messages
                    await self._receive_loop(peer_id, websocket)
            else:
                # Handle management commands from CLI
                await self._handle_management_command(websocket, data)
                return

        except asyncio.TimeoutError:
            pass
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"  Connection error: {e}")
        finally:
            if peer_id:
                await self._close_connection(peer_id)

    async def _receive_loop(self, peer_id: str, websocket):
        """Receive messages from a peer."""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(peer_id, data)
                except json.JSONDecodeError:
                    continue
        except websockets.exceptions.ConnectionClosed:
            pass

    async def _handle_message(self, peer_id: str, data: dict):
        """Handle a message from a peer."""
        msg_type = data.get("type")

        if msg_type == "proof":
            # Route proof through node
            proof = data.get("proof", {})
            await self.node.route_proof(proof, from_peer=peer_id)

        elif msg_type == "subscribe":
            # Register subscription
            subscriber_id = data.get("subscriber_id")
            subscription = data.get("subscription")
            if subscriber_id and subscription:
                await self.node.register_subscription(subscriber_id, subscription)

        elif msg_type == "unsubscribe":
            subscriber_id = data.get("subscriber_id")
            if subscriber_id:
                await self.node.unregister_subscription(subscriber_id)

        elif msg_type == "get_proofs":
            # Return pending proofs
            subscriber_id = data.get("subscriber_id")
            if subscriber_id and peer_id in self.connections:
                proofs = await self.node.get_pending_proofs(subscriber_id)
                await self.connections[peer_id].send(
                    json.dumps(
                        {
                            "type": "proofs",
                            "subscriber_id": subscriber_id,
                            "proofs": proofs,
                        }
                    )
                )

    async def _handle_management_command(self, websocket, data: dict):
        """Handle management commands from CLI."""
        msg_type = data.get("type")

        if msg_type == "status_request":
            stats = await self.node.get_stats()
            await websocket.send(
                json.dumps({"type": "status_response", "stats": stats})
            )

        elif msg_type == "peers_request":
            peers = []
            for peer_id, info in self.connection_info.items():
                peers.append({"peer_id": peer_id, **info})
            await websocket.send(json.dumps({"type": "peers_response", "peers": peers}))

        elif msg_type == "connect_request":
            peer_id = data.get("peer_id")
            peer_host = data.get("peer_host")
            peer_port = data.get("peer_port")

            success = await self.connect_to_peer(peer_id, peer_host, peer_port)
            await websocket.send(
                json.dumps(
                    {
                        "type": "connect_response",
                        "success": success,
                        "error": None if success else "Connection failed",
                    }
                )
            )

    async def _close_connection(self, peer_id: str):
        """Close connection to a peer."""
        if peer_id in self.connections:
            try:
                await self.connections[peer_id].close()
            except Exception:
                pass
            del self.connections[peer_id]

        if peer_id in self.connection_info:
            del self.connection_info[peer_id]

        # Notify node
        await self.node.disconnect_peer(peer_id)
        print(f"  Peer disconnected: {peer_id}")
