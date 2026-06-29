"""
Tests for Tessera validation and error handling.
"""

import unittest
import base64
from tessera.utils.validation import InputValidator
from tessera.utils.exceptions import ValidationError, ProofError, EncryptionError
from tessera.crypto.crypto_utils import SecureEncryption, ZKProver, ZKVerifier
from tessera.sdk import Sender


class TestInputValidator(unittest.TestCase):
    """Test input validation functionality."""

    def test_validate_phone_number_valid(self):
        """Test valid phone number validation."""
        valid_phones = ["+1234567890", "+44123456789", "1234567890"]
        for phone in valid_phones:
            result = InputValidator.validate_phone_number(phone)
            self.assertEqual(result, phone)

    def test_validate_phone_number_invalid(self):
        """Test invalid phone number validation."""
        invalid_phones = [
            "",
            "abc",
            "123",
            "+",
            "phone",
            "++123456789",
            "123456",
        ]  # Too short
        for phone in invalid_phones:
            with self.assertRaises(ValidationError):
                InputValidator.validate_phone_number(phone)

    def test_validate_public_key_bytes(self):
        """Test public key validation with bytes."""
        # Valid 64-byte key
        valid_key = b"x" * 64
        result = InputValidator.validate_public_key(valid_key)
        self.assertEqual(result, valid_key)

        # Valid 33-byte key (compressed)
        valid_key_compressed = b"x" * 33
        result = InputValidator.validate_public_key(valid_key_compressed)
        self.assertEqual(result, valid_key_compressed)

    def test_validate_public_key_hex(self):
        """Test public key validation with hex string."""
        hex_key = "a" * 128  # 64 bytes in hex
        result = InputValidator.validate_public_key(hex_key)
        self.assertEqual(len(result), 64)

    def test_validate_public_key_invalid(self):
        """Test invalid public key validation."""
        invalid_keys = [
            b"x" * 32,  # Too short
            b"x" * 100,  # Too long
            "invalid_hex",  # Invalid hex
            123,  # Wrong type
        ]
        for key in invalid_keys:
            with self.assertRaises(ValidationError):
                InputValidator.validate_public_key(key)

    def test_validate_session_id_valid(self):
        """Test valid session ID validation."""
        valid_ids = ["session123", "test_session", "a" * 8, "a" * 64, "session-id"]
        for session_id in valid_ids:
            result = InputValidator.validate_session_id(session_id)
            self.assertEqual(result, session_id)

    def test_validate_session_id_invalid(self):
        """Test invalid session ID validation."""
        invalid_ids = ["", "a" * 7, "a" * 65, "session@id", "session id"]
        for session_id in invalid_ids:
            with self.assertRaises(ValidationError):
                InputValidator.validate_session_id(session_id)

    def test_validate_base64_valid(self):
        """Test valid base64 validation."""
        test_data = b"Hello, World!"
        b64_data = base64.b64encode(test_data).decode()
        result = InputValidator.validate_base64(b64_data)
        self.assertEqual(result, test_data)

    def test_validate_base64_invalid(self):
        """Test invalid base64 validation."""
        invalid_b64 = ["invalid!@#", "123", "not base64"]
        for data in invalid_b64:
            with self.assertRaises(ValidationError):
                InputValidator.validate_base64(data)

    def test_validate_metadata_valid(self):
        """Test valid metadata validation."""
        valid_metadata = {
            "timestamp": 1234567890,
            "call_type": "voice",
            "urgent": True,
            "message": "Test message",
        }
        result = InputValidator.validate_metadata(valid_metadata)
        self.assertEqual(result["timestamp"], 1234567890)
        self.assertEqual(result["call_type"], "voice")
        self.assertTrue(result["urgent"])

    def test_validate_metadata_invalid(self):
        """Test invalid metadata validation."""
        # Invalid call type
        with self.assertRaises(ValidationError):
            InputValidator.validate_metadata({"call_type": "invalid"})

        # Invalid timestamp
        with self.assertRaises(ValidationError):
            InputValidator.validate_metadata({"timestamp": -1})

        # Message too long
        with self.assertRaises(ValidationError):
            InputValidator.validate_metadata({"message": "x" * 1001})

    def test_sanitize_string_valid(self):
        """Test valid string sanitization."""
        test_string = "  Hello, World!  "
        result = InputValidator.sanitize_string(test_string)
        self.assertEqual(result, "Hello, World!")

    def test_sanitize_string_invalid(self):
        """Test string sanitization with invalid input."""
        # Too long
        with self.assertRaises(ValidationError):
            InputValidator.sanitize_string("x" * 1001)

        # Wrong type
        with self.assertRaises(ValidationError):
            InputValidator.sanitize_string(123)

    def test_validate_recipients_list_valid(self):
        """Test valid recipients list validation."""
        recipients = ["user1", "user2", "user3"]
        result = InputValidator.validate_recipients_list(recipients)
        self.assertEqual(result, recipients)

    def test_validate_recipients_list_invalid(self):
        """Test invalid recipients list validation."""
        # Too many recipients
        with self.assertRaises(ValidationError):
            InputValidator.validate_recipients_list(["user"] * 101)

        # Wrong type
        with self.assertRaises(ValidationError):
            InputValidator.validate_recipients_list("not a list")


