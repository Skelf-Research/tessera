"""
Key management utilities for Tessera.
Provides key derivation, backup, and recovery functionality.
"""

import os
import json
import time
import hashlib
import secrets
import zipfile
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..utils.exceptions import EncryptionError, IdentityError


class KeyDerivation:
    """
    Utilities for secure key derivation.
    Implements various key derivation functions for different use cases.
    """

    @staticmethod
    def derive_key_hkdf(
        master_key: bytes,
        purpose: str,
        length: int = 32,
        salt: bytes = None,
        info: bytes = None,
    ) -> bytes:
        """
        Derive a key using HKDF (HMAC-based Key Derivation Function).

        Args:
            master_key: Master key material
            purpose: Purpose of the derived key
            length: Desired output length in bytes
            salt: Optional salt (recommended)
            info: Optional context information

        Returns:
            bytes: Derived key

        Raises:
            EncryptionError: If key derivation fails
        """
        try:
            if salt is None:
                salt = hashlib.sha256(purpose.encode()).digest()[:16]

            if info is None:
                info = purpose.encode()

            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=length,
                salt=salt,
                info=info,
            )

            return hkdf.derive(master_key)

        except Exception as e:
            raise EncryptionError(f"HKDF key derivation failed: {e}", "derivation")

    @staticmethod
    def derive_key_pbkdf2(
        password: bytes, salt: bytes, iterations: int = 100000, length: int = 32
    ) -> bytes:
        """
        Derive a key using PBKDF2.

        Args:
            password: Password/passphrase
            salt: Salt value
            iterations: Number of iterations
            length: Desired output length in bytes

        Returns:
            bytes: Derived key

        Raises:
            EncryptionError: If key derivation fails
        """
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=length,
                salt=salt,
                iterations=iterations,
            )

            return kdf.derive(password)

        except Exception as e:
            raise EncryptionError(f"PBKDF2 key derivation failed: {e}", "derivation")

    @staticmethod
    def generate_salt(length: int = 32) -> bytes:
        """Generate a cryptographically secure salt."""
        return secrets.token_bytes(length)

    @staticmethod
    def stretch_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """
        Stretch a password using PBKDF2.

        Args:
            password: User password
            salt: Optional salt (generated if not provided)

        Returns:
            tuple: (stretched_key, salt)
        """
        if salt is None:
            salt = KeyDerivation.generate_salt()

        password_bytes = password.encode("utf-8")
        stretched_key = KeyDerivation.derive_key_pbkdf2(password_bytes, salt)

        return stretched_key, salt


