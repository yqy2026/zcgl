# Phase4 No-Go SQL Snapshot（2026-03-02）

## 执行命令

```bash
cd backend
DB_URL="$(./.venv/bin/python -c 'from src.core.config import settings; print(settings.DATABASE_URL)' 2>/tmp/phase4-db-url.log)"
PHASE4_TENANT_NOT_NULL_DECISION=B ./.venv/bin/python -m src.scripts.migration.party_migration.phase4_no_go_snapshot \
  --database-url "$DB_URL" \
  --format markdown \
  --enforce
```

## 输出

# Phase4 No-Go SQL Snapshot

- generated_at_utc: `2026-03-02T04:16:15Z`
- tenant_decision: `B`
- result: `PASS`

## Snapshot
| metric | value |
|---|---|
| `assets_manager_null` | `0` |
| `assets_owner_null` | `0` |
| `ledger_owner_null` | `0` |
| `projects_manager_null` | `0` |
| `rc_manager_null` | `0` |
| `rc_owner_null` | `0` |
| `subject_count` | `0` |
| `subject_table` | `null` |
| `tenant_null_count` | `0` |
| `tenant_total_count` | `0` |
| `user_dual_party_viewer_mapping_count` | `1` |

## Gate Results
| gate | status | actual | expected |
|---|---|---|---|
| `subject_count_zero` | `PASS` | `0` | `=0` |
| `assets_owner_null_zero` | `PASS` | `0` | `=0` |
| `assets_manager_null_zero` | `PASS` | `0` | `=0` |
| `rc_owner_null_zero` | `PASS` | `0` | `=0` |
| `rc_manager_null_zero` | `PASS` | `0` | `=0` |
| `ledger_owner_null_zero` | `PASS` | `0` | `=0` |
| `projects_manager_null_zero` | `PASS` | `0` | `=0` |
| `user_dual_party_viewer_mapping_ge_1` | `PASS` | `1` | `>=1` |
| `tenant_decision_declared` | `PASS` | `B` | `A|B` |
| `tenant_null_zero_when_decision_a` | `SKIP` | `0` | `SKIP_WHEN_DECISION_B` |
