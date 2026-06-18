"""
WebSocket support for real-time proof delivery in Tessera.
Enables instant notification when proofs are broadcast to devices.
"""

import json
import time
import asyncio
import base64
from typing import Dict, Set, Optional
from collections import defaultdict


class WebSocketManager:
    """
    Manages WebSocket connections for real-time proof delivery.

    Devices connect via WebSocket and subscribe to their commitments.
    When a proof is broadcast, all subscribed devices receive it instantly.
    """

    def __init__(self):
        # Map commitment -> set of websocket connections
        self.subscriptions: Dict[str, Set] = defaultdict(set)

        # Map connection_id -> connection info
        self.connections: Dict[str, Dict] = {}

        # Map device_id -> connection_id
        self.device_connections: Dict[str, str] = {}

        # Pending proofs for offline devices (limited retention)
        self.pending_proofs: Dict[str, list] = defaultdict(list)
        self.max_pending_per_device = 100
        self.pending_retention_seconds = 3600  # 1 hour

    def register_connection(self, connection_id: str, websocket, device_id: str,
                           commitments: list) -> Dict:
        """
        Register a new WebSocket connection.

        Args:
            connection_id: Unique connection identifier
            websocket: The WebSocket connection object
            device_id: Device identifier
            commitments: List of commitment strings to subscribe to

        Returns:
            dict: Connection info
        """
        # Store connection
        connection_info = {
            "connection_id": connection_id,
            "websocket": websocket,
            "device_id": device_id,
            "commitments": commitments,
            "connected_at": int(time.time()),
            "last_ping": int(time.time())
        }

        self.connections[connection_id] = connection_info
        self.device_connections[device_id] = connection_id

        # Subscribe to all commitments
        for commitment in commitments:
            self.subscriptions[commitment].add(connection_id)

        return connection_info

    def unregister_connection(self, connection_id: str):
        """
        Unregister a WebSocket connection.

        Args:
            connection_id: Connection to unregister
        """
        if connection_id not in self.connections:
            return

        connection_info = self.connections[connection_id]

        # Remove from subscriptions
        for commitment in connection_info.get("commitments", []):
            if commitment in self.subscriptions:
                self.subscriptions[commitment].discard(connection_id)
                if not self.subscriptions[commitment]:
                    del self.subscriptions[commitment]

        # Remove from device mapping
        device_id = connection_info.get("device_id")
        if device_id and device_id in self.device_connections:
            del self.device_connections[device_id]

        # Remove connection
        del self.connections[connection_id]

    def get_subscribers(self, commitment: str) -> Set[str]:
        """
        Get all connection IDs subscribed to a commitment.

        Args:
            commitment: Commitment string

        Returns:
            set: Set of connection IDs
        """
        return self.subscriptions.get(commitment, set())

    async def broadcast_proof(self, commitment: str, proof_data: Dict) -> int:
        """
        Broadcast a proof to all devices subscribed to a commitment.

        Args:
            commitment: Target commitment
            proof_data: Proof data to broadcast

        Returns:
            int: Number of devices notified
        """
        subscribers = self.get_subscribers(commitment)

        if not subscribers:
            # Store as pending for when device comes online
            self._store_pending_proof(commitment, proof_data)
            return 0

        message = {
            "type": "proof_received",
            "commitment": commitment,
            "proof": proof_data,
            "timestamp": int(time.time())
        }

        message_json = json.dumps(message)
        notified = 0
        failed_connections = []

        for connection_id in subscribers:
            connection = self.connections.get(connection_id)
            if not connection:
                continue

            websocket = connection.get("websocket")
            if not websocket:
                continue

            try:
                await websocket.send(message_json)
                notified += 1
            except Exception as e:
                print(f"Failed to send to {connection_id}: {e}")
                failed_connections.append(connection_id)

        # Clean up failed connections
        for conn_id in failed_connections:
            self.unregister_connection(conn_id)

        return notified

    def _store_pending_proof(self, commitment: str, proof_data: Dict):
        """Store proof for offline device."""
        pending_entry = {
            "proof": proof_data,
            "timestamp": int(time.time())
        }

        self.pending_proofs[commitment].append(pending_entry)

        # Limit pending proofs
        if len(self.pending_proofs[commitment]) > self.max_pending_per_device:
            self.pending_proofs[commitment] = self.pending_proofs[commitment][-self.max_pending_per_device:]

    def get_pending_proofs(self, commitment: str) -> list:
        """
        Get pending proofs for a commitment (when device comes online).

        Args:
            commitment: Commitment string

        Returns:
            list: List of pending proofs
        """
        current_time = int(time.time())

        # Filter out expired proofs
        valid_proofs = [
            entry for entry in self.pending_proofs.get(commitment, [])
            if current_time - entry["timestamp"] < self.pending_retention_seconds
        ]

        # Update stored proofs
        if commitment in self.pending_proofs:
            self.pending_proofs[commitment] = valid_proofs

        return [entry["proof"] for entry in valid_proofs]

    def clear_pending_proofs(self, commitment: str):
        """Clear pending proofs for a commitment after delivery."""
        if commitment in self.pending_proofs:
            del self.pending_proofs[commitment]

    def update_ping(self, connection_id: str):
        """Update last ping time for a connection."""
        if connection_id in self.connections:
            self.connections[connection_id]["last_ping"] = int(time.time())

    def cleanup_stale_connections(self, timeout_seconds: int = 300):
        """
        Clean up connections that haven't pinged recently.

        Args:
            timeout_seconds: Seconds since last ping before considering stale
        """
        current_time = int(time.time())
        stale_connections = [
            conn_id for conn_id, info in self.connections.items()
            if current_time - info.get("last_ping", 0) > timeout_seconds
        ]

        for conn_id in stale_connections:
            self.unregister_connection(conn_id)

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.connections)

    def get_subscription_count(self) -> int:
        """Get total number of active subscriptions."""
        return sum(len(subs) for subs in self.subscriptions.values())


