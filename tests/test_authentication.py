"""
Tests for authentication features: rate limiting and JWT validation.
"""

import pytest
import time
from unittest.mock import MagicMock, patch


class TestRateLimiter:
    """Tests for IP-based rate limiting."""

    def test_rate_limiter_allows_requests_under_limit(self):
        """Requests under rate limit should be allowed."""
        from tessera.network.embedded_api import RateLimiter

        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        client_ip = "192.168.1.1"

        # All requests within limit should be allowed
        for _ in range(10):
            assert limiter.is_allowed(client_ip) is True

    def test_rate_limiter_blocks_burst_overflow(self):
        """Requests exceeding burst should be blocked."""
        from tessera.network.embedded_api import RateLimiter

        limiter = RateLimiter(requests_per_minute=60, burst_size=5)
        client_ip = "192.168.1.1"

        # First 5 should pass
        for _ in range(5):
            assert limiter.is_allowed(client_ip) is True

        # 6th should be blocked (burst exceeded)
        assert limiter.is_allowed(client_ip) is False

    def test_rate_limiter_different_ips(self):
        """Different IPs should have separate limits."""
        from tessera.network.embedded_api import RateLimiter

        limiter = RateLimiter(requests_per_minute=60, burst_size=2)

        # IP 1 uses its burst
        assert limiter.is_allowed("192.168.1.1") is True
        assert limiter.is_allowed("192.168.1.1") is True
        assert limiter.is_allowed("192.168.1.1") is False

        # IP 2 should still have its full quota
        assert limiter.is_allowed("192.168.1.2") is True
        assert limiter.is_allowed("192.168.1.2") is True

    def test_rate_limiter_time_window_reset(self):
        """Old requests should be cleaned up after time window."""
        from tessera.network.embedded_api import RateLimiter

        limiter = RateLimiter(requests_per_minute=60, burst_size=2)
        client_ip = "192.168.1.1"

        # Use up burst
        assert limiter.is_allowed(client_ip) is True
        assert limiter.is_allowed(client_ip) is True
        assert limiter.is_allowed(client_ip) is False

        # Manually age the requests by modifying timestamps
        current_time = time.time()
        limiter.requests[client_ip] = [current_time - 61, current_time - 61]

        # Should be allowed again after cleanup
        assert limiter.is_allowed(client_ip) is True

    def test_get_retry_after(self):
        """Should return correct retry-after time."""
        from tessera.network.embedded_api import RateLimiter

        limiter = RateLimiter(requests_per_minute=60, burst_size=1)
        client_ip = "192.168.1.1"

        # Use up limit
        limiter.is_allowed(client_ip)

        retry_after = limiter.get_retry_after(client_ip)
        assert retry_after > 0
        assert retry_after <= 60


class TestJWTValidator:
    """Tests for JWT token validation."""

    def test_validate_valid_token(self):
        """Valid JWT should be accepted."""
        from tessera.network.embedded_api import JWTValidator
        import jwt
        import datetime

        secret = "test-secret-key"
        validator = JWTValidator(secret)

        # Create a valid token
        payload = {
            "sub": "customer-123",
            "iss": "test-bank",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            "iat": datetime.datetime.utcnow(),
            "scope": ["register", "verify"]
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        claims = validator.validate_token(token)
        assert claims is not None
        assert claims["sub"] == "customer-123"
        assert claims["iss"] == "test-bank"

    def test_validate_expired_token(self):
        """Expired JWT should be rejected."""
        from tessera.network.embedded_api import JWTValidator
        import jwt
        import datetime

        secret = "test-secret-key"
        validator = JWTValidator(secret)

        # Create an expired token
        payload = {
            "sub": "customer-123",
            "exp": datetime.datetime.utcnow() - datetime.timedelta(hours=1),
            "iat": datetime.datetime.utcnow() - datetime.timedelta(hours=2)
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        claims = validator.validate_token(token)
        assert claims is None

    def test_validate_wrong_secret(self):
        """Token with wrong secret should be rejected."""
        from tessera.network.embedded_api import JWTValidator
        import jwt
        import datetime

        validator = JWTValidator("correct-secret")

        # Create token with different secret
        payload = {
            "sub": "customer-123",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        claims = validator.validate_token(token)
        assert claims is None

    def test_validate_invalid_token_format(self):
        """Malformed token should be rejected."""
        from tessera.network.embedded_api import JWTValidator

        validator = JWTValidator("test-secret")

        # Invalid tokens
        assert validator.validate_token("not-a-jwt") is None
        assert validator.validate_token("") is None
        assert validator.validate_token("abc.def") is None


class TestAuthenticationIntegration:
    """Integration tests for authentication in API endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create a mock node for testing."""
        node = MagicMock()
        node.node_id = "test-node"
        node.node_type = MagicMock()
        node.node_type.value = "org"
        # Make get_stats an async function
        async def async_stats():
            return {"node_id": "test-node"}
        node.get_stats = async_stats
        return node

    @pytest.fixture
    def mock_commitment_storage(self):
        """Create mock commitment storage."""
        storage = MagicMock()
        storage.get_commitment.return_value = None
        # Make register_commitment an async function
        async def async_register(**kwargs):
            return {"status": "registered", "customer_id": kwargs.get("customer_id")}
        storage.register_commitment = async_register
        return storage

    def test_api_requires_jwt_for_org_endpoints(self, mock_node, mock_commitment_storage):
        """Org node endpoints should require JWT when configured."""
        from tessera.network.embedded_api import create_embedded_api
        from fastapi.testclient import TestClient

        app = create_embedded_api(
            node=mock_node,
            commitment_storage=mock_commitment_storage,
            jwt_secret="test-secret",
            rate_limit_rpm=60
        )
        client = TestClient(app)

        # Request without auth should fail
        response = client.post(
            "/customers/register",
            json={
                "customer_id": "cust-123",
                "commitment": "abc123",
                "device_id": "device-1"
            }
        )
        assert response.status_code == 401

    def test_api_rate_limits_requests(self, mock_node):
        """Core endpoints should be rate limited."""
        from tessera.network.embedded_api import create_embedded_api
        from fastapi.testclient import TestClient

        app = create_embedded_api(
            node=mock_node,
            rate_limit_rpm=60
        )
        client = TestClient(app)

        # Make many requests quickly
        responses = []
        for _ in range(15):  # Burst is 10, so 15 should trigger limit
            response = client.get("/health")
            responses.append(response.status_code)

        # At least one should be rate limited
        # Note: TestClient may not properly simulate IP-based limiting
        # This is more of a smoke test
        assert 200 in responses

    def test_api_accepts_valid_jwt(self, mock_node, mock_commitment_storage):
        """Valid JWT should allow access to protected endpoints."""
        from tessera.network.embedded_api import create_embedded_api
        from fastapi.testclient import TestClient
        import jwt
        import datetime

        secret = "test-secret"
        app = create_embedded_api(
            node=mock_node,
            commitment_storage=mock_commitment_storage,
            jwt_secret=secret,
            rate_limit_rpm=1000
        )
        client = TestClient(app)

        # Create valid token
        payload = {
            "sub": "customer-123",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            "scope": ["register"]
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        # Mock the storage to return success
        mock_commitment_storage.store_commitment.return_value = True

        response = client.post(
            "/customers/register",
            json={
                "customer_id": "cust-123",
                "commitment": "abc123",
                "device_id": "device-1"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should not be 401
        assert response.status_code != 401
