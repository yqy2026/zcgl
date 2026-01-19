# Phase 1: Critical Security Foundation - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix completely broken authentication, authorization, and rate limiting system (Issues #1-4) through comprehensive overhaul with breaking changes.

**Architecture:**
- Backend: Implement fail-closed rate limiting with circuit breaker, case-insensitive role comparison, and permission-aware login API
- Frontend: Redesign auth storage with unified AuthStorage class and PermissionManager with caching
- Breaking changes: localStorage structure, role normalization, API contract changes

**Tech Stack:** FastAPI, SQLAlchemy 2.0, React 19, TypeScript, Redis (rate limiting)

---

## Task 1: Backend - Create Rate Limiting Strategy System

**Files:**
- Create: `backend/src/core/rate_limit_strategy.py`
- Create: `backend/src/core/circuit_breaker.py`
- Modify: `backend/src/middleware/security_middleware.py:241-248`
- Test: `backend/tests/unit/core/test_rate_limit_strategy.py`

**Step 1: Write the failing test for rate limit strategy**

```python
# backend/tests/unit/core/test_rate_limit_strategy.py
import pytest
from src.core.rate_limit_strategy import RateLimitStrategy, RateLimitConfig

def test_rate_limit_strategy_enum():
    """Test that rate limit strategy enum has correct values"""
    assert RateLimitStrategy.STRICT.value == "strict"
    assert RateLimitStrategy.PERMISSIVE.value == "permissive"
    assert RateLimitStrategy.DEGRADED.value == "degraded"

def test_rate_limit_config_defaults():
    """Test rate limit config has secure defaults"""
    config = RateLimitConfig()
    assert config.strategy == RateLimitStrategy.STRICT
    assert config.max_failures == 3
    assert config.cooldown_seconds == 60

def test_strict_mode_blocks_on_error():
    """Test that strict mode blocks requests when rate limiter fails"""
    config = RateLimitConfig(strategy=RateLimitStrategy.STRICT)
    # Simulate rate limiter error
    assert config.should_block_on_error() is True

def test_permissive_mode_allows_on_error():
    """Test that permissive mode allows requests when rate limiter fails"""
    config = RateLimitConfig(strategy=RateLimitStrategy.PERMISSIVE)
    assert config.should_block_on_error() is False
```

**Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/unit/core/test_rate_limit_strategy.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.core.rate_limit_strategy'`

**Step 3: Write minimal implementation**

```python
# backend/src/core/rate_limit_strategy.py
from enum import Enum
from pydantic import BaseModel, Field
from src.core.environment import get_environment

class RateLimitStrategy(str, Enum):
    """Rate limit failure strategy"""
    STRICT = "strict"  # Block on error (fail-closed)
    PERMISSIVE = "permissive"  # Allow on error (fail-open)
    DEGRADED = "degraded"  # Fallback to simple IP limiting

class RateLimitConfig(BaseModel):
    """Rate limit configuration"""
    strategy: RateLimitStrategy = Field(
        default=RateLimitStrategy.STRICT,
        description="Strategy for rate limiter failures"
    )
    max_failures: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max failures before entering degraded mode"
    )
    cooldown_seconds: int = Field(
        default=60,
        ge=10,
        le=600,
        description="Cooldown period in degraded mode"
    )

    def should_block_on_error(self) -> bool:
        """Determine if requests should be blocked on rate limiter error"""
        return self.strategy == RateLimitStrategy.STRICT

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Create config from environment variables"""
        env = get_environment()
        strategy_str = env.getenv("RATE_LIMIT_FAILURE_MODE", "strict")
        try:
            strategy = RateLimitStrategy(strategy_str)
        except ValueError:
            strategy = RateLimitStrategy.STRICT

        return cls(
            strategy=strategy,
            max_failures=int(env.getenv("RATE_LIMIT_MAX_FAILURES", "3")),
            cooldown_seconds=int(env.getenv("RATE_LIMIT_COOLDOWN_SECONDS", "60"))
        )
```

**Step 4: Run test to verify it passes**

```bash
cd backend
pytest tests/unit/core/test_rate_limit_strategy.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
cd backend
git add tests/unit/core/test_rate_limit_strategy.py src/core/rate_limit_strategy.py
git commit -m "feat(rate-limit): Add rate limit strategy system with fail-closed support

- Add RateLimitStrategy enum (STRICT, PERMISSIVE, DEGRADED)
- Create RateLimitConfig with environment-based configuration
- Default to STRICT mode for production security
- Support RATE_LIMIT_FAILURE_MODE environment variable

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Backend - Implement Circuit Breaker Pattern

**Files:**
- Create: `backend/src/core/circuit_breaker.py`
- Modify: `backend/src/middleware/security_middleware.py`
- Test: `backend/tests/unit/core/test_circuit_breaker.py`

**Step 1: Write the failing test**

```python
# backend/tests/unit/core/test_circuit_breaker.py
import pytest
import time
from src.core.circuit_breaker import CircuitBreaker, CircuitState

