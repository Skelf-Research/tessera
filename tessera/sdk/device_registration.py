"""
Device registration for CallDNS.
Handles device-specific commitment registration and multi-device support.
"""

import hashlib
import secrets
import time
import json
import base64
from typing import Dict, List, Optional
from .identity_manager import IdentityManager
from .commitment_manager import CommitmentManager


class DeviceRegistration:
    """Manages device registration and commitment generation for end users."""

    def __init__(self, device_name: str = None):
        """
        Initialize device registration.

        Args:
            device_name: Human-readable device name (e.g., "iPhone 15", "Chrome Browser")
        """
        self.identity_manager = IdentityManager()
        self.commitment_manager = CommitmentManager()
        self.device_id = self._generate_device_id()
        self.device_name = device_name or f"Device-{self.device_id[:8]}"
        self.commitment = None
        self.registration_token = None
        self.linked_organizations: Dict[str, Dict] = {}

    def _generate_device_id(self) -> str:
        """Generate a unique device identifier."""
        # Combine public key hash with random bytes for uniqueness
        public_key = self.identity_manager.get_public_key()
        random_component = secrets.token_bytes(16)
        device_data = public_key + random_component
        return hashlib.sha256(device_data).hexdigest()[:32]

    def generate_commitment(self, session_id: str = None) -> bytes:
        """
        Generate a reception commitment for this device.

        Args:
            session_id: Optional session identifier (defaults to device_id)

        Returns:
            bytes: The reception commitment
        """
        if session_id is None:
            session_id = self.device_id

        public_key = self.identity_manager.get_public_key()
        self.commitment = self.commitment_manager.generate_reception_commitment(
            public_key, session_id
        )
        return self.commitment

    def get_registration_payload(self) -> Dict:
        """
        Get the payload for registering this device with CallDNS service.

        Returns:
            dict: Registration payload
        """
        if self.commitment is None:
            self.generate_commitment()

        public_key = self.identity_manager.get_public_key()

        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "commitment": base64.b64encode(self.commitment).decode('utf-8'),
            "public_key": base64.b64encode(public_key).decode('utf-8'),
            "registered_at": int(time.time())
        }

    def generate_linking_token(self, organization_id: str) -> str:
        """
        Generate a token for linking this device to an organization.

        The customer shares this token with the organization (e.g., their bank)
        to allow the organization to send verified calls to this device.

        Args:
            organization_id: The organization to link with

        Returns:
            str: Linking token (base64 encoded)
        """
        if self.commitment is None:
            self.generate_commitment()

        # Create linking data
        linking_data = {
            "device_id": self.device_id,
            "commitment": base64.b64encode(self.commitment).decode('utf-8'),
            "organization_id": organization_id,
            "created_at": int(time.time()),
            "expires_at": int(time.time()) + 3600,  # 1 hour validity
            "nonce": secrets.token_hex(16)
        }

        # Sign the linking data
        linking_json = json.dumps(linking_data, sort_keys=True)
        signature = hashlib.sha256(
            linking_json.encode() + self.identity_manager.get_public_key()
        ).hexdigest()

        linking_data["signature"] = signature

        # Encode as token
        token = base64.urlsafe_b64encode(
            json.dumps(linking_data).encode()
        ).decode('utf-8')

        return token

    def link_organization(self, organization_id: str, organization_name: str,
                         permissions: List[str] = None) -> Dict:
        """
        Record a link to an organization locally.

        Args:
            organization_id: Organization identifier
            organization_name: Human-readable organization name
            permissions: List of permissions granted

        Returns:
            dict: Link record
        """
        if permissions is None:
            permissions = ["verify_calls"]

        link_record = {
            "organization_id": organization_id,
            "organization_name": organization_name,
            "linked_at": int(time.time()),
            "permissions": permissions,
            "active": True
        }

        self.linked_organizations[organization_id] = link_record
        return link_record

    def unlink_organization(self, organization_id: str) -> bool:
        """
        Remove link to an organization.

        Args:
            organization_id: Organization to unlink

        Returns:
            bool: True if unlinked, False if not found
        """
        if organization_id in self.linked_organizations:
            del self.linked_organizations[organization_id]
            return True
        return False

    def get_linked_organizations(self) -> List[Dict]:
        """
        Get all linked organizations.

        Returns:
            list: List of linked organization records
        """
        return list(self.linked_organizations.values())

    def is_organization_linked(self, organization_id: str) -> bool:
        """
        Check if an organization is linked.

        Args:
            organization_id: Organization to check

        Returns:
            bool: True if linked
        """
        return organization_id in self.linked_organizations

    def get_bloom_fingerprints(self, time_window_minutes: int = 5) -> List[bytes]:
        """
        Get bloom filter fingerprints for querying proofs.

        Generates fingerprints for recent time windows to find matching proofs.

        Args:
            time_window_minutes: How far back to generate fingerprints

        Returns:
            list: List of bloom filter fingerprints
        """
        if self.commitment is None:
            return []

        fingerprints = []
        current_time = int(time.time())

        # Generate fingerprints for each second in the time window
        # In production, you'd use larger time buckets (e.g., 10-second intervals)
        for offset in range(0, time_window_minutes * 60, 10):  # 10-second intervals
            timestamp = current_time - offset
            fingerprint = self.commitment_manager.generate_bloom_fingerprint(
                self.commitment, timestamp
            )
            fingerprints.append(fingerprint)

        return fingerprints

    def to_dict(self) -> Dict:
        """
        Serialize device registration to dictionary.

        Returns:
            dict: Serialized registration
        """
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "commitment": base64.b64encode(self.commitment).decode('utf-8') if self.commitment else None,
            "public_key": base64.b64encode(self.identity_manager.get_public_key()).decode('utf-8'),
            "linked_organizations": self.linked_organizations
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DeviceRegistration':
        """
        Deserialize device registration from dictionary.

        Args:
            data: Serialized registration data

        Returns:
            DeviceRegistration: Restored registration
        """
        registration = cls(device_name=data.get("device_name"))
        registration.device_id = data["device_id"]

        if data.get("commitment"):
            registration.commitment = base64.b64decode(data["commitment"])

        registration.linked_organizations = data.get("linked_organizations", {})

        return registration


