# 土地物业资产管理系统（AI拼凑项目）代码审计报告（专家视角）

**审计日期**：2026-01-31  
**审计范围**：`backend/src`、`frontend/src`、关键配置与安全模块  
**审计方式**：静态审阅 + 关键路径搜索（未运行应用与自动化测试）

---

## 严重程度定义
- **P0（致命）**：安全/数据完整性高风险，或可导致系统不可用
- **P1（高）**：核心功能错误、配置失效、或稳定性严重下降
- **P2（中）**：功能缺陷、可维护性问题、潜在性能/可靠性问题
- **P3（低）**：可优化项、工程规范问题

---

## 执行摘要
本项目具有较完整的分层结构，但存在多处“AI拼凑式”不一致与半成品问题：
- **安全与认证链路存在关键一致性缺陷**（JWT iss/aud、黑名单逻辑/降级策略）。
- **数据加密“版本化”承诺实际未兑现**，密钥轮换将导致解密失败。
- **缓存体系重复且配置失效**，Redis 配置在多个模块中未被正确使用。
- **部分功能声明与实现不一致**（如产权证图片上传、PII搜索）。
- **系统级接口存在鉴权缺失与组织权限空实现**，可能导致未授权访问或跨组织越权。

这些问题若进入生产，会造成安全绕过、功能失败、以及不可预测的数据行为。

---

## 关键问题清单（按严重度）

### P0-01 Token 黑名单逻辑失效 + 失败时默认放行
**证据**：
- `backend/src/security/token_blacklist.py:21-70`（黑名单为内存集合，`revoke_all_user_tokens` 写入通配符）
- `backend/src/security/token_blacklist.py:45-50`（`is_blacklisted` 仅做精确命中）
- `backend/src/middleware/auth.py:32-52`（检查失败/熔断时 **允许 token**）
- `backend/src/core/config.py:118-119`（`TOKEN_BLACKLIST_ENABLED` 配置未见使用）

**问题说明**：
- `revoke_all_user_tokens()` 写入 `pattern_user_*`，但 `is_blacklisted()` 仅做 `jti in set`，导致“撤销全量 token”无效。
- 黑名单为进程内内存集合，多实例部署时无法共享，重启即失效。
- 熔断/异常时直接放行 token，撤销机制在故障时完全失效。

**影响**：撤销、登出、强制踢下线在生产中不可靠，存在安全绕过风险。

**建议**：
- 黑名单改为 Redis 或数据库持久化；
- 实现 pattern 匹配或改为存储 session-id 并做统一校验；
- 熔断策略应优先“拒绝”而非“放行”，或至少记录高危告警；
- `TOKEN_BLACKLIST_ENABLED` 必须落地控制逻辑。

**修复进展（2026-01-31）**：
- Token 黑名单在 `REDIS_ENABLED=true` 时写入 Redis（带 TTL），保留内存回退；
- 用户级撤销记录已参与黑名单校验；
- 黑名单检查在生产环境失败时默认拒绝。

**验证进展（2026-02-01）**：
- 新增单测覆盖黑名单熔断与异常路径，生产环境 fail-closed、非生产 fail-open。
- 新增集成测试覆盖黑名单 token 访问受保护接口时返回 401。

---

### P0-02 JWT 配置与实际实现不一致（iss/aud硬编码）
**证据**：
- `backend/src/core/config.py:109-113`（配置 `JWT_ISSUER/JWT_AUDIENCE`）
- `backend/src/services/core/authentication_service.py:137-155`（硬编码 `aud/iss`）
- `backend/src/middleware/auth.py` 中 decode 同样硬编码 `audience/issuer`

**问题说明**：
配置中有 issuer/audience，但生成与校验阶段均使用硬编码值，导致环境配置无效。

**影响**：
- 配置变更无法生效；
- 多服务/多环境之间 token 可能互不兼容；
- 增加排障成本。

**建议**：统一使用 `settings.JWT_ISSUER/JWT_AUDIENCE`，并在生成与校验时一致引用。

