# Phase4 X-Authz-Stale Contract Evidence

## 状态
- result: `PASS_LOCAL`

## 合同项
1. Header 名称：`X-Authz-Stale`
2. 触发场景：非管理员命中 admin-only 端点拒绝链路
3. 预期结果：HTTP `401/403` 且响应头包含 `X-Authz-Stale`

## 代码与测试证据（本地）
1. 代码落地
- `backend/src/core/exception_handler.py` 已在统一异常处理链中对 `401/403` 响应注入 `X-Authz-Stale: true`。
- 探针：`rg -n "X-Authz-Stale" backend/src` 命中 `src/core/exception_handler.py`。

2. 单测留痕
- 用例文件：`backend/tests/unit/core/test_exception_handling.py`
- 覆盖点：
  - `forbidden()` -> 403 响应包含 `X-Authz-Stale`
  - `HTTPException(403)` -> 响应包含 `X-Authz-Stale`
  - 非鉴权错误（400）-> 不包含该头
- 命令：`cd backend && ./.venv/bin/pytest --no-cov tests/unit/core/test_exception_handling.py -q`
- 结果：`11 passed`

## 待窗口联调证据
1. 本地 HTTP 拒绝样例（2026-03-02）
- 执行方式：`fastapi.testclient` 访问 `GET /api/v1/system/backup/stats`（未授权请求）
- 结果：`status_code=401`，`X-Authz-Stale=true`

2. 生产窗口补充（可选）
- 如需线上闭环，可继续补充“非管理员真实 token”拒绝样例并附 header 原文。
