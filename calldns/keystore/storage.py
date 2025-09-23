"""
Key storage backends for CallDNS.
Provides secure storage for cryptographic keys with various backends.
"""

import os
import json
import time
import secrets
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..utils.exceptions import EncryptionError, IdentityError


class KeyStore(ABC):
    """Abstract base class for key storage backends."""

    @abstractmethod
    def store_key(self, key_id: str, key_data: dict, master_password: bytes = None) -> bool:
        """Store a key securely."""
        pass

    @abstractmethod
    def load_key(self, key_id: str, master_password: bytes = None) -> Optional[dict]:
        """Load a key from storage."""
        pass

    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """Delete a key from storage."""
        pass

    @abstractmethod
    def list_keys(self) -> List[str]:
        """List all stored key identifiers."""
        pass

    @abstractmethod
    def key_exists(self, key_id: str) -> bool:
        """Check if a key exists in storage."""
        pass


class FileKeyStore(KeyStore):
    """
    File-based key storage (unencrypted - for development only).

    WARNING: This stores keys in plaintext and should only be used for development.
    """

    def __init__(self, storage_dir: str = None):
        """
        Initialize file-based key storage.

        Args:
            storage_dir: Directory to store keys (defaults to ~/.calldns/keys)
        """
        if storage_dir is None:
            storage_dir = os.path.expanduser("~/.calldns/keys")

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Set restrictive permissions
        os.chmod(self.storage_dir, 0o700)

    def store_key(self, key_id: str, key_data: dict, master_password: bytes = None) -> bool:
        """Store a key to file."""
        try:
            # Sanitize key_id for filesystem
            safe_key_id = self._sanitize_filename(key_id)
            key_file = self.storage_dir / f"{safe_key_id}.key"

            # Prepare storage data
            storage_data = {
                'key_id': key_id,
                'stored_at': int(time.time()),
                'data': key_data
            }

            # Write to file with restrictive permissions
            with open(key_file, 'w') as f:
                json.dump(storage_data, f, indent=2, default=self._json_serializer)

            # Set restrictive file permissions
            os.chmod(key_file, 0o600)
            return True

        except Exception as e:
            raise IdentityError(f"Failed to store key: {e}", "storage")

    def load_key(self, key_id: str, master_password: bytes = None) -> Optional[dict]:
        """Load a key from file."""
        try:
            safe_key_id = self._sanitize_filename(key_id)
            key_file = self.storage_dir / f"{safe_key_id}.key"

            if not key_file.exists():
                return None

            with open(key_file, 'r') as f:
                storage_data = json.load(f)

            # Convert hex strings back to bytes for key data
            data = storage_data.get('data')
            if data:
                data = self._load_json_with_bytes(data)
            return data

        except Exception as e:
            raise IdentityError(f"Failed to load key: {e}", "storage")

    def delete_key(self, key_id: str) -> bool:
        """Delete a key file."""
        try:
            safe_key_id = self._sanitize_filename(key_id)
            key_file = self.storage_dir / f"{safe_key_id}.key"

            if key_file.exists():
                key_file.unlink()
                return True
            return False

        except Exception as e:
            raise IdentityError(f"Failed to delete key: {e}", "storage")

    def list_keys(self) -> List[str]:
        """List all stored key identifiers."""
        try:
            key_files = self.storage_dir.glob("*.key")
            key_ids = []

            for key_file in key_files:
                try:
                    with open(key_file, 'r') as f:
                        storage_data = json.load(f)
                    key_ids.append(storage_data.get('key_id', key_file.stem))
                except:
                    continue  # Skip corrupted files

            return key_ids

        except Exception as e:
            raise IdentityError(f"Failed to list keys: {e}", "storage")

    def key_exists(self, key_id: str) -> bool:
        """Check if a key file exists."""
        safe_key_id = self._sanitize_filename(key_id)
        key_file = self.storage_dir / f"{safe_key_id}.key"
        return key_file.exists()

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a string for use as a filename."""
        # Replace unsafe characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        sanitized = ''.join(c if c in safe_chars else '_' for c in filename)
        return sanitized[:100]  # Limit length

    def _json_serializer(self, obj):
        """Custom JSON serializer for bytes objects."""
        if isinstance(obj, bytes):
            return obj.hex()  # Simple hex encoding
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _load_json_with_bytes(self, data):
        """Load JSON and convert hex strings back to bytes for key fields."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key in ['private_key', 'public_key'] and isinstance(value, str):
                    try:
                        result[key] = bytes.fromhex(value)
                    except ValueError:
                        result[key] = value
                elif isinstance(value, (dict, list)):
                    result[key] = self._load_json_with_bytes(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [self._load_json_with_bytes(item) for item in data]
        return data


class EncryptedKeyStore(KeyStore):
    """
    Encrypted file-based key storage for production use.
    Uses AES-GCM with PBKDF2 key derivation.
    """

    def __init__(self, storage_dir: str = None, default_iterations: int = 100000):
        """
        Initialize encrypted key storage.

        Args:
            storage_dir: Directory to store encrypted keys
            default_iterations: PBKDF2 iterations for key derivation
        """
        if storage_dir is None:
            storage_dir = os.path.expanduser("~/.calldns/secure_keys")

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.default_iterations = default_iterations

        # Set restrictive permissions
        os.chmod(self.storage_dir, 0o700)

    def store_key(self, key_id: str, key_data: dict, master_password: bytes = None) -> bool:
        """Store a key with encryption."""
        try:
            if master_password is None:
                raise EncryptionError("Master password required for encrypted storage", "storage")

            # Sanitize key_id
            safe_key_id = self._sanitize_filename(key_id)
            key_file = self.storage_dir / f"{safe_key_id}.ekey"

            # Prepare storage data
            storage_data = {
                'key_id': key_id,
                'stored_at': int(time.time()),
                'data': key_data
            }

            # Serialize to JSON
            plaintext = json.dumps(storage_data, default=self._json_serializer).encode('utf-8')

            # Generate salt and derive encryption key
            salt = secrets.token_bytes(32)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.default_iterations,
            )
            encryption_key = kdf.derive(master_password)

            # Encrypt with AES-GCM
            aesgcm = AESGCM(encryption_key)
            nonce = secrets.token_bytes(12)
            ciphertext = aesgcm.encrypt(nonce, plaintext, b"")

            # Prepare encrypted storage format
            encrypted_data = {
                'version': 1,
                'algorithm': 'AES-GCM',
                'kdf': 'PBKDF2-SHA256',
                'iterations': self.default_iterations,
                'salt': salt.hex(),
                'nonce': nonce.hex(),
                'ciphertext': ciphertext.hex()
            }

            # Write encrypted data
            with open(key_file, 'w') as f:
                json.dump(encrypted_data, f, indent=2)

            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return True

        except Exception as e:
            if isinstance(e, EncryptionError):
                raise
            raise EncryptionError(f"Failed to store encrypted key: {e}", "storage")

    def load_key(self, key_id: str, master_password: bytes = None) -> Optional[dict]:
        """Load and decrypt a key."""
        try:
            if master_password is None:
                raise EncryptionError("Master password required for encrypted storage", "storage")

            safe_key_id = self._sanitize_filename(key_id)
            key_file = self.storage_dir / f"{safe_key_id}.ekey"

            if not key_file.exists():
                return None

            # Load encrypted data
            with open(key_file, 'r') as f:
                encrypted_data = json.load(f)

            # Validate format
            if encrypted_data.get('version') != 1:
                raise EncryptionError("Unsupported key file version", "storage")

            # Extract encryption parameters
            salt = bytes.fromhex(encrypted_data['salt'])
            nonce = bytes.fromhex(encrypted_data['nonce'])
            ciphertext = bytes.fromhex(encrypted_data['ciphertext'])
            iterations = encrypted_data.get('iterations', self.default_iterations)

            # Derive decryption key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=iterations,
            )
            decryption_key = kdf.derive(master_password)

            # Decrypt
            aesgcm = AESGCM(decryption_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, b"")

            # Parse JSON and convert hex strings back to bytes
            storage_data = json.loads(plaintext.decode('utf-8'))
            data = storage_data.get('data')
            if data:
                data = self._load_json_with_bytes(data)
            return data

        except Exception as e:
            if isinstance(e, EncryptionError):
                raise
            # Return None for decryption failures (likely wrong password)
            return None

    def delete_key(self, key_id: str) -> bool:
        """Delete an encrypted key file."""
        try:
            safe_key_id = self._sanitize_filename(key_id)
            key_file = self.storage_dir / f"{safe_key_id}.ekey"

            if key_file.exists():
                # Securely overwrite before deletion
                self._secure_delete(key_file)
                return True
            return False

        except Exception as e:
            raise IdentityError(f"Failed to delete encrypted key: {e}", "storage")

    def list_keys(self) -> List[str]:
        """List all encrypted key identifiers."""
        try:
            key_files = self.storage_dir.glob("*.ekey")
            key_ids = []

            for key_file in key_files:
                # We can't decrypt without password, so use filename
                key_id = key_file.stem
                key_ids.append(key_id)

            return key_ids

        except Exception as e:
            raise IdentityError(f"Failed to list encrypted keys: {e}", "storage")

    def key_exists(self, key_id: str) -> bool:
        """Check if an encrypted key file exists."""
        safe_key_id = self._sanitize_filename(key_id)
        key_file = self.storage_dir / f"{safe_key_id}.ekey"
        return key_file.exists()

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a string for use as a filename."""
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        sanitized = ''.join(c if c in safe_chars else '_' for c in filename)
        return sanitized[:100]

    def _json_serializer(self, obj):
        """Custom JSON serializer for bytes objects."""
        if isinstance(obj, bytes):
            return obj.hex()  # Simple hex encoding
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _secure_delete(self, file_path: Path):
        """Securely overwrite a file before deletion."""
        try:
            if file_path.exists():
                # Get file size
                file_size = file_path.stat().st_size

                # Overwrite with random data (3 passes)
                with open(file_path, 'r+b') as f:
                    for _ in range(3):
                        f.seek(0)
                        f.write(secrets.token_bytes(file_size))
                        f.flush()
                        os.fsync(f.fileno())

                # Delete the file
                file_path.unlink()

        except Exception:
            # If secure deletion fails, try normal deletion
            try:
                file_path.unlink()
            except:
                pass

    def _load_json_with_bytes(self, data):
        """Load JSON and convert hex strings back to bytes for key fields."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key in ['private_key', 'public_key'] and isinstance(value, str):
                    try:
                        result[key] = bytes.fromhex(value)
                    except ValueError:
                        result[key] = value
                elif isinstance(value, (dict, list)):
                    result[key] = self._load_json_with_bytes(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [self._load_json_with_bytes(item) for item in data]
        return data