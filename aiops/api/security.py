"""Enhanced security features for AIOps API."""

import hashlib
import hmac
import secrets
import time
import re
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import ipaddress
import threading

from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from aiops.core.logger import get_logger

logger = get_logger(__name__)


# ==================== Password Hashing ====================

class PasswordHasher:
    """Secure password hashing using bcrypt or argon2."""

    def __init__(self, algorithm: str = "bcrypt"):
        """
        Initialize password hasher.

        Args:
            algorithm: Hashing algorithm ('bcrypt' or 'argon2')
        """
        self.algorithm = algorithm

        if algorithm == "argon2":
            try:
                from argon2 import PasswordHasher as Argon2Hasher
                self._hasher = Argon2Hasher()
            except ImportError:
                logger.warning("argon2-cffi not installed, falling back to bcrypt")
                self.algorithm = "bcrypt"

        if self.algorithm == "bcrypt":
            try:
                import bcrypt
                self._bcrypt = bcrypt
            except ImportError:
                raise ImportError("bcrypt package required for password hashing")

    def hash(self, password: str) -> str:
        """Hash a password."""
        if self.algorithm == "argon2":
            return self._hasher.hash(password)
        else:
            salt = self._bcrypt.gensalt(rounds=12)
            return self._bcrypt.hashpw(password.encode(), salt).decode()

    def verify(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash."""
        try:
            if self.algorithm == "argon2":
                self._hasher.verify(hashed, password)
                return True
            else:
                return self._bcrypt.checkpw(password.encode(), hashed.encode())
        except Exception:
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """Check if hash needs to be rehashed (algorithm upgrade)."""
        if self.algorithm == "argon2":
            return self._hasher.check_needs_rehash(hashed)
        return False


# ==================== API Key Management ====================

@dataclass
class APIKeyPolicy:
    """API key rotation and expiration policy."""
    max_age_days: int = 90
    rotation_warning_days: int = 14
    auto_rotate: bool = False
    notification_enabled: bool = True


class APIKeyManager:
    """Manage API key lifecycle and rotation."""

    def __init__(self, policy: Optional[APIKeyPolicy] = None):
        """Initialize API key manager."""
        self.policy = policy or APIKeyPolicy()
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def generate_key(self, prefix: str = "aiops") -> tuple[str, str]:
        """
        Generate a new API key.

        Returns:
            Tuple of (key, key_hash)
        """
        # Generate secure random key
        random_part = secrets.token_urlsafe(32)
        key = f"{prefix}_{random_part}"

        # Hash for storage
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        return key, key_hash

    def register_key(
        self,
        key_hash: str,
        user_id: str,
        name: str,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Register a new API key."""
        with self._lock:
            if expires_at is None:
                expires_at = datetime.utcnow() + timedelta(days=self.policy.max_age_days)

            key_info = {
                "key_hash": key_hash,
                "user_id": user_id,
                "name": name,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at,
                "last_used": None,
                "use_count": 0,
                "is_active": True,
            }

            self._keys[key_hash] = key_info
            return key_info

    def validate_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return its info."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        with self._lock:
            key_info = self._keys.get(key_hash)

            if not key_info:
                return None

            if not key_info["is_active"]:
                return None

            if key_info["expires_at"] and datetime.utcnow() > key_info["expires_at"]:
                return None

            # Update usage
            key_info["last_used"] = datetime.utcnow()
            key_info["use_count"] += 1

            return key_info

    def check_rotation_needed(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Check if key needs rotation."""
        with self._lock:
            key_info = self._keys.get(key_hash)
            if not key_info:
                return None

            expires_at = key_info["expires_at"]
            if expires_at:
                warning_date = expires_at - timedelta(days=self.policy.rotation_warning_days)
                if datetime.utcnow() > warning_date:
                    return {
                        "needs_rotation": True,
                        "expires_at": expires_at,
                        "days_remaining": (expires_at - datetime.utcnow()).days,
                    }

            return {"needs_rotation": False}

    def revoke_key(self, key_hash: str):
        """Revoke an API key."""
        with self._lock:
            if key_hash in self._keys:
                self._keys[key_hash]["is_active"] = False
                logger.info(f"API key revoked: {key_hash[:16]}...")


# ==================== Request Signing ====================

class RequestSigner:
    """Sign and verify webhook requests."""

    def __init__(self, secret: str, algorithm: str = "sha256"):
        """
        Initialize request signer.

        Args:
            secret: Signing secret
            algorithm: Hash algorithm
        """
        self.secret = secret.encode()
        self.algorithm = algorithm

    def sign(self, payload: bytes, timestamp: Optional[int] = None) -> str:
        """
        Sign a payload.

        Args:
            payload: Request payload bytes
            timestamp: Unix timestamp (uses current time if None)

        Returns:
            Signature string in format "t=timestamp,v1=signature"
        """
        timestamp = timestamp or int(time.time())
        signed_payload = f"{timestamp}.".encode() + payload

        signature = hmac.new(
            self.secret,
            signed_payload,
            self.algorithm,
        ).hexdigest()

        return f"t={timestamp},v1={signature}"

    def verify(
        self,
        payload: bytes,
        signature: str,
        tolerance: int = 300,
    ) -> bool:
        """
        Verify a signature.

        Args:
            payload: Request payload bytes
            signature: Signature string
            tolerance: Time tolerance in seconds

        Returns:
            True if signature is valid
        """
        try:
            # Parse signature
            parts = dict(p.split("=") for p in signature.split(","))
            timestamp = int(parts.get("t", 0))
            received_sig = parts.get("v1", "")

            # Check timestamp
            if abs(time.time() - timestamp) > tolerance:
                logger.warning(f"Signature timestamp too old: {timestamp}")
                return False

            # Compute expected signature
            signed_payload = f"{timestamp}.".encode() + payload
            expected_sig = hmac.new(
                self.secret,
                signed_payload,
                self.algorithm,
            ).hexdigest()

            # Compare signatures
            return hmac.compare_digest(received_sig, expected_sig)

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False


# ==================== IP Filtering ====================

@dataclass
class IPFilterConfig:
    """IP filtering configuration."""
    whitelist: List[str] = field(default_factory=list)
    blacklist: List[str] = field(default_factory=list)
    mode: str = "blacklist"  # 'whitelist' or 'blacklist'


class IPFilter:
    """IP whitelist/blacklist filter."""

    def __init__(self, config: Optional[IPFilterConfig] = None):
        """Initialize IP filter."""
        self.config = config or IPFilterConfig()
        self._whitelist_networks: List[ipaddress.IPv4Network] = []
        self._blacklist_networks: List[ipaddress.IPv4Network] = []

        self._parse_networks()

    def _parse_networks(self):
        """Parse CIDR networks from config."""
        for ip_str in self.config.whitelist:
            try:
                network = ipaddress.ip_network(ip_str, strict=False)
                self._whitelist_networks.append(network)
            except ValueError:
                logger.warning(f"Invalid whitelist IP/CIDR: {ip_str}")

        for ip_str in self.config.blacklist:
            try:
                network = ipaddress.ip_network(ip_str, strict=False)
                self._blacklist_networks.append(network)
            except ValueError:
                logger.warning(f"Invalid blacklist IP/CIDR: {ip_str}")

    def is_allowed(self, ip: str) -> bool:
        """Check if IP is allowed."""
        try:
            ip_addr = ipaddress.ip_address(ip)
        except ValueError:
            logger.warning(f"Invalid IP address: {ip}")
            return False

        if self.config.mode == "whitelist":
            # Only allow whitelisted IPs
            for network in self._whitelist_networks:
                if ip_addr in network:
                    return True
            return len(self._whitelist_networks) == 0

        else:
            # Block blacklisted IPs
            for network in self._blacklist_networks:
                if ip_addr in network:
                    return False
            return True


# ==================== Security Audit Logging ====================

@dataclass
class SecurityEvent:
    """Security event for audit logging."""
    event_type: str
    timestamp: datetime
    ip_address: str
    user_id: Optional[str]
    action: str
    resource: Optional[str]
    outcome: str  # 'success', 'failure', 'blocked'
    details: Optional[Dict[str, Any]] = None


class SecurityAuditLogger:
    """Log security-related events for audit."""

    def __init__(self, max_events: int = 10000):
        """Initialize audit logger."""
        self._events: List[SecurityEvent] = []
        self._lock = threading.Lock()
        self.max_events = max_events

    def log_event(
        self,
        event_type: str,
        ip_address: str,
        action: str,
        outcome: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log a security event."""
        event = SecurityEvent(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
            user_id=user_id,
            action=action,
            resource=resource,
            outcome=outcome,
            details=details,
        )

        with self._lock:
            self._events.append(event)

            # Trim old events
            if len(self._events) > self.max_events:
                self._events = self._events[-self.max_events:]

        # Log to application logger
        log_msg = (
            f"SECURITY: {event_type} | "
            f"action={action} | outcome={outcome} | "
            f"ip={ip_address} | user={user_id}"
        )

        if outcome == "failure" or outcome == "blocked":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    def get_events(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        outcome: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[SecurityEvent]:
        """Query security events."""
        with self._lock:
            events = self._events.copy()

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if outcome:
            events = [e for e in events if e.outcome == outcome]
        if since:
            events = [e for e in events if e.timestamp > since]

        return events[-limit:]

    def get_suspicious_activity(self, threshold: int = 5) -> List[Dict[str, Any]]:
        """Detect suspicious activity patterns."""
        with self._lock:
            # Group by IP and count failures
            ip_failures: Dict[str, int] = {}
            for event in self._events:
                if event.outcome == "failure":
                    ip_failures[event.ip_address] = ip_failures.get(event.ip_address, 0) + 1

        suspicious = []
        for ip, count in ip_failures.items():
            if count >= threshold:
                suspicious.append({
                    "ip_address": ip,
                    "failure_count": count,
                    "alert": "Multiple authentication failures",
                })

        return suspicious


# ==================== Security Middleware ====================

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware."""

    def __init__(
        self,
        app: ASGIApp,
        ip_filter: Optional[IPFilter] = None,
        audit_logger: Optional[SecurityAuditLogger] = None,
        request_signer: Optional[RequestSigner] = None,
        verify_webhooks: bool = True,
    ):
        """Initialize security middleware."""
        super().__init__(app)
        self.ip_filter = ip_filter or IPFilter()
        self.audit_logger = audit_logger or SecurityAuditLogger()
        self.request_signer = request_signer
        self.verify_webhooks = verify_webhooks

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with security checks."""
        client_ip = self._get_client_ip(request)

        # IP filtering
        if not self.ip_filter.is_allowed(client_ip):
            self.audit_logger.log_event(
                event_type="ip_filter",
                ip_address=client_ip,
                action="access_attempt",
                outcome="blocked",
                details={"path": request.url.path},
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"},
            )

        # Webhook signature verification
        if (
            self.verify_webhooks
            and self.request_signer
            and request.url.path.startswith("/webhooks")
        ):
            signature = request.headers.get("X-Signature")
            if signature:
                body = await request.body()
                if not self.request_signer.verify(body, signature):
                    self.audit_logger.log_event(
                        event_type="webhook",
                        ip_address=client_ip,
                        action="signature_verify",
                        outcome="failure",
                        details={"path": request.url.path},
                    )
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid signature"},
                    )

        # Process request
        response = await call_next(request)

        # Log successful requests to sensitive endpoints
        if request.url.path.startswith(("/api/v1/auth", "/api/v1/admin")):
            self.audit_logger.log_event(
                event_type="api_access",
                ip_address=client_ip,
                action=f"{request.method} {request.url.path}",
                outcome="success" if response.status_code < 400 else "failure",
                details={"status_code": response.status_code},
            )

        return response


# ==================== Security Headers ====================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


# ==================== Input Validation ====================

class InputValidator:
    """Validate and sanitize user inputs."""

    # Common dangerous patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
    ]

    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """Sanitize a string input."""
        # Truncate
        value = value[:max_length]

        # Remove null bytes
        value = value.replace("\x00", "")

        # Encode HTML entities
        value = value.replace("<", "&lt;").replace(">", "&gt;")

        return value

    @classmethod
    def check_sql_injection(cls, value: str) -> bool:
        """Check for potential SQL injection."""
        value_upper = value.upper()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        return False

    @classmethod
    def check_xss(cls, value: str) -> bool:
        """Check for potential XSS."""
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False


# Global instances
_password_hasher: Optional[PasswordHasher] = None
_api_key_manager: Optional[APIKeyManager] = None
_audit_logger: Optional[SecurityAuditLogger] = None


def get_password_hasher() -> PasswordHasher:
    """Get global password hasher."""
    global _password_hasher
    if _password_hasher is None:
        _password_hasher = PasswordHasher()
    return _password_hasher


def get_api_key_manager() -> APIKeyManager:
    """Get global API key manager."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


def get_audit_logger() -> SecurityAuditLogger:
    """Get global security audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = SecurityAuditLogger()
    return _audit_logger
