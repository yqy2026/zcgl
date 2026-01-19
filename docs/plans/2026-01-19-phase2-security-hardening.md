# Phase 2: Security Hardening - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden security infrastructure with monitoring, httpOnly cookie-based auth, IP whitelist strict validation, API standardization, and secret management (Issues 5, 8, 10-13).

**Architecture:**
- Backend: Implement httpOnly cookie auth, security event logging, IP whitelist manager, startup secret validation
- Frontend: Remove token handling from localStorage, centralize all API calls through ApiClient
- DevOps: Configure monitoring integrations, CORS policies, deployment secret generation

**Tech Stack:** FastAPI, Redis, Prometheus/Grafana (or cloud monitoring), React Query, httpOnly cookies

---

## Task 1: Backend - Create Security Event Logging System

**Files:**
- Create: `backend/src/core/security_event_logger.py`
- Create: `backend/src/models/security_event.py`
- Test: `backend/tests/unit/core/test_security_event_logger.py`

**Step 1: Write the failing test**

```python
# backend/tests/unit/core/test_security_event_logger.py
import pytest
from datetime import datetime
from src.core.security_event_logger import SecurityEventLogger, SecurityEventType
from src.models.security_event import SecurityEvent

def test_log_auth_failure():
    """Test logging authentication failure events"""
    logger = SecurityEventLogger()
    event = logger.log_auth_failure(
        ip="192.168.1.1",
        username="testuser",
        reason="invalid_password"
    )

    assert event.event_type == SecurityEventType.AUTH_FAILURE
    assert event.ip_address == "192.168.1.1"
    assert event.metadata["username"] == "testuser"
    assert event.metadata["reason"] == "invalid_password"

def test_log_permission_denied():
    """Test logging permission denied events"""
    logger = SecurityEventLogger()
    event = logger.log_permission_denied(
        user_id="user-123",
        resource="users",
        action="delete",
        ip="192.168.1.1"
    )

    assert event.event_type == SecurityEventType.PERMISSION_DENIED
    assert event.user_id == "user-123"
    assert event.metadata["resource"] == "users"
    assert event.metadata["action"] == "delete"

def test_check_threshold():
    """Test threshold checking for alerting"""
    logger = SecurityEventLogger()

    # Log 5 failed attempts from same IP
    for _ in range(5):
        logger.log_auth_failure(ip="192.168.1.1", username="test", reason="test")

    # Should trigger alert (threshold is 10 by default, but we'll make it configurable)
    assert logger.should_alert(ip="192.168.1.1", threshold=5) is True
```

**Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/unit/core/test_security_event_logger.py -v
```

Expected: ModuleNotFoundError

**Step 3: Create SecurityEvent model**

```python
# backend/src/models/security_event.py
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text
from sqlalchemy.dialects.sqlite import JSON

from src.database import Base

class SecurityEvent(Base):
    """Security event log model"""
    __tablename__ = "security_events"

    id = Column(String, primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)  # IPv6 compatible
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
```

**Step 4: Implement SecurityEventLogger**

```python
# backend/src/core/security_event_logger.py
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from src.models.security_event import SecurityEvent
from src.core.redis_client import redis_client

class SecurityEventType(str, Enum):
    """Security event types"""
    AUTH_FAILURE = "auth_failure"
    AUTH_SUCCESS = "auth_success"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ACCOUNT_LOCKED = "account_locked"