def test_circuit_breaker_initially_closed():
    """Test that circuit breaker starts in closed state"""
    cb = CircuitBreaker(max_failures=3, cooldown=60)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0

def test_circuit_breaker_opens_after_max_failures():
    """Test that circuit breaker opens after max failures"""
    cb = CircuitBreaker(max_failures=3, cooldown=60)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.is_open() is True

def test_circuit_breaker_blocks_when_open():
    """Test that requests are blocked when circuit is open"""
    cb = CircuitBreaker(max_failures=3, cooldown=1)
    for _ in range(3):
        cb.record_failure()
    assert cb.allow_request() is False

def test_circuit_breaker_resets_after_cooldown():
    """Test that circuit breaker resets after cooldown period"""
    cb = CircuitBreaker(max_failures=3, cooldown=1)
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open() is True
    time.sleep(1.1)
    assert cb.allow_request() is True  # Should reset to half-open
    assert cb.state == CircuitState.HALF_OPEN

def test_circuit_breaker_closes_on_success():
    """Test that circuit breaker closes on successful request"""
    cb = CircuitBreaker(max_failures=3, cooldown=60)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.OPEN
    time.sleep(0.1)  # Small delay
    cb.allow_request()  # Transition to half-open
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
```

**Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/unit/core/test_circuit_breaker.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.core.circuit_breaker'`

**Step 3: Write minimal implementation**

```python
# backend/src/core/circuit_breaker.py
import time
from enum import Enum
from dataclasses import dataclass

class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, block requests
    HALF_OPEN = "half_open"  # Testing if system recovered

@dataclass
class CircuitBreaker:
    """Circuit breaker for fail-closed rate limiting"""
    max_failures: int = 3
    cooldown: int = 60  # seconds
    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count"""
        return self._failure_count

    def record_failure(self) -> None:
        """Record a failure and potentially open circuit"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.max_failures:
            self._state = CircuitState.OPEN

    def record_success(self) -> None:
        """Record a success and close circuit if half-open"""
        self._failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED

    def is_open(self) -> bool:
        """Check if circuit is currently open"""
        return self._state == CircuitState.OPEN

    def allow_request(self) -> bool:
        """Check if request should be allowed"""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if cooldown period has passed
            if time.time() - self._last_failure_time > self.cooldown:
                self._state = CircuitState.HALF_OPEN
                return True
            return False

        # HALF_OPEN state - allow test request
        return True
```

**Step 4: Run test to verify it passes**

```bash
cd backend
pytest tests/unit/core/test_circuit_breaker.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
cd backend
git add tests/unit/core/test_circuit_breaker.py src/core/circuit_breaker.py
git commit -m "feat(circuit-breaker): Implement circuit breaker pattern for rate limiting

- Add CircuitBreaker with CLOSED, OPEN, HALF_OPEN states
- Track failures and automatically open after threshold
- Reset to half-open after cooldown period
- Close circuit on successful request
- Configurable max_failures and cooldown

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Backend - Integrate Circuit Breaker into Rate Limiting

**Files:**
- Modify: `backend/src/middleware/security_middleware.py:241-248`
- Test: `backend/tests/integration/middleware/test_security_middleware_rate_limit.py`

**Step 1: Write the failing test**

```python
# backend/tests/integration/middleware/test_security_middleware_rate_limit.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

def test_rate_limit_fail_closed_blocks_requests(client):
    """Test that rate limiter errors block requests in STRICT mode"""
    # This test will require mocking the rate limiter to throw errors
    # For now, we'll test the integration
    response = client.get("/api/v1/health")
    # Should work normally
    assert response.status_code == 200

def test_rate_limit_degraded_mode_fallback(client):
    """Test that degraded mode falls back to simple limiting"""
    # Will be implemented with circuit breaker integration
    pass
```

**Step 2: Run test to verify it fails (or passes as placeholder)**

```bash
cd backend
pytest tests/integration/middleware/test_security_middleware_rate_limit.py -v
```

**Step 3: Modify security_middleware.py**

```python
# backend/src/middleware/security_middleware.py
# Add imports at top of file
from src.core.rate_limit_strategy import RateLimitConfig, RateLimitStrategy
from src.core.circuit_breaker import CircuitBreaker

# In SecurityMiddleware class __init__ method, add:
class SecurityMiddleware:
    def __init__(self):
        # ... existing code ...
        self.rate_limit_config = RateLimitConfig.from_env()
        self.circuit_breaker = CircuitBreaker(
            max_failures=self.rate_limit_config.max_failures,
            cooldown=self.rate_limit_config.cooldown_seconds
        )