# Global WebSocket manager instance
ws_manager = WebSocketManager()


# Flask-SocketIO integration
def create_socketio_handlers(socketio, customer_manager):
    """
    Create Socket.IO event handlers for Flask-SocketIO.

    Args:
        socketio: Flask-SocketIO instance
        customer_manager: CustomerRegistrationManager instance
    """
    from flask_socketio import emit, join_room, leave_room
    from flask import request

    @socketio.on('connect')
    def handle_connect():
        """Handle new WebSocket connection."""
        print(f"Client connected: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle WebSocket disconnection."""
        ws_manager.unregister_connection(request.sid)
        print(f"Client disconnected: {request.sid}")

    @socketio.on('subscribe')
    def handle_subscribe(data):
        """
        Handle device subscription to commitments.

        Expected data:
        {
            "device_id": "dev_123",
            "commitments": ["commitment1", "commitment2"]
        }
        """
        device_id = data.get('device_id')
        commitments = data.get('commitments', [])

        if not device_id or not commitments:
            emit('error', {'message': 'Missing device_id or commitments'})
            return

        # Register connection
        ws_manager.register_connection(
            connection_id=request.sid,
            websocket=None,  # Socket.IO handles this differently
            device_id=device_id,
            commitments=commitments
        )

        # Join rooms for each commitment
        for commitment in commitments:
            join_room(commitment)

        # Send any pending proofs
        for commitment in commitments:
            pending = ws_manager.get_pending_proofs(commitment)
            if pending:
                for proof in pending:
                    emit('proof_received', {
                        'commitment': commitment,
                        'proof': proof,
                        'timestamp': int(time.time()),
                        'pending': True
                    })
                ws_manager.clear_pending_proofs(commitment)

        emit('subscribed', {
            'device_id': device_id,
            'commitments': commitments,
            'count': len(commitments)
        })

        print(f"Device {device_id} subscribed to {len(commitments)} commitments")

    @socketio.on('unsubscribe')
    def handle_unsubscribe(data):
        """Handle device unsubscription."""
        commitments = data.get('commitments', [])

        for commitment in commitments:
            leave_room(commitment)

        emit('unsubscribed', {'commitments': commitments})

    @socketio.on('ping')
    def handle_ping():
        """Handle keepalive ping."""
        ws_manager.update_ping(request.sid)
        emit('pong', {'timestamp': int(time.time())})

    return socketio


def broadcast_to_room(socketio, commitment: str, proof_data: Dict):
    """
    Broadcast proof to all devices in a commitment room.

    Args:
        socketio: Flask-SocketIO instance
        commitment: Target commitment (room name)
        proof_data: Proof data to broadcast
    """
    message = {
        'type': 'proof_received',
        'commitment': commitment,
        'proof': proof_data,
        'timestamp': int(time.time())
    }

    # Check if anyone is subscribed
    if not ws_manager.get_subscribers(commitment):
        # Store for later delivery
        ws_manager._store_pending_proof(commitment, proof_data)
        return 0

    # Broadcast to room
    socketio.emit('proof_received', message, room=commitment)

    return len(ws_manager.get_subscribers(commitment))


# Async WebSocket server (for standalone deployment)
async def websocket_handler(websocket, path, customer_manager):
    """
    Handle WebSocket connections for standalone async server.

    Args:
        websocket: WebSocket connection
        path: Request path
        customer_manager: CustomerRegistrationManager instance
    """
    connection_id = str(id(websocket))
    device_id = None

    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'subscribe':
                device_id = data.get('device_id')
                commitments = data.get('commitments', [])

                ws_manager.register_connection(
                    connection_id=connection_id,
                    websocket=websocket,
                    device_id=device_id,
                    commitments=commitments
                )

                # Send pending proofs
                for commitment in commitments:
                    pending = ws_manager.get_pending_proofs(commitment)
                    for proof in pending:
                        await websocket.send(json.dumps({
                            'type': 'proof_received',
                            'commitment': commitment,
                            'proof': proof,
                            'timestamp': int(time.time()),
                            'pending': True
                        }))
                    ws_manager.clear_pending_proofs(commitment)

                await websocket.send(json.dumps({
                    'type': 'subscribed',
                    'device_id': device_id,
                    'commitments': commitments
                }))

            elif msg_type == 'ping':
                ws_manager.update_ping(connection_id)
                await websocket.send(json.dumps({
                    'type': 'pong',
                    'timestamp': int(time.time())
                }))

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        ws_manager.unregister_connection(connection_id)


async def run_websocket_server(host: str = '0.0.0.0', port: int = 8001,
                               customer_manager=None):
    """
    Run standalone WebSocket server.

    Args:
        host: Host to bind to
        port: Port to bind to
        customer_manager: CustomerRegistrationManager instance
    """
    try:
        import websockets
    except ImportError:
        print("websockets package required. Install with: pip install websockets")
        return

    async def handler(websocket, path):
        await websocket_handler(websocket, path, customer_manager)

    server = await websockets.serve(handler, host, port)
    print(f"WebSocket server running on ws://{host}:{port}")

    await server.wait_closed()