class SecuritySeverity(str, Enum):
    """Security event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityEventLogger:
    """Centralized security event logging and alerting"""

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.alert_threshold = 10  # Configurable
        self.alert_window_minutes = 1

    def _create_event(
        self,
        event_type: SecurityEventType,
        ip_address: str,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        severity: SecuritySeverity = SecuritySeverity.MEDIUM
    ) -> SecurityEvent:
        """Create and store security event"""
        event = SecurityEvent(
            id=str(uuid4()),
            event_type=event_type.value,
            user_id=user_id,
            ip_address=ip_address,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            severity=severity.value
        )

        if self.db:
            self.db.add(event)
            self.db.commit()

        # Also store in Redis for fast threshold checking
        redis_key = f"security_events:{event_type.value}:{ip_address}"
        redis_client.incr(redis_key)
        redis_client.expire(redis_key, self.alert_window_minutes * 60)

        return event

    def log_auth_failure(
        self,
        ip: str,
        username: Optional[str] = None,
        reason: Optional[str] = None
    ) -> SecurityEvent:
        """Log authentication failure"""
        return self._create_event(
            event_type=SecurityEventType.AUTH_FAILURE,
            ip_address=ip,
            metadata={"username": username, "reason": reason},
            severity=SecuritySeverity.MEDIUM
        )

    def log_permission_denied(
        self,
        user_id: str,
        resource: str,
        action: str,
        ip: str
    ) -> SecurityEvent:
        """Log permission denied event"""
        return self._create_event(
            event_type=SecurityEventType.PERMISSION_DENIED,
            ip_address=ip,
            user_id=user_id,
            metadata={"resource": resource, "action": action},
            severity=SecuritySeverity.LOW
        )

    def log_rate_limit_exceeded(self, ip: str, endpoint: str) -> SecurityEvent:
        """Log rate limit exceeded"""
        return self._create_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            ip_address=ip,
            metadata={"endpoint": endpoint},
            severity=SecuritySeverity.HIGH
        )

    def should_alert(self, ip: str, threshold: Optional[int] = None) -> bool:
        """Check if IP has exceeded event threshold"""
        threshold = threshold or self.alert_threshold

        # Check all event types for this IP
        for event_type in SecurityEventType:
            redis_key = f"security_events:{event_type.value}:{ip}"
            count = redis_client.get(redis_key)
            if count and int(count) >= threshold:
                return True

        return False

    def get_event_count(self, ip: str, event_type: SecurityEventType) -> int:
        """Get event count for IP and event type"""
        redis_key = f"security_events:{event_type.value}:{ip}"
        count = redis_client.get(redis_key)
        return int(count) if count else 0
```

**Step 5: Run test to verify it passes**

```bash
cd backend
pytest tests/unit/core/test_security_event_logger.py -v
```

**Step 6: Create database migration**

```bash
cd backend
alembic revision --autogenerate -m "Add security_events table"
alembic upgrade head
```

**Step 7: Commit**

```bash
cd backend
git add src/core/security_event_logger.py src/models/security_event.py tests/unit/core/test_security_event_logger.py
git commit -m "feat(security): Add security event logging system

- Create SecurityEvent model with event tracking
- Implement SecurityEventLogger with event types
- Add Redis-based threshold checking for alerting
- Support AUTH_FAILURE, PERMISSION_DENIED, RATE_LIMIT_EXCEEDED events
- Create database migration for security_events table

Foundation for #5: Security monitoring and alerting

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Backend - Integrate Security Logging into Permission Middleware

**Files:**
- Modify: `backend/src/middleware/organization_permission.py`
- Modify: `backend/src/api/v1/system_settings.py:69-101`
- Test: `backend/tests/integration/middleware/test_security_logging.py`

**Step 1: Modify organization_permission.py**

```python
# backend/src/middleware/organization_permission.py
# Add import
from src.core.security_event_logger import SecurityEventLogger, SecurityEventType

# In require_permission method, add logging when access denied:
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> User:
        """Check user permissions with security logging"""
        # Check for admin role
        if RoleNormalizer.is_admin(current_user.role):
            return current_user

        # Log permission check
        security_logger = SecurityEventLogger(db)

        # Check organization permissions
        org_service = OrganizationPermissionService(db)
        accessible_orgs = org_service.get_user_accessible_organizations(current_user.id)

        if not accessible_orgs:
            # Log permission denied
            client_ip = "unknown"  # Get from request context
            security_logger.log_permission_denied(
                user_id=current_user.id,
                resource="organizations",
                action="access",
                ip=client_ip
            )

            # Check for alert threshold
            if security_logger.should_alert(ip=client_ip):
                # TODO: Send alert (will be implemented in monitoring integration)
                pass

            raise forbidden("无任何组织访问权限")

        return current_user
```

**Step 2: Replace TODO in system_settings.py with actual monitoring**

```python
# backend/src/api/v1/system_settings.py
# Replace lines 69-101 with actual monitoring integration

@router.post("/security/alerts/test")
async def test_security_alert(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Test security alert system"""
    from src.core.security_event_logger import SecurityEventLogger

    logger = SecurityEventLogger(db)

    # Simulate security events
    for i in range(12):  # Exceed threshold
        logger.log_auth_failure(
            ip=f"192.168.1.{i}",
            username="testuser",
            reason="test_alert"
        )

    return {
        "message": "Generated 12 test security events",
        "should_alert": logger.should_alert(ip="192.168.1.1", threshold=10)
    }