**修复进展（2026-01-31）**：
- 生成与校验已统一读取 `settings.JWT_ISSUER/JWT_AUDIENCE`（`authentication_service` / `middleware.auth`），环境配置可生效。

**验证进展（2026-02-01）**：
- `cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/services/core/test_authentication_service.py --no-cov` 通过（验证 JWT issuer/audience 读取配置与黑名单调用参数）。

---

### P0-03 加密“版本化”未真正生效，密钥轮换会破坏解密
**证据**：
- `backend/src/core/encryption.py:278-297`（解析 version 但未使用）
- `backend/src/core/encryption.py:393-410`（标准加密同样忽略 version）

**问题说明**：
密文格式含版本号，但解密始终使用当前 key，未根据版本选择密钥。

**影响**：
- 密钥轮换后，旧数据无法解密（解密返回 None）；
- 数据完整性和可追溯性风险。

**建议**：
- 实现多版本密钥管理（至少保留旧 key）；
- 解密根据 version 选择对应密钥；
- 对旧数据执行迁移或按需重加密。

**修复进展（2026-01-31）**：
- `EncryptionKeyManager` 支持多版本密钥加载；
- `decrypt_deterministic` / `decrypt_standard` 按密文中的版本号选择密钥解密。

**验证进展（2026-02-01）**：
- `cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/core/test_encryption.py --no-cov` 通过（验证密钥轮换后旧数据可解密）。

---

### P0-04 任务配置接口缺少认证/权限控制（未授权可读写）
**证据**：
- `backend/src/api/v1/system/tasks.py:312-367`（Excel 配置查询/详情无 `current_user` 依赖）
- `backend/src/api/v1/system/tasks.py:380-414`（更新/删除 Excel 配置无认证或权限检查）

**问题说明**：
Excel 任务配置相关接口未强制认证，任何未登录用户可查询、更新或删除配置。

**影响**：
- 配置被未授权篡改，可能导致任务执行逻辑异常或数据损坏；
- 配置泄露（若包含敏感字段/路径）；
- 破坏系统稳定性与可追溯性。

**建议**：
- 为所有配置管理接口统一加 `Depends(get_current_active_user)` 并叠加 RBAC 权限；
- 与 `create_excel_config` 的权限策略保持一致；
- 增加审计日志记录（读写均记录）。

**修复进展（2026-01-31）**：
- Excel 配置接口已统一加 RBAC 认证（`excel_config:read/write`），未登录访问被拒绝。

**验证进展（2026-02-01）**：
- `cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/api/v1/test_tasks.py --no-cov` 通过（验证未认证访问 Excel 配置接口返回 401/403）。

---

### P1-01 资产 PII 搜索逻辑未实现（搜索结果错误）
**证据**：
- `backend/src/crud/asset.py:378-389`（搜索加密逻辑为 `pass`）
- `backend/src/crud/query_builder.py:244-250`（统一使用 `ILIKE`）

**问题说明**：
资产表对 `address/ownership_entity` 进行确定性加密，但搜索仍用 `ILIKE` 且未加密 search term，导致 PII 搜索永远命不中。

**影响**：
- 用户搜索“地址/权属方”几乎无结果；
- 业务误判为“数据缺失”。

**建议**：
- 搜索 PII 字段时，先对搜索词做确定性加密，并走“精确匹配”；
- 或取消对这些字段的模糊搜索入口。

**修复进展（2026-01-31）**：
- 资产列表搜索已对 `address/ownership_entity` 做确定性加密匹配（加密启用时），未启用时回退为 ILIKE；
- 同步与异步路径均使用相同的搜索条件构建。

**验证进展（2026-02-01）**：
- 新增集成测试覆盖地址/权属方加密搜索，验证启用加密时可命中并返回解密结果。

---

