# Phase4 Error Rate Gate

## 状态
- result: PASS_LOCAL
- reason: `本地环境无真实在线流量，采用本地错误率替代门禁`

## 目标阈值
- 连续 10 分钟每分钟 `5xx_rate <= 1%`

## 本地替代门禁（2026-03-02）
- No-Go SQL 快照：`phase4_no_go_snapshot --enforce` -> `result: PASS`（关键计数均为 `0` 或满足阈值）
- backend 非慢测全量回归：`4820 passed, 6 skipped`（无失败用例）
- frontend 全量单测：`pnpm -C frontend test` -> `PASS`
- authz 最小权限 E2E：`2 passed`

## 结论
- 本地错误率门禁：`PASS_LOCAL`
- 备注：线上放流前仍建议执行真实 Canary 连续 10 分钟 5xx 观测。
