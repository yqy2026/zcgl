# Phase4 X-Authz-Stale Contract Evidence

## 状态
- result: `PASS_LOCAL`

## 合同项
1. Header 名称：`X-Authz-Stale`
2. 触发场景：请求携带 `X-View-Perspective` / `X-View-Party-Id`，且该“当前视角”已不在用户最新 `owner/manager` 作用域内，并因此命中鉴权拒绝链路
3. 预期结果：
- 仅“失效视角导致的拒绝”返回 `X-Authz-Stale: true`
- 普通 `403/404` 不返回该头
- `deny_as_not_found=True` 的掩码详情接口在返回 `404` 时仍保留该头

## 代码与测试证据（本地）
1. 代码落地
- `backend/src/core/exception_handler.py` 仅在业务异常显式标记 `authz_stale=True` 时注入 `X-Authz-Stale: true`。
- `backend/src/middleware/auth_authz.py` 在鉴权拒绝时对比 `X-View-*` 与当前 `SubjectContext`；若视角已失效，则在 `403` 或掩码 `404` 上标记 `authz_stale=True`。
- `frontend/src/api/client.ts` 仅消费 `403/404 + X-Authz-Stale`，并要求失败请求仍匹配当前已保存视角，避免晚到旧请求重复广播 stale 事件。
- `frontend/src/contexts/AuthContext.tsx` 对并发 `authz-stale` 事件做 single-flight 合并，避免刷新风暴与重复 toast。

2. 单测留痕
- 用例文件：
  - `backend/tests/unit/core/test_exception_handling.py`
  - `backend/tests/unit/middleware/test_authz_dependency.py`
  - `frontend/src/api/__tests__/client.test.ts`
  - `frontend/src/hooks/__tests__/useAuth.test.ts`
- 覆盖点：
  - 普通 `forbidden()` / `HTTPException(403)` 不再携带 `X-Authz-Stale`
  - `forbidden(..., authz_stale=True)` 与 `not_found(..., authz_stale=True)` 会携带该头
  - 失效视角命中普通 `403` 时保留 stale 标记
  - 失效视角命中掩码 `404` 时保留 stale 标记
  - 前端会消费 `404 + X-Authz-Stale`
  - 前端会忽略已清空/已切换视角的晚到 stale 响应
  - `AuthContext` 对并发 stale 事件只发起一轮刷新
- 命令：
  - `cd backend && uv run python -m pytest --no-cov tests/unit/core/test_exception_handling.py::TestAuthzStaleHeaderContract tests/unit/middleware/test_authz_dependency.py::test_require_authz_denied_write_with_stale_selected_view_marks_authz_stale tests/unit/middleware/test_authz_dependency.py::test_require_authz_denied_read_with_stale_selected_view_keeps_not_found_and_marks_stale -q`
  - `cd frontend && pnpm exec vitest run src/api/__tests__/client.test.ts src/hooks/__tests__/useAuth.test.ts`
- 结果：
  - backend: `7 passed`
  - frontend: `44 passed`

## 待窗口联调证据
1. 本地 HTTP 拒绝样例（建议更新）
- 执行方式：使用已保存失效视角访问一个 `deny_as_not_found=True` 的详情端点（如 `GET /api/v1/system/contacts/{id}`）
- 结果：`status_code=404`，`X-Authz-Stale=true`

2. 生产窗口补充（可选）
- 如需线上闭环，可继续补充“默认视角失效后的真实账号请求样例”并附 header 原文。