### P1-02 缓存体系重复且配置失效（Redis未真正接入）
**证据**：
- `backend/src/core/cache_manager.py:153-163`（默认 MemoryCache）
- `backend/src/core/cache_manager.py:160-162` 使用 `CACHE_KEY_PREFIX`，但配置中为 `CACHE_PREFIX`
- `backend/src/utils/cache_manager.py:29-37`（硬编码 Redis 设置，不使用全局配置）
- `backend/src/utils/cache_manager.py:83-103`（`ping()` 未 await）
- `backend/src/utils/cache_manager.py:234-240`（`initialize()` 未见调用）
- `backend/src/core/performance.py:288-296`（第三套 CacheManager，仅内存）

**问题说明**：
存在至少三套缓存管理实现，配置不统一且 Redis 没有被可靠初始化。

**影响**：
- 生产环境缓存不一致、跨进程失效；
- 配置看似已启用 Redis，但实际未生效；
- 难以定位缓存问题。

**建议**：
- 收敛为单一缓存实现；
- 统一读取 `settings`；
- 在应用启动时明确初始化并校验 Redis 连接；
- 修正 `CACHE_PREFIX`/`CACHE_KEY_PREFIX` 命名错误。

已确认 `main.py` 应用启动生命周期会调用 `utils.cache_manager.initialize()`，核心缓存初始化由 `core.cache_manager` 统一处理。

**修复进展（2026-01-31）**：
- `utils.cache_manager` 已统一委托到 `core.cache_manager`，避免多套实现分叉；
- 缓存前缀使用 `CACHE_PREFIX`，兼容旧 `CACHE_KEY_PREFIX`；
- Redis 使用核心缓存统一初始化与连接测试（失败时降级为内存）。

**验证进展（2026-02-01）**：
- `cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/utils/test_cache_manager_unified.py --no-cov` 通过（验证 utils.cache_manager 委托 core 缓存并清理 pattern 生效）。

---

### P1-03 产权证上传允许图片，但安全文件名只允许 PDF
**证据**：
- `backend/src/api/v1/assets/property_certificate.py:63-88`

**问题说明**：
入口允许 `.jpg/.jpeg/.png`，但 `generate_safe_filename(... allowed_extensions=["pdf"])` 只允许 PDF。

**影响**：
- 图片上传会抛异常并返回 500；
- 与接口说明不一致。

**建议**：
- `allowed_extensions` 参数应与校验入口保持一致；
- 失败时返回 4xx 并提示正确格式。

**修复进展（2026-01-31）**：
- 上传端点 `allowed_extensions` 与安全文件名生成保持一致（支持 .pdf/.jpg/.jpeg/.png）。

**验证进展（2026-02-01）**：
- `cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/api/v1/test_property_certificate.py --no-cov` 通过（验证图片格式上传允许通过）。

---

### P1-04 前端自动刷新 token 可能陷入递归 401 循环
**证据**：
- `frontend/src/api/client.ts:327-352`（401 时调用 `/auth/refresh`，未对 refresh 请求自身做排除）

**问题说明**：
若 refresh 也返回 401，拦截器会再次进入刷新逻辑，形成递归重试链路。

**影响**：
- 前端陷入无限刷新/跳转；
- 用户体验极差，可能触发接口风暴。

**建议**：
- 若 `originalRequest.url` 为 `/auth/refresh`，直接拒绝并登出；
- 或设置全局“refresh in-progress”与失败熔断标记。

**修复进展（2026-01-31）**：
- 前端拦截器已显式排除 refresh 请求并在 401 时登出，避免递归刷新。

**验证进展（2026-02-01）**：
- 新增 ApiClient 单测覆盖 refresh 401 直接登出与刷新失败登出路径，防止递归刷新。

---

### P1-05 组织级权限检查存在空实现（跨组织越权风险）
**证据**：
- `backend/src/middleware/organization_permission.py:246-254`（当 `organization_id_param` 提供时仅 `pass`）

**问题说明**：
当依赖注入传入 `organization_id_param` 时，本应校验用户是否有该组织权限，但目前为空实现。

**影响**：
- 只要用户对任意组织有访问权限，即可能访问其它组织资源；
- 组织隔离形同虚设，存在越权风险。

