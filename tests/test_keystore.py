"""
Tests for Tessera key management system.
"""

import os
import tempfile
import unittest
from pathlib import Path

from tessera.keystore import KeyManager, KeyRotationManager, FileKeyStore, EncryptedKeyStore
from tessera.keystore.utils import KeyDerivation, KeyBackup
from tessera.utils.exceptions import IdentityError, EncryptionError


class TestKeyManager(unittest.TestCase):
    """Test key manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FileKeyStore(self.temp_dir)
        self.key_manager = KeyManager(self.storage)
        self.test_identity = "test_user_123"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_identity_keypair(self):
        """Test identity keypair generation."""
        private_key, public_key = self.key_manager.generate_identity_keypair(self.test_identity)

        self.assertIsInstance(private_key, bytes)
        self.assertIsInstance(public_key, bytes)
        self.assertEqual(len(private_key), 32)  # SECP256k1 private key
        self.assertEqual(len(public_key), 64)   # SECP256k1 public key

        # Verify key is stored
        self.assertTrue(self.key_manager.key_exists(self.test_identity))

    def test_get_identity_keys(self):
        """Test retrieving identity keys."""
        # Generate keys first
        orig_private, orig_public = self.key_manager.generate_identity_keypair(self.test_identity)

        # Retrieve keys
        retrieved_private, retrieved_public = self.key_manager.get_identity_keys(self.test_identity)

        self.assertEqual(orig_private, retrieved_private)
        self.assertEqual(orig_public, retrieved_public)

    def test_get_public_key_only(self):
        """Test retrieving only public key."""
        orig_private, orig_public = self.key_manager.generate_identity_keypair(self.test_identity)

        public_key = self.key_manager.get_public_key(self.test_identity)
        self.assertEqual(orig_public, public_key)

    def test_derive_encryption_key(self):
        """Test key derivation."""
        self.key_manager.generate_identity_keypair(self.test_identity)

        derived_key1 = self.key_manager.derive_encryption_key(self.test_identity, "proof_encryption")
        derived_key2 = self.key_manager.derive_encryption_key(self.test_identity, "storage")

        self.assertIsInstance(derived_key1, bytes)
        self.assertIsInstance(derived_key2, bytes)
        self.assertEqual(len(derived_key1), 32)
        self.assertEqual(len(derived_key2), 32)
        self.assertNotEqual(derived_key1, derived_key2)  # Different purposes should yield different keys

        # Same purpose should yield same key
        derived_key1_again = self.key_manager.derive_encryption_key(self.test_identity, "proof_encryption")
        self.assertEqual(derived_key1, derived_key1_again)

    def test_key_rotation(self):
        """Test key rotation."""
        # Generate initial keys
        old_private, old_public = self.key_manager.generate_identity_keypair(self.test_identity)

        # Rotate keys
        new_private, new_public = self.key_manager.rotate_keys(self.test_identity)

        self.assertNotEqual(old_private, new_private)
        self.assertNotEqual(old_public, new_public)

        # Verify new keys are active
        current_private, current_public = self.key_manager.get_identity_keys(self.test_identity)
        self.assertEqual(new_private, current_private)
        self.assertEqual(new_public, current_public)

    def test_list_identities(self):
        """Test listing identities."""
        identities = ["user1", "user2", "user3"]

        for identity in identities:
            self.key_manager.generate_identity_keypair(identity, {"test": f"metadata_{identity}"})

        listed_identities = self.key_manager.list_identities()
        self.assertEqual(len(listed_identities), 3)

        identity_ids = [identity['identity_id'] for identity in listed_identities]
        for identity in identities:
            self.assertIn(identity, identity_ids)

    def test_delete_identity(self):
        """Test identity deletion."""
        self.key_manager.generate_identity_keypair(self.test_identity)
        self.assertTrue(self.key_manager.key_exists(self.test_identity))

        # Delete identity
        result = self.key_manager.delete_identity(self.test_identity, force=True)
        self.assertTrue(result)
        self.assertFalse(self.key_manager.key_exists(self.test_identity))

    def test_duplicate_identity_error(self):
        """Test error when creating duplicate identity."""
        self.key_manager.generate_identity_keypair(self.test_identity)

        with self.assertRaises(IdentityError):
            self.key_manager.generate_identity_keypair(self.test_identity)

    def test_nonexistent_identity(self):
        """Test handling of nonexistent identity."""
        keys = self.key_manager.get_identity_keys("nonexistent")
        self.assertIsNone(keys)

        public_key = self.key_manager.get_public_key("nonexistent")
        self.assertIsNone(public_key)


class TestEncryptedKeyStore(unittest.TestCase):
    """Test encrypted key storage."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = EncryptedKeyStore(self.temp_dir)
        self.master_password = b"test_master_password"
        self.test_key_data = {
            'private_key': b'x' * 32,
            'public_key': b'y' * 64,
            'metadata': {'test': 'data'}
        }

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_store_and_load_encrypted_key(self):
        """Test storing and loading encrypted keys."""
        key_id = "test_key"

        # Store key
        result = self.storage.store_key(key_id, self.test_key_data, self.master_password)
        self.assertTrue(result)

        # Load key
        loaded_data = self.storage.load_key(key_id, self.master_password)
        self.assertEqual(loaded_data, self.test_key_data)

    def test_wrong_password(self):
        """Test loading with wrong password."""
        key_id = "test_key"

        # Store key
        self.storage.store_key(key_id, self.test_key_data, self.master_password)

        # Try to load with wrong password
        wrong_password = b"wrong_password"
        loaded_data = self.storage.load_key(key_id, wrong_password)
        self.assertIsNone(loaded_data)

    def test_key_exists(self):
        """Test key existence checking."""
        key_id = "test_key"

        self.assertFalse(self.storage.key_exists(key_id))

        self.storage.store_key(key_id, self.test_key_data, self.master_password)
        self.assertTrue(self.storage.key_exists(key_id))

    def test_delete_encrypted_key(self):
        """Test deleting encrypted keys."""
        key_id = "test_key"

        # Store and verify
        self.storage.store_key(key_id, self.test_key_data, self.master_password)
        self.assertTrue(self.storage.key_exists(key_id))

        # Delete and verify
        result = self.storage.delete_key(key_id)
        self.assertTrue(result)
        self.assertFalse(self.storage.key_exists(key_id))