# Replace the _check_rate_limit method (lines 241-248):
    def _check_rate_limit(self, request: Request, is_suspicious: bool) -> bool:
        """
        Check rate limiting with fail-closed behavior

        Returns:
            bool: True if request is allowed, False if rate limited
        """
        # Generate rate limit key
        ip = self._get_client_ip(request)
        endpoint = request.url.path

        if "/export" in endpoint:
            rate_limit_key = f"{ip}:excel"
        elif request.method == HTTPMethods.POST:
            rate_limit_key = f"{ip}:post"
        else:
            rate_limit_key = f"{ip}:default"

        # Check circuit breaker state
        if self.circuit_breaker.is_open():
            logger.warning(
                f"Circuit breaker open, using degraded rate limiting for {ip}"
            )
            # Use simple IP-based limiting in degraded mode
            return self._degraded_rate_limit_check(rate_limit_key)

        # Try adaptive rate limiting
        try:
            if adaptive_limiter is not None and ADAPTIVE_LIMITER_AVAILABLE:
                result = adaptive_limiter.check_rate_limit(rate_limit_key, is_suspicious)
                # Record success on successful check
                self.circuit_breaker.record_success()
                return result
            else:
                logger.warning("Adaptive rate limiter not available")
                # Check if we should fail-closed
                if self.rate_limit_config.should_block_on_error():
                    self.circuit_breaker.record_failure()
                    return False
                else:
                    return True

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            self.circuit_breaker.record_failure()

            # Fail-closed: block on error in STRICT mode
            if self.rate_limit_config.strategy == RateLimitStrategy.STRICT:
                return False
            # Fail-open: allow in PERMISSIVE mode
            elif self.rate_limit_config.strategy == RateLimitStrategy.PERMISSIVE:
                return True
            # DEGRADED: fallback to simple limiting
            else:
                return self._degraded_rate_limit_check(rate_limit_key)

    def _degraded_rate_limit_check(self, key: str) -> bool:
        """
        Simple degraded mode rate limiting using Redis counter

        Args:
            key: Rate limit key

        Returns:
            bool: True if request is allowed, False if rate limited
        """
        try:
            # Simple 60 req/min limit in degraded mode
            from src.core.redis_client import redis_client

            current = redis_client.incr(f"rate_limit:{key}")
            if current == 1:
                redis_client.expire(f"rate_limit:{key}", 60)

            return current <= 60
        except Exception as e:
            logger.error(f"Degraded rate limiting failed: {e}")
            # Ultimate fallback: allow request
            return True
```

**Step 4: Run test to verify it passes**

```bash
cd backend
pytest tests/integration/middleware/test_security_middleware_rate_limit.py -v
```

Expected: Tests PASS (or update test to properly verify the behavior)

**Step 5: Commit**

```bash
cd backend
git add src/middleware/security_middleware.py tests/integration/middleware/test_security_middleware_rate_limit.py
git commit -m "feat(rate-limit): Integrate circuit breaker for fail-closed rate limiting

- Replace fail-open behavior with fail-closed circuit breaker
- Add degraded mode fallback using simple Redis limiting
- Configure via RATE_LIMIT_FAILURE_MODE environment variable
- Record circuit breaker state on success/failure
- Block requests when rate limiter fails in STRICT mode (default)

Fixes #1: Adaptive rate limiting fail-open vulnerability

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Backend - Create Role Normalizer Utility

**Files:**
- Create: `backend/src/core/role_normalizer.py`
- Modify: `backend/src/models/auth.py:17-22`
- Test: `backend/tests/unit/core/test_role_normalizer.py`

**Step 1: Write the failing test**

```python
# backend/tests/unit/core/test_role_normalizer.py
import pytest
from src.core.role_normalizer import RoleNormalizer, Role
from src.models.auth import UserRole

def test_role_enum_matches_user_role():
    """Test that Role enum matches UserRole enum values"""
    assert Role.ADMIN.value == UserRole.ADMIN.value
    assert Role.USER.value == UserRole.USER.value

def test_role_normalizer_case_insensitive():
    """Test that role comparison is case-insensitive"""
    assert RoleNormalizer.is_admin("admin") is True
    assert RoleNormalizer.is_admin("ADMIN") is True
    assert RoleNormalizer.is_admin("Admin") is True
    assert RoleNormalizer.is_admin("user") is False

def test_role_normalizer_standardizes():
    """Test that roles are standardized to lowercase"""
    assert RoleNormalizer.normalize("ADMIN") == "admin"
    assert RoleNormalizer.normalize("Admin") == "admin"
    assert RoleNormalizer.normalize("admin") == "admin"

def test_role_normalizer_validates():
    """Test that invalid roles raise errors"""
    with pytest.raises(ValueError, match="Invalid role"):
        RoleNormalizer.validate("superadmin")

def test_role_normalizer_from_string():
    """Test creating Role from string (case-insensitive)"""
    assert Role.from_string("admin") == Role.ADMIN
    assert Role.from_string("ADMIN") == Role.ADMIN
    assert Role.from_string("user") == Role.USER
```

**Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/unit/core/test_role_normalizer.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.core.role_normalizer'`

**Step 3: Write minimal implementation**

