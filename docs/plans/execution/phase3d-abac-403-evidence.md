# Phase 3d ABAC 403 结构化拒绝证据

> 用途：关闭 P3d 门禁中“ABAC 403 结构化拒绝标识”`Re-verify` 状态，补齐代码与样例证据。

## 元信息
- 日期：`2026-02-27`
- 责任人：`phase3-preflight`
- release-id：`phase3-preflight-20260227`
- 范围：`Phase 3d authz/forbidden response`

## 结论
1. 后端 403 业务拒绝统一使用 `error.code = "PERMISSION_DENIED"`。
2. 响应结构稳定为 `{"success": false, "error": {...}}`，可供前端 refresh 精确触发。
3. `error_code=AUTHZ_DENIED` 当前未作为主返回字段；前端可保留兼容降级匹配，但主路径应优先 `error.code`。

## 代码证据
1. `PermissionDeniedError` 固定编码为 `PERMISSION_DENIED`：
   - `backend/src/core/exception_handler.py:124`
   - `backend/src/core/exception_handler.py:135`
2. 标准错误结构由 `BaseBusinessError.to_dict()` 统一输出：
   - `backend/src/core/exception_handler.py:41`
   - `backend/src/core/exception_handler.py:50`
3. 所有 `forbidden(...)` 便捷入口都回到 `PermissionDeniedError`：
   - `backend/src/core/exception_handler.py:616`
   - `backend/src/core/exception_handler.py:617`

## 测试证据
1. Admin API 单测校验 403 响应 `error.code`：
   - `backend/tests/unit/api/v1/test_admin.py:124`
   - `backend/tests/unit/api/v1/test_admin.py:126`
   - `backend/tests/unit/api/v1/test_admin.py:155`
   - `backend/tests/unit/api/v1/test_admin.py:157`
2. E2E 认证流校验普通用户访问受限接口返回 `PERMISSION_DENIED`：
   - `backend/tests/e2e/test_auth_flow_e2e.py:327`
   - `backend/tests/e2e/test_auth_flow_e2e.py:332`

## 403 样例（本地生成）
执行命令：
```bash
cd backend
.venv/bin/python - <<'PY'
from src.core.exception_handler import forbidden
import json
print(json.dumps(forbidden("权限不足").to_dict(), ensure_ascii=False, indent=2))
PY
```

输出样例：
```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "权限不足",
    "details": {
      "required_permission": null
    },
    "timestamp": "2026-02-27T04:44:27.918791+00:00"
  }
}
```