class TestKeyRotationManager(unittest.TestCase):
    """Test key rotation management."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FileKeyStore(self.temp_dir)
        self.key_manager = KeyManager(self.storage)
        self.rotation_manager = KeyRotationManager(self.key_manager)
        self.test_identity = "test_user"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rotation_policy(self):
        """Test setting rotation policies."""
        self.key_manager.generate_identity_keypair(self.test_identity)

        # Set rotation policy
        self.rotation_manager.set_rotation_policy(self.test_identity, max_age_days=30, auto_rotate=True)

        # Check rotation status
        status = self.rotation_manager.get_rotation_status()
        self.assertIn(self.test_identity, status)
        self.assertEqual(status[self.test_identity]['max_age_days'], 30)
        self.assertTrue(status[self.test_identity]['auto_rotate'])

    def test_rotation_needed_check(self):
        """Test rotation needed check."""
        self.key_manager.generate_identity_keypair(self.test_identity)

        # Set policy for immediate rotation (0 days)
        self.rotation_manager.set_rotation_policy(self.test_identity, max_age_days=0)

        # Should need rotation
        needs_rotation = self.rotation_manager.check_rotation_needed(self.test_identity)
        self.assertTrue(needs_rotation)


class TestKeyDerivation(unittest.TestCase):
    """Test key derivation utilities."""

    def test_hkdf_derivation(self):
        """Test HKDF key derivation."""
        master_key = b'x' * 32
        purpose = "test_purpose"

        derived_key = KeyDerivation.derive_key_hkdf(master_key, purpose)

        self.assertIsInstance(derived_key, bytes)
        self.assertEqual(len(derived_key), 32)

        # Same inputs should yield same output
        derived_key2 = KeyDerivation.derive_key_hkdf(master_key, purpose)
        self.assertEqual(derived_key, derived_key2)

        # Different purpose should yield different output
        derived_key3 = KeyDerivation.derive_key_hkdf(master_key, "different_purpose")
        self.assertNotEqual(derived_key, derived_key3)

    def test_pbkdf2_derivation(self):
        """Test PBKDF2 key derivation."""
        password = b"test_password"
        salt = b"test_salt_16b"

        derived_key = KeyDerivation.derive_key_pbkdf2(password, salt, iterations=1000)

        self.assertIsInstance(derived_key, bytes)
        self.assertEqual(len(derived_key), 32)

    def test_password_stretching(self):
        """Test password stretching."""
        password = "user_password"

        stretched_key, salt = KeyDerivation.stretch_password(password)

        self.assertIsInstance(stretched_key, bytes)
        self.assertIsInstance(salt, bytes)
        self.assertEqual(len(stretched_key), 32)
        self.assertEqual(len(salt), 32)

        # Same password with same salt should yield same key
        stretched_key2, _ = KeyDerivation.stretch_password(password, salt)
        self.assertEqual(stretched_key, stretched_key2)


class TestKeyBackup(unittest.TestCase):
    """Test key backup functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = Path(self.temp_dir) / "backups"
        self.storage_dir = Path(self.temp_dir) / "storage"

        self.storage = FileKeyStore(str(self.storage_dir))
        self.key_manager = KeyManager(self.storage)
        self.backup = KeyBackup(str(self.backup_dir))

        # Create test identities
        self.identities = ["user1", "user2", "user3"]
        for identity in self.identities:
            self.key_manager.generate_identity_keypair(identity, {"test": f"metadata_{identity}"})

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_backup(self):
        """Test creating encrypted backup."""
        backup_password = "backup_password_123"

        backup_path = self.backup.create_backup(self.key_manager, backup_password)

        self.assertTrue(os.path.exists(backup_path))
        self.assertTrue(backup_path.endswith('.cbk'))

    def test_verify_backup(self):
        """Test backup verification."""
        backup_password = "backup_password_123"

        backup_path = self.backup.create_backup(self.key_manager, backup_password)
        info = self.backup.verify_backup(backup_path, backup_password)

        self.assertTrue(info['valid'])
        self.assertEqual(info['total_identities'], len(self.identities))
        self.assertEqual(set(info['identities']), set(self.identities))

    def test_restore_backup(self):
        """Test restoring from backup."""
        backup_password = "backup_password_123"

        # Create backup
        backup_path = self.backup.create_backup(self.key_manager, backup_password)

        # Create new key manager (simulate fresh install)
        new_storage_dir = Path(self.temp_dir) / "new_storage"
        new_storage = FileKeyStore(str(new_storage_dir))
        new_key_manager = KeyManager(new_storage)

        # Restore backup
        restored_identities = self.backup.restore_backup(
            backup_path, backup_password, new_key_manager
        )

        self.assertEqual(set(restored_identities), set(self.identities))

        # Verify restored keys work
        for identity in self.identities:
            keys = new_key_manager.get_identity_keys(identity)
            self.assertIsNotNone(keys)

    def test_list_backups(self):
        """Test listing backups."""
        backup_password = "backup_password_123"

        # Create multiple backups
        backup_path1 = self.backup.create_backup(self.key_manager, backup_password)
        backup_path2 = self.backup.create_backup(self.key_manager, backup_password, ["user1"])

        backups = self.backup.list_backups()
        self.assertEqual(len(backups), 2)

        backup_paths = [backup['path'] for backup in backups]
        self.assertIn(backup_path1, backup_paths)
        self.assertIn(backup_path2, backup_paths)


if __name__ == "__main__":
    unittest.main()