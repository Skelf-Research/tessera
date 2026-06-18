"""
Tessera web service module.
Provides REST API endpoints for Tessera network operations.
"""

import json
import time
import base64
from typing import Dict, Any
from flask import Flask, request, jsonify
from ..sdk import Sender, Verifier
from ..sdk.commitment_manager import CommitmentManager
from ..sdk.device_registration import CustomerRegistrationManager
from ..network.enhanced_broadcast import EnhancedBroadcast
from .websocket import ws_manager, create_socketio_handlers, broadcast_to_room


class TesseraService:
    """Main Tessera web service class."""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.verifier = Verifier()
        self.commitment_manager = CommitmentManager()
        self.customer_manager = CustomerRegistrationManager()
        self.broadcast = EnhancedBroadcast()
        self.setup_routes()

        # In-memory storage for demo (use database in production)
        self.active_commitments = {}
        self.verified_proofs = []
        self.organizations = {}  # org_id -> org_data

        # WebSocket support (optional, requires flask-socketio)
        self.socketio = None
    
    def setup_routes(self):
        """Set up the web service routes."""
        self.app.route('/health')(self.health_check)
        self.app.route('/proofs/broadcast', methods=['POST'])(self.broadcast_proof)
        self.app.route('/proofs/verify', methods=['POST'])(self.verify_proof)
        self.app.route('/commitments/register', methods=['POST'])(self.register_commitment)
        self.app.route('/commitments/lookup/<commitment_id>', methods=['GET'])(self.lookup_commitment)
        self.app.route('/stats', methods=['GET'])(self.get_stats)
        self.app.route('/proofs/recent', methods=['GET'])(self.get_recent_proofs)

        # Customer registration endpoints
        self.app.route('/customers/register', methods=['POST'])(self.register_customer)
        self.app.route('/customers/<customer_id>/devices', methods=['POST'])(self.register_device)
        self.app.route('/customers/<customer_id>/devices', methods=['GET'])(self.get_customer_devices)
        self.app.route('/customers/<customer_id>/devices/<device_id>', methods=['DELETE'])(self.unregister_device)
        self.app.route('/customers/<customer_id>/link', methods=['POST'])(self.link_organization)
        self.app.route('/customers/<customer_id>/unlink/<org_id>', methods=['DELETE'])(self.unlink_organization)
        self.app.route('/customers/<customer_id>/commitments', methods=['GET'])(self.get_customer_commitments)

        # Organization endpoints
        self.app.route('/organizations/register', methods=['POST'])(self.register_organization)
        self.app.route('/organizations/<org_id>/customers/<customer_id>/commitments', methods=['GET'])(self.org_get_customer_commitments)
    
    def health_check(self):
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "service": "Tessera",
            "version": "0.1.0",
            "timestamp": int(time.time()),
            "active_commitments": len(self.active_commitments),
            "verified_proofs": len(self.verified_proofs),
            "websocket": {
                "enabled": self.socketio is not None,
                "connections": ws_manager.get_connection_count(),
                "subscriptions": ws_manager.get_subscription_count()
            },
            "customers": len(self.customer_manager.customers),
            "organizations": len(self.organizations)
        })
    
    def broadcast_proof(self):
        """Broadcast a proof to the network."""
        try:
            data = request.get_json()

            if not data or 'proof' not in data:
                return jsonify({
                    "status": "error",
                    "message": "Missing proof data"
                }), 400

            proof = data['proof']
            metadata = data.get('metadata', {})

            # Route proof to appropriate recipients
            recipients = data.get('recipients', [])
            commitments = data.get('commitments', [])

            # If recipients specified, get their commitments
            if recipients and not commitments:
                for recipient_id in recipients:
                    recipient_commitments = self.customer_manager.get_customer_commitments(recipient_id)
                    commitments.extend(recipient_commitments)

            # Store in network broadcast layer
            proof_id = self.broadcast.route_proof(proof, recipients, metadata)

            # Real-time WebSocket delivery
            ws_delivered = 0
            if commitments:
                for commitment in commitments:
                    if self.socketio:
                        # Flask-SocketIO mode
                        delivered = broadcast_to_room(self.socketio, commitment, proof)
                    else:
                        # Track for async delivery
                        delivered = len(ws_manager.get_subscribers(commitment))
                        if delivered == 0:
                            # Store for later delivery when device connects
                            ws_manager._store_pending_proof(commitment, proof)

                    ws_delivered += delivered

            return jsonify({
                "status": "proof_broadcasted",
                "proof_id": proof_id,
                "recipients": len(recipients),
                "commitments_targeted": len(commitments),
                "websocket_delivered": ws_delivered,
                "timestamp": int(time.time())
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Broadcast failed: {str(e)}"
            }), 500
    
    def verify_proof(self):
        """Verify a proof."""
        try:
            data = request.get_json()

            if not data or 'proof' not in data:
                return jsonify({
                    "status": "error",
                    "message": "Missing proof data"
                }), 400

            proof = data['proof']

            # Convert from JSON serializable format if needed
            if isinstance(proof.get('R'), str):
                # Convert base64 strings back to bytes
                proof_bytes = {}
                for key, value in proof.items():
                    if key in ['R', 'public_key'] and isinstance(value, str):
                        try:
                            proof_bytes[key] = base64.b64decode(value)
                        except:
                            proof_bytes[key] = value
                    else:
                        proof_bytes[key] = value
                proof = proof_bytes

            # Verify the proof
            is_valid = self.verifier.verify_call_proof(proof)

            if is_valid:
                # Store verified proof
                proof_record = {
                    "proof": proof,
                    "verified_at": int(time.time()),
                    "verifier_id": "service"
                }
                self.verified_proofs.append(proof_record)

                return jsonify({
                    "status": "verified",
                    "valid": True,
                    "message": "Proof verification successful",
                    "timestamp": int(time.time())
                })
            else:
                return jsonify({
                    "status": "verified",
                    "valid": False,
                    "message": "Proof verification failed",
                    "timestamp": int(time.time())
                })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Verification failed: {str(e)}"
            }), 500
    
    def register_commitment(self):
        """Register a commitment."""
        try:
            data = request.get_json()

            if not data or 'session_id' not in data:
                return jsonify({
                    "status": "error",
                    "message": "Missing session_id"
                }), 400

            session_id = data['session_id']
            public_key = data.get('public_key', 'default_key').encode()

            # Generate commitment
            commitment = self.commitment_manager.generate_reception_commitment(
                public_key, session_id
            )

            # Store commitment
            commitment_id = commitment.hex()
            self.active_commitments[commitment_id] = {
                "commitment": commitment,
                "session_id": session_id,
                "public_key": public_key.hex(),
                "created_at": int(time.time()),
                "expires_at": int(time.time()) + 3600  # 1 hour
            }

            return jsonify({
                "status": "commitment_registered",
                "commitment_id": commitment_id,
                "session_id": session_id,
                "expires_at": self.active_commitments[commitment_id]["expires_at"]
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Registration failed: {str(e)}"
            }), 500
    
    def lookup_commitment(self, commitment_id: str):
        """Lookup a commitment."""
        try:
            if commitment_id not in self.active_commitments:
                return jsonify({
                    "status": "not_found",
                    "message": "Commitment not found"
                }), 404

            commitment_data = self.active_commitments[commitment_id]

            # Check if commitment is expired
            if int(time.time()) > commitment_data["expires_at"]:
                # Clean up expired commitment
                del self.active_commitments[commitment_id]
                return jsonify({
                    "status": "expired",
                    "message": "Commitment has expired"
                }), 410

            return jsonify({
                "status": "found",
                "commitment_id": commitment_id,
                "session_id": commitment_data["session_id"],
                "created_at": commitment_data["created_at"],
                "expires_at": commitment_data["expires_at"],
                "time_remaining": commitment_data["expires_at"] - int(time.time())
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Lookup failed: {str(e)}"
            }), 500

    def get_stats(self):
        """Get service statistics."""
        try:
            current_time = int(time.time())

            # Calculate some basic stats
            active_count = len(self.active_commitments)
            verified_count = len(self.verified_proofs)

            # Recent activity (last hour)
            recent_verifications = sum(
                1 for proof in self.verified_proofs
                if current_time - proof.get('verified_at', 0) < 3600
            )

            # Expired commitments cleanup
            expired_commitments = [
                cid for cid, data in self.active_commitments.items()
                if current_time > data['expires_at']
            ]
            for cid in expired_commitments:
                del self.active_commitments[cid]

            return jsonify({
                "status": "success",
                "stats": {
                    "active_commitments": active_count - len(expired_commitments),
                    "total_verified_proofs": verified_count,
                    "recent_verifications_1h": recent_verifications,
                    "expired_commitments_cleaned": len(expired_commitments),
                    "uptime_seconds": current_time,
                    "service_version": "0.1.0"
                },
                "timestamp": current_time
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Stats retrieval failed: {str(e)}"
            }), 500

    def get_recent_proofs(self):
        """Get recent verified proofs (limited for privacy)."""
        try:
            limit = request.args.get('limit', 10, type=int)
            limit = min(limit, 50)  # Max 50 for performance

            # Return limited info about recent proofs (no actual proof data)
            recent_proofs = []
            for proof in self.verified_proofs[-limit:]:
                recent_proofs.append({
                    "verified_at": proof["verified_at"],
                    "verifier_id": proof["verifier_id"],
                    "proof_id": str(hash(str(proof["proof"])))[:16]  # Anonymous ID
                })

            return jsonify({
                "status": "success",
                "recent_proofs": recent_proofs,
                "count": len(recent_proofs),
                "timestamp": int(time.time())
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Recent proofs retrieval failed: {str(e)}"
            }), 500

    # Customer Registration Endpoints

    def register_customer(self):
        """Register a new customer."""
        try:
            data = request.get_json()

            if not data or 'customer_id' not in data:
                return jsonify({
                    "status": "error",
                    "message": "Missing customer_id"
                }), 400

            customer_id = data['customer_id']
            metadata = data.get('metadata', {})

            customer = self.customer_manager.register_customer(customer_id, metadata)

            return jsonify({
                "status": "customer_registered",
                "customer_id": customer_id,
                "created_at": customer["created_at"]
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Customer registration failed: {str(e)}"
            }), 500

    def register_device(self, customer_id: str):
        """Register a device for a customer."""
        try:
            data = request.get_json()

            if not data:
                return jsonify({
                    "status": "error",
                    "message": "Missing device data"
                }), 400

            required_fields = ['device_id', 'commitment', 'public_key']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        "status": "error",
                        "message": f"Missing required field: {field}"
                    }), 400

            device = self.customer_manager.register_device(customer_id, data)

            return jsonify({
                "status": "device_registered",
                "customer_id": customer_id,
                "device_id": device["device_id"],
                "device_name": device["device_name"],
                "registered_at": device["registered_at"]
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Device registration failed: {str(e)}"
            }), 500

    def get_customer_devices(self, customer_id: str):
        """Get all devices for a customer."""
        try:
            customer = self.customer_manager.get_customer(customer_id)

            if not customer:
                return jsonify({
                    "status": "not_found",
                    "message": "Customer not found"
                }), 404

            devices = []
            for device in customer["devices"].values():
                devices.append({
                    "device_id": device["device_id"],
                    "device_name": device["device_name"],
                    "registered_at": device["registered_at"],
                    "last_seen": device["last_seen"],
                    "active": device["active"]
                })

            return jsonify({
                "status": "success",
                "customer_id": customer_id,
                "devices": devices,
                "count": len(devices)
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Failed to get devices: {str(e)}"
            }), 500

    def unregister_device(self, customer_id: str, device_id: str):
        """Unregister a device."""
        try:
            success = self.customer_manager.unregister_device(customer_id, device_id)

            if not success:
                return jsonify({
                    "status": "not_found",
                    "message": "Device or customer not found"
                }), 404

            return jsonify({
                "status": "device_unregistered",
                "customer_id": customer_id,
                "device_id": device_id
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Device unregistration failed: {str(e)}"
            }), 500

    def link_organization(self, customer_id: str):
        """Link a customer to an organization."""
        try:
            data = request.get_json()

            if not data or 'organization_id' not in data or 'linking_token' not in data:
                return jsonify({
                    "status": "error",
                    "message": "Missing organization_id or linking_token"
                }), 400

            organization_id = data['organization_id']
            linking_token = data['linking_token']

            result = self.customer_manager.link_organization(
                customer_id, organization_id, linking_token
            )

            if "error" in result:
                return jsonify({
                    "status": "error",
                    "message": result["error"]
                }), 400

            return jsonify({
                "status": "organization_linked",
                "customer_id": customer_id,
                "organization_id": organization_id,
                "linked_at": result["linked_at"]
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Organization linking failed: {str(e)}"
            }), 500

    def unlink_organization(self, customer_id: str, org_id: str):
        """Unlink a customer from an organization."""
        try:
            success = self.customer_manager.unlink_organization(customer_id, org_id)

            if not success:
                return jsonify({
                    "status": "not_found",
                    "message": "Customer or organization link not found"
                }), 404

            return jsonify({
                "status": "organization_unlinked",
                "customer_id": customer_id,
                "organization_id": org_id
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Organization unlinking failed: {str(e)}"
            }), 500

    def get_customer_commitments(self, customer_id: str):
        """Get all commitments for a customer (for their own use)."""
        try:
            commitments = self.customer_manager.get_customer_commitments(customer_id)

            if not commitments:
                customer = self.customer_manager.get_customer(customer_id)
                if not customer:
                    return jsonify({
                        "status": "not_found",
                        "message": "Customer not found"
                    }), 404

            return jsonify({
                "status": "success",
                "customer_id": customer_id,
                "commitments": commitments,
                "count": len(commitments)
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Failed to get commitments: {str(e)}"
            }), 500

    # Organization Endpoints

    def register_organization(self):
        """Register a new organization."""
        try:
            data = request.get_json()

            if not data or 'organization_id' not in data:
                return jsonify({
                    "status": "error",
                    "message": "Missing organization_id"
                }), 400

            org_id = data['organization_id']
            org_name = data.get('organization_name', org_id)
            metadata = data.get('metadata', {})

            # Generate API key for the organization
            import secrets
            api_key = secrets.token_urlsafe(32)

            org_record = {
                "organization_id": org_id,
                "organization_name": org_name,
                "api_key": api_key,
                "created_at": int(time.time()),
                "metadata": metadata
            }

            self.organizations[org_id] = org_record

            return jsonify({
                "status": "organization_registered",
                "organization_id": org_id,
                "organization_name": org_name,
                "api_key": api_key,
                "created_at": org_record["created_at"]
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Organization registration failed: {str(e)}"
            }), 500

    def org_get_customer_commitments(self, org_id: str, customer_id: str):
        """
        Get customer commitments for an organization.

        Organizations use this to get all device commitments for a customer
        before broadcasting a proof.
        """
        try:
            # Verify organization exists
            if org_id not in self.organizations:
                return jsonify({
                    "status": "error",
                    "message": "Organization not found"
                }), 404

            # Check authorization
            if not self.customer_manager.is_organization_authorized(
                customer_id, org_id, "get_commitments"
            ):
                return jsonify({
                    "status": "unauthorized",
                    "message": "Organization not authorized to access this customer's commitments"
                }), 403

            # Get commitments
            commitments = self.customer_manager.get_customer_commitments(customer_id)

            return jsonify({
                "status": "success",
                "organization_id": org_id,
                "customer_id": customer_id,
                "commitments": commitments,
                "count": len(commitments)
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Failed to get customer commitments: {str(e)}"
            }), 500

    def enable_websocket(self):
        """
        Enable WebSocket support using Flask-SocketIO.

        Requires: pip install flask-socketio

        Returns:
            SocketIO instance or None if not available
        """
        try:
            from flask_socketio import SocketIO
            self.socketio = SocketIO(self.app, cors_allowed_origins="*")
            create_socketio_handlers(self.socketio, self.customer_manager)
            print("WebSocket support enabled")
            return self.socketio
        except ImportError:
            print("flask-socketio not installed. WebSocket support disabled.")
            print("Install with: pip install flask-socketio")
            return None

    def run(self, host: str = '0.0.0.0', port: int = 8000, debug: bool = False,
            websocket: bool = False):
        """
        Run the web service.

        Args:
            host: Host to bind to
            port: Port to bind to
            debug: Enable debug mode
            websocket: Enable WebSocket support
        """
        if websocket:
            socketio = self.enable_websocket()
            if socketio:
                socketio.run(self.app, host=host, port=port, debug=debug)
                return

        self.app.run(host=host, port=port, debug=debug)


# Create a default service instance
service = TesseraService()


if __name__ == '__main__':
    service.run()