class TestCryptoErrorHandling(unittest.TestCase):
    """Test error handling in crypto operations."""

    def test_secure_encryption_invalid_input(self):
        """Test SecureEncryption with invalid inputs."""
        key = b"x" * 32

        # Invalid plaintext type
        with self.assertRaises(EncryptionError):
            SecureEncryption.encrypt("not bytes", key)

        # Empty plaintext
        with self.assertRaises(EncryptionError):
            SecureEncryption.encrypt(b"", key)

        # Invalid key type
        with self.assertRaises(EncryptionError):
            SecureEncryption.encrypt(b"test", "not bytes")

    def test_secure_decryption_invalid_input(self):
        """Test SecureEncryption decryption with invalid inputs."""
        key = b"x" * 32

        # Invalid encrypted data type
        with self.assertRaises(EncryptionError):
            SecureEncryption.decrypt("not dict", key)

        # Missing required fields
        with self.assertRaises(EncryptionError):
            SecureEncryption.decrypt({}, key)

        # Invalid nonce length
        with self.assertRaises(EncryptionError):
            SecureEncryption.decrypt(
                {
                    "nonce": b"x" * 10,  # Wrong length
                    "ciphertext": b"test",
                },
                key,
            )

    def test_secure_encryption_authentication_failure(self):
        """Test authentication failure in decryption."""
        key = b"x" * 32
        plaintext = b"Hello, World!"

        encrypted = SecureEncryption.encrypt(plaintext, key)

        # Tamper with ciphertext
        encrypted["ciphertext"] = b"tampered" + encrypted["ciphertext"][8:]

        with self.assertRaises(EncryptionError) as context:
            SecureEncryption.decrypt(encrypted, key)

        self.assertIn("Authentication failed", str(context.exception))

    def test_zk_prover_invalid_input(self):
        """Test ZKProver with invalid inputs."""
        prover = ZKProver()

        # Invalid private key
        with self.assertRaises(ProofError):
            prover.generate_proof("not int", b"x" * 64)

        with self.assertRaises(ProofError):
            prover.generate_proof(-1, b"x" * 64)

        # Invalid public key - now wrapped in ProofError
        with self.assertRaises(ProofError):
            prover.generate_proof(12345, b"x" * 32)  # Wrong length

    def test_zk_verifier_invalid_proof(self):
        """Test ZKVerifier with invalid proof structure."""
        verifier = ZKVerifier()

        # Missing fields - now handled by returning False
        result = verifier.verify_proof({})
        self.assertFalse(result)

        # Invalid field types - now handled by returning False
        result = verifier.verify_proof(
            {"R": "not bytes", "s": 12345, "public_key": b"x" * 64}
        )
        self.assertFalse(result)


class TestIntegratedValidation(unittest.TestCase):
    """Test validation in integrated scenarios."""

    def test_sender_with_invalid_metadata(self):
        """Test Sender with invalid metadata."""
        sender = Sender()

        # Invalid metadata should raise ValidationError
        with self.assertRaises(ProofError):
            sender.generate_call_proof({"call_type": "invalid_type"})

    def test_end_to_end_validation(self):
        """Test end-to-end validation in normal flow."""
        sender = Sender()

        # Valid metadata should work
        valid_metadata = {
            "timestamp": 1234567890,
            "call_type": "voice",
            "urgent": False,
            "message": "Test call",
        }

        proof = sender.generate_call_proof(valid_metadata)
        self.assertIn("R", proof)
        self.assertIn("s", proof)
        self.assertIn("public_key", proof)

        # Validation should pass
        try:
            validated_proof = InputValidator.validate_proof_structure(proof)
            self.assertIsInstance(validated_proof, dict)
        except ValidationError:
            self.fail("Valid proof should pass validation")


if __name__ == "__main__":
    unittest.main()
