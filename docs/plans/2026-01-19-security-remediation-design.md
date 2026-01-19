# Security and Feature Remediation Design

**Date**: 2026-01-19
**Scope**: Full system remediation addressing 13 critical security and functionality issues
**Approach**: Comprehensive overhaul with breaking changes, 4-week phased timeline

## Executive Summary

This document outlines a complete remediation of the zcgl (土地物业资产管理系统) codebase to address critical security vulnerabilities, broken functionality, and technical debt. The remediation follows a comprehensive overhaul philosophy, accepting breaking changes to achieve production-grade security and functionality.

**Key Decisions**:
- Accept breaking changes to fix issues properly
- Use httpOnly cookies instead of localStorage for tokens
- Implement case-insensitive role comparison system
- Standardize all API paths to `/api/v1` prefix
- Fail-closed rate limiting with circuit breaker pattern

## Timeline

| Phase | Duration | Focus | Risk |
|-------|----------|-------|------|
| 1: Critical Security Foundation | Week 1 | Auth, permissions, rate limiting | High |
| 2: Security Hardening | Week 2 | Monitoring, token security, IP whitelist | Medium-High |
| 3: Feature Completion | Week 3 | Asset matching, export, profile management | Medium |
| 4: Validation & Hardening | 3-4 days | Testing, documentation, security audit | Low |

## Phase 1: Critical Security Foundation (Issues 1-4)

### Issue #1: Rate Limiting Fail-Open
**Problem**: Adaptive rate limiting catches exceptions and allows requests through, creating a fail-open security vulnerability.

**Solution**: Implement fail-closed rate limiting with circuit breaker pattern.

- Create `RateLimitStrategy` enum: `STRICT`, `PERMISSIVE`, `DEGRADED`
- Add circuit breaker: after 3 failures, enable strict mode temporarily
- Implement metrics tracking for rate limiter health
- Environment variable: `RATE_LIMIT_FAILURE_MODE=strict|permissive|degraded`

**Breaking Change**: Default behavior changes from fail-open to fail-closed.

### Issue #2: Admin Role Mismatch
**Problem**: Code checks for "ADMIN" but actual role is "admin", breaking admin permissions.

**Solution**: Standardize on case-insensitive role comparison.

- Create `RoleNormalizer` utility class for all role operations
- Define roles as enum/constants: `Role.ADMIN`, `Role.USER`, `Role.MODERATOR`
- Database migration to normalize existing role data
- Update all role checks: `if user.role.lower() == Role.ADMIN.value.lower()`

**Breaking Change**: API responses return normalized role names.

### Issue #3 & #4: Permission System Broken
**Problem**: Frontend reads `localStorage.getItem('currentUser')` but code writes `authData`, and login returns empty permissions array.

**Solution**: Redesign frontend permission storage to match backend.

- Create unified `AuthStorage` class for all auth-related localStorage operations
- Update login API to return real permissions from backend
- Implement permission caching with TTL
- Create `PermissionManager` class: `hasPermission()`, `refreshPermissions()`, `clearPermissions()`

**Breaking Change**: localStorage structure changes from `authData` to `{token, user, permissions, metadata}`.

**Team Coordination**:
- Backend: Update login API to return permissions
- Frontend: Implement new permission storage system
- Together: Design auth token/permission contract

## Phase 2: Security Hardening (Issues 5, 8, 10-13)

### Issue #5: Security Monitoring System
**Problem**: Permission failures log to console with no alerting (just TODO comments).

**Solution**: Implement structured security event logging with monitoring integration.

- Create `SecurityEventLogger` class with event types
- Integrate with monitoring stack (Prometheus/Grafana or cloud-native)
- Alert on thresholds (e.g., 10 failures from same IP in 1 minute)
- Create security dashboard in admin panel
- Add webhook integration for Slack/email alerts

**Breaking Change**: New environment variables for monitoring endpoints.

### Issue #8: Standardize API Paths
**Problem**: `AuthContext` calls `/auth/refresh` directly instead of `/api/v1/auth/refresh`.

