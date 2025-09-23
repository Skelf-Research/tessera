"""
Secure key management for CallDNS.
Handles key generation, storage, rotation, and lifecycle management.
"""

import os
import time
import secrets
import hashlib
from typing import Dict, Optional, Tuple, List
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..utils.exceptions import IdentityError, EncryptionError
from ..utils.validation import InputValidator
from .storage import FileKeyStore, EncryptedKeyStore


class KeyManager:
    """
    Secure key management for CallDNS operations.
    Handles identity keys, encryption keys, and key derivation.
    """

    def __init__(self, storage_backend=None, master_password: bytes = None):
        """
        Initialize key manager.

        Args:
            storage_backend: Key storage backend (defaults to encrypted file storage)
            master_password: Master password for key encryption (optional)
        """
        self.storage = storage_backend or EncryptedKeyStore()
        self.master_password = master_password
        self._key_cache: Dict[str, dict] = {}
        self._cache_expiry: Dict[str, float] = {}
        self._cache_ttl = 3600  # 1 hour cache TTL

    def generate_identity_keypair(self, identity_id: str, metadata: dict = None) -> Tuple[bytes, bytes]:
        """
        Generate a new identity keypair.

        Args:
            identity_id: Unique identifier for this identity
            metadata: Optional metadata to store with the key

        Returns:
            tuple: (private_key_bytes, public_key_bytes)

        Raises:
            IdentityError: If key generation fails
        """
        try:
            # Validate identity ID
            identity_id = InputValidator.sanitize_string(identity_id, 100, "identity_id")

            if self.key_exists(identity_id):
                raise IdentityError(f"Identity {identity_id} already exists", "generation")

            # Generate cryptographically secure keypair
            from ecdsa import SigningKey, SECP256k1
            private_key = SigningKey.generate(curve=SECP256k1)
            public_key = private_key.get_verifying_key()

            # Serialize keys
            private_key_bytes = private_key.to_string()
            public_key_bytes = public_key.to_string()

            # Prepare key entry
            key_entry = {
                'private_key': private_key_bytes,
                'public_key': public_key_bytes,
                'created_at': int(time.time()),
                'key_type': 'identity',
                'algorithm': 'ECDSA-SECP256k1',
                'metadata': metadata or {},
                'version': 1,
                'status': 'active'
            }

            # Store securely
            self._store_key(identity_id, key_entry)

            return private_key_bytes, public_key_bytes

        except Exception as e:
            if isinstance(e, IdentityError):
                raise
            raise IdentityError(f"Failed to generate identity keypair: {e}", "generation")

    def get_identity_keys(self, identity_id: str) -> Optional[Tuple[bytes, bytes]]:
        """
        Retrieve identity keypair.

        Args:
            identity_id: Identity identifier

        Returns:
            tuple: (private_key_bytes, public_key_bytes) or None if not found

        Raises:
            IdentityError: If key retrieval fails
        """
        try:
            identity_id = InputValidator.sanitize_string(identity_id, 100, "identity_id")

            # Check cache first
            if self._is_cached(identity_id):
                key_entry = self._key_cache[identity_id]
                return key_entry['private_key'], key_entry['public_key']

            # Load from storage
            key_entry = self._load_key(identity_id)
            if not key_entry:
                return None

            # Validate key entry
            if key_entry['key_type'] != 'identity':
                raise IdentityError(f"Key {identity_id} is not an identity key", "retrieval")

            if key_entry['status'] != 'active':
                raise IdentityError(f"Key {identity_id} is not active", "retrieval")

            # Cache the key
            self._cache_key(identity_id, key_entry)

            return key_entry['private_key'], key_entry['public_key']

        except Exception as e:
            if isinstance(e, IdentityError):
                raise
            raise IdentityError(f"Failed to retrieve identity keys: {e}", "retrieval")

    def get_public_key(self, identity_id: str) -> Optional[bytes]:
        """
        Retrieve only the public key for an identity.

        Args:
            identity_id: Identity identifier

        Returns:
            bytes: Public key or None if not found
        """
        keys = self.get_identity_keys(identity_id)
        return keys[1] if keys else None

    def derive_encryption_key(self, identity_id: str, purpose: str, salt: bytes = None) -> bytes:
        """
        Derive an encryption key from identity key for specific purpose.

        Args:
            identity_id: Identity identifier
            purpose: Purpose of the derived key (e.g., 'proof_encryption', 'storage')
            salt: Optional salt (generated if not provided)

        Returns:
            bytes: Derived encryption key

        Raises:
            IdentityError: If key derivation fails
        """
        try:
            keys = self.get_identity_keys(identity_id)
            if not keys:
                raise IdentityError(f"Identity {identity_id} not found", "derivation")

            private_key = keys[0]

            # Use PBKDF2 for key derivation
            if salt is None:
                salt = hashlib.sha256(f"{identity_id}:{purpose}".encode()).digest()[:16]

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256-bit key
                salt=salt,
                iterations=100000,  # OWASP recommended minimum
            )

            derived_key = kdf.derive(private_key)
            return derived_key

        except Exception as e:
            if isinstance(e, IdentityError):
                raise
            raise IdentityError(f"Failed to derive encryption key: {e}", "derivation")

    def rotate_keys(self, identity_id: str, keep_backup: bool = True) -> Tuple[bytes, bytes]:
        """
        Rotate keys for an identity.

        Args:
            identity_id: Identity identifier
            keep_backup: Whether to keep a backup of old keys

        Returns:
            tuple: New (private_key_bytes, public_key_bytes)

        Raises:
            IdentityError: If key rotation fails
        """
        try:
            # Get existing key entry
            old_key_entry = self._load_key(identity_id)
            if not old_key_entry:
                raise IdentityError(f"Identity {identity_id} not found", "rotation")

            # Create backup if requested
            if keep_backup:
                backup_id = f"{identity_id}.backup.{int(time.time())}"
                old_key_entry['status'] = 'backup'
                self._store_key(backup_id, old_key_entry)

            # Generate new keypair
            metadata = old_key_entry.get('metadata', {})
            metadata['rotated_from'] = identity_id
            metadata['rotation_time'] = int(time.time())

            # Remove old key from cache and storage
            self._invalidate_cache(identity_id)
            self.storage.delete_key(identity_id)

            # Generate new keys
            return self.generate_identity_keypair(identity_id, metadata)

        except Exception as e:
            if isinstance(e, IdentityError):
                raise
            raise IdentityError(f"Failed to rotate keys: {e}", "rotation")

    def key_exists(self, identity_id: str) -> bool:
        """Check if a key exists for the given identity."""
        try:
            return self._load_key(identity_id) is not None
        except:
            return False

    def list_identities(self) -> List[Dict[str, any]]:
        """
        List all identities and their metadata.

        Returns:
            list: List of identity information dictionaries
        """
        try:
            identities = []
            for key_id in self.storage.list_keys():
                if '.backup.' in key_id:
                    continue  # Skip backup keys

                key_entry = self._load_key(key_id)
                if key_entry and key_entry.get('key_type') == 'identity':
                    identities.append({
                        'identity_id': key_id,
                        'created_at': key_entry.get('created_at'),
                        'algorithm': key_entry.get('algorithm'),
                        'status': key_entry.get('status'),
                        'metadata': key_entry.get('metadata', {})
                    })

            return identities

        except Exception as e:
            raise IdentityError(f"Failed to list identities: {e}", "listing")

    def delete_identity(self, identity_id: str, force: bool = False) -> bool:
        """
        Delete an identity and its keys.

        Args:
            identity_id: Identity identifier
            force: Force deletion even if key is active

        Returns:
            bool: True if deleted successfully

        Raises:
            IdentityError: If deletion fails
        """
        try:
            key_entry = self._load_key(identity_id)
            if not key_entry:
                return False

            if key_entry.get('status') == 'active' and not force:
                raise IdentityError("Cannot delete active identity without force=True", "deletion")

            # Remove from cache
            self._invalidate_cache(identity_id)

            # Delete from storage
            return self.storage.delete_key(identity_id)

        except Exception as e:
            if isinstance(e, IdentityError):
                raise
            raise IdentityError(f"Failed to delete identity: {e}", "deletion")

    def _store_key(self, key_id: str, key_entry: dict):
        """Store a key entry securely."""
        self.storage.store_key(key_id, key_entry, self.master_password)

    def _load_key(self, key_id: str) -> Optional[dict]:
        """Load a key entry from storage."""
        return self.storage.load_key(key_id, self.master_password)

    def _cache_key(self, key_id: str, key_entry: dict):
        """Cache a key entry temporarily."""
        self._key_cache[key_id] = key_entry
        self._cache_expiry[key_id] = time.time() + self._cache_ttl

    def _is_cached(self, key_id: str) -> bool:
        """Check if a key is cached and not expired."""
        return (key_id in self._key_cache and
                key_id in self._cache_expiry and
                time.time() < self._cache_expiry[key_id])

    def _invalidate_cache(self, key_id: str):
        """Remove a key from cache."""
        self._key_cache.pop(key_id, None)
        self._cache_expiry.pop(key_id, None)

    def cleanup_cache(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key_id for key_id, expiry in self._cache_expiry.items()
            if current_time >= expiry
        ]
        for key_id in expired_keys:
            self._invalidate_cache(key_id)