**建议**：
- 从 `request` 中解析组织 ID（path/query/body），与用户可访问组织集合比对；
- 对无权限组织直接返回 `403` 并记录安全事件；
- 覆盖单元测试：不同组织用户访问非授权组织资源应被拒绝。

**修复进展（2026-01-31）**：
- 新增 `OrganizationPermissionService`，统一组织访问权限计算；
- `OrganizationPermissionChecker` 从请求中解析组织ID并校验访问权限，拒绝越权并记录安全事件。

**验证进展（2026-02-01）**：
- `cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/middleware/test_organization_permission.py --no-cov` 通过（验证无权限组织访问被拒绝、合法组织可访问）。

---

### P2-01 Service 层导入失败被吞掉，错误不可见
**证据**：
- `backend/src/services/__init__.py:16-38` 多处 `except Exception: pass`

**问题说明**：
服务层导入失败被静默吞掉，导致运行时缺服务但无日志。

**影响**：
- 隐藏真实错误；
- 部分功能可能悄然失效。

**建议**：
- 至少记录 warning 级日志；
- 对关键服务使用严格失败策略。

**修复进展（2026-01-31）**：
- 服务层导入失败已记录 warning 日志（含堆栈），并保留必要的降级占位实现。

**验证进展（2026-02-01）**：
- `cd backend && .venv\\Scripts\\python.exe -c "import io, logging; stream=io.StringIO(); handler=logging.StreamHandler(stream); root=logging.getLogger(); root.addHandler(handler); root.setLevel(logging.WARNING); import src.services; root.removeHandler(handler); assert 'Service import failed' in stream.getvalue(); print('ok')"` 通过（导入服务层时可捕获 warning 日志）。

---

### P2-02 通用 Exception 抛出，无法区分业务/系统错误
**证据**：
- `backend/src/services/document/pdf_import_service.py:296`
- `backend/src/api/v1/system/error_recovery.py:390`

**问题说明**：
抛出 `Exception` 影响异常链路、日志分类及 API 错误响应一致性。

**建议**：
- 使用自定义异常类型（如 `BusinessValidationError`、`DocumentProcessingError`）。

**复核进展（2026-01-31）**：
- 已全局检索 `raise Exception`，未发现直接抛出；现有路径均通过 `BaseBusinessError`/`BusinessValidationError` 或 `internal_error` 包装。

**验证进展（2026-02-01）**：
- `rg -n "raise Exception" backend/src` 通过（未发现直接抛出）。

---

### P2-03 前端模块级定时器常驻，HMR/测试场景可能泄漏
**证据**：
- `frontend/src/utils/routeCache.ts:122-128`（模块加载即 `setInterval`）
- `frontend/src/services/cacheManager.ts:16-23`（单例构造即 `setInterval`）

**问题说明**：
模块级定时器无法随组件卸载或 HMR 自动清理，开发/测试时可能重复创建。

**建议**：
- 提供显式 `dispose()`；
- 或在应用根组件的生命周期内启动/清理。

**修复进展（2026-01-31）**：
- `routeCache` 与 `cacheManager` 改为惰性启动清理定时器，并在 HMR dispose 时清理定时器。

**验证进展（2026-02-01）**：
- `cd frontend && pnpm test:single -- src/services/__tests__/cacheManager.test.ts --reporter=dot` 通过（验证 cacheManager 主要缓存行为）。
- `rg -n "setInterval" frontend/src/utils/routeCache.ts frontend/src/services/cacheManager.ts` 通过（定时器仅在启动函数内创建）。
- `rg -n "hot.dispose|dispose\\(" frontend/src/utils/routeCache.ts frontend/src/services/cacheManager.ts` 通过（HMR dispose 清理逻辑存在）。

---

### P2-04 权限检查实现分裂，RBAC 配置可能失效
**证据**：
- `backend/src/middleware/auth.py:327-360`（`PermissionChecker` 使用硬编码权限列表）
- `backend/src/api/v1/system/error_recovery.py` 多处使用 `PermissionChecker(["system:error_recovery:*"])`

