# TODO/FIXME Debt Plan

Last updated: 2026-02-02

## Scope and counting method
- Command: `git grep -n "\bTODO\b\|\bFIXME\b"`
- Result (tracked files): 0 TODO/FIXME comments in code or tests; matches appear only in audit documents.
- Note: An audit report (2026-02-01) claims 927 TODO/FIXME/HACK items, likely from a broader scan (ignored/untracked/vendor or a different snapshot). Reconciliation is tracked below.

## Policy for new TODO/FIXME
- Format: `TODO(ID): short description` or `FIXME(ID): short description`
- Each entry must have a tracking issue and include: owner, priority (P0-P3), target date (<= 90 days), and status.
- No merge if a new TODO/FIXME lacks an ID and target date (enforce via lint/CI when ready).
- Review cadence: triage every 2 weeks; debt review monthly.

## Plan template
| ID | Description | File path | Priority | Owner | Target date | Status | Tracking issue |
|---|---|---|---|---|---|---|---|
| TODO-XXX-000 | Short actionable text | path/to/file.ext:line | P2 | name | YYYY-MM-DD | open | JIRA-123 / GH-123 |

## Seeded backlog (from current repo TODO list)
| ID | Description | File path | Priority | Owner | Target date | Status | Tracking issue |
|---|---|---|---|---|---|---|---|
| TODO-SEC-001 | IP blacklist configuration support | backend/src/security/ip_blacklist.py | P2 | Codex | 2026-02-28 | done (per audit) | n/a |
| TODO-SEC-002 | Adaptive rate limiting configuration support | backend/src/security/rate_limiting.py | P2 | Codex | 2026-02-28 | done (per audit) | n/a |
| TODO-SEC-003 | Request limit configuration support | backend/src/security/rate_limiting.py | P2 | Codex | 2026-02-28 | done (per audit) | n/a |
| TODO-SEC-004 | Security analyzer configuration support | backend/src/security/security_analyzer.py | P2 | Codex | 2026-02-28 | done (per audit) | n/a |
| TODO-SEC-005 | Security middleware configuration support | backend/src/security/security_middleware.py | P2 | Codex | 2026-02-28 | done (per audit) | n/a |
| TODO-OPS-001 | Monitoring integration (Sentry, etc.) | backend/src/api/v1/system/system_settings.py | P2 | Codex | 2026-03-31 | done (per audit) | n/a |
| TODO-ANA-001 | Financial summary and occupancy statistics | backend/src/api/v1/analytics/statistics_modules/basic_stats.py | P2 | Codex | 2026-03-15 | done (per audit) | n/a |

## Reconciliation task
| ID | Description | Owner | Target date | Status |
|---|---|---|---|---|
| TODO-AUDIT-000 | Reconcile the 927 TODO/FIXME/HACK audit count with a reproducible scan (include ignored/vendor/untracked if needed) and update this plan. | TBD | 2026-02-09 | open |
