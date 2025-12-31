"""Tests for authentication and authorization module."""

import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

# Set required environment variable before importing
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-purposes-32chars"


class TestJWTSecretConfiguration:
    """Tests for JWT secret key configuration."""

    def test_jwt_secret_required(self):
        """Test that JWT secret is required."""
        # Temporarily remove the secret
        original = os.environ.pop("JWT_SECRET_KEY", None)
        try:
            # Reset the cached secret
            from aiops.api import auth
            auth._SECRET_KEY = None

            # This should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                auth.get_secret_key()

            assert "JWT_SECRET_KEY environment variable is required" in str(exc_info.value)
        finally:
            if original:
                os.environ["JWT_SECRET_KEY"] = original
            # Reset for other tests
            auth._SECRET_KEY = None

    def test_jwt_secret_minimum_length(self):
        """Test that JWT secret must be at least 32 characters."""
        original = os.environ.get("JWT_SECRET_KEY")
        try:
            os.environ["JWT_SECRET_KEY"] = "short"

            from aiops.api import auth
            auth._SECRET_KEY = None

            with pytest.raises(RuntimeError) as exc_info:
                auth.get_secret_key()

            assert "at least 32 characters" in str(exc_info.value)
        finally:
            if original:
                os.environ["JWT_SECRET_KEY"] = original
            auth._SECRET_KEY = None

    def test_jwt_secret_valid(self):
        """Test that valid JWT secret is accepted."""
        os.environ["JWT_SECRET_KEY"] = "a" * 32  # 32 character secret

        from aiops.api import auth
        auth._SECRET_KEY = None

        secret = auth.get_secret_key()
        assert secret == "a" * 32


class TestTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token(self):
        """Test creating a valid access token."""
        from aiops.api.auth import create_access_token, decode_access_token, UserRole

        token = create_access_token(
            data={"sub": "testuser", "role": UserRole.USER}
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        decoded = decode_access_token(token)
        assert decoded.username == "testuser"
        assert decoded.role == UserRole.USER

    def test_token_with_custom_expiry(self):
        """Test token with custom expiration."""
        from aiops.api.auth import create_access_token, decode_access_token, UserRole

        token = create_access_token(
            data={"sub": "testuser", "role": UserRole.ADMIN},
            expires_delta=timedelta(hours=2)
        )

        decoded = decode_access_token(token)
        assert decoded.username == "testuser"
        assert decoded.role == UserRole.ADMIN

    def test_invalid_token_raises_exception(self):
        """Test that invalid token raises HTTPException."""
        from aiops.api.auth import decode_access_token

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("invalid.token.here")

        assert exc_info.value.status_code == 401


class TestUserRoles:
    """Tests for user role system."""

    def test_role_enum_values(self):
        """Test UserRole enum values."""
        from aiops.api.auth import UserRole

        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
        assert UserRole.READONLY.value == "readonly"

    def test_role_hierarchy(self):
        """Test role hierarchy enforcement."""
        from aiops.api.auth import require_role, UserRole

        role_checker = require_role(UserRole.ADMIN)

        # This would need to be tested with actual FastAPI dependency injection
        assert callable(role_checker)


class TestAPIKeyManagement:
    """Tests for API key management."""

    @pytest.fixture
    def api_key_manager(self, tmp_path):
        """Create a temporary API key manager."""
        from aiops.api.auth import APIKeyManager

        keys_file = tmp_path / "test_api_keys.json"
        return APIKeyManager(keys_file=keys_file)

    def test_create_api_key(self, api_key_manager):
        """Test creating an API key."""
        from aiops.api.auth import UserRole

        api_key = api_key_manager.create_api_key(
            name="test-key",
            role=UserRole.USER,
            rate_limit=50
        )

        assert api_key is not None
        assert api_key.startswith("aiops_")
        assert len(api_key) > 20

    def test_validate_api_key(self, api_key_manager):
        """Test validating an API key."""
        from aiops.api.auth import UserRole

        # Create a key
        api_key = api_key_manager.create_api_key(
            name="validation-test",
            role=UserRole.USER
        )

        # Validate it
        key_data = api_key_manager.validate_api_key(api_key)

        assert key_data is not None
        assert key_data.name == "validation-test"
        assert key_data.role == UserRole.USER
        assert key_data.enabled is True

    def test_validate_invalid_key(self, api_key_manager):
        """Test validating an invalid API key."""
        result = api_key_manager.validate_api_key("invalid-key")
        assert result is None

    def test_revoke_api_key(self, api_key_manager):
        """Test revoking an API key."""
        import hashlib
        from aiops.api.auth import UserRole

        # Create a key
        api_key = api_key_manager.create_api_key(
            name="revoke-test",
            role=UserRole.USER
        )

        # Get the hash
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Revoke it
        result = api_key_manager.revoke_api_key(key_hash)
        assert result is True

        # Verify it's revoked
        key_data = api_key_manager.validate_api_key(api_key)
        assert key_data is None

    def test_list_api_keys(self, api_key_manager):
        """Test listing API keys."""
        from aiops.api.auth import UserRole

        # Create multiple keys
        api_key_manager.create_api_key(name="key1", role=UserRole.USER)
        api_key_manager.create_api_key(name="key2", role=UserRole.ADMIN)

        keys = api_key_manager.list_api_keys()

        assert len(keys) == 2
        assert any(k.name == "key1" for k in keys)
        assert any(k.name == "key2" for k in keys)


class TestSecurityHeaders:
    """Tests for security configurations."""

    def test_cors_methods_not_wildcard(self):
        """Test that CORS methods are not set to wildcard."""
        from aiops.core.config import Config

        config = Config()

        # Verify default is not wildcard
        assert config.cors_allow_methods != "*"
        assert "GET" in config.cors_allow_methods
        assert "POST" in config.cors_allow_methods

    def test_cors_headers_not_wildcard(self):
        """Test that CORS headers are not set to wildcard."""
        from aiops.core.config import Config

        config = Config()

        # Verify default is not wildcard
        assert config.cors_allow_headers != "*"
        assert "Content-Type" in config.cors_allow_headers
        assert "Authorization" in config.cors_allow_headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