**问题说明**：
`PermissionChecker` 未接入 RBAC 服务，非管理员仅有固定权限列表（`read/profile`），导致 RBAC 配置无法生效。

**影响**：
- RBAC 权限配置被忽略，功能权限不可控；
- 非管理员用户可能被错误拒绝，形成“假权限”假象。

**建议**：
- 将 `PermissionChecker` 替换为 RBACService 校验；
- 或统一使用 `require_permission`，避免权限体系分裂；
- 增加权限回归测试（角色/权限矩阵）。

**修复进展（2026-01-31）**：
- 错误恢复相关路由已改用 `require_permission(resource, action)`，走 RBACService 权限校验。

**验证进展（2026-02-01）**：
- `rg -n "PermissionChecker" backend/src/api/v1/system/error_recovery.py` 通过（未再使用硬编码权限检查器）。
- `rg -n "require_permission" backend/src/api/v1/system/error_recovery.py` 通过（错误恢复路由已切换 RBAC 依赖）。

---

### P2-05 上传文件数量限制未实现（DoS 风险）
**证据**：
- `backend/src/middleware/security_middleware.py:572-580`（Excel/PDF 上传数量限制为 `pass`）

**问题说明**：
上传数量限制仅有注释，未实际校验，导致批量上传无法限制。

**影响**：
- 大量文件上传可能导致资源耗尽或后台任务堆积；
- 业务侧期望的限制形同虚设。

**建议**：
- 在中间件或具体端点读取 multipart 并验证文件数量；
- 对超限请求返回 4xx 并记录安全日志。

**修复进展（2026-01-31）**：
- `FileUploadSecurityMiddleware` 在 `/api/v1/excel` 与 `/api/v1/pdf-import` 路径解析 multipart，统计 `filename` 部分数量并强制上限（Excel=10，PDF=5）。

**验证进展（2026-02-01）**：
- 新增单测覆盖 Excel/PDF 导入路径的上传数量上限，超限返回 400。

---

### P2-06 可选认证路径未覆盖黑名单校验
**证据**：
- `backend/src/middleware/auth.py:298-332`（`get_optional_current_user` 直接 `jwt.decode`，未调用黑名单检查）

**问题说明**：
被撤销的 token 在“可选认证”路径仍可被解析为有效用户。

**影响**：
- 在依赖可选认证的接口中，撤销 token 仍可触发“已登录”行为；
- 审计、个性化或权限判断可能被污染。

**建议**：
- 复用 `_validate_jwt_token()` 或显式调用 `_is_token_blacklisted()`；
- 对撤销 token 返回 `None`，保持匿名身份。

**修复进展（2026-01-31）**：
- `get_optional_current_user` 已复用 `_validate_jwt_token()`，黑名单与 issuer/aud 校验对可选认证路径生效。

**验证进展（2026-02-01）**：
- 新增单测覆盖可选认证路径：黑名单 token 返回 None，合法 token 返回用户。

---

### P3-01 列表 key 使用 index，易导致渲染状态错乱
**证据**：
- `frontend/src/App.tsx:43-45` 以及多处组件使用 `key={index}`

**建议**：使用稳定唯一键（如路由 path/ID）。

**修复进展（2026-01-31）**：
- 核心展示组件已将 `key={index}` 替换为业务字段（title/name/status 等）的稳定 key；测试与 mock 代码保留索引用于简化渲染。

**验证进展（2026-02-01）**：
- `rg -n "key=\\{index\\}" frontend/src` 通过（仅剩 __tests__ 与 test-utils 中的示例使用）。

---

### P3-02 文档提取成功状态允许空字段（质量一致性不足）
**证据**：
- `backend/src/services/document/base.py:122-126`（`success=True` 且 `extracted_fields` 为空时直接 `pass`）

**问题说明**：
成功状态与内容不一致，可能返回“成功但无数据”的结果。

**影响**：
- 下游流程无法区分“真实成功”与“空提取”；
- 数据质量降低，影响审计与回溯。

