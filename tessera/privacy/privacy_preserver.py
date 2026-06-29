"""
Privacy preservation for Tessera.
Ensures sender/recipient anonymity and minimizes information leakage.
"""

import hashlib
import secrets


class PrivacyPreserver:
    """Ensures privacy in the Tessera system."""

    @staticmethod
    def anonymize_metadata(metadata):
        """
        Remove identifying information from metadata.

        Args:
            metadata: Metadata to anonymize

        Returns:
            dict: Anonymized metadata
        """
        if not metadata:
            return {}

        # Remove potentially identifying fields
        anonymized = metadata.copy()

        # Remove common identifying fields
        identifying_fields = [
            "sender_id",
            "recipient_id",
            "email",
            "ip_address",
            "device_id",
            "location",
        ]

        for field in identifying_fields:
            anonymized.pop(field, None)

        return anonymized

    @staticmethod
    def generate_session_id():
        """
        Generate a temporary session identifier.

        Returns:
            str: A random session identifier
        """
        return secrets.token_hex(16)

    @staticmethod
    def obfuscate_timestamp(timestamp):
        """
        Obfuscate timestamp to reduce precision.

        Args:
            timestamp: Original timestamp

        Returns:
            int: Obfuscated timestamp with reduced precision
        """
        # Round to nearest 10 minutes to reduce precision
        return (timestamp // 600) * 600