**Solution**: Centralize API client configuration to enforce `/api/v1` prefix.

- Update `ApiClient` to throw build-time error on non-prefixed URLs
- Deprecate direct `fetch()` calls in auth context
- Add API version negotiation support
- Create `ApiClient` methods: `refreshToken()`, `revokeToken()`, `validateToken()`

**Breaking Change**: All API calls must go through `ApiClient`.

### Issue #10: IP Whitelist Security
**Problem**: Whitelist includes `0.0.0.0` and broad ranges, potentially bypassing protections.

**Solution**: Redesign as explicit allowlist with strict validation.

- Remove `0.0.0.0` and overly broad ranges (default-deny)
- Add IP range validation: reject private ranges in production
- Create `IPWhitelistManager`: `isAllowed()`, `addRange()`, `validateRange()`
- Environment-based defaults: development (permissive) vs production (strict)
- Implement CIDR notation support
- Add audit logging for modifications

**Breaking Change**: Existing whitelist configs reset to safe defaults.

### Issues #11-12: Token Security
**Problem**: Incomplete cleanup and XSS risk from localStorage token storage.

**Solution**: Migrate to httpOnly, secure, SameSite cookies.

- Backend sets cookies on login, frontend never sees tokens
- Add CSRF token rotation on each request
- Implement strict CORS validation
- Remove all token handling from localStorage

**Breaking Change**: Complete auth flow redesign, requires backend cookie support.

### Issue #13: Secret Management
**Problem**: `.env.example` contains default SECRET_KEY, encouraging weak secrets.

**Solution**: Remove defaults and add validation.

- Replace default with generation command in `.env.example`
- Add startup validation that rejects weak secrets
- Implement secret rotation support in deployment scripts
- Add vault integration support (HashiCorp, AWS, Azure)
- Create pre-commit hook to validate .env files

**Breaking Change**: Development environments must generate proper secrets on first run.

## Phase 3: Feature Completion (Issues 6, 7, 9)

### Issue #6: Property Certificate Asset Matching
**Problem**: Asset matching returns empty `asset_matches` array, feature not implemented.

**Solution**: Implement fuzzy matching algorithm with confidence scoring.

**Backend**:
- Create `AssetMatcher` class with match strategies:
  - Exact match: Certificate ID + property address
  - Fuzzy match: Address similarity using Levenshtein distance (>80%)
  - Partial match: Certificate ID match, address needs verification
- Add confidence scores: `HIGH`, `MEDIUM`, `LOW`
- Endpoint: `POST /api/v1/property-certificates/{id}/match-assets`
- Add batch matching for bulk uploads
- Implement manual override workflow

**Frontend**:
- Create `AssetMatchReview` component
- Show confidence scores with visual indicators
- Allow manual linking/unlinking of assets
- Add bulk actions: "Auto-match all", "Review matches"

**Data Model**:
- Add `asset_matches` JSONB field for match history
- Track who approved/verified each match (audit trail)

### Issue #7: Analytics Dashboard Export
**Problem**: Export button exists with no implementation.

**Solution**: Implement multi-format export system.

- Create `ExportService` with format handlers:
  - Excel: Formatted cells, charts, conditional formatting
  - CSV: Delimiter-based with UTF-8 BOM
  - PDF: Table generation and charts
- Add export configuration dialog:
  - Date range selector
  - Metric checkboxes
  - Format selection
  - Include/exclude charts
- Implement async export for large datasets (>10,000 rows)
- Add branding: logo, title, timestamp
- Cache export results for 1 hour

### Issue #9: Profile Update API Mismatch
**Problem**: `updateProfile` calls password change endpoint instead of profile update endpoint.

**Solution**: Create proper profile management endpoints.

- `PATCH /api/v1/users/me` - Update profile (name, email, phone)
- `PUT /api/v1/users/me/password` - Change password (separate)
- `PUT /api/v1/users/me/avatar` - Upload profile picture