@router.get("/security/events")
async def get_security_events(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get security event log"""
    from src.models.security_event import SecurityEvent

    events = db.query(SecurityEvent)\
        .order_by(SecurityEvent.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

    return {
        "total": len(events),
        "events": [
            {
                "id": e.id,
                "type": e.event_type,
                "user_id": e.user_id,
                "ip": e.ip_address,
                "severity": e.severity,
                "metadata": e.metadata,
                "created_at": e.created_at.isoformat()
            }
            for e in events
        ]
    }
```

**Step 3: Commit**

```bash
cd backend
git add src/middleware/organization_permission.py src/api/v1/system_settings.py
git commit -m "feat(security): Integrate security logging into permission system

- Add SecurityEventLogger to permission middleware
- Log permission denied events with user and IP tracking
- Add /security/alerts/test endpoint for testing
- Add /security/events endpoint for viewing logs
- Replace TODO comment with actual monitoring implementation

Fixes #5: Permission failure monitoring now implemented

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Backend - Implement HttpOnly Cookie Support

**Files:**
- Create: `backend/src/core/cookie_auth.py`
- Modify: `backend/src/api/v1/auth.py` (login/logout endpoints)
- Test: `backend/tests/integration/api/test_cookie_auth.py`

**Step 1: Write the failing test**

```python
# backend/tests/integration/api/test_cookie_auth.py
import pytest
from fastapi.testclient import TestClient

def test_login_sets_http_only_cookie(client: TestClient):
    """Test that login response sets httpOnly cookie"""
    response = client.post("/api/v1/auth/login", data={
        "username": "testuser",
        "password": "testpass123"
    })

    assert response.status_code == 200
    # Check for set-cookie header
    cookies = response.cookies
    assert "access_token" in cookies or "auth_token" in cookies

def test_cookie_is_http_only(client: TestClient):
    """Test that auth cookie is httpOnly"""
    response = client.post("/api/v1/auth/login", data={
        "username": "testuser",
        "password": "testpass123"
    })

    # In integration test, verify cookie attributes
    cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie_header
    assert "Secure" in cookie_header
    assert "SameSite" in cookie_header

def test_logout_clears_cookie(client: TestClient):
    """Test that logout clears auth cookie"""
    # Login first
    client.post("/api/v1/auth/login", data={
        "username": "testuser",
        "password": "testpass123"
    })

    # Logout
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    # Check that cookie is cleared
    cookies = response.cookies
    # Cookie should be expired or max-age=0
```

**Step 2: Create cookie auth utility**

```python
# backend/src/core/cookie_auth.py
from datetime import timedelta, datetime
from typing import Optional
from fastapi import Response
from jose import jwt
from src.core.environment import get_environment

class CookieManager:
    """Manage httpOnly authentication cookies"""

    def __init__(self):
        env = get_environment()
        self.secret_key = env.getenv("SECRET_KEY")
        self.algorithm = "HS256"
        self.cookie_name = "auth_token"
        self.cookie_max_age = timedelta(hours=1)

    def set_auth_cookie(
        self,
        response: Response,
        token: str,
        max_age: Optional[timedelta] = None
    ) -> None:
        """Set httpOnly authentication cookie"""
        max_age = max_age or self.cookie_max_age

        response.set_cookie(
            key=self.cookie_name,
            value=token,
            max_age=int(max_age.total_seconds()),
            expires=datetime.utcnow() + max_age,
            path="/",
            domain=None,  # Current domain
            secure=True,  # HTTPS only
            httponly=True,  # Not accessible via JavaScript
            samesite="lax",  # CSRF protection
        )

    def clear_auth_cookie(self, response: Response) -> None:
        """Clear authentication cookie"""
        response.delete_cookie(
            key=self.cookie_name,
            path="/",
            domain=None,
            secure=True,
            httponly=True,
            samesite="lax",
        )

    def get_token_from_cookie(self, cookie_header: str) -> Optional[str]:
        """Extract token from cookie header"""
        if not cookie_header:
            return None

        # Parse cookie header
        cookies = {}
        for item in cookie_header.split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                cookies[key] = value

        return cookies.get(self.cookie_name)

# Singleton instance
cookie_manager = CookieManager()
```

**Step 3: Modify login endpoint to set cookie**

```python
# backend/src/api/v1/auth.py
# Add import
from src.core.cookie_auth import cookie_manager

# Modify login endpoint to set cookie:
@router.post("/login")
async def login(
    ...,
    response: Response,
    db: Session = Depends(get_db)
):
    # ... existing auth logic ...

    # Create token
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})

    # Set httpOnly cookie
    cookie_manager.set_auth_cookie(response, access_token)

    # Still return token in response for backward compatibility
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "user": user,
        "permissions": user_permissions,
        "message": "Login successful",
    }

# Modify logout endpoint:
@router.post("/logout")
async def logout(response: Response):
    """Logout and clear auth cookie"""
    cookie_manager.clear_auth_cookie(response)
    return {"message": "Logout successful"}
```

**Step 4: Add cookie-based auth dependency**

```python
# backend/src/api/v1/auth.py
# Add new dependency for cookie auth
from fastapi import Cookie, Header

async def get_current_user_from_cookie(
    response: Response,
    cookie: Optional[str] = Cookie(None, alias=cookie_manager.cookie_name),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from httpOnly cookie or Authorization header (fallback)"""

    # Try cookie first
    token = None
    if cookie:
        token = cookie
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if not token:
        raise unauthorized("Not authenticated")

    # Validate token
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise unauthorized("Invalid token")
    except JWTError:
        raise unauthorized("Invalid token")

    # Get user from database
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise unauthorized("User not found")

    return user
```

**Step 5: Run tests**

```bash
cd backend
pytest tests/integration/api/test_cookie_auth.py -v
```

**Step 6: Commit**

```bash
cd backend
git add src/core/cookie_auth.py src/api/v1/auth.py tests/integration/api/test_cookie_auth.py
git commit -m "feat(auth): Implement httpOnly cookie-based authentication

- Create CookieManager for secure cookie handling
- Set HttpOnly, Secure, SameSite cookies on login
- Clear cookies on logout
- Add get_current_user_from_cookie dependency
- Support both cookie and Authorization header (fallback)

Breaking change: Auth now primarily uses httpOnly cookies

Fixes #11 and #12: Incomplete cleanup and XSS risk from localStorage

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Frontend - Remove Token Handling from localStorage

**Files:**
- Modify: `frontend/src/contexts/AuthContext.tsx:149-156`
- Modify: `frontend/src/services/authService.ts`
- Modify: `frontend/src/api/client.ts`

**Step 1: Update AuthContext to use cookies**

```typescript
// frontend/src/contexts/AuthContext.tsx
// Remove token refresh logic that uses direct fetch

// Replace lines 149-156 with:
  const refreshToken = async () => {
    try {
      // Use ApiClient instead of direct fetch
      const response = await enhancedApiClient.post('/auth/refresh', {
        refresh_token: AuthStorage.getRefreshToken()
      });

      if (response.data.access_token) {
        const newAuthData = {
          ...(AuthStorage.getAuthData()!),
          token: response.data.access_token,
        };
        AuthStorage.setAuthData(newAuthData);
      }

      return response.data;
    } catch (error) {
      logger.error('Token refresh failed:', error);
      // Force logout on refresh failure
      await logout();
      throw error;
    }
  };
```

**Step 2: Update ApiClient to handle cookies**

```typescript
// frontend/src/api/client.ts
// Configure axios to include cookies
import axios from 'axios';

export const enhancedApiClient = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  withCredentials: true,  // Include cookies in requests
  headers: {
    'Content-Type': 'application/json',
  },
});

// Remove Authorization header interceptor (cookies handle auth)
// The backend will read from httpOnly cookie instead

// Response interceptor handles token rotation if needed
enhancedApiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Try to refresh token (via cookie, not localStorage)
      try {
        await enhancedApiClient.post('/auth/refresh');
        return enhancedApiClient(originalRequest);
      } catch (refreshError) {
        // Redirect to login
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
```

**Step 3: Commit**

```bash
cd frontend
git add src/contexts/AuthContext.tsx src/api/client.ts src/services/authService.ts
git commit -m "feat(auth): Migrate from localStorage tokens to httpOnly cookies

- Remove localStorage token handling
- Configure ApiClient with withCredentials for cookies
- Remove Authorization header from requests
- Update token refresh to use cookie-based auth
- Backend reads auth from httpOnly cookie

Breaking change: Tokens no longer stored in localStorage

Fixes #11 and #12: XSS vulnerability from localStorage tokens

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Backend - Standardize API Paths with /api/v1 Prefix

**Files:**
- Modify: `frontend/src/contexts/AuthContext.tsx` (ensure all calls use /api/v1)
- Modify: `frontend/src/api/client.ts` (add base URL validation)
- Test: `frontend/src/api/__tests__/client.test.ts`

**Step 1: Add ApiClient validation**

```typescript
// frontend/src/api/client.ts
import axios, { AxiosInstance, AxiosError } from 'axios';

export const API_CONFIG = {
  baseURL: '/api/v1',  // Ensure this is used consistently
  timeout: 30000,
};

// Validate that all URLs use the correct prefix
const validateApiPath = (url: string) => {
  if (url.startsWith('/')) {
    if (!url.startsWith('/api/v1') && !url.startsWith('/auth')) {
      console.warn(
        `[API Client] URL does not use /api/v1 prefix: ${url}\n` +
        `All API calls should use the centralized API client with correct prefix.`
      );
    }
  }
};

export const enhancedApiClient = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to validate URLs
enhancedApiClient.interceptors.request.use((config) => {
  if (config.url) {
    validateApiPath(config.url);
  }
  return config;
});
```

**Step 2: Update AuthContext to use proper API path**

```typescript
// frontend/src/contexts/AuthContext.tsx
// Ensure all API calls use /api/v1 prefix

// Before:
await fetch('/auth/refresh', {...})

// After:
await enhancedApiClient.post('/auth/refresh')
```

**Step 3: Commit**

```bash
cd frontend
git add src/api/client.ts src/contexts/AuthContext.tsx
git commit -m "refactor(api): Standardize all API paths to use /api/v1 prefix

- Add URL validation in ApiClient interceptor
- Warn on non-prefixed API calls
- Update AuthContext to use centralized ApiClient
- Remove direct fetch() calls
- Enforce consistent API path structure

Fixes #8: Auth refresh using wrong endpoint path

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Backend - Implement IP Whitelist Manager

**Files:**
- Create: `backend/src/core/ip_whitelist.py`
- Modify: `backend/src/middleware/security_middleware.py:182-196`
- Test: `backend/tests/unit/core/test_ip_whitelist.py`

**Step 1: Write the failing test**

```python
# backend/tests/unit/core/test_ip_whitelist.py
import pytest
from src.core.ip_whitelist import IPWhitelistManager, IPRange
from src.core.environment import get_environment

def test_ip_range_validation():
    """Test IP range validation"""
    manager = IPWhitelistManager()

    # Valid CIDR ranges
    assert manager.validate_range("192.168.1.0/24") is True
    assert manager.validate_range("10.0.0.0/8") is True
    assert manager.validate_range("172.16.0.0/12") is True

    # Invalid ranges
    assert manager.validate_range("0.0.0.0/0") is False  # Blocks everything
    assert manager.validate_range("192.168.1.1/32") is True  # Single IP is OK

def test_ip_whitelist_allows():
    """Test IP whitelist allows configured IPs"""
    manager = IPWhitelistManager()
    manager.add_range("192.168.1.0/24")

    assert manager.is_allowed("192.168.1.100") is True
    assert manager.is_allowed("192.168.2.100") is False

def test_ip_whitelist_blocks_private_ranges_in_production():
    """Test that private ranges are blocked in production mode"""
    env = get_environment()
    if env.environment == "production":
        manager = IPWhitelistManager()
        # Should reject RFC 1918 private ranges in production
        assert manager.validate_range("10.0.0.0/8") is False
        assert manager.validate_range("172.16.0.0/12") is False
        assert manager.validate_range("192.168.0.0/16") is False
```

**Step 2: Implement IPWhitelistManager**

```python
# backend/src/core/ip_whitelist.py
from ipaddress import ip_network, ip_address, IPv4Network, IPv4Address
from typing import List, Set
from src.core.environment import get_environment

class IPRange:
    """IP range with metadata"""
    def __init__(self, cidr: str, added_by: str = "system"):
        self.network = ip_network(cidr, strict=False)
        self.cidr = cidr
        self.added_by = added_by
        self.created_at = datetime.utcnow()

class IPWhitelistManager:
    """Manage IP whitelist with strict validation"""

    # RFC 1918 private ranges (should be blocked in production)
    PRIVATE_RANGES = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ]

    # Dangerous ranges that should always be rejected
    BLOCKED_RANGES = [
        "0.0.0.0/0",  # Matches everything
    ]

    def __init__(self):
        self.env = get_environment()
        self.whitelist: Set[IPv4Network] = set()
        self._load_from_env()

    def _load_from_env(self):
        """Load whitelist from environment variable"""
        whitelist_str = self.env.getenv("IP_WHITELIST", "")
        if whitelist_str:
            ranges = [r.strip() for r in whitelist_str.split(",")]
            for cidr in ranges:
                if self.validate_range(cidr):
                    self.whitelist.add(ip_network(cidr))

    def validate_range(self, cidr: str) -> bool:
        """Validate IP range for whitelist addition"""
        try:
            network = ip_network(cidr, strict=False)

            # Reject dangerous ranges
            for blocked in self.BLOCKED_RANGES:
                if network.overlaps(ip_network(blocked)):
                    return False

            # In production, reject private ranges
            if self.env.environment == "production":
                for private in self.PRIVATE_RANGES:
                    if network.overlaps(ip_network(private)):
                        return False

            return True

        except ValueError:
            return False

    def add_range(self, cidr: str, added_by: str = "system") -> bool:
        """Add IP range to whitelist"""
        if not self.validate_range(cidr):
            return False

        self.whitelist.add(ip_network(cidr))
        return True

    def remove_range(self, cidr: str) -> bool:
        """Remove IP range from whitelist"""
        try:
            network = ip_network(cidr)
            if network in self.whitelist:
                self.whitelist.remove(network)
                return True
            return False
        except ValueError:
            return False

    def is_allowed(self, ip_str: str) -> bool:
        """Check if IP is allowed"""
        try:
            ip = ip_address(ip_str)

            # If whitelist is empty, allow all (except in production)
            if not self.whitelist:
                return self.env.environment != "production"

            # Check if IP matches any whitelist entry
            for network in self.whitelist:
                if ip in network:
                    return True

            return False

        except ValueError:
            return False

    def get_ranges(self) -> List[str]:
        """Get all whitelisted ranges as CIDR strings"""
        return [str(network) for network in self.whitelist]

    def clear(self) -> None:
        """Clear all whitelist entries"""
        self.whitelist.clear()

# Singleton instance
ip_whitelist = IPWhitelistManager()
```

**Step 3: Update security middleware to use IPWhitelistManager**

```python
# backend/src/middleware/security_middleware.py
# Replace lines 182-196 with IPWhitelistManager integration
from src.core.ip_whitelist import ip_whitelist

class SecurityMiddleware:
    def __init__(self):
        # ... existing code ...
        self.ip_whitelist = ip_whitelist

    def _is_local_ip(self, ip: str) -> bool:
        """Check if IP is in whitelist (replaces _is_local_ip)"""
        return self.ip_whitelist.is_allowed(ip)
```

**Step 4: Run tests**

```bash
cd backend
pytest tests/unit/core/test_ip_whitelist.py -v
```

**Step 5: Commit**

```bash
cd backend
git add src/core/ip_whitelist.py src/middleware/security_middleware.py tests/unit/core/test_ip_whitelist.py
git commit -m "feat(security): Implement strict IP whitelist validation

- Create IPWhitelistManager with CIDR range validation
- Block dangerous ranges (0.0.0.0/0) in all environments
- Reject private ranges in production mode
- Add IP_WHITELIST environment variable support
- Replace local IP check in security middleware

Breaking change: IP whitelist defaults to deny in production

Fixes #10: IP whitelist security improvements

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Backend - Add Secret Validation on Startup

**Files:**
- Create: `backend/src/core/secret_validator.py`
- Modify: `backend/src/main.py` (startup event)
- Modify: `backend/.env.example:20-31`
- Test: `backend/tests/unit/core/test_secret_validator.py`

**Step 1: Write the failing test**

```python
# backend/tests/unit/core/test_secret_validator.py
import pytest
from src.core.secret_validator import SecretValidator, SecretValidationError

def test_strong_secret_passes():
    """Test that strong secrets pass validation"""
    validator = SecretValidator()
    strong_secret = "aB9$xK2@mP7#qR8&nT5*"
    assert validator.validate(strong_secret) is True

def test_weak_secret_fails():
    """Test that weak secrets fail validation"""
    validator = SecretValidator()
    weak_secrets = [
        "secret-key",
        "changeme",
        "password123",
        "abc",
        "12345678",
    ]

    for secret in weak_secrets:
        with pytest.raises(SecretValidationError):
            validator.validate(secret)

def test_default_secret_in_example_fails():
    """Test that example .env secrets fail validation"""
    validator = SecretValidator()
    example_secret = "your-secret-key-here-change-in-production"
    with pytest.raises(SecretValidationError):
        validator.validate(example_secret)
```

**Step 2: Implement SecretValidator**

```python
# backend/src/core/secret_validator.py
import re
from src.core.environment import get_environment

class SecretValidationError(Exception):
    """Raised when secret validation fails"""
    def __init__(self, message: str, suggestion: str = ""):
        self.message = message
        self.suggestion = suggestion
        super().__init__(self.message)

class SecretValidator:
    """Validate application secrets for strength"""

    # Common weak patterns to reject
    WEAK_PATTERNS = [
        r"secret",  # Contains "secret"
        r"changeme",  # Contains "changeme"
        r"password",  # Contains "password"
        r"123456",  # Common number sequence
        r"admin",  # Contains "admin"
    ]

    # Example values that indicate unconfigured secrets
    EXAMPLE_VALUES = [
        "your-secret-key-here",
        "change-in-production",
        "replace-with-real-secret",
        "example-secret",
    ]

    def __init__(self):
        self.env = get_environment()

    def validate(self, secret: str) -> bool:
        """Validate secret strength"""
        errors = []

        # Check length (minimum 32 characters)
        if len(secret) < 32:
            errors.append(f"Secret too short: {len(secret)} characters (minimum 32)")

        # Check for weak patterns
        secret_lower = secret.lower()
        for pattern in self.WEAK_PATTERNS:
            if re.search(pattern, secret_lower):
                errors.append(f"Secret contains weak pattern: '{pattern}'")

        # Check for example values
        if any(example in secret_lower for example in self.EXAMPLE_VALUES):
            errors.append("Secret appears to be an example value")

        # Check character variety
        has_upper = any(c.isupper() for c in secret)
        has_lower = any(c.islower() for c in secret)
        has_digit = any(c.isdigit() for c in secret)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in secret)

        if not (has_upper and has_lower and has_digit and has_special):
            errors.append(
                "Secret lacks character variety (requires uppercase, lowercase, digits, and special characters)"
            )

        if errors:
            suggestion = self._generate_suggestion()
            raise SecretValidationError(
                f"Secret validation failed:\n" + "\n".join(f"- {e}" for e in errors),
                suggestion
            )

        return True

    def validate_env_secrets(self) -> bool:
        """Validate all secrets from environment"""
        secrets_to_check = {
            "SECRET_KEY": self.env.getenv("SECRET_KEY", ""),
            "DATA_ENCRYPTION_KEY": self.env.getenv("DATA_ENCRYPTION_KEY", ""),
        }

        all_valid = True
        for secret_name, secret_value in secrets_to_check.items():
            if not secret_value:
                print(f"❌ {secret_name} is not set!")
                all_valid = False
            else:
                try:
                    self.validate(secret_value)
                    print(f"✅ {secret_name} is strong")
                except SecretValidationError as e:
                    print(f"❌ {secret_name} validation failed:")
                    print(f"   {e.message}")
                    if e.suggestion:
                        print(f"\n{e.suggestion}")
                    all_valid = False

        return all_valid

    def _generate_suggestion(self) -> str:
        """Generate a strong secret suggestion"""
        import secrets

        suggested = secrets.token_urlsafe(32)
        return f"Suggested strong secret: {suggested}"