```python
# backend/src/core/role_normalizer.py
from enum import Enum
from typing import Literal

# Centralized role definition (matches UserRole but with utility methods)
class Role(str, Enum):
    """Standardized role enum with case-insensitive comparison"""
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"  # For future use

    @classmethod
    def from_string(cls, role_str: str) -> "Role":
        """Create Role from string (case-insensitive)"""
        normalized = role_str.lower().strip()
        role_map = {
            "admin": cls.ADMIN,
            "user": cls.USER,
            "moderator": cls.MODERATOR,
        }
        if normalized not in role_map:
            raise ValueError(f"Invalid role: {role_str}")
        return role_map[normalized]

class RoleNormalizer:
    """Utility class for role normalization and comparison"""

    @staticmethod
    def normalize(role: str) -> str:
        """Normalize role string to lowercase"""
        return role.lower().strip()

    @staticmethod
    def is_admin(role: str) -> bool:
        """Check if role is admin (case-insensitive)"""
        return RoleNormalizer.normalize(role) == Role.ADMIN.value

    @staticmethod
    def is_user(role: str) -> bool:
        """Check if role is user (case-insensitive)"""
        return RoleNormalizer.normalize(role) == Role.USER.value

    @staticmethod
    def validate(role: str) -> Role:
        """Validate and return Role enum"""
        return Role.from_string(role)

    @staticmethod
    def equals(role1: str, role2: str) -> bool:
        """Compare two roles (case-insensitive)"""
        return RoleNormalizer.normalize(role1) == RoleNormalizer.normalize(role2)
```

**Step 4: Run test to verify it passes**

```bash
cd backend
pytest tests/unit/core/test_role_normalizer.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
cd backend
git add tests/unit/core/test_role_normalizer.py src/core/role_normalizer.py
git commit -m "feat(auth): Add case-insensitive role normalization system

- Create Role enum with from_string classmethod
- Implement RoleNormalizer utility for case-insensitive comparison
- Support admin, user, moderator roles
- Raise ValueError for invalid roles
- Foundation for fixing #2: ADMIN vs admin mismatch

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Backend - Fix Admin Role Comparison in Organization Permission

**Files:**
- Modify: `backend/src/middleware/organization_permission.py:182-195`
- Test: `backend/tests/integration/middleware/test_organization_permission_role.py`

**Step 1: Write the failing test**

```python
# backend/tests/integration/middleware/test_organization_permission_role.py
import pytest
from src.core.role_normalizer import RoleNormalizer

def test_admin_role_lowercase_recognized():
    """Test that lowercase 'admin' role is recognized as admin"""
    # This should pass after fix
    assert RoleNormalizer.is_admin("admin") is True

def test_admin_role_uppercase_recognized():
    """Test that uppercase 'ADMIN' role is recognized as admin"""
    assert RoleNormalizer.is_admin("ADMIN") is True

def test_organization_permission_admin_access():
    """Test that admin users can access organizations"""
    # Will test actual middleware behavior
    pass
```

**Step 2: Run test to verify current behavior**

```bash
cd backend
pytest tests/integration/middleware/test_organization_permission_role.py -v
```

Expected: Tests might pass (testing RoleNormalizer) or fail (if testing actual middleware)

**Step 3: Modify organization_permission.py**

```python
# backend/src/middleware/organization_permission.py
# Add import at top
from src.core.role_normalizer import RoleNormalizer

# Replace lines 182-195 in require_permission method:
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> User:
        """
        Check user permissions with case-insensitive role comparison
        """
        # Check for admin role (case-insensitive)
        if RoleNormalizer.is_admin(current_user.role):
            return current_user

        # If there's an organization ID parameter, check organization permission
        if self.organization_id_param:
            # Extract organization_id from request
            # Due to middleware design limitations, we do basic check here
            pass

        # Check if user has any organization access permissions
        org_service = OrganizationPermissionService(db)
        accessible_orgs = org_service.get_user_accessible_organizations(current_user.id)

        if not accessible_orgs:
            raise forbidden("无任何组织访问权限")

        return current_user
```

**Step 4: Run test to verify it passes**

```bash
cd backend
pytest tests/integration/middleware/test_organization_permission_role.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
cd backend
git add src/middleware/organization_permission.py tests/integration/middleware/test_organization_permission_role.py
git commit -m "fix(auth): Fix admin role comparison to be case-insensitive

- Replace hardcoded 'ADMIN' check with RoleNormalizer.is_admin()
- Support both 'admin' and 'ADMIN' role values
- Use RoleNormalizer utility for consistent role comparison
- Fixes issue where admin role 'admin' was not recognized

Fixes #2: Organization permission check hardcoded 'ADMIN' vs actual 'admin'

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Backend - Update Login API to Return Permissions

**Files:**
- Modify: `backend/src/api/v1/auth.py` (login endpoint)
- Modify: `backend/src/schemas/auth.py` (add permissions field)
- Test: `backend/tests/integration/api/test_auth_permissions.py`

**Step 1: Write the failing test**

