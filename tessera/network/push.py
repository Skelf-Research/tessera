"""
Push notification services for Tessera.
Supports MQTT and WebSocket for mobile app real-time updates.
"""

import asyncio
import json
import time
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

import websockets
from websockets.server import WebSocketServerProtocol


@dataclass
class PushSubscription:
    """A push subscription for a device."""

    subscriber_id: str
    device_token: Optional[str] = None  # For MQTT
    commitments: List[str] = None
    last_seen: float = 0


class WebSocketPushServer:
    """WebSocket server for real-time push to mobile apps."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port

        # Active connections
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.subscriptions: Dict[str, PushSubscription] = {}

        # Commitment to subscriber mapping
        self.commitment_subscribers: Dict[str, Set[str]] = {}

        self.server = None
        self._running = False

    async def start(self):
        """Start the WebSocket push server."""
        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
        )
        self._running = True
        print(f"  WebSocket push server on ws://{self.host}:{self.port}")

    async def stop(self):
        """Stop the server."""
        self._running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def _handle_connection(
        self, websocket: WebSocketServerProtocol, path: str = ""
    ):
        """Handle incoming WebSocket connection."""
        subscriber_id = None

        try:
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "subscribe":
                    subscriber_id = data.get("subscriber_id")
                    commitments = data.get("commitments", [])

                    if subscriber_id:
                        self.connections[subscriber_id] = websocket
                        self.subscriptions[subscriber_id] = PushSubscription(
                            subscriber_id=subscriber_id,
                            commitments=commitments,
                            last_seen=time.time(),
                        )

                        # Map commitments
                        for commitment in commitments:
                            if commitment not in self.commitment_subscribers:
                                self.commitment_subscribers[commitment] = set()
                            self.commitment_subscribers[commitment].add(subscriber_id)

                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "subscribed",
                                    "subscriber_id": subscriber_id,
                                    "commitments": commitments,
                                }
                            )
                        )

                elif msg_type == "ping":
                    if subscriber_id:
                        self.subscriptions[subscriber_id].last_seen = time.time()
                    await websocket.send(
                        json.dumps({"type": "pong", "timestamp": int(time.time())})
                    )

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            if subscriber_id:
                self._cleanup_subscriber(subscriber_id)

    def _cleanup_subscriber(self, subscriber_id: str):
        """Clean up subscriber on disconnect."""
        if subscriber_id in self.connections:
            del self.connections[subscriber_id]

        if subscriber_id in self.subscriptions:
            sub = self.subscriptions[subscriber_id]
            for commitment in sub.commitments or []:
                if commitment in self.commitment_subscribers:
                    self.commitment_subscribers[commitment].discard(subscriber_id)
            del self.subscriptions[subscriber_id]

    async def push_proof(self, commitment: str, proof: dict) -> int:
        """Push a proof to all subscribers of a commitment."""
        subscribers = self.commitment_subscribers.get(commitment, set())
        sent = 0

        for subscriber_id in list(subscribers):
            ws = self.connections.get(subscriber_id)
            if ws:
                try:
                    await ws.send(
                        json.dumps(
                            {
                                "type": "proof",
                                "commitment": commitment,
                                "proof": proof,
                                "timestamp": int(time.time()),
                            }
                        )
                    )
                    sent += 1
                except Exception:
                    self._cleanup_subscriber(subscriber_id)

        return sent

    async def push_to_subscriber(self, subscriber_id: str, message: dict) -> bool:
        """Push a message to a specific subscriber."""
        ws = self.connections.get(subscriber_id)
        if ws:
            try:
                await ws.send(json.dumps(message))
                return True
            except Exception:
                self._cleanup_subscriber(subscriber_id)
        return False

    def get_stats(self) -> dict:
        return {
            "active_connections": len(self.connections),
            "total_subscriptions": len(self.subscriptions),
            "commitment_mappings": len(self.commitment_subscribers),
        }


class MQTTBridge:
    """
    MQTT bridge for push notifications.
    Publishes proofs to MQTT topics for mobile apps.
    """

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        username: str = None,
        password: str = None,
        use_tls: bool = False,
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.use_tls = use_tls

        self.client = None
        self._connected = False

        # Topic patterns
        self.proof_topic_pattern = "tessera/proofs/{commitment}"
        self.device_topic_pattern = "tessera/devices/{device_id}"

    async def connect(self):
        """Connect to MQTT broker."""
        try:
            import aiomqtt
        except ImportError:
            print("MQTT support requires aiomqtt: pip install aiomqtt")
            return False

        try:
            self.client = aiomqtt.Client(
                hostname=self.broker_host,
                port=self.broker_port,
                username=self.username,
                password=self.password,
            )
            await self.client.__aenter__()
            self._connected = True
            print(f"  MQTT connected to {self.broker_host}:{self.broker_port}")
            return True
        except Exception as e:
            print(f"  MQTT connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client and self._connected:
            await self.client.__aexit__(None, None, None)
            self._connected = False

    async def publish_proof(self, commitment: str, proof: dict) -> bool:
        """Publish a proof to the commitment's topic."""
        if not self._connected:
            return False

        topic = self.proof_topic_pattern.format(commitment=commitment)
        payload = json.dumps(
            {
                "type": "proof",
                "commitment": commitment,
                "proof": proof,
                "timestamp": int(time.time()),
            }
        )

        try:
            await self.client.publish(topic, payload, qos=1)
            return True
        except Exception as e:
            print(f"MQTT publish error: {e}")
            return False

    async def publish_to_device(self, device_id: str, message: dict) -> bool:
        """Publish a message to a specific device."""
        if not self._connected:
            return False

        topic = self.device_topic_pattern.format(device_id=device_id)
        payload = json.dumps(message)

        try:
            await self.client.publish(topic, payload, qos=1)
            return True
        except Exception as e:
            print(f"MQTT publish error: {e}")
            return False

    def is_connected(self) -> bool:
        return self._connected


class PushService:
    """
    Unified push service supporting WebSocket and MQTT.
    """

    def __init__(self):
        self.ws_server: Optional[WebSocketPushServer] = None
        self.mqtt_bridge: Optional[MQTTBridge] = None

    async def start_websocket(self, host: str = "0.0.0.0", port: int = 8080):
        """Start WebSocket push server."""
        self.ws_server = WebSocketPushServer(host, port)
        await self.ws_server.start()

    async def start_mqtt(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        username: str = None,
        password: str = None,
    ):
        """Start MQTT bridge."""
        self.mqtt_bridge = MQTTBridge(broker_host, broker_port, username, password)
        await self.mqtt_bridge.connect()

    async def stop(self):
        """Stop all push services."""
        if self.ws_server:
            await self.ws_server.stop()
        if self.mqtt_bridge:
            await self.mqtt_bridge.disconnect()

    async def push_proof(self, commitment: str, proof: dict) -> dict:
        """Push a proof via all available channels."""
        results = {"websocket": 0, "mqtt": False}

        if self.ws_server:
            results["websocket"] = await self.ws_server.push_proof(commitment, proof)

        if self.mqtt_bridge and self.mqtt_bridge.is_connected():
            results["mqtt"] = await self.mqtt_bridge.publish_proof(commitment, proof)

        return results

    def get_stats(self) -> dict:
        stats = {}
        if self.ws_server:
            stats["websocket"] = self.ws_server.get_stats()
        if self.mqtt_bridge:
            stats["mqtt"] = {"connected": self.mqtt_bridge.is_connected()}
        return stats