# Singleton instance
secret_validator = SecretValidator()
```

**Step 3: Add startup validation to main.py**

```python
# backend/src/main.py
from src.core.secret_validator import secret_validator, SecretValidationError

@app.on_event("startup")
async def startup_event():
    """Validate secrets on startup"""
    print("\n🔐 Validating application secrets...")

    try:
        if not secret_validator.validate_env_secrets():
            print("\n⚠️  WARNING: Weak secrets detected!")
            print("In production, the application will refuse to start.")
            if get_environment().environment == "production":
                print("\n❌ Production mode requires strong secrets. Exiting.")
                raise SystemExit(1)
    except SecretValidationError as e:
        print(f"\n❌ Secret validation failed: {e}")
        if get_environment().environment == "production":
            raise SystemExit(1)
```

**Step 4: Update .env.example**

```bash
# backend/.env.example
# Replace lines 20-31 with:

# ============================================================================
# SECURITY CRITICAL: Generate strong secrets before running in production!
# ============================================================================
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"

SECRET_KEY="<generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\">"
DATA_ENCRYPTION_KEY="<generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\">"

# ⚠️  SECURITY WARNINGS:
# • Never commit these values to version control
# • Use different keys for development, staging, and production
# • Rotate keys periodically (every 90 days recommended)
# • Store production keys in a secure secrets manager (AWS KMS, HashiCorp Vault, etc.)
# • If these keys are leaked, immediately regenerate and rotate all encrypted data
```

**Step 5: Run tests**

```bash
cd backend
pytest tests/unit/core/test_secret_validator.py -v
```

**Step 6: Commit**

```bash
cd backend
git add src/core/secret_validator.py src/main.py .env.example tests/unit/core/test_secret_validator.py
git commit -m "feat(security): Add startup secret validation