class KeyBackup:
    """
    Utilities for secure key backup and recovery.
    Provides encrypted backup functionality with integrity checking.
    """

    def __init__(self, backup_dir: str = None):
        """
        Initialize key backup manager.

        Args:
            backup_dir: Directory for storing backups
        """
        if backup_dir is None:
            backup_dir = os.path.expanduser("~/.tessera/backups")

        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.backup_dir, 0o700)

    def create_backup(
        self, key_manager, backup_password: str, identity_ids: List[str] = None
    ) -> str:
        """
        Create an encrypted backup of keys.

        Args:
            key_manager: KeyManager instance
            backup_password: Password for backup encryption
            identity_ids: Specific identities to backup (all if None)

        Returns:
            str: Path to backup file

        Raises:
            IdentityError: If backup creation fails
        """
        try:
            # Determine which identities to backup
            backup_type = "full"
            if identity_ids is None:
                identities = key_manager.list_identities()
                identity_ids = [identity["identity_id"] for identity in identities]
            else:
                backup_type = "partial"

            # Collect key data
            backup_data = {
                "version": 1,
                "created_at": int(time.time()),
                "identities": {},
                "metadata": {
                    "total_keys": len(identity_ids),
                    "backup_type": backup_type,
                },
            }

            for identity_id in identity_ids:
                try:
                    keys = key_manager.get_identity_keys(identity_id)
                    if keys:
                        # Get full key entry for metadata
                        key_entry = key_manager._load_key(identity_id)
                        backup_data["identities"][identity_id] = {
                            "private_key": keys[0].hex(),
                            "public_key": keys[1].hex(),
                            "metadata": key_entry.get("metadata", {}),
                            "created_at": key_entry.get("created_at"),
                            "algorithm": key_entry.get("algorithm"),
                        }
                except Exception as e:
                    # Log the error but continue with other keys
                    print(f"Warning: Failed to backup identity {identity_id}: {e}")

            # Only create backup if we have identities to backup
            if not backup_data["identities"]:
                raise IdentityError("No valid identities found to backup", "backup")

            # Encrypt backup data
            backup_json = json.dumps(backup_data, indent=2)
            encrypted_backup = self._encrypt_backup(
                backup_json.encode(), backup_password
            )

            # Save to file with more precise timestamp
            timestamp = int(time.time() * 1000)  # Use milliseconds for uniqueness
            backup_filename = f"tessera_backup_{timestamp}.cbk"
            backup_path = self.backup_dir / backup_filename

            with open(backup_path, "wb") as f:
                f.write(encrypted_backup)

            os.chmod(backup_path, 0o600)
            return str(backup_path)

        except Exception as e:
            raise IdentityError(f"Failed to create backup: {e}", "backup")

    def restore_backup(
        self,
        backup_path: str,
        backup_password: str,
        key_manager,
        overwrite: bool = False,
    ) -> List[str]:
        """
        Restore keys from encrypted backup.

        Args:
            backup_path: Path to backup file
            backup_password: Password for backup decryption
            key_manager: KeyManager instance
            overwrite: Whether to overwrite existing keys

        Returns:
            list: List of restored identity IDs

        Raises:
            IdentityError: If restore fails
        """
        try:
            # Load and decrypt backup
            with open(backup_path, "rb") as f:
                encrypted_data = f.read()

            backup_json = self._decrypt_backup(encrypted_data, backup_password)
            backup_data = json.loads(backup_json.decode())

            # Validate backup format
            if backup_data.get("version") != 1:
                raise IdentityError("Unsupported backup version", "restore")

            restored_identities = []

            for identity_id, key_data in backup_data["identities"].items():
                try:
                    # Check if identity already exists
                    if key_manager.key_exists(identity_id) and not overwrite:
                        print(
                            f"Skipping existing identity {identity_id} (use overwrite=True to replace)"
                        )
                        continue

                    # Restore key data
                    private_key = bytes.fromhex(key_data["private_key"])
                    public_key = bytes.fromhex(key_data["public_key"])

                    # Create key entry
                    key_entry = {
                        "private_key": private_key,
                        "public_key": public_key,
                        "created_at": key_data.get("created_at", int(time.time())),
                        "key_type": "identity",
                        "algorithm": key_data.get("algorithm", "ECDSA-SECP256k1"),
                        "metadata": key_data.get("metadata", {}),
                        "version": 1,
                        "status": "active",
                        "restored_from_backup": True,
                        "restore_time": int(time.time()),
                    }

                    # Store the key
                    key_manager._store_key(identity_id, key_entry)
                    restored_identities.append(identity_id)

                except Exception as e:
                    print(f"Warning: Failed to restore identity {identity_id}: {e}")

            return restored_identities

        except Exception as e:
            if isinstance(e, IdentityError):
                raise
            raise IdentityError(f"Failed to restore backup: {e}", "restore")

    def list_backups(self) -> List[Dict[str, any]]:
        """
        List all available backups.

        Returns:
            list: List of backup information
        """
        try:
            backups = []
            for backup_file in self.backup_dir.glob("*.cbk"):
                stat = backup_file.stat()
                backups.append(
                    {
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size": stat.st_size,
                        "created_at": int(stat.st_mtime),
                        "age_days": (time.time() - stat.st_mtime) / (24 * 3600),
                    }
                )

            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            return backups

        except Exception as e:
            raise IdentityError(f"Failed to list backups: {e}", "listing")

    def verify_backup(self, backup_path: str, backup_password: str) -> Dict[str, any]:
        """
        Verify the integrity of a backup file.

        Args:
            backup_path: Path to backup file
            backup_password: Password for backup decryption

        Returns:
            dict: Backup verification information

        Raises:
            IdentityError: If verification fails
        """
        try:
            # Load and decrypt backup
            with open(backup_path, "rb") as f:
                encrypted_data = f.read()

            backup_json = self._decrypt_backup(encrypted_data, backup_password)
            backup_data = json.loads(backup_json.decode())

            # Extract information
            info = {
                "valid": True,
                "version": backup_data.get("version"),
                "created_at": backup_data.get("created_at"),
                "total_identities": len(backup_data.get("identities", {})),
                "metadata": backup_data.get("metadata", {}),
                "identities": list(backup_data.get("identities", {}).keys()),
            }

            return info

        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _encrypt_backup(self, data: bytes, password: str) -> bytes:
        """Encrypt backup data with password."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # Derive key from password
        salt = secrets.token_bytes(32)
        key, _ = KeyDerivation.stretch_password(password, salt)

        # Encrypt with AES-GCM
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)
        ciphertext = aesgcm.encrypt(nonce, data, b"")

        # Combine salt, nonce, and ciphertext
        return salt + nonce + ciphertext

    def _decrypt_backup(self, encrypted_data: bytes, password: str) -> bytes:
        """Decrypt backup data with password."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if len(encrypted_data) < 44:  # 32 (salt) + 12 (nonce)
            raise EncryptionError("Invalid backup file format", "decrypt")

        # Extract components
        salt = encrypted_data[:32]
        nonce = encrypted_data[32:44]
        ciphertext = encrypted_data[44:]

        # Derive key from password
        key, _ = KeyDerivation.stretch_password(password, salt)

        # Decrypt
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, b"")
