"""
Tessera - A zero-knowledge sender verification system.

This package provides:
1. Zero-knowledge proof generation and verification
2. Privacy-preserving call verification
3. Scalable proof matching
4. Client SDK for integration
5. CLI tools for end-users
6. Web service for network operations
"""

__version__ = "0.1.0"
__author__ = "Dipankar Sarkar"
__email__ = "me@dipankar.name"
__license__ = "MIT"

# Import main components for easy access
from .sdk import Sender, Verifier
from .crypto import ZKProver, ZKVerifier, SecureEncryption
from .privacy import PrivacyPreserver
from .network import EnhancedBroadcast
from .utils import InputValidator, ValidationError, TesseraError, ProofError, EncryptionError
from .keystore import KeyManager, KeyRotationManager, EncryptedKeyStore
from .logging import TesseraLogger, SecurityLogger, MetricsCollector, SecurityMonitor, PerformanceMonitor

__all__ = [
    "Sender",
    "Verifier",
    "ZKProver",
    "ZKVerifier",
    "SecureEncryption",
    "PrivacyPreserver",
    "EnhancedBroadcast",
    "InputValidator",
    "ValidationError",
    "TesseraError",
    "ProofError",
    "EncryptionError",
    "KeyManager",
    "KeyRotationManager",
    "EncryptedKeyStore",
    "TesseraLogger",
    "SecurityLogger",
    "MetricsCollector",
    "SecurityMonitor",
    "PerformanceMonitor"
]