**建议**：
- 将该 `pass` 改为显式校验错误；
- 或将状态降级为 `SKIPPED/FAILED` 并输出告警。

**修复进展（2026-01-31）**：
- `ExtractionResult` 在 `success=True` 且 `extracted_fields` 为空（非 SKIPPED）时直接抛出校验错误，避免“成功但无数据”。

**验证进展（2026-02-01）**：
- `cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/services/document/test_extraction_result_validator.py --no-cov` 通过（验证 success=True 且 extracted_fields 为空时报错，SKIPPED 状态允许空字段）。

---

### P3-03 产权证上传资产匹配未实现
**证据**：
- `backend/src/api/v1/assets/property_certificate.py:125-130`（`asset_matches=[]  # TODO`）

**问题说明**：
上传后资产匹配流程为空实现，仅返回空列表。

**影响**：
- 用户需手动关联资产，流程中断；
- “智能匹配”体验与预期不符。

**建议**：
- 实现基于证书号/地址的匹配逻辑；
- 或在接口文档中明确该能力未实现。

**修复进展（2026-01-31）**：
- 产权证上传流程已接入资产匹配：按地址与权属方字段匹配资产并返回匹配原因与置信度。

**验证进展（2026-02-01）**：
- `cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/services/property_certificate/test_service.py -k "match_assets" --no-cov` 通过（验证地址/权属方匹配与置信度计算）。

---
## 修复优先级建议（摘要）
- **P0（立即）**：Token 黑名单机制、JWT iss/aud 配置一致性、加密密钥轮换逻辑、任务配置接口鉴权缺失
- **P1（1-2 周）**：PII 搜索逻辑、缓存体系收敛、产权证上传格式一致性、前端 refresh 循环
- **P2（1 个月）**：Service 层异常吞掉、异常类型规范、前端全局定时器治理

---

## 建议的验证路径
1. **认证安全回归**
   - 生成 token → 修改 `JWT_ISSUER/AUDIENCE` → 校验是否生效
   - 撤销用户 token → 跨进程/重启后测试是否失效

2. **加密轮换回归**
   - 使用 v1 key 加密数据 → 切换 v2 key → 验证旧数据解密是否成功

3. **功能一致性测试**
   - 上传 JPG/PNG 产权证 → 验证可成功导入
   - 资产 PII 字段搜索 → 验证结果

4. **前端 refresh 回归**
   - 模拟 refresh 返回 401 → 验证不会无限递归
5. **任务配置鉴权**
   - 未登录访问 Excel 配置接口 → 期望 401/403
6. **组织权限校验**
   - 用户仅可访问授权组织 ID → 非授权组织应返回 403

---