**Frontend Refactor**:
- `updateProfile(data: ProfileUpdateDTO)` - User info
- `changePassword(data: PasswordChangeDTO)` - Password
- `updateAvatar(file: File)` - Avatar

**Additional Features**:
- Profile validation (email uniqueness, phone format)
- Optimistic updates in UI
- Profile change history (audit log)

## Phase 4: Validation & Hardening

### Testing Strategy

**Backend**:
- Unit tests for each fixed component
- Integration tests for API endpoints and permission flows
- Security tests (attempt to exploit fixed vulnerabilities)
- Load tests for rate limiting and concurrent auth
- Target: 80%+ coverage for security-critical code

**Frontend**:
- Component tests for permission guards and auth flows
- E2E tests for complete user journeys
- Security tests (XSS attempts, token storage verification)
- Integration tests for frontend-backend contracts

**Manual Testing Checklist**:
- [ ] Admin can access all features
- [ ] Regular users restricted properly
- [ ] Rate limiting blocks abusive requests
- [ ] Token refresh works without page reload
- [ ] Permission failures trigger alerts
- [ ] Export generates all formats
- [ ] Asset matching suggests candidates
- [ ] Profile updates work independently

### Migration Guides

**For Developers**:
- New auth storage structure (old keys deprecated)
- API path changes (all use `/api/v1` prefix)
- Role normalization (case-insensitive comparison)
- Environment variable additions

**For DevOps**:
- Required environment variables (monitoring, rate limiting)
- Secret generation process for deployments
- IP whitelist configuration changes
- Cookie domain/path configuration

**For Users**:
- One-time re-authentication required
- New permission model explanation
- Export feature availability announcement

### Security Audit

- Run dependency vulnerability scans (`pip-audit`, `npm audit`)
- Review all middleware for security gaps
- Validate CORS configuration
- Test SQL injection prevention
- Verify file upload restrictions
- Check for information disclosure in error messages
- Add security headers (CSP, X-Frame-Options)

### Performance Validation

- Permission checks: <50ms with caching
- Export system: handle 100k+ rows via backend generation
- Asset matching: optimize batch uploads
- Rate limiter overhead: <5ms per request

### Documentation Updates

- Update `CLAUDE.md` with new architecture patterns
- Document cookie-based auth flow
- Add security section to README
- Create troubleshooting guide
- Document export formats and limitations
- Add API documentation for new endpoints

## Risk Mitigation

### High-Risk Items

**Cookie-based Auth Migration**:
- Plan rollback strategy
- Keep old auth endpoint for 1 week
- Gradual rollout with feature flags

**Role Normalization**:
- Database backup before migration
- Test on staging first
- Create rollback migration script

**IP Whitelist Changes**:
- Maintain emergency access method
- Document override procedures
- Test whitelist validation before deploy

### Rollback Plan

- Feature flags for each phase
- Database migrations designed to be reversible
- Keep old code branches for 2 weeks post-deployment
- Emergency access procedures documented

## Team Coordination

### Week 1: Phase 1
- Days 1-2: Backend foundation (rate limiting, roles, login API)
- Days 3-4: Frontend permission system (AuthStorage, PermissionManager)
- Day 5: Integration testing

### Week 2: Phase 2
- Days 1-2: Token security overhaul (cookies, CSRF)
- Day 3: Monitoring and IP whitelist
- Days 4-5: API standardization and secrets

### Week 3: Phase 3
- Days 1-3: Asset matching system
- Days 4-5: Export and profile features

### Week 4: Phase 4
- Days 1-2: Testing and validation
- Day 3: Documentation and migration
- Day 4: Final validation and deployment prep

## Success Criteria

1. All 13 issues resolved with comprehensive fixes
2. Security test suite passes with 80%+ coverage
3. Manual testing checklist completed
4. Migration guides written and reviewed
5. Performance benchmarks met
6. Rollback plan validated
7. Full documentation updated

## Next Steps

1. Review and approve this design
2. Create git worktrees for isolated branches
3. Generate detailed task breakdown
4. Set up staging environment for testing
5. Begin Phase 1 implementation