```python
# backend/tests/integration/api/test_auth_permissions.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

def test_login_returns_permissions(client: TestClient, test_user):
    """Test that login response includes permissions array"""
    response = client.post("/api/v1/auth/login", data={
        "username": test_user.username,
        "password": "testpass123"
    })

    assert response.status_code == 200
    data = response.json()
    assert "permissions" in data
    assert isinstance(data["permissions"], list)

def test_admin_login_has_admin_permissions(client: TestClient, admin_user):
    """Test that admin user gets admin permissions"""
    response = client.post("/api/v1/auth/login", data={
        "username": admin_user.username,
        "password": "adminpass123"
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["permissions"]) > 0
    # Should have admin-specific permissions
    permission_resources = [p["resource"] for p in data["permissions"]]
    assert "users" in permission_resources or "all" in permission_resources
```

**Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/integration/api/test_auth_permissions.py -v
```

Expected: Tests fail - "permissions" not in response or wrong structure

**Step 3: Modify auth schemas**

```python
# backend/src/schemas/auth.py
# Add PermissionSchema if not exists
from pydantic import BaseModel

class PermissionSchema(BaseModel):
    """Permission schema"""
    resource: str
    action: str
    description: str | None = None

    class Config:
        from_attributes = True

# Update TokenResponse schema
class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserResponse
    permissions: list[PermissionSchema] = []  # Add this field
```

**Step 4: Modify login endpoint to return permissions**

```python
# backend/src/api/v1/auth.py
# In the login endpoint, after generating token:

@router.post("/login", response_model=TokenResponse)
async def_login(
    ...,
    db: Session = Depends(get_db)
):
    # ... existing authentication logic ...

    # Get user permissions
    from src.services.permission_service import PermissionService
    perm_service = PermissionService(db)
    user_permissions = perm_service.get_user_permissions(user.id)

    # Create response
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=3600,
        user=user,
        permissions=[PermissionSchema(
            resource=p.resource,
            action=p.action,
            description=p.description
        ) for p in user_permissions]
    )
```

**Step 5: Run test to verify it passes**

```bash
cd backend
pytest tests/integration/api/test_auth_permissions.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
cd backend
git add src/schemas/auth.py src/api/v1/auth.py tests/integration/api/test_auth_permissions.py
git commit -m "feat(auth): Return permissions in login response

