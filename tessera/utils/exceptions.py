"""
Custom exceptions for Tessera.
Provides specific error types for better error handling and debugging.
"""


class TesseraError(Exception):
    """Base exception for Tessera operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "CALLDNS_ERROR"
        self.details = details or {}

    def to_dict(self):
        """Convert exception to dictionary for JSON responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ValidationError(TesseraError):
    """Exception raised for input validation errors."""

    def __init__(self, message: str, field: str = None, value=None):
        super().__init__(message, "VALIDATION_ERROR", {
            "field": field,
            "value": str(value) if value is not None else None
        })
        self.field = field
        self.value = value


class ProofError(TesseraError):
    """Exception raised for zero-knowledge proof operations."""

    def __init__(self, message: str, proof_type: str = None):
        super().__init__(message, "PROOF_ERROR", {"proof_type": proof_type})
        self.proof_type = proof_type


class EncryptionError(TesseraError):
    """Exception raised for encryption/decryption operations."""

    def __init__(self, message: str, operation: str = None):
        super().__init__(message, "ENCRYPTION_ERROR", {"operation": operation})
        self.operation = operation


class NetworkError(TesseraError):
    """Exception raised for network operations."""

    def __init__(self, message: str, endpoint: str = None, status_code: int = None):
        super().__init__(message, "NETWORK_ERROR", {
            "endpoint": endpoint,
            "status_code": status_code
        })
        self.endpoint = endpoint
        self.status_code = status_code


class CommitmentError(TesseraError):
    """Exception raised for commitment operations."""

    def __init__(self, message: str, commitment_id: str = None):
        super().__init__(message, "COMMITMENT_ERROR", {"commitment_id": commitment_id})
        self.commitment_id = commitment_id


class IdentityError(TesseraError):
    """Exception raised for identity management operations."""

    def __init__(self, message: str, identity_type: str = None):
        super().__init__(message, "IDENTITY_ERROR", {"identity_type": identity_type})
        self.identity_type = identity_type