"""
Outbound caller verification for CallDNS.
Enables customers to prove their identity when calling organizations (banks, etc.).
"""

import asyncio
import hashlib
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .caller import Caller
from .device_registration import DeviceRegistration


@dataclass
class OutboundCallProof:
    """Proof generated for an outbound call."""
    proof_id: str
    commitment: str
    bucket: int
    ciphertext: str
    fingerprint: str
    destination: str
    timestamp: int
    ttl: int = 300  # 5 minutes default


class OutboundCaller:
    """
    Handles outbound call verification where customer proves identity to organization.

    Flow:
    1. Customer taps "Verified Call" button in app
    2. SDK generates proof and broadcasts to network
    3. Customer places call (via dialer)
    4. Organization's contact center verifies proof
    """

    def __init__(
        self,
        core_node_url: str,
        device_registration: Optional[DeviceRegistration] = None
    ):
        self.core_node_url = core_node_url
        self.caller = Caller()
        self.device_registration = device_registration
        self._pending_proofs: Dict[str, OutboundCallProof] = {}

    async def prepare_verified_call(
        self,
        destination_id: str,
        destination_commitment: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> OutboundCallProof:
        """
        Prepare a verified outbound call.

        Args:
            destination_id: Organization identifier (e.g., "natwest-uk")
            destination_commitment: Organization's reception commitment
            metadata: Optional call metadata (purpose, account hint, etc.)

        Returns:
            OutboundCallProof ready for broadcast
        """
        # Generate base proof
        call_metadata = {
            "direction": "outbound",
            "destination": destination_id,
            "timestamp": int(time.time()),
            **(metadata or {})
        }

        proof = self.caller.generate_call_proof(call_metadata)

        # Encrypt for destination
        encrypted = self.caller.encrypt_proof_for_callee(
            proof,
            destination_commitment,
            call_metadata
        )

        # Calculate bucket for routing
        bucket = int.from_bytes(destination_commitment[:2], 'big') % 64

        # Generate proof ID
        proof_id = hashlib.sha256(
            f"{encrypted['ciphertext'][:32]}{time.time()}".encode()
        ).hexdigest()[:16]

        outbound_proof = OutboundCallProof(
            proof_id=proof_id,
            commitment=destination_commitment.hex(),
            bucket=bucket,
            ciphertext=encrypted['ciphertext'],
            fingerprint=encrypted['bloom_fingerprint'],
            destination=destination_id,
            timestamp=int(time.time())
        )

        self._pending_proofs[proof_id] = outbound_proof
        return outbound_proof

    async def broadcast_and_call(
        self,
        proof: OutboundCallProof,
        phone_number: str
    ) -> Dict[str, Any]:
        """
        Broadcast proof to network then initiate call.

        Args:
            proof: The prepared outbound proof
            phone_number: Phone number to dial

        Returns:
            Result with broadcast status and dial intent
        """
        import aiohttp

        # Broadcast to core network
        broadcast_url = f"{self.core_node_url}/proofs/broadcast"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                broadcast_url,
                json={
                    "proof": {
                        "bucket": proof.bucket,
                        "fingerprint": proof.fingerprint,
                        "ciphertext": proof.ciphertext,
                        "commitment_id": proof.commitment,
                        "timestamp": proof.timestamp,
                        "ttl": proof.ttl
                    },
                    "decoys": 3
                }
            ) as resp:
                broadcast_result = await resp.json()

        return {
            "status": "ready_to_dial",
            "proof_id": proof.proof_id,
            "broadcast": broadcast_result,
            "dial": {
                "phone_number": phone_number,
                "intent": f"tel:{phone_number}"
            },
            "verification_window": proof.ttl
        }

    async def quick_verified_call(
        self,
        destination_id: str,
        destination_commitment: bytes,
        phone_number: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        One-step verified call - prepare, broadcast, and return dial intent.

        This is the main method for the "Verified Call" button UX.

        Args:
            destination_id: Organization identifier
            destination_commitment: Organization's commitment
            phone_number: Phone number to dial
            metadata: Optional call metadata

        Returns:
            Result with dial intent and verification status
        """
        proof = await self.prepare_verified_call(
            destination_id,
            destination_commitment,
            metadata
        )

        return await self.broadcast_and_call(proof, phone_number)

    def get_pending_proof(self, proof_id: str) -> Optional[OutboundCallProof]:
        """Get a pending proof by ID."""
        return self._pending_proofs.get(proof_id)

    def clear_expired_proofs(self):
        """Remove expired pending proofs."""
        now = int(time.time())
        expired = [
            pid for pid, proof in self._pending_proofs.items()
            if now - proof.timestamp > proof.ttl
        ]
        for pid in expired:
            del self._pending_proofs[pid]


class ContactCenterVerifier:
    """
    Verifier for organization contact centers to verify incoming customer calls.

    Integrates with the org's node to look up proofs by caller commitment.
    """

    def __init__(self, org_node_url: str):
        self.org_node_url = org_node_url

    async def verify_incoming_caller(
        self,
        caller_commitment: str,
        caller_id: Optional[str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Verify an incoming caller against broadcast proofs.

        Args:
            caller_commitment: The caller's commitment (from customer record)
            caller_id: Optional caller ID for additional matching
            timeout: How long to wait for proof (seconds)

        Returns:
            Verification result
        """
        import aiohttp

        # Look up proof from node
        lookup_url = f"{self.org_node_url}/proofs/lookup"

        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < timeout:
                async with session.get(
                    lookup_url,
                    params={
                        "commitment": caller_commitment,
                        "since": int(start_time - 300)  # Last 5 minutes
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("proofs"):
                            # Found matching proof
                            proof = data["proofs"][0]
                            return {
                                "verified": True,
                                "caller_commitment": caller_commitment,
                                "proof_timestamp": proof.get("timestamp"),
                                "metadata": proof.get("metadata", {}),
                                "confidence": "high"
                            }

                # Wait and retry
                await asyncio.sleep(1)

        # No proof found within timeout
        return {
            "verified": False,
            "caller_commitment": caller_commitment,
            "reason": "no_proof_found",
            "confidence": "none"
        }

    async def lookup_customer_commitment(
        self,
        customer_id: str
    ) -> Optional[str]:
        """
        Look up a customer's commitment from the org's registration database.

        Args:
            customer_id: Internal customer ID

        Returns:
            Customer's commitment or None
        """
        import aiohttp

        lookup_url = f"{self.org_node_url}/customers/{customer_id}/commitments"

        async with aiohttp.ClientSession() as session:
            async with session.get(lookup_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    commitments = data.get("commitments", [])
                    return commitments[0] if commitments else None

        return None