class KeyRotationManager:
    """
    Manages automatic key rotation policies and schedules.
    """

    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.rotation_policies: Dict[str, dict] = {}

    def set_rotation_policy(self, identity_id: str, max_age_days: int,
                          auto_rotate: bool = False):
        """
        Set rotation policy for an identity.

        Args:
            identity_id: Identity identifier
            max_age_days: Maximum age in days before rotation is recommended
            auto_rotate: Whether to automatically rotate when threshold is reached
        """
        self.rotation_policies[identity_id] = {
            'max_age_days': max_age_days,
            'auto_rotate': auto_rotate,
            'last_check': int(time.time())
        }

    def check_rotation_needed(self, identity_id: str) -> bool:
        """
        Check if an identity needs key rotation.

        Args:
            identity_id: Identity identifier

        Returns:
            bool: True if rotation is needed
        """
        if identity_id not in self.rotation_policies:
            return False

        policy = self.rotation_policies[identity_id]
        max_age_seconds = policy['max_age_days'] * 24 * 3600

        key_entry = self.key_manager._load_key(identity_id)
        if not key_entry:
            return False

        key_age = int(time.time()) - key_entry.get('created_at', 0)
        return key_age >= max_age_seconds

    def rotate_if_needed(self, identity_id: str) -> bool:
        """
        Rotate keys if policy dictates it's needed.

        Args:
            identity_id: Identity identifier

        Returns:
            bool: True if rotation was performed
        """
        if not self.check_rotation_needed(identity_id):
            return False

        policy = self.rotation_policies.get(identity_id, {})
        if not policy.get('auto_rotate', False):
            return False

        try:
            self.key_manager.rotate_keys(identity_id)
            policy['last_check'] = int(time.time())
            return True
        except Exception:
            return False

    def get_rotation_status(self) -> Dict[str, dict]:
        """
        Get rotation status for all managed identities.

        Returns:
            dict: Status information for each identity
        """
        status = {}
        for identity_id, policy in self.rotation_policies.items():
            needs_rotation = self.check_rotation_needed(identity_id)
            key_entry = self.key_manager._load_key(identity_id)

            status[identity_id] = {
                'needs_rotation': needs_rotation,
                'auto_rotate': policy.get('auto_rotate', False),
                'max_age_days': policy.get('max_age_days'),
                'key_age_days': (int(time.time()) - key_entry.get('created_at', 0)) // (24 * 3600) if key_entry else None,
                'last_check': policy.get('last_check')
            }

        return status