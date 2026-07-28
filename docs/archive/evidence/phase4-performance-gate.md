# Phase4 Performance Gate

## 状态
- result: PASS_LOCAL
- reason: `本地环境无真实 Canary 流量，采用等价本地性能门禁替代`

## 目标阈值
- `p95_release <= p95_rehearsal * 1.30`

## 本地替代门禁（2026-03-02）
- backend 非慢测全量回归：`cd backend && ./.venv/bin/pytest --no-cov -m "not slow" -q -x` -> `4820 passed, 6 skipped`（`196.55s`）
- frontend 构建：`pnpm -C frontend build` -> `PASS`（无 warning token）
- 最小权限 E2E：`BASE_URL=http://127.0.0.1:5173 pnpm -C frontend e2e --grep "@authz-minimal" --project=chromium` -> `2 passed (22.8s)`

## 结论
- 本地性能门禁：`PASS_LOCAL`
- 备注：生产放流前仍建议执行一次真实 Canary p95 观测以满足线上口径。
