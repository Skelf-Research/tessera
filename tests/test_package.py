"""
Test to verify the package structure works correctly.
"""

def test_package_imports():
    """Test that all package modules can be imported."""
    # Test core SDK imports
    from tessera import Sender, Verifier
    print("✓ Core SDK imports successful")

    # Test crypto imports
    from tessera.crypto import ZKProver, ZKVerifier
    print("✓ Crypto imports successful")

    # Test privacy imports
    from tessera.privacy import PrivacyPreserver
    print("✓ Privacy imports successful")

    # Test network imports
    from tessera.network import EnhancedBroadcast
    print("✓ Network imports successful")

    # Test module imports
    from tessera.sdk import IdentityManager, CommitmentManager, TrafficManager
    print("✓ SDK module imports successful")

    print("\n🎉 All package imports successful!")
    # Use assert instead of return for pytest compatibility
    assert True


def test_basic_functionality():
    """Test basic functionality."""
    from tessera import Sender, Verifier

    # Create sender and verifier
    sender = Sender()
    verifier = Verifier()

    # Generate and verify a proof
    proof = sender.generate_call_proof({"test": "functionality"})
    is_valid = verifier.verify_call_proof(proof)

    print("✓ Basic functionality test passed" if is_valid else "❌ Basic functionality test failed")
    # Use assert instead of return for pytest compatibility
    assert is_valid, "Basic functionality test should pass"


if __name__ == "__main__":
    print("Testing Tessera Package Structure")
    print("=" * 35)
    
    import_success = test_package_imports()
    functionality_success = test_basic_functionality()
    
    if import_success and functionality_success:
        print("\n🎉 Package structure is working correctly!")
    else:
        print("\n❌ Package structure has issues!")