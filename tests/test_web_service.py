"""
Tests for CallDNS web service components.
"""

import unittest
import json
import base64
from calldns.service.web import CallDNSService
from calldns.sdk import Caller


def proof_to_json_serializable(proof):
    """Convert proof with bytes to JSON serializable format."""
    serializable_proof = {}
    for key, value in proof.items():
        if isinstance(value, bytes):
            serializable_proof[key] = base64.b64encode(value).decode('utf-8')
        else:
            serializable_proof[key] = value
    return serializable_proof


def json_serializable_to_proof(serializable_proof):
    """Convert JSON serializable proof back to proof with bytes."""
    proof = {}
    for key, value in serializable_proof.items():
        if key in ['R', 'public_key'] and isinstance(value, str):
            proof[key] = base64.b64decode(value)
        else:
            proof[key] = value
    return proof


class TestWebService(unittest.TestCase):
    """Test web service functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = CallDNSService()
        self.app = self.service.app.test_client()
        self.app.testing = True

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'CallDNS')
        self.assertIn('timestamp', data)

    def test_register_commitment(self):
        """Test commitment registration."""
        payload = {
            'session_id': 'test_session_123',
            'public_key': 'test_public_key'
        }

        response = self.app.post('/commitments/register',
                               data=json.dumps(payload),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'commitment_registered')
        self.assertIn('commitment_id', data)
        self.assertEqual(data['session_id'], 'test_session_123')

    def test_lookup_commitment(self):
        """Test commitment lookup."""
        # First register a commitment
        payload = {
            'session_id': 'test_session_lookup',
            'public_key': 'test_key'
        }

        reg_response = self.app.post('/commitments/register',
                                   data=json.dumps(payload),
                                   content_type='application/json')
        reg_data = json.loads(reg_response.data)
        commitment_id = reg_data['commitment_id']

        # Now lookup the commitment
        response = self.app.get(f'/commitments/lookup/{commitment_id}')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'found')
        self.assertEqual(data['commitment_id'], commitment_id)
        self.assertEqual(data['session_id'], 'test_session_lookup')

    def test_lookup_nonexistent_commitment(self):
        """Test lookup of non-existent commitment."""
        response = self.app.get('/commitments/lookup/nonexistent')
        self.assertEqual(response.status_code, 404)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'not_found')

    def test_verify_proof(self):
        """Test proof verification endpoint."""
        # Generate a valid proof
        caller = Caller()
        proof = caller.generate_call_proof({'test': 'data'})

        # Convert to JSON serializable format
        serializable_proof = proof_to_json_serializable(proof)
        payload = {'proof': serializable_proof}

        response = self.app.post('/proofs/verify',
                               data=json.dumps(payload),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'verified')
        self.assertTrue(data['valid'])

    def test_verify_invalid_proof(self):
        """Test verification of invalid proof."""
        invalid_proof = {
            'R': base64.b64encode(b'invalid').decode('utf-8'),
            's': 12345,
            'public_key': base64.b64encode(b'invalid').decode('utf-8')
        }

        payload = {'proof': invalid_proof}

        response = self.app.post('/proofs/verify',
                               data=json.dumps(payload),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'verified')
        self.assertFalse(data['valid'])

    def test_broadcast_proof(self):
        """Test proof broadcasting endpoint."""
        # Generate a valid proof
        caller = Caller()
        proof = caller.generate_call_proof({'test': 'broadcast'})

        # Convert to JSON serializable format
        serializable_proof = proof_to_json_serializable(proof)
        payload = {
            'proof': serializable_proof,
            'recipients': ['recipient1', 'recipient2'],
            'metadata': {'routing_hint': 'test'}
        }

        response = self.app.post('/proofs/broadcast',
                               data=json.dumps(payload),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'proof_broadcasted')
        self.assertIn('proof_id', data)
        self.assertEqual(data['recipients'], 2)

    def test_get_stats(self):
        """Test statistics endpoint."""
        response = self.app.get('/stats')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('stats', data)
        self.assertIn('active_commitments', data['stats'])
        self.assertIn('total_verified_proofs', data['stats'])

    def test_get_recent_proofs(self):
        """Test recent proofs endpoint."""
        response = self.app.get('/proofs/recent')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('recent_proofs', data)
        self.assertIn('count', data)

    def test_invalid_request_handling(self):
        """Test handling of invalid requests."""
        # Test missing data
        response = self.app.post('/proofs/verify',
                               data=json.dumps({}),
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)

        # Test missing session_id for commitment
        response = self.app.post('/commitments/register',
                               data=json.dumps({}),
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()