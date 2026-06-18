"""
Cryptographic utilities for Tessera.
Implements Schnorr-based zero-knowledge proofs for fast verification using ECDSA library.
Includes secure AEAD encryption for proof routing.
"""

import hashlib
import secrets
import ecdsa
from ecdsa import SECP256k1
from ecdsa.util import sigencode_string, sigdecode_string
from ecdsa.curves import Curve
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from ..utils.exceptions import ProofError, EncryptionError
from ..utils.validation import InputValidator


class CryptoUtils:
    """Utility class for cryptographic operations."""
    
    @staticmethod
    def generate_keypair():
        """Generate a key pair using SECP256k1."""
        private_key = ecdsa.SigningKey.generate(curve=SECP256k1)
        public_key = private_key.get_verifying_key()
        
        # Get private key value as integer
        private_int = int.from_bytes(private_key.to_string(), 'big')
        public_bytes = public_key.to_string()
        
        return private_int, public_bytes, private_key
    
    @staticmethod
    def hash_data(*args):
        """Hash multiple data elements together."""
        hasher = hashlib.sha256()
        for data in args:
            if isinstance(data, str):
                hasher.update(data.encode('utf-8'))
            elif isinstance(data, bytes):
                hasher.update(data)
            elif isinstance(data, int):
                hasher.update(data.to_bytes(32, byteorder='big'))
            else:
                hasher.update(str(data).encode('utf-8'))
        return hasher.digest()


class ZKProver:
    """Implements Schnorr-based zero-knowledge proof generation."""
    
    def __init__(self):
        self.curve = SECP256k1
        self.order = SECP256k1.order
    
    def generate_proof(self, private_key_int, public_key_bytes, metadata=None):
        """
        Generate a Schnorr zero-knowledge proof.

        Args:
            private_key_int: The private key (integer)
            public_key_bytes: The public key (bytes)
            metadata: Optional metadata to include in the proof

        Returns:
            dict: The ZK proof containing R and s

        Raises:
            ProofError: If proof generation fails
        """
        try:
            # Validate inputs
            if not isinstance(private_key_int, int) or private_key_int <= 0:
                raise ProofError("Invalid private key: must be positive integer", "generation")

            if private_key_int >= self.order:
                raise ProofError("Private key out of valid range", "generation")

            public_key_bytes = InputValidator.validate_public_key(public_key_bytes)

            if metadata is not None:
                metadata = InputValidator.validate_metadata(metadata)

            # Generate random nonce
            r = secrets.randbelow(self.order)

            # Create ephemeral point for R = g^r
            R_point = self.curve.generator * r
            R = R_point.to_bytes()

            # Compute challenge c = H(R || Y || metadata)
            c_hash = CryptoUtils.hash_data(R, public_key_bytes, metadata or "")
            # Convert hash to integer mod order
            c = int.from_bytes(c_hash, byteorder='big') % self.order

            # Compute response s = r + c*x mod q
            s = (r + c * private_key_int) % self.order

            return {
                'R': R,
                's': s,
                'public_key': public_key_bytes,
                'metadata': metadata
            }

        except Exception as e:
            if isinstance(e, ProofError):
                raise
            raise ProofError(f"Proof generation failed: {e}", "generation")


class ZKVerifier:
    """Implements Schnorr-based zero-knowledge proof verification."""
    
    def __init__(self):
        self.curve = SECP256k1
        self.order = SECP256k1.order
    
    def verify_proof(self, proof):
        """
        Verify a Schnorr zero-knowledge proof.

        Args:
            proof: The proof dictionary containing R, s, and public_key

        Returns:
            bool: True if proof is valid, False otherwise

        Raises:
            ProofError: If proof verification encounters critical errors
        """
        try:
            # Validate proof structure
            validated_proof = InputValidator.validate_proof_structure(proof)

            R = validated_proof['R']
            s = validated_proof['s']
            Y = validated_proof['public_key']
            metadata = validated_proof.get('metadata', "")

            # Additional validation for elliptic curve operations
            # Support both 64-byte and 65-byte formats
            if len(R) not in [64, 65]:
                return False

            if len(Y) not in [64, 65]:  # Support both formats
                return False

            # Deserialize points with error handling
            try:
                if len(R) == 65:  # Uncompressed with prefix
                    R_point = ecdsa.ellipticcurve.Point(
                        self.curve.curve,
                        int.from_bytes(R[1:33], 'big'),  # Skip prefix byte
                        int.from_bytes(R[33:], 'big')
                    )
                else:  # 64-byte format
                    R_point = ecdsa.ellipticcurve.Point(
                        self.curve.curve,
                        int.from_bytes(R[:32], 'big'),
                        int.from_bytes(R[32:], 'big')
                    )

                if len(Y) == 65:  # Uncompressed with prefix
                    Y_point = ecdsa.ellipticcurve.Point(
                        self.curve.curve,
                        int.from_bytes(Y[1:33], 'big'),
                        int.from_bytes(Y[33:], 'big')
                    )
                else:  # 64-byte format
                    Y_point = ecdsa.ellipticcurve.Point(
                        self.curve.curve,
                        int.from_bytes(Y[:32], 'big'),
                        int.from_bytes(Y[32:], 'big')
                    )
            except Exception:
                # Invalid point coordinates
                return False

            # Validate scalar s is in valid range
            if s <= 0 or s >= self.order:
                return False

            # Compute challenge c = H(R || Y || metadata)
            c_hash = CryptoUtils.hash_data(R, Y, metadata or "")
            c = int.from_bytes(c_hash, byteorder='big') % self.order

            # Compute g^s
            gs_point = self.curve.generator * s

            # Compute Y^c
            Yc_point = Y_point * c

            # Compute R' = g^s * Y^(-c)
            # Y^(-c) is the negation of Y^c
            Y_neg_c_point = ecdsa.ellipticcurve.Point(
                self.curve.curve,
                Yc_point.x(),
                -Yc_point.y() % self.curve.curve.p()
            )

            # R' = g^s * Y^(-c)
            Rp_point = gs_point + Y_neg_c_point

            # Check if R == R'
            return R_point.x() == Rp_point.x() and R_point.y() == Rp_point.y()

        except Exception as e:
            # Log critical verification errors for debugging
            if "validation" in str(e).lower():
                raise ProofError(f"Proof validation failed: {e}", "verification")
            # Return False for mathematical verification failures
            return False


