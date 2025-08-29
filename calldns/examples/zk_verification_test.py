"""
Test to verify ZK proof verification works correctly.
"""

from calldns.crypto.crypto_utils import CryptoUtils, ZKProver, ZKVerifier


def test_zk_verification():
    """Test that ZK proof verification works correctly."""
    print("Testing ZK Proof Verification")
    print("=" * 30)
    
    # Generate a key pair
    private_int, public_bytes, private_obj = CryptoUtils.generate_keypair()
    print(f"Generated key pair")
    
    # Create prover and verifier
    prover = ZKProver()
    verifier = ZKVerifier()
    
    # Generate a valid proof
    metadata = "test_call"
    valid_proof = prover.generate_proof(private_int, public_bytes, metadata)
    print(f"Generated valid proof with R: {valid_proof['R'][:8].hex()}...")
    
    # Verify the valid proof
    is_valid = verifier.verify_proof(valid_proof)
    print(f"Valid proof verification: {'✓ PASS' if is_valid else '✗ FAIL'}")
    
    # Create an invalid proof by tampering with the valid one
    invalid_proof = valid_proof.copy()
    invalid_proof['s'] = invalid_proof['s'] + 1  # Tamper with the signature
    
    # Verify the invalid proof
    is_invalid = verifier.verify_proof(invalid_proof)
    print(f"Invalid proof verification: {'✓ PASS (correctly rejected)' if not is_invalid else '✗ FAIL (incorrectly accepted)'}")
    
    # Test with wrong public key - create a proof with a different key
    wrong_private, wrong_public, _ = CryptoUtils.generate_keypair()
    wrong_proof = prover.generate_proof(wrong_private, wrong_public, metadata)
    
    # This should be valid since it's correctly signed with the wrong key
    is_wrong_valid = verifier.verify_proof(wrong_proof)
    print(f"Wrong key proof verification: {'✓ PASS (correctly signed)' if is_wrong_valid else '✗ FAIL'}")
    
    print("\nTest Summary:")
    print(f"- Valid proof correctly verified: {'PASS' if is_valid else 'FAIL'}")
    print(f"- Invalid proof correctly rejected: {'PASS' if not is_invalid else 'FAIL'}")
    print(f"- Wrong key proof correctly verified: {'PASS' if is_wrong_valid else 'FAIL'}")
    
    # Final verification that our ZK implementation is working
    if is_valid and not is_invalid:
        print("\n🎉 ZK PROOF IMPLEMENTATION IS WORKING CORRECTLY! 🎉")
    else:
        print("\n❌ ZK PROOF IMPLEMENTATION HAS ISSUES! ❌")


if __name__ == "__main__":
    test_zk_verification()