"""
CallDNS - A zero-knowledge caller verification system.

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
from .sdk import Caller, Verifier
from .crypto import ZKProver, ZKVerifier
from .privacy import PrivacyPreserver
from .network import EnhancedBroadcast

__all__ = [
    "Caller",
    "Verifier",
    "ZKProver",
    "ZKVerifier",
    "PrivacyPreserver",
    "EnhancedBroadcast"
]