## 已执行的验证（更新：2026-02-01）
- 前端：`pnpm test:single -- src/components/Project/__tests__/ProjectList.test.tsx src/components/Ownership/__tests__/OwnershipList.test.tsx --reporter=dot` 通过（验证列表重构与统计加载逻辑）。
- 前端：`pnpm test:single -- src/pages/System/__tests__/PromptListPage.test.tsx --reporter=dot` 通过（验证 PromptListPage 列表重构与交互逻辑）。
- 前端：`pnpm test:single -- src/pages/System/__tests__/RoleManagementPage.test.tsx --reporter=dot` 通过（验证角色列表重构与权限配置逻辑）。
- 前端：`pnpm test:single -- src/pages/System/__tests__/DictionaryPage.test.tsx --reporter=dot` 通过（验证枚举概览与详情加载逻辑）。
- 前端：`pnpm test:single -- src/hooks/__tests__/useContractList.test.ts --reporter=dot` 通过（验证租赁合同列表加载、分页与操作逻辑）。
- 前端：`pnpm test:single -- src/components/Monitoring/__tests__/ApiMonitor.test.tsx --reporter=dot` 通过（验证 API 监控列表重构后的表格渲染与刷新逻辑）。
- 前端：`pnpm test:single -- src/components/Asset/__tests__/AssetList.test.tsx --reporter=dot` 通过（验证资产列表分页与汇总行渲染）。
- 前端：`pnpm test:single -- src/pages/Assets/__tests__/AssetListPage.test.tsx --reporter=dot` 通过（验证资产列表页 useListData 改造与交互逻辑）。
- 前端：`pnpm test:single -- src/components/Asset/__tests__/AssetHistory.test.tsx --reporter=dot` 通过（验证资产历史列表 useListData 改造与交互逻辑）。
- 前端：`pnpm test:single -- src/components/Asset/__tests__/AssetSearch.test.tsx --reporter=dot` 通过（验证资产搜索表单展开/历史弹窗逻辑）。
- 前端：`pnpm test:single -- src/api/__tests__/client.test.ts --reporter=dot` 通过（验证 refresh 401 不递归、刷新失败登出跳转）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/api/v1/test_tasks.py --no-cov` 通过（任务/Excel配置API单测；初次运行因 `notifications.py` 缺少 `datetime` 导入失败，修复后通过）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/api/v1/test_tasks.py --no-cov` 通过（新增未认证访问 `/api/v1/tasks/configs/excel` 的 401/403 断言）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/api/v1/test_property_certificate.py --no-cov` 通过（新增图片格式上传用例，验证 .jpg/.jpeg/.png 允许上传）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/services/core/test_authentication_service.py --no-cov` 通过（验证 JWT issuer/audience 读取配置与黑名单调用参数）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/e2e/test_auth_flow_e2e.py --no-cov` 未完全通过（1 failed：`test_permission_enforcement` 中管理员访问 `/api/v1/auth/users` 返回 403，期望 200/206）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/e2e/test_auth_flow_e2e.py --no-cov` 通过（调整 `test_permission_enforcement` 执行顺序，避免登录用户覆盖 admin cookie 导致 403）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/core/test_encryption.py --no-cov` 通过（新增密钥轮换解密回归验证，修正无密钥加密回退预期）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/middleware/test_organization_permission.py --no-cov` 通过（验证无组织权限时拒绝访问，抛出 403）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/middleware/test_organization_permission.py --no-cov` 通过（新增允许访问的正向用例）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/integration/crud/test_asset_encryption.py -k "test_search_on_encrypted_address_and_owner" --no-cov` 通过（验证地址/权属方加密搜索命中与解密结果）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/core/test_blacklist.py -k "fail_closed or fail_open" --no-cov` 通过（验证黑名单熔断/异常路径的 fail-closed 行为）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/integration/api/test_token_blacklist_api.py --no-cov` 通过（验证黑名单 token 访问 `/api/v1/auth/me` 被拒绝）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/middleware/test_optional_auth.py --no-cov` 通过（验证可选认证对黑名单 token 的匿名回退）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/middleware/test_security_middleware.py -k "file_count_limit" --no-cov` 通过（验证 Excel/PDF 上传数量超限返回 400）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/middleware/test_security_middleware.py --no-cov` 通过（验证安全中间件完整用例集）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/utils/test_cache_manager_unified.py --no-cov` 通过（验证缓存统一委托与清理 pattern）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/services/document/test_extraction_result_validator.py --no-cov` 通过（验证提取结果校验：success=True 且空字段会报错，SKIPPED 允许空字段）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -m pytest tests/unit/services/property_certificate/test_service.py -k "match_assets" --no-cov` 通过（验证产权证资产匹配逻辑）。
- 后端：`cd backend && .venv\\Scripts\\python.exe -c "import io, logging; stream=io.StringIO(); handler=logging.StreamHandler(stream); root=logging.getLogger(); root.addHandler(handler); root.setLevel(logging.WARNING); import src.services; root.removeHandler(handler); assert 'Service import failed' in stream.getvalue(); print('ok')"` 通过（验证服务导入失败时的 warning 日志）。
- 后端：`rg -n "raise Exception" backend/src` 通过（未发现直接抛出）。
- 后端：`rg -n "PermissionChecker" backend/src/api/v1/system/error_recovery.py` / `rg -n "require_permission" backend/src/api/v1/system/error_recovery.py` 通过（确认错误恢复路由使用 RBAC 依赖）。
- 前端：`cd frontend && pnpm test:single -- src/services/__tests__/cacheManager.test.ts --reporter=dot` 通过（验证 cacheManager 核心逻辑）。
- 前端：`rg -n "setInterval" frontend/src/utils/routeCache.ts frontend/src/services/cacheManager.ts` 通过（定时器仅在启动函数内创建）。
- 前端：`rg -n "hot.dispose|dispose\\(" frontend/src/utils/routeCache.ts frontend/src/services/cacheManager.ts` 通过（HMR dispose 清理逻辑存在）。
- 前端：`rg -n "key=\\{index\\}" frontend/src` 通过（仅剩测试/Mock 使用）。