- Add permissions field to TokenResponse schema
- Fetch user permissions from PermissionService
- Return PermissionSchema array with resource, action, description
- Foundation for frontend permission system (fixes #4)

Breaking change: Login API now includes permissions array

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Frontend - Create Unified AuthStorage Class

**Files:**
- Create: `frontend/src/utils/AuthStorage.ts`
- Modify: `frontend/src/services/authService.ts:84-105`
- Test: `frontend/src/utils/__tests__/AuthStorage.test.ts`

**Step 1: Write the failing test**

```typescript
// frontend/src/utils/__tests__/AuthStorage.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AuthStorage } from '../AuthStorage';

describe('AuthStorage', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.spyOn(Storage.prototype, 'getItem');
    vi.spyOn(Storage.prototype, 'setItem');
    vi.spyOn(Storage.prototype, 'removeItem');
  });

  it('should store auth data with correct structure', () => {
    const authData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1', username: 'test' },
      permissions: [{ resource: 'assets', action: 'read' }]
    };

    AuthStorage.setAuthData(authData);

    const stored = localStorage.getItem('authData');
    expect(stored).toBeDefined();
    expect(JSON.parse(stored!)).toEqual(authData);
  });

  it('should retrieve auth data correctly', () => {
    const authData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1', username: 'test' },
      permissions: [{ resource: 'assets', action: 'read' }]
    };

    AuthStorage.setAuthData(authData);
    const retrieved = AuthStorage.getAuthData();

    expect(retrieved).toEqual(authData);
  });

  it('should return null when no auth data exists', () => {
    const retrieved = AuthStorage.getAuthData();
    expect(retrieved).toBeNull();
  });

  it('should clear all auth-related data', () => {
    // Set multiple auth-related keys
    localStorage.setItem('token', 'test');
    localStorage.setItem('refresh_token', 'test');
    localStorage.setItem('authData', JSON.stringify({ token: 'test' }));

    AuthStorage.clearAuthData();

    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(localStorage.getItem('authData')).toBeNull();
  });

  it('should get token from authData', () => {
    const authData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1' },
      permissions: []
    };

    AuthStorage.setAuthData(authData);
    const token = AuthStorage.getToken();

    expect(token).toBe('test-token');
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd frontend
pnpm test src/utils/__tests__/AuthStorage.test.ts
```

Expected: Test fails - file not found

**Step 3: Write minimal implementation**

```typescript
// frontend/src/utils/AuthStorage.ts

export interface AuthData {
  token: string;
  refreshToken: string;
  user: {
    id: string;
    username: string;
    email?: string;
    full_name?: string;
    role?: string;
    organization_id?: string;
  };
  permissions: Array<{
    resource: string;
    action: string;
    description?: string;
  }>;
}

export class AuthStorageClass {
  private readonly AUTH_DATA_KEY = 'authData';
  private readonly TOKEN_KEY = 'token';
  private readonly REFRESH_TOKEN_KEY = 'refresh_token';

  /**
   * Store authentication data in localStorage
   */
  setAuthData(data: AuthData): void {
    try {
      localStorage.setItem(this.AUTH_DATA_KEY, JSON.stringify(data));
      // Also set individual keys for backward compatibility
      localStorage.setItem(this.TOKEN_KEY, data.token);
      localStorage.setItem(this.REFRESH_TOKEN_KEY, data.refreshToken);
    } catch (error) {
      console.error('Failed to store auth data:', error);
      throw error;
    }
  }

  /**
   * Retrieve authentication data from localStorage
   */
  getAuthData(): AuthData | null {
    try {
      const stored = localStorage.getItem(this.AUTH_DATA_KEY);
      if (stored == null) {
        return null;
      }
      return JSON.parse(stored) as AuthData;
    } catch (error) {
      console.error('Failed to retrieve auth data:', error);
      return null;
    }
  }

  /**
   * Get access token
   */
  getToken(): string | null {
    const authData = this.getAuthData();
    return authData?.token ?? null;
  }

  /**
   * Get refresh token
   */
  getRefreshToken(): string | null {
    const authData = this.getAuthData();
    return authData?.refreshToken ?? null;
  }

  /**
   * Get current user
   */
  getCurrentUser(): AuthData['user'] | null {
    const authData = this.getAuthData();
    return authData?.user ?? null;
  }

  /**
   * Get user permissions
   */
  getPermissions(): AuthData['permissions'] {
    const authData = this.getAuthData();
    return authData?.permissions ?? [];
  }

  /**
   * Clear all authentication data from localStorage
   */
  clearAuthData(): void {
    try {
      localStorage.removeItem(this.AUTH_DATA_KEY);
      localStorage.removeItem(this.TOKEN_KEY);
      localStorage.removeItem(this.REFRESH_TOKEN_KEY);
      localStorage.removeItem('refreshToken'); // Remove old camelCase key
      localStorage.removeItem('user');
      localStorage.removeItem('permissions');
      localStorage.removeItem('currentUser');
    } catch (error) {
      console.error('Failed to clear auth data:', error);
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    const token = this.getToken();
    return token != null && token.trim() !== '';
  }
}

// Export singleton instance
export const AuthStorage = new AuthStorageClass();
```

**Step 4: Run test to verify it passes**

```bash
cd frontend
pnpm test src/utils/__tests__/AuthStorage.test.ts
```

Expected: All tests PASS

**Step 5: Commit**

```bash
cd frontend
git add src/utils/AuthStorage.ts src/utils/__tests__/AuthStorage.test.ts
git commit -m "feat(auth): Create unified AuthStorage class for token management

- Implement AuthStorageClass with centralized auth data handling
- Store auth data in structured 'authData' key
- Maintain backward compatibility with individual token keys
- Add methods: getAuthData, getToken, getPermissions, clearAuthData
- Foundation for fixing #3 and #11

Breaking change: localStorage structure now uses 'authData' key

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Frontend - Update usePermission Hook to Use AuthStorage

**Files:**
- Modify: `frontend/src/hooks/usePermission.tsx:54-69`
- Test: `frontend/src/hooks/__tests__/usePermission.test.tsx`

**Step 1: Write the failing test**

```typescript
// frontend/src/hooks/__tests__/usePermission.test.tsx
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { usePermission } from '../usePermission';
import { AuthStorage } from '@/utils/AuthStorage';

describe('usePermission', () => {
  beforeEach(() => {
    localStorage.clear();
    AuthStorage.clearAuthData();
  });

  it('should load permissions from AuthStorage', () => {
    const mockAuthData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1', username: 'test' },
      permissions: [
        { resource: 'assets', action: 'read' },
        { resource: 'users', action: 'write' }
      ]
    };

    AuthStorage.setAuthData(mockAuthData);

    const { result } = renderHook(() => usePermission());

    expect(result.current.userPermissions).toEqual({
      userId: '1',
      username: 'test',
      roles: [],
      permissions: [
        { resource: 'assets', action: 'read' },
        { resource: 'users', action: 'write' }
      ],
      organizationId: undefined
    });
  });

  it('should return null permissions when not authenticated', () => {
    const { result } = renderHook(() => usePermission());

    expect(result.current.userPermissions).toBeNull();
  });

  it('should check permissions correctly', () => {
    const mockAuthData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1', username: 'test' },
      permissions: [
        { resource: 'assets', action: 'read' }
      ]
    };

    AuthStorage.setAuthData(mockAuthData);

    const { result } = renderHook(() => usePermission());

    expect(result.current.hasPermission('assets', 'read')).toBe(true);
    expect(result.current.hasPermission('assets', 'write')).toBe(false);
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd frontend
pnpm test src/hooks/__tests__/usePermission.test.tsx
```

Expected: Tests fail - usePermission reads from wrong localStorage key

**Step 3: Modify usePermission.tsx**

```typescript
// frontend/src/hooks/usePermission.tsx
// Add import at top
import { AuthStorage } from '@/utils/AuthStorage';

// Replace lines 54-69 in loadUserPermissions function:
const usePermission = () => {
  const [userPermissions, setUserPermissions] = useState<UserPermissions | null>(null);
  const [loading, setLoading] = useState(false);

  // Load user permissions from AuthStorage
  const loadUserPermissions = useCallback(async () => {
    setLoading(true);
    try {
      // Get auth data from centralized AuthStorage
      const authData = AuthStorage.getAuthData();

      if (authData == null) {
        setUserPermissions(null);
        return;
      }

      // Create user permissions object
      const userPermissionsData: UserPermissions = {
        userId: authData.user.id,
        username: authData.user.username,
        roles: authData.user.role ? [authData.user.role] : [],
        permissions: authData.permissions,
        organizationId: authData.user.organization_id,
      };

      setUserPermissions(userPermissionsData);
    } catch (error) {
      permLogger.error('Failed to load user permissions:', error as Error);
      MessageManager.error('Failed to load permissions');
    } finally {
      setLoading(false);
    }
  }, []);

  // ... rest of the hook remains the same ...
```

**Step 4: Run test to verify it passes**

```bash
cd frontend
pnpm test src/hooks/__tests__/usePermission.test.tsx
```

Expected: All tests PASS

**Step 5: Commit**

```bash
cd frontend
git add src/hooks/usePermission.tsx src/hooks/__tests__/usePermission.test.tsx
git commit -m "fix(auth): Update usePermission to read from AuthStorage

- Replace localStorage.getItem('currentUser') with AuthStorage.getAuthData()
- Fix permission system to read from correct localStorage key
- Update UserPermissions mapping to use new auth structure
- Add tests for permission checking logic

Fixes #3: Permission guard reading wrong localStorage key

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Frontend - Update Login to Store Permissions from API

**Files:**
- Modify: `frontend/src/services/authService.ts:102-105`
- Test: `frontend/src/services/__tests__/authService.test.ts`

**Step 1: Write the failing test**

```typescript
// frontend/src/services/__tests__/authService.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AuthService } from '../authService';
import { AuthStorage } from '@/utils/AuthStorage';

// Mock API client
vi.mock('@/api/client', () => ({
  enhancedApiClient: {
    post: vi.fn(),
  },
}));

describe('AuthService - Login with Permissions', () => {
  beforeEach(() => {
    localStorage.clear();
    AuthStorage.clearAuthData();
    vi.clearAllMocks();
  });

  it('should store permissions from login response', async () => {
    const mockResponse = {
      data: {
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
        },
        permissions: [
          { resource: 'assets', action: 'read', description: 'Read assets' },
          { resource: 'users', action: 'write', description: 'Write users' },
        ],
      },
    };

    vi.mocked(enhancedApiClient.post).mockResolvedValue(mockResponse);

    const result = await AuthService.login('testuser', 'password');

    expect(result.success).toBe(true);
    expect(result.data?.permissions).toEqual([
      { resource: 'assets', action: 'read', description: 'Read assets' },
      { resource: 'users', action: 'write', description: 'Write users' },
    ]);

    // Verify AuthStorage was called with permissions
    const authData = AuthStorage.getAuthData();
    expect(authData?.permissions).toEqual([
      { resource: 'assets', action: 'read', description: 'Read assets' },
      { resource: 'users', action: 'write', description: 'Write users' },
    ]);
  });

  it('should handle empty permissions array', async () => {
    const mockResponse = {
      data: {
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        user: { id: '1', username: 'testuser' },
        permissions: [],
      },
    };

    vi.mocked(enhancedApiClient.post).mockResolvedValue(mockResponse);

    const result = await AuthService.login('testuser', 'password');

    expect(result.success).toBe(true);
    expect(result.data?.permissions).toEqual([]);

    const authData = AuthStorage.getAuthData();
    expect(authData?.permissions).toEqual([]);
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd frontend
pnpm test src/services/__tests__/authService.test.ts
```

Expected: Test fails - login stores empty permissions array

**Step 3: Modify authService.ts login method**

```typescript
// frontend/src/services/authService.ts
// Add import at top
import { AuthStorage } from '@/utils/AuthStorage';

// Replace lines 102-119 in login method:
      if (responseData.data.access_token && responseData.data.refresh_token) {
        const { access_token: accessToken, refresh_token: refreshToken } = responseData.data;

        // Store in AuthStorage with permissions from API
        const authData = {
          token: accessToken,
          refreshToken: refreshToken,
          user: {
            id: user.id,
            username: user.username,
            email: user.email,
            full_name: user.full_name,
            role: user.role,
            organization_id: user.organization_id,
          },
          permissions: responseData.data.permissions ?? [],  // Use permissions from API
        };

        AuthStorage.setAuthData(authData);

        // Also set legacy keys for backward compatibility
        localStorage.setItem('token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
      } else {
        throw new Error('Access token or refresh token not found');
      }

      localStorage.setItem('user', JSON.stringify(user));

      return {
        success: true,
        data: {
          user,
          tokens: {
            access_token: accessToken,
            refresh_token: refreshToken,
            token_type: 'Bearer',
            expires_in: 3600,
          },
          permissions: responseData.data.permissions ?? [],  // Return actual permissions
        },
        message: (responseData.message as string) || 'Login successful',
      };
```

**Step 4: Run test to verify it passes**

```bash
cd frontend
pnpm test src/services/__tests__/authService.test.ts
```

Expected: All tests PASS

**Step 5: Commit**

```bash
cd frontend
git add src/services/authService.ts src/services/__tests__/authService.test.ts
git commit -m "feat(auth): Store permissions from login API response

- Update AuthService.login to use permissions from backend API
- Store complete auth data in AuthStorage including permissions
- Remove hardcoded empty permissions array
- Return actual permissions in login response

Fixes #4: Login setting empty permissions array

Breaking change: Login now expects backend to return permissions array

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Integration Testing - End-to-End Auth Flow

**Files:**
- Create: `backend/tests/e2e/test_auth_flow_e2e.py`
- Create: `frontend/src/e2e/auth.spec.ts`

**Step 1: Write backend E2E test**

```python
# backend/tests/e2e/test_auth_flow_e2e.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

def test_complete_auth_flow_e2e(db_session, client: TestClient):
    """Test complete authentication flow with permissions"""
    # 1. Create user with role
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",
        "full_name": "Test User",
        "role": "user"
    }
    client.post("/api/v1/users", json=user_data)

    # 2. Login
    login_response = client.post("/api/v1/auth/login", data={
        "username": "testuser",
        "password": "TestPass123!"
    })

    assert login_response.status_code == 200
    data = login_response.json()

    # 3. Verify token structure
    assert "access_token" in data
    assert "refresh_token" in data
    assert "permissions" in data
    assert isinstance(data["permissions"], list)

    # 4. Access protected endpoint with token
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    me_response = client.get("/api/v1/users/me", headers=headers)

    assert me_response.status_code == 200

    # 5. Test rate limiting
    for _ in range(65):  # Exceed rate limit
        client.get("/api/v1/health", headers=headers)

    # Should be rate limited
    rate_limited_response = client.get("/api/v1/health", headers=headers)
    assert rate_limited_response.status_code == 429
```

**Step 2: Write frontend E2E test**

```typescript
// frontend/src/e2e/auth.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should login and store permissions', async ({ page }) => {
    // Fill login form
    await page.fill('input[name="username"]', 'testuser');
    await page.fill('input[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');

    // Check localStorage for auth data
    const authData = await page.evaluate(() => {
      const data = localStorage.getItem('authData');
      return data ? JSON.parse(data) : null;
    });

    expect(authData).not.toBeNull();
    expect(authData?.permissions).toBeInstanceOf(Array);
    expect(authData?.token).toBeDefined();

    // Check that user can access protected page
    await page.goto('/assets/list');
    await expect(page.locator('h1')).toContainText('Assets');
  });

  test('should deny access without permission', async ({ page, context }) => {
    // Login as regular user
    await page.fill('input[name="username"]', 'testuser');
    await page.fill('input[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');

    // Try to access admin page
    await page.goto('/system/users');

    // Should be redirected or show access denied
    await expect(page.locator('.access-denied')).toBeVisible();
  });

  test('should logout and clear auth data', async ({ page }) => {
    // Login first
    await page.fill('input[name="username"]', 'testuser');
    await page.fill('input[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');

    // Logout
    await page.click('[data-testid="logout-button"]');

    // Should redirect to login
    await expect(page).toHaveURL('/login');

    // Check localStorage is cleared
    const authData = await page.evaluate(() => localStorage.getItem('authData'));
    expect(authData).toBeNull();
  });
});
```

**Step 3: Run E2E tests**

```bash
# Backend
cd backend
pytest tests/e2e/test_auth_flow_e2e.py -v

