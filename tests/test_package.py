"""
Test to verify the package structure works correctly.
"""

def test_package_imports():
    """Test that all package modules can be imported."""
    try:
        # Test core SDK imports
        from calldns import Caller, Verifier
        print("✓ Core SDK imports successful")
        
        # Test crypto imports
        from calldns.crypto import ZKProver, ZKVerifier
        print("✓ Crypto imports successful")
        
        # Test privacy imports
        from calldns.privacy import PrivacyPreserver
        print("✓ Privacy imports successful")
        
        # Test network imports
        from calldns.network import EnhancedBroadcast
        print("✓ Network imports successful")
        
        # Test module imports
        from calldns.sdk import IdentityManager, CommitmentManager, TrafficManager
        print("✓ SDK module imports successful")
        
        print("\n🎉 All package imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality."""
    try:
        from calldns import Caller, Verifier
        
        # Create caller and verifier
        caller = Caller()
        verifier = Verifier()
        
        # Generate and verify a proof
        proof = caller.generate_call_proof({"test": "functionality"})
        is_valid = verifier.verify_call_proof(proof)
        
        if is_valid:
            print("✓ Basic functionality test passed")
            return True
        else:
            print("❌ Basic functionality test failed")
            return False
            
    except Exception as e:
        print(f"❌ Functionality test error: {e}")
        return False


if __name__ == "__main__":
    print("Testing CallDNS Package Structure")
    print("=" * 35)
    
    import_success = test_package_imports()
    functionality_success = test_basic_functionality()
    
    if import_success and functionality_success:
        print("\n🎉 Package structure is working correctly!")
    else:
        print("\n❌ Package structure has issues!")