## 补充进展（更新：2026-02-01）
- 前端 `PromptListPage` 已迁移至 `useListData` + `TableWithPagination`，进一步减少列表逻辑重复。
- 前端 `RoleManagementPage` 已迁移至 `useListData` + `TableWithPagination`，统一分页与筛选处理。
- 前端 `UserManagementPage` 已迁移至 `useListData` + `TableWithPagination`，补齐分页筛选与统一刷新逻辑。
- 前端 `OrganizationPage` 已迁移至 `useListData` + `TableWithPagination`，列表视图接入统一分页与搜索逻辑。
- 前端 `OrganizationPage` 历史记录弹窗改用 `TableWithPagination`，统一分页展示行为。
- 前端 `NotificationCenter` 已迁移至 `useListData`，统一通知列表分页加载逻辑。
- 前端 `TemplateManagementPage` 已迁移至 `useListData` + `TableWithPagination`，保持模板列表分页行为一致。
- 前端 `EnumFieldPage` 已迁移至 `useListData` + `TableWithPagination`，枚举类型/枚举值列表统一分页逻辑。
- 前端 `DictionaryPage` 已迁移至 `useListData` + `TableWithPagination`，概览与详情列表统一分页加载逻辑。
- 前端租赁合同列表已迁移至 `useListData` + `TableWithPagination`（`useContractList` + `ContractTable`），统一分页与刷新逻辑。
- 前端 `PropertyCertificateList` 已迁移至 `useListData` + `TableWithPagination`，统一产权证列表分页与搜索逻辑。
- 前端 `ApiMonitor` 已迁移至 `useListData` + `TableWithPagination`，统一端点状态列表分页与刷新逻辑。
- 前端 `TestCoverageDashboard` 已迁移至 `useListData` + `TableWithPagination`，模块覆盖率列表统一分页逻辑。
- 前端 `RentStatisticsPage` 已迁移至 `useListData` + `TableWithPagination`，资产统计列表统一分页逻辑。
- 前端 `ProjectDetailPage` 已迁移至 `useListData` + `TableWithPagination`，关联资产列表统一分页逻辑。
- 前端 `OwnershipDetailPage` 已迁移至 `useListData` + `TableWithPagination`，关联资产/合同列表统一分页逻辑。
- 前端 `AssetList` 已切换至 `TableWithPagination`，统一分页展示与汇总行渲染。
- 前端 `AssetImport` 错误详情表改用 `TableWithPagination`，统一分页展示行为。
- 前端 `AssetTable`（非虚拟滚动路径）已切换至 `TableWithPagination`，保持分页配置一致。
- 前端 `VirtualTable` 分页切换已回调 `onTableChange`，修复大数据列表分页无效问题。
- 前端 `AssetListPage` 已迁移至 `useListData`，列表分页/筛选逻辑统一由通用Hook驱动，删除后触发列表重载而非整页刷新。
- 复核剩余 `Table` 使用场景（均为 `pagination={false}` 的说明/详情/静态表格），维持现状未做迁移。
- 前端 `AssetHistory` 已迁移至 `useListData`，历史列表分页/筛选逻辑统一由通用 Hook 驱动。

---

*本报告基于静态审阅得出，未执行运行时集成测试。建议在修复后补充自动化回归测试。*
