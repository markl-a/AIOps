"""Authentication and authorization for AIOps API."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import hashlib
from enum import Enum

from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from pydantic import BaseModel
import json
import os
from pathlib import Path

from aiops.core.logger import get_logger

logger = get_logger(__name__)

# Configuration
# JWT Secret MUST be set via environment variable (validated at startup)
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "JWT_SECRET_KEY environment variable must be set. "
        "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
API_KEYS_FILE = Path(os.getenv("API_KEYS_FILE", ".aiops_api_keys.json"))

# Security schemes
security_bearer = HTTPBearer(auto_error=False)
security_apikey = APIKeyHeader(name="X-API-Key", auto_error=False)


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class TokenData(BaseModel):
    """JWT token data."""
    username: str
    role: UserRole
    exp: datetime


class APIKey(BaseModel):
    """API Key model."""
    key_hash: str
    name: str
    role: UserRole
    created_at: datetime
    last_used: Optional[datetime] = None
    rate_limit: int = 100  # requests per minute
    enabled: bool = True


class APIKeyManager:
    """Manage API keys with file-based storage."""

    def __init__(self, keys_file: Path = API_KEYS_FILE):
        self.keys_file = keys_file
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Ensure the API keys file exists."""
        if not self.keys_file.exists():
            self.keys_file.write_text(json.dumps({}))
            logger.info(f"Created API keys file: {self.keys_file}")

    def _load_keys(self) -> Dict[str, Dict[str, Any]]:
        """Load API keys from file."""
        try:
            return json.loads(self.keys_file.read_text())
        except Exception as e:
            logger.error(f"Failed to load API keys: {e}")
            return {}

    def _save_keys(self, keys: Dict[str, Dict[str, Any]]):
        """Save API keys to file."""
        try:
            self.keys_file.write_text(json.dumps(keys, indent=2, default=str))
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")

    def create_api_key(self, name: str, role: UserRole = UserRole.USER, rate_limit: int = 100) -> str:
        """
        Create a new API key.

        Args:
            name: Descriptive name for the API key
            role: User role for RBAC
            rate_limit: Rate limit in requests per minute

        Returns:
            The generated API key (only shown once)
        """
        # Generate a secure random API key
        api_key = f"aiops_{secrets.token_urlsafe(32)}"

        # Hash the key for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Create API key record
        key_data = APIKey(
            key_hash=key_hash,
            name=name,
            role=role,
            created_at=datetime.utcnow(),
            rate_limit=rate_limit,
        )

        # Save to storage
        keys = self._load_keys()
        keys[key_hash] = key_data.model_dump()
        self._save_keys(keys)

        logger.info(f"Created API key: {name} (role: {role})")
        return api_key

    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """
        Validate an API key and return its data.

        Args:
            api_key: The API key to validate

        Returns:
            APIKey object if valid, None otherwise
        """
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Load keys and check
        keys = self._load_keys()
        key_data = keys.get(key_hash)

        if not key_data:
            return None

        api_key_obj = APIKey(**key_data)

        if not api_key_obj.enabled:
            logger.warning(f"Attempted use of disabled API key: {api_key_obj.name}")
            return None

        # Update last used timestamp
        api_key_obj.last_used = datetime.utcnow()
        keys[key_hash] = api_key_obj.model_dump()
        self._save_keys(keys)

        return api_key_obj

    def revoke_api_key(self, key_hash: str) -> bool:
        """
        Revoke an API key.

        Args:
            key_hash: Hash of the API key to revoke

        Returns:
            True if revoked, False if not found
        """
        keys = self._load_keys()
        if key_hash in keys:
            keys[key_hash]["enabled"] = False
            self._save_keys(keys)
            logger.info(f"Revoked API key: {keys[key_hash]['name']}")
            return True
        return False

    def list_api_keys(self) -> list[APIKey]:
        """List all API keys (without sensitive data)."""
        keys = self._load_keys()
        return [APIKey(**data) for data in keys.values()]


# Global API key manager
api_key_manager = APIKeyManager()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token to decode

    Returns:
        TokenData object

    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", UserRole.USER)
        exp: float = payload.get("exp")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")

        return TokenData(
            username=username,
            role=UserRole(role),
            exp=datetime.fromtimestamp(exp)
        )
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")


async def get_current_user_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> TokenData:
    """
    Get current user from JWT token.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        TokenData object

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication credentials")

    return decode_access_token(credentials.credentials)


async def get_current_user_apikey(
    api_key: Optional[str] = Security(security_apikey),
) -> APIKey:
    """
    Get current user from API key.

    Args:
        api_key: API key from header

    Returns:
        APIKey object

    Raises:
        HTTPException: If authentication fails
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    key_data = api_key_manager.validate_api_key(api_key)

    if not key_data:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return key_data


async def get_current_user(
    jwt_user: Optional[TokenData] = Depends(get_current_user_jwt),
    apikey_user: Optional[APIKey] = Depends(get_current_user_apikey),
) -> Dict[str, Any]:
    """
    Get current user from either JWT or API key (fallback).

    Supports both authentication methods:
    - Bearer token (JWT)
    - API key in X-API-Key header

    Returns:
        User information dict

    Raises:
        HTTPException: If authentication fails
    """
    # Try JWT first
    if jwt_user:
        return {
            "username": jwt_user.username,
            "role": jwt_user.role,
            "auth_method": "jwt"
        }

    # Fallback to API key
    if apikey_user:
        return {
            "username": apikey_user.name,
            "role": apikey_user.role,
            "auth_method": "apikey",
            "rate_limit": apikey_user.rate_limit
        }

    raise HTTPException(status_code=401, detail="Authentication required")


def require_role(required_role: UserRole):
    """
    Dependency to require a specific role.

    Args:
        required_role: Minimum required role

    Returns:
        Dependency function
    """
    async def role_checker(user: Dict[str, Any] = Depends(get_current_user)):
        role_hierarchy = {
            UserRole.READONLY: 0,
            UserRole.USER: 1,
            UserRole.ADMIN: 2,
        }

        user_role = user.get("role", UserRole.READONLY)

        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )

        return user

    return role_checker


# Convenience dependencies
require_admin = require_role(UserRole.ADMIN)
require_user = require_role(UserRole.USER)
require_readonly = require_role(UserRole.READONLY)