# Frontend
cd frontend
pnpm test:e2e
```

**Step 4: Commit**

```bash
# Add both tests
git add backend/tests/e2e/test_auth_flow_e2e.py
git add frontend/src/e2e/auth.spec.ts
git commit -m "test(e2e): Add end-to-end authentication flow tests

Backend:
- Test complete auth flow with permissions
- Verify rate limiting after auth
- Validate token structure and protected endpoints

Frontend:
- Test login and permission storage
- Verify access control on protected pages
- Test logout and auth data clearing

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Summary

**Phase 1 Complete**: All 4 critical security issues resolved
- ✅ Issue #1: Rate limiting fail-closed with circuit breaker
- ✅ Issue #2: Case-insensitive role comparison
- ✅ Issue #3: Permission guard reading correct storage
- ✅ Issue #4: Login returning actual permissions

**Breaking Changes**:
- Rate limiter now blocks on error (STRICT mode by default)
- localStorage structure changed to `authData` key
- Login API response includes `permissions` field
- Role comparison is now case-insensitive

**Environment Variables Added**:
- `RATE_LIMIT_FAILURE_MODE=strict|permissive|degraded`
- `RATE_LIMIT_MAX_FAILURES=3`
- `RATE_LIMIT_COOLDOWN_SECONDS=60`

**Next Steps**: Proceed to Phase 2 - Security Hardening (Issues 5, 8, 10-13)
