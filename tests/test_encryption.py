"""
Tests for Tessera secure encryption components.
"""

import unittest
import secrets
from tessera.crypto.crypto_utils import SecureEncryption
from tessera.utils.exceptions import EncryptionError


class TestSecureEncryption(unittest.TestCase):
    """Test secure encryption functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.key = secrets.token_bytes(32)
        self.plaintext = b"This is a test message for encryption"
        self.aad = b"additional_authenticated_data"

    def test_encrypt_decrypt_basic(self):
        """Test basic encryption and decryption."""
        # Encrypt
        encrypted_data = SecureEncryption.encrypt(self.plaintext, self.key, self.aad)

        # Check encrypted data structure
        self.assertIn('nonce', encrypted_data)
        self.assertIn('ciphertext', encrypted_data)
        self.assertIn('additional_data', encrypted_data)

        # Decrypt
        decrypted = SecureEncryption.decrypt(encrypted_data, self.key)

        # Verify plaintext matches
        self.assertEqual(decrypted, self.plaintext)

    def test_encrypt_decrypt_without_aad(self):
        """Test encryption and decryption without additional authenticated data."""
        encrypted_data = SecureEncryption.encrypt(self.plaintext, self.key)
        decrypted = SecureEncryption.decrypt(encrypted_data, self.key)
        self.assertEqual(decrypted, self.plaintext)

    def test_authentication_failure_with_wrong_key(self):
        """Test that decryption fails with wrong key."""
        encrypted_data = SecureEncryption.encrypt(self.plaintext, self.key, self.aad)
        wrong_key = secrets.token_bytes(32)

        with self.assertRaises(EncryptionError):
            SecureEncryption.decrypt(encrypted_data, wrong_key)

    def test_authentication_failure_with_tampered_ciphertext(self):
        """Test that decryption fails with tampered ciphertext."""
        encrypted_data = SecureEncryption.encrypt(self.plaintext, self.key, self.aad)

        # Tamper with ciphertext
        tampered_ciphertext = bytearray(encrypted_data['ciphertext'])
        tampered_ciphertext[0] ^= 1  # Flip one bit
        encrypted_data['ciphertext'] = bytes(tampered_ciphertext)

        with self.assertRaises(EncryptionError):
            SecureEncryption.decrypt(encrypted_data, self.key)

    def test_authentication_failure_with_tampered_aad(self):
        """Test that decryption fails with tampered AAD."""
        encrypted_data = SecureEncryption.encrypt(self.plaintext, self.key, self.aad)

        # Tamper with AAD
        encrypted_data['additional_data'] = b"tampered_aad"

        with self.assertRaises(EncryptionError):
            SecureEncryption.decrypt(encrypted_data, self.key)

    def test_key_derivation_from_different_length(self):
        """Test that keys of different lengths are properly handled."""
        short_key = b"short"
        long_key = b"this_is_a_very_long_key_that_exceeds_32_bytes_significantly"

        # Both should work (keys are hashed to 32 bytes)
        encrypted_short = SecureEncryption.encrypt(self.plaintext, short_key)
        encrypted_long = SecureEncryption.encrypt(self.plaintext, long_key)

        decrypted_short = SecureEncryption.decrypt(encrypted_short, short_key)
        decrypted_long = SecureEncryption.decrypt(encrypted_long, long_key)

        self.assertEqual(decrypted_short, self.plaintext)
        self.assertEqual(decrypted_long, self.plaintext)

    def test_nonce_uniqueness(self):
        """Test that nonces are unique for each encryption."""
        encrypted1 = SecureEncryption.encrypt(self.plaintext, self.key)
        encrypted2 = SecureEncryption.encrypt(self.plaintext, self.key)

        # Nonces should be different
        self.assertNotEqual(encrypted1['nonce'], encrypted2['nonce'])

        # But both should decrypt to the same plaintext
        decrypted1 = SecureEncryption.decrypt(encrypted1, self.key)
        decrypted2 = SecureEncryption.decrypt(encrypted2, self.key)

        self.assertEqual(decrypted1, self.plaintext)
        self.assertEqual(decrypted2, self.plaintext)


if __name__ == "__main__":
    unittest.main()