class SecureEncryption:
    """Secure AEAD encryption for proof routing using AES-GCM."""

    @staticmethod
    def encrypt(plaintext: bytes, key: bytes, additional_data: bytes = b"") -> dict:
        """
        Encrypt data using AES-GCM (Authenticated Encryption with Associated Data).

        Args:
            plaintext: Data to encrypt
            key: 32-byte encryption key
            additional_data: Additional authenticated data (not encrypted)

        Returns:
            dict: Contains nonce, ciphertext, and tag

        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Validate inputs
            if not isinstance(plaintext, bytes):
                raise EncryptionError("Plaintext must be bytes", "validation")

            if not isinstance(key, bytes):
                raise EncryptionError("Key must be bytes", "validation")

            if not isinstance(additional_data, bytes):
                raise EncryptionError("Additional data must be bytes", "validation")

            if len(plaintext) == 0:
                raise EncryptionError("Plaintext cannot be empty", "validation")

            if len(plaintext) > 10 * 1024 * 1024:  # 10MB limit
                raise EncryptionError("Plaintext too large (max 10MB)", "validation")

            # Ensure key is exactly 32 bytes for AES-256
            if len(key) != 32:
                key = hashlib.sha256(key).digest()

            # Generate random 12-byte nonce for GCM
            nonce = secrets.token_bytes(12)

            # Create AES-GCM cipher
            aesgcm = AESGCM(key)

            # Encrypt and authenticate
            ciphertext = aesgcm.encrypt(nonce, plaintext, additional_data)

            return {
                'nonce': nonce,
                'ciphertext': ciphertext,
                'additional_data': additional_data
            }

        except Exception as e:
            if isinstance(e, EncryptionError):
                raise
            raise EncryptionError(f"Encryption failed: {e}", "encrypt")

    @staticmethod
    def decrypt(encrypted_data: dict, key: bytes) -> bytes:
        """
        Decrypt data using AES-GCM.

        Args:
            encrypted_data: Dictionary containing nonce, ciphertext, and additional_data
            key: 32-byte decryption key

        Returns:
            bytes: Decrypted plaintext

        Raises:
            EncryptionError: If decryption fails or authentication fails
        """
        try:
            # Validate inputs
            if not isinstance(encrypted_data, dict):
                raise EncryptionError("Encrypted data must be a dictionary", "validation")

            if not isinstance(key, bytes):
                raise EncryptionError("Key must be bytes", "validation")

            required_fields = ['nonce', 'ciphertext']
            for field in required_fields:
                if field not in encrypted_data:
                    raise EncryptionError(f"Missing required field: {field}", "validation")

            nonce = encrypted_data['nonce']
            ciphertext = encrypted_data['ciphertext']
            additional_data = encrypted_data.get('additional_data', b"")

            # Validate field types
            if not isinstance(nonce, bytes):
                raise EncryptionError("Nonce must be bytes", "validation")

            if not isinstance(ciphertext, bytes):
                raise EncryptionError("Ciphertext must be bytes", "validation")

            if not isinstance(additional_data, bytes):
                raise EncryptionError("Additional data must be bytes", "validation")

            # Validate nonce length for GCM
            if len(nonce) != 12:
                raise EncryptionError(f"Invalid nonce length: {len(nonce)} (expected 12)", "validation")

            if len(ciphertext) == 0:
                raise EncryptionError("Ciphertext cannot be empty", "validation")

            # Ensure key is exactly 32 bytes for AES-256
            if len(key) != 32:
                key = hashlib.sha256(key).digest()

            # Create AES-GCM cipher
            aesgcm = AESGCM(key)

            # Decrypt and verify authentication
            plaintext = aesgcm.decrypt(nonce, ciphertext, additional_data)

            return plaintext

        except InvalidTag:
            raise EncryptionError("Authentication failed: data may have been tampered with", "decrypt")
        except Exception as e:
            if isinstance(e, EncryptionError):
                raise
            raise EncryptionError(f"Decryption failed: {e}", "decrypt")