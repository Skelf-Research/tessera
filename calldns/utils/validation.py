"""
Input validation utilities for CallDNS.
Provides comprehensive validation for all input types and data structures.
"""

import re
import base64
import hashlib
from typing import Any, Dict, List, Optional, Union
from .exceptions import ValidationError


class InputValidator:
    """Comprehensive input validator for CallDNS operations."""

    # Regular expressions for validation
    PHONE_REGEX = re.compile(r'^\+?[1-9]\d{6,14}$')  # E.164 format (min 7 digits)
    HEX_REGEX = re.compile(r'^[0-9a-fA-F]+$')
    SESSION_ID_REGEX = re.compile(r'^[a-zA-Z0-9_-]{8,64}$')
    BASE64_REGEX = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')

    @staticmethod
    def validate_phone_number(phone: str) -> str:
        """
        Validate phone number format.

        Args:
            phone: Phone number string

        Returns:
            str: Validated phone number

        Raises:
            ValidationError: If phone number is invalid
        """
        if not isinstance(phone, str):
            raise ValidationError("Phone number must be a string", "phone", phone)

        phone = phone.strip()
        if not phone:
            raise ValidationError("Phone number cannot be empty", "phone", phone)

        if not InputValidator.PHONE_REGEX.match(phone):
            raise ValidationError(
                "Invalid phone number format (expected E.164 format)",
                "phone",
                phone
            )

        return phone

    @staticmethod
    def validate_public_key(public_key: Union[str, bytes]) -> bytes:
        """
        Validate public key format and size.

        Args:
            public_key: Public key as hex string or bytes

        Returns:
            bytes: Validated public key

        Raises:
            ValidationError: If public key is invalid
        """
        if isinstance(public_key, str):
            if not InputValidator.HEX_REGEX.match(public_key):
                raise ValidationError("Public key must be valid hex", "public_key", public_key)

            try:
                public_key = bytes.fromhex(public_key)
            except ValueError:
                raise ValidationError("Invalid hex format for public key", "public_key", public_key)

        if not isinstance(public_key, bytes):
            raise ValidationError("Public key must be bytes or hex string", "public_key", type(public_key))

        # SECP256k1 public key should be 64 bytes (uncompressed) or 33 bytes (compressed)
        if len(public_key) not in [33, 64, 65]:  # 65 for uncompressed with prefix
            raise ValidationError(
                f"Invalid public key length: {len(public_key)} bytes (expected 33, 64, or 65)",
                "public_key",
                len(public_key)
            )

        return public_key

    @staticmethod
    def validate_session_id(session_id: str) -> str:
        """
        Validate session ID format.

        Args:
            session_id: Session identifier

        Returns:
            str: Validated session ID

        Raises:
            ValidationError: If session ID is invalid
        """
        if not isinstance(session_id, str):
            raise ValidationError("Session ID must be a string", "session_id", session_id)

        if not InputValidator.SESSION_ID_REGEX.match(session_id):
            raise ValidationError(
                "Invalid session ID format (8-64 alphanumeric, underscore, hyphen)",
                "session_id",
                session_id
            )

        return session_id

    @staticmethod
    def validate_base64(data: str, field_name: str = "data") -> bytes:
        """
        Validate and decode base64 data.

        Args:
            data: Base64 encoded string
            field_name: Name of the field for error reporting

        Returns:
            bytes: Decoded data

        Raises:
            ValidationError: If base64 data is invalid
        """
        if not isinstance(data, str):
            raise ValidationError(f"{field_name} must be a string", field_name, data)

        if not InputValidator.BASE64_REGEX.match(data):
            raise ValidationError(f"Invalid base64 format for {field_name}", field_name, data)

        try:
            return base64.b64decode(data)
        except Exception as e:
            raise ValidationError(f"Failed to decode base64 {field_name}: {e}", field_name, data)

    @staticmethod
    def validate_proof_structure(proof: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate zero-knowledge proof structure.

        Args:
            proof: Proof dictionary

        Returns:
            dict: Validated proof

        Raises:
            ValidationError: If proof structure is invalid
        """
        if not isinstance(proof, dict):
            raise ValidationError("Proof must be a dictionary", "proof", type(proof))

        required_fields = ['R', 's', 'public_key']
        for field in required_fields:
            if field not in proof:
                raise ValidationError(f"Missing required proof field: {field}", field, None)

        # Validate R (elliptic curve point)
        if isinstance(proof['R'], str):
            proof['R'] = InputValidator.validate_base64(proof['R'], 'R')
        elif not isinstance(proof['R'], bytes):
            raise ValidationError("Proof R must be bytes or base64 string", 'R', type(proof['R']))

        # Support both 64-byte (compressed) and 65-byte (uncompressed) formats
        if len(proof['R']) not in [64, 65]:
            raise ValidationError(
                f"Invalid R length: {len(proof['R'])} bytes (expected 64 or 65)",
                'R',
                len(proof['R'])
            )

        # Validate s (scalar)
        if not isinstance(proof['s'], int):
            raise ValidationError("Proof s must be an integer", 's', type(proof['s']))

        if proof['s'] <= 0 or proof['s'] >= 2**256:
            raise ValidationError("Proof s must be positive and less than 2^256", 's', proof['s'])

        # Validate public key
        if isinstance(proof['public_key'], str):
            proof['public_key'] = InputValidator.validate_base64(proof['public_key'], 'public_key')

        proof['public_key'] = InputValidator.validate_public_key(proof['public_key'])

        return proof

    @staticmethod
    def validate_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate call metadata structure.

        Args:
            metadata: Metadata dictionary

        Returns:
            dict: Validated metadata

        Raises:
            ValidationError: If metadata is invalid
        """
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a dictionary", "metadata", type(metadata))

        validated = {}

        # Validate timestamp
        if 'timestamp' in metadata:
            timestamp = metadata['timestamp']
            if not isinstance(timestamp, (int, float)):
                raise ValidationError("Timestamp must be a number", "timestamp", timestamp)

            if timestamp < 0 or timestamp > 2**32:
                raise ValidationError("Timestamp out of valid range", "timestamp", timestamp)

            validated['timestamp'] = int(timestamp)

        # Validate call type
        if 'call_type' in metadata:
            call_type = metadata['call_type']
            valid_types = ['voice', 'video', 'text', 'emergency']
            if call_type not in valid_types:
                raise ValidationError(
                    f"Invalid call type: {call_type} (must be one of {valid_types})",
                    "call_type",
                    call_type
                )
            validated['call_type'] = call_type

        # Validate urgency flag
        if 'urgent' in metadata:
            urgent = metadata['urgent']
            if not isinstance(urgent, bool):
                raise ValidationError("Urgent flag must be boolean", "urgent", urgent)
            validated['urgent'] = urgent

        # Validate message
        if 'message' in metadata:
            message = metadata['message']
            if not isinstance(message, str):
                raise ValidationError("Message must be a string", "message", message)

            if len(message) > 1000:  # Reasonable limit
                raise ValidationError("Message too long (max 1000 characters)", "message", len(message))

            validated['message'] = message

        # Copy other valid fields
        for key, value in metadata.items():
            if key not in validated and isinstance(key, str) and len(key) <= 50:
                validated[key] = value

        return validated

    @staticmethod
    def validate_commitment_id(commitment_id: str) -> str:
        """
        Validate commitment ID format.

        Args:
            commitment_id: Commitment identifier

        Returns:
            str: Validated commitment ID

        Raises:
            ValidationError: If commitment ID is invalid
        """
        if not isinstance(commitment_id, str):
            raise ValidationError("Commitment ID must be a string", "commitment_id", commitment_id)

        if not InputValidator.HEX_REGEX.match(commitment_id):
            raise ValidationError("Commitment ID must be hex format", "commitment_id", commitment_id)

        if len(commitment_id) != 64:  # SHA-256 hash length
            raise ValidationError(
                f"Invalid commitment ID length: {len(commitment_id)} (expected 64)",
                "commitment_id",
                len(commitment_id)
            )

        return commitment_id.lower()

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000, field_name: str = "string") -> str:
        """
        Sanitize string input by removing dangerous characters and limiting length.

        Args:
            value: String to sanitize
            max_length: Maximum allowed length
            field_name: Field name for error reporting

        Returns:
            str: Sanitized string

        Raises:
            ValidationError: If string is invalid
        """
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string", field_name, value)

        # Remove null bytes and control characters (except newlines and tabs)
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)

        # Limit length
        if len(sanitized) > max_length:
            raise ValidationError(
                f"{field_name} too long (max {max_length} characters)",
                field_name,
                len(sanitized)
            )

        return sanitized.strip()

    @staticmethod
    def validate_recipients_list(recipients: List[str]) -> List[str]:
        """
        Validate list of recipients.

        Args:
            recipients: List of recipient identifiers

        Returns:
            list: Validated recipients

        Raises:
            ValidationError: If recipients list is invalid
        """
        if not isinstance(recipients, list):
            raise ValidationError("Recipients must be a list", "recipients", type(recipients))

        if len(recipients) > 100:  # Reasonable limit
            raise ValidationError("Too many recipients (max 100)", "recipients", len(recipients))

        validated_recipients = []
        for i, recipient in enumerate(recipients):
            if not isinstance(recipient, str):
                raise ValidationError(
                    f"Recipient {i} must be a string",
                    f"recipients[{i}]",
                    type(recipient)
                )

            recipient = InputValidator.sanitize_string(recipient, 200, f"recipients[{i}]")
            if recipient:  # Only add non-empty recipients
                validated_recipients.append(recipient)

        return validated_recipients