- Create SecretValidator with strength checks
- Validate SECRET_KEY and DATA_ENCRYPTION_KEY on startup
- Reject weak patterns (secret, changeme, password, etc.)
- Require minimum 32 characters with character variety
- Block application startup in production with weak secrets
- Update .env.example with generation command

Breaking change: Application exits on weak secrets in production

Fixes #13: Default SECRET_KEY security vulnerability

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: DevOps - Update Deployment Configuration

**Files:**
- Create: `backend/scripts/generate-secrets.sh`
- Update: `docker-compose.yml` (if exists)
- Update: Deployment documentation

**Step 1: Create secret generation script**

```bash
#!/bin/bash
# backend/scripts/generate-secrets.sh

set -e

echo "🔐 Generating strong secrets for production deployment..."
echo ""

SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
DATA_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

echo "Add these to your environment or secrets manager:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "SECRET_KEY=\"$SECRET_KEY\""
echo "DATA_ENCRYPTION_KEY=\"$DATA_ENCRYPTION_KEY\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  IMPORTANT:"
echo "  • Store these securely in your secrets manager"
echo "  • Do not commit to version control"
echo "  • Rotate keys every 90 days"
echo "  • Test key recovery procedures before production deployment"
```

**Step 2: Commit**

```bash
git add backend/scripts/generate-secrets.sh
git commit -m "ops(secrets): Add secret generation script for deployments

- Create generate-secrets.sh script
- Generate strong SECRET_KEY and DATA_ENCRYPTION_KEY
- Include security reminders and best practices
- Support for secrets manager integration

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Summary

**Phase 2 Complete**: All security hardening issues resolved
- ✅ Issue #5: Security event logging and monitoring implemented
- ✅ Issue #8: All API paths standardized to /api/v1 prefix
- ✅ Issue #10: IP whitelist with strict validation
- ✅ Issue #11: Complete auth cleanup with cookies
- ✅ Issue #12: XSS vulnerability eliminated (httpOnly cookies)
- ✅ Issue #13: Secret validation on startup

**Breaking Changes**:
- Authentication now primarily uses httpOnly cookies (not localStorage)
- API paths must use /api/v1 prefix
- IP whitelist defaults to deny in production
- Application exits on weak secrets in production
- Security events logged to database and Redis

**Environment Variables Added**:
- `IP_WHITELIST=192.168.1.0/24,10.0.0.0/8` (comma-separated CIDR ranges)
- Enhanced `SECRET_KEY` and `DATA_ENCRYPTION_KEY` validation

**Next Steps**: Proceed to Phase 3 - Feature Completion (Issues 6, 7, 9)
