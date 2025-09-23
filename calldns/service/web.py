"""
CallDNS web service module.
Provides REST API endpoints for CallDNS network operations.
"""

import json
import time
import base64
from typing import Dict, Any
from flask import Flask, request, jsonify
from ..sdk import Caller, Verifier
from ..sdk.commitment_manager import CommitmentManager
from ..network.enhanced_broadcast import EnhancedBroadcast


class CallDNSService:
    """Main CallDNS web service class."""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.verifier = Verifier()
        self.commitment_manager = CommitmentManager()
        self.broadcast = EnhancedBroadcast()
        self.setup_routes()

        # In-memory storage for demo (use database in production)
        self.active_commitments = {}
        self.verified_proofs = []
    
    def setup_routes(self):
        """Set up the web service routes."""
        self.app.route('/health')(self.health_check)
        self.app.route('/proofs/broadcast', methods=['POST'])(self.broadcast_proof)
        self.app.route('/proofs/verify', methods=['POST'])(self.verify_proof)
        self.app.route('/commitments/register', methods=['POST'])(self.register_commitment)
        self.app.route('/commitments/lookup/<commitment_id>', methods=['GET'])(self.lookup_commitment)
        self.app.route('/stats', methods=['GET'])(self.get_stats)
        self.app.route('/proofs/recent', methods=['GET'])(self.get_recent_proofs)
    
    def health_check(self):
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "service": "CallDNS",
            "version": "0.1.0",
            "timestamp": int(time.time()),
            "active_commitments": len(self.active_commitments),
            "verified_proofs": len(self.verified_proofs)
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

            # Validate proof structure
            required_fields = ['R', 's', 'public_key']
            for field in required_fields:
                if field not in proof:
                    return jsonify({
                        "status": "error",
                        "message": f"Missing required field: {field}"
                    }), 400

            # Route proof to appropriate recipients
            recipients = data.get('recipients', [])
            proof_id = self.broadcast.route_proof(proof, recipients, metadata)

            return jsonify({
                "status": "proof_broadcasted",
                "proof_id": proof_id,
                "recipients": len(recipients),
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

    def run(self, host: str = '0.0.0.0', port: int = 8000, debug: bool = False):
        """Run the web service."""
        self.app.run(host=host, port=port, debug=debug)


# Create a default service instance
service = CallDNSService()


if __name__ == '__main__':
    service.run()