class CustomerRegistrationManager:
    """
    Manages customer registrations across multiple devices.

    This is used by the CallDNS service to track customer-device relationships.
    """

    def __init__(self):
        # In production, this would be backed by a database
        self.customers: Dict[str, Dict] = {}
        self.device_to_customer: Dict[str, str] = {}
        self.commitment_to_device: Dict[str, str] = {}

    def register_customer(self, customer_id: str, metadata: Dict = None) -> Dict:
        """
        Register a new customer.

        Args:
            customer_id: Unique customer identifier
            metadata: Optional customer metadata

        Returns:
            dict: Customer record
        """
        if customer_id in self.customers:
            return self.customers[customer_id]

        customer_record = {
            "customer_id": customer_id,
            "created_at": int(time.time()),
            "devices": {},
            "organization_links": {},
            "metadata": metadata or {}
        }

        self.customers[customer_id] = customer_record
        return customer_record

    def register_device(self, customer_id: str, device_payload: Dict) -> Dict:
        """
        Register a device for a customer.

        Args:
            customer_id: Customer identifier
            device_payload: Device registration payload from DeviceRegistration

        Returns:
            dict: Device record
        """
        # Ensure customer exists
        if customer_id not in self.customers:
            self.register_customer(customer_id)

        device_id = device_payload["device_id"]
        commitment = device_payload["commitment"]

        # Create device record
        device_record = {
            "device_id": device_id,
            "device_name": device_payload.get("device_name", "Unknown Device"),
            "commitment": commitment,
            "public_key": device_payload["public_key"],
            "registered_at": device_payload.get("registered_at", int(time.time())),
            "last_seen": int(time.time()),
            "active": True
        }

        # Store in customer record
        self.customers[customer_id]["devices"][device_id] = device_record

        # Update indexes
        self.device_to_customer[device_id] = customer_id
        self.commitment_to_device[commitment] = device_id

        return device_record

    def unregister_device(self, customer_id: str, device_id: str) -> bool:
        """
        Unregister a device.

        Args:
            customer_id: Customer identifier
            device_id: Device to unregister

        Returns:
            bool: True if unregistered
        """
        if customer_id not in self.customers:
            return False

        if device_id not in self.customers[customer_id]["devices"]:
            return False

        device = self.customers[customer_id]["devices"][device_id]
        commitment = device["commitment"]

        # Remove from indexes
        del self.device_to_customer[device_id]
        if commitment in self.commitment_to_device:
            del self.commitment_to_device[commitment]

        # Remove from customer
        del self.customers[customer_id]["devices"][device_id]

        return True

    def get_customer_commitments(self, customer_id: str) -> List[str]:
        """
        Get all active commitments for a customer.

        This is called by organizations to get all device commitments
        for broadcasting proofs.

        Args:
            customer_id: Customer identifier

        Returns:
            list: List of commitment strings (base64)
        """
        if customer_id not in self.customers:
            return []

        commitments = []
        for device in self.customers[customer_id]["devices"].values():
            if device.get("active", True):
                commitments.append(device["commitment"])

        return commitments

    def link_organization(self, customer_id: str, organization_id: str,
                         linking_token: str) -> Dict:
        """
        Link a customer to an organization using a linking token.

        Args:
            customer_id: Customer identifier
            organization_id: Organization identifier
            linking_token: Token generated by customer's device

        Returns:
            dict: Link record
        """
        if customer_id not in self.customers:
            return {"error": "Customer not found"}

        # Decode and validate token
        try:
            token_data = json.loads(
                base64.urlsafe_b64decode(linking_token.encode()).decode('utf-8')
            )
        except Exception as e:
            return {"error": f"Invalid token: {e}"}

        # Check expiration
        if int(time.time()) > token_data.get("expires_at", 0):
            return {"error": "Token expired"}

        # Check organization matches
        if token_data.get("organization_id") != organization_id:
            return {"error": "Organization mismatch"}

        # Create link
        link_record = {
            "organization_id": organization_id,
            "linked_at": int(time.time()),
            "permissions": ["verify_calls", "get_commitments"],
            "linked_device": token_data.get("device_id")
        }

        self.customers[customer_id]["organization_links"][organization_id] = link_record

        return link_record

    def unlink_organization(self, customer_id: str, organization_id: str) -> bool:
        """
        Unlink a customer from an organization.

        Args:
            customer_id: Customer identifier
            organization_id: Organization to unlink

        Returns:
            bool: True if unlinked
        """
        if customer_id not in self.customers:
            return False

        if organization_id in self.customers[customer_id]["organization_links"]:
            del self.customers[customer_id]["organization_links"][organization_id]
            return True

        return False

    def is_organization_authorized(self, customer_id: str, organization_id: str,
                                   permission: str = "get_commitments") -> bool:
        """
        Check if an organization is authorized to access customer data.

        Args:
            customer_id: Customer identifier
            organization_id: Organization to check
            permission: Required permission

        Returns:
            bool: True if authorized
        """
        if customer_id not in self.customers:
            return False

        link = self.customers[customer_id]["organization_links"].get(organization_id)
        if not link:
            return False

        return permission in link.get("permissions", [])

    def get_customer_by_device(self, device_id: str) -> Optional[str]:
        """
        Get customer ID by device ID.

        Args:
            device_id: Device identifier

        Returns:
            str: Customer ID or None
        """
        return self.device_to_customer.get(device_id)

    def update_device_last_seen(self, device_id: str):
        """
        Update the last seen timestamp for a device.

        Args:
            device_id: Device identifier
        """
        customer_id = self.device_to_customer.get(device_id)
        if customer_id and customer_id in self.customers:
            if device_id in self.customers[customer_id]["devices"]:
                self.customers[customer_id]["devices"][device_id]["last_seen"] = int(time.time())

    def get_customer(self, customer_id: str) -> Optional[Dict]:
        """
        Get customer record.

        Args:
            customer_id: Customer identifier

        Returns:
            dict: Customer record or None
        """
        return self.customers.get(customer_id)

    def get_all_customers(self) -> List[Dict]:
        """
        Get all customer records.

        Returns:
            list: All customer records
        """
        return list(self.customers.values())
