"""
TLS-enabled transport layer for secure node-to-node communication.
Supports both TLS and mTLS (mutual TLS) for peer authentication.
"""

import asyncio
import json
import ssl
from pathlib import Path
from typing import Dict, Optional

import websockets
from websockets.server import WebSocketServerProtocol

from ..network.async_node import AsyncDecentralizedNode


class TLSNodeTransport:
    """TLS-enabled WebSocket transport layer for node communication."""

    def __init__(
        self,
        node: AsyncDecentralizedNode,
        host: str,
        port: int,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        ca_file: Optional[str] = None,
        require_client_cert: bool = False
    ):
        self.node = node
        self.host = host
        self.port = port

        # TLS configuration
        self.cert_file = cert_file
        self.key_file = key_file
        self.ca_file = ca_file
        self.require_client_cert = require_client_cert

        # Active connections
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.connection_info: Dict[str, dict] = {}

        self.server = None
        self._running = False

    def _create_server_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for server."""
        if not self.cert_file or not self.key_file:
            return None

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(self.cert_file, self.key_file)

        if self.ca_file:
            ctx.load_verify_locations(self.ca_file)

        if self.require_client_cert:
            ctx.verify_mode = ssl.CERT_REQUIRED
        else:
            ctx.verify_mode = ssl.CERT_OPTIONAL

        # Security settings
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20')

        return ctx

    def _create_client_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for client connections."""
        if not self.ca_file:
            return None

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_verify_locations(self.ca_file)

        if self.cert_file and self.key_file:
            ctx.load_cert_chain(self.cert_file, self.key_file)

        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED

        return ctx

    async def start(self):
        """Start the TLS WebSocket server."""
        ssl_context = self._create_server_ssl_context()

        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ssl=ssl_context,
            ping_interval=30,
            ping_timeout=10,
            max_size=10 * 1024 * 1024
        )
        self._running = True

        protocol = "wss" if ssl_context else "ws"
        print(f"  Transport listening on {protocol}://{self.host}:{self.port}")
        if ssl_context:
            print(f"  TLS enabled (mTLS: {self.require_client_cert})")

    async def stop(self):
        """Stop the WebSocket server."""
        self._running = False

        for peer_id in list(self.connections.keys()):
            await self._close_connection(peer_id)

        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def connect_to_peer(
        self,
        peer_id: str,
        host: str,
        port: int,
        use_tls: bool = False
    ) -> bool:
        """Connect to a peer node with optional TLS."""
        if peer_id in self.connections:
            return True

        protocol = "wss" if use_tls else "ws"
        uri = f"{protocol}://{host}:{port}"

        ssl_context = self._create_client_ssl_context() if use_tls else None

        try:
            ws = await websockets.connect(
                uri,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=10
            )

            # Send handshake
            await ws.send(json.dumps({
                "type": "handshake",
                "node_id": self.node.node_id,
                "node_type": self.node.node_type.value,
                "host": self.host,
                "port": self.port,
                "tls_enabled": use_tls
            }))

            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("type") == "handshake_ack":
                self.connections[peer_id] = ws
                self.connection_info[peer_id] = {
                    "host": host,
                    "port": port,
                    "node_type": data.get("node_type", "unknown"),
                    "tls_enabled": use_tls
                }

                await self.node.connect_peer(peer_id, {
                    "node_type": data.get("node_type"),
                    "host": host,
                    "port": port,
                    "tls_enabled": use_tls
                })

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
            await ws.send(json.dumps({
                "type": "proof",
                "proof": proof
            }))
        except Exception as e:
            print(f"  Failed to send to {peer_id}: {e}")
            await self._close_connection(peer_id)

    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str = ""):
        """Handle incoming WebSocket connection."""
        peer_id = None

        # Get client certificate info if mTLS
        client_cert = None
        if hasattr(websocket, 'transport'):
            ssl_object = websocket.transport.get_extra_info('ssl_object')
            if ssl_object:
                client_cert = ssl_object.getpeercert()

        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(message)

            if data.get("type") == "handshake":
                peer_id = data.get("node_id")

                if peer_id:
                    await websocket.send(json.dumps({
                        "type": "handshake_ack",
                        "node_id": self.node.node_id,
                        "node_type": self.node.node_type.value
                    }))

                    self.connections[peer_id] = websocket
                    self.connection_info[peer_id] = {
                        "host": data.get("host", "unknown"),
                        "port": data.get("port", 0),
                        "node_type": data.get("node_type", "unknown"),
                        "tls_enabled": data.get("tls_enabled", False),
                        "client_cert": client_cert
                    }

                    await self.node.connect_peer(peer_id, {
                        "node_type": data.get("node_type"),
                        "host": data.get("host"),
                        "port": data.get("port")
                    })

                    print(f"  Peer connected: {peer_id} ({data.get('node_type')})")
                    await self._receive_loop(peer_id, websocket)
            else:
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
            proof = data.get("proof", {})
            await self.node.route_proof(proof, from_peer=peer_id)

        elif msg_type == "subscribe":
            subscriber_id = data.get("subscriber_id")
            subscription = data.get("subscription")
            if subscriber_id and subscription:
                await self.node.register_subscription(subscriber_id, subscription)

        elif msg_type == "unsubscribe":
            subscriber_id = data.get("subscriber_id")
            if subscriber_id:
                await self.node.unregister_subscription(subscriber_id)

        elif msg_type == "get_proofs":
            subscriber_id = data.get("subscriber_id")
            if subscriber_id and peer_id in self.connections:
                proofs = await self.node.get_pending_proofs(subscriber_id)
                await self.connections[peer_id].send(json.dumps({
                    "type": "proofs",
                    "subscriber_id": subscriber_id,
                    "proofs": proofs
                }))

    async def _handle_management_command(self, websocket, data: dict):
        """Handle management commands."""
        msg_type = data.get("type")

        if msg_type == "status_request":
            stats = await self.node.get_stats()
            await websocket.send(json.dumps({
                "type": "status_response",
                "stats": stats
            }))

        elif msg_type == "peers_request":
            peers = []
            for peer_id, info in self.connection_info.items():
                peers.append({
                    "peer_id": peer_id,
                    **info
                })
            await websocket.send(json.dumps({
                "type": "peers_response",
                "peers": peers
            }))

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

        await self.node.disconnect_peer(peer_id)
        print(f"  Peer disconnected: {peer_id}")


def generate_self_signed_cert(
    cert_path: str,
    key_path: str,
    common_name: str = "calldns-node"
):
    """Generate a self-signed certificate for testing."""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime

    # Generate key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CallDNS"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName(common_name),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    # Write key
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Write certificate
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"Generated certificate: {cert_path}")
    print(f"Generated key: {key_path}")
