# AI 生成代码技术债务修复计划

**文档类型**: 技术方案  
**创建日期**: 2026-03-16  
**作者**: Codex  
**状态**: 📋 待评审  
**需求编号**: 内部质量改进（非 REQ）  
**里程碑**: M5（建议）

---

## 1. 摘要

本项目自 0→1 阶段大量依赖 AI 编程助手生成代码，随着规模增长（后端 395 文件 / 前端 588 文件），暴露出典型的 AI 生成代码弊端。本计划系统性识别并修复这些问题，建立防御机制防止复发。

**核心问题分类**：

| 类别 | 严重程度 | 影响范围 |
|------|---------|---------|
| 函数重复定义 | 🔴 严重 | 32 处 `_utcnow_naive`，10 处 `_normalize_optional_str` |
| 超大文件 | 🟡 中等 | 后端 7 个 >1000 行文件，前端 12 个 >700 行文件（含 services 层）+ 2 个接近阈值 |
| 错误处理混乱 | 🟡 中等 | HTTPException / BusinessError / 自定义异常混用 |
| Schema-Model 脱节 | 🟡 中等 | 14 个 Model 无对应 Schema |
| 布尔检查 bug | 🔴 严重 | `FilenameValidator.tsx` 存在逻辑错误 |
| 状态管理混用 | 🟢 轻微 | 部分页面用 useState 而非 React Query |

---

## 2. 已确认根因分析

### 2.1 AI 生成代码的系统性弊端

| 弊端 | 表现 | 根因 |
|------|------|------|
| **就地定义倾向** | `_utcnow_naive` 重复 32 次 | AI 每次生成新文件时不主动搜索已有实现 |
| **缺乏全局视角** | CRUD 继承模式不一致 | AI 只看当前文件上下文，不知道项目规范 |
| **模式漂移** | 同一功能不同时间实现方式分化 | 不同 session 的 AI 没有共享"记忆" |
| **文件膨胀** | 单文件 1500+ 行 | AI 不擅长判断拆分时机 |
| **过度简化** | 布尔值检查写成 `!== undefined && !== null` | AI 模式匹配错误，未理解业务语义 |
| **错误处理简化** | `except Exception` 泛滥 | AI 倾向用最简单方式"完成"异常处理 |

### 2.2 技术债务累积路径

```
初期：每个功能独立生成 → 函数重复定义
     ↓
中期：新增功能复用已有文件 → 文件膨胀
     ↓
后期：不同 session 处理同类问题 → 模式漂移
     ↓
现在：代码库规模 10 万行 → 维护成本指数增长
```

---

## 3. 目标与验收标准

### 3.1 定量目标

| 指标 | 当前值 | 目标值 | 验收方式 |
|------|--------|--------|---------|
| `_utcnow_naive` 定义次数 | 32 | **1** | `grep -r "def _utcnow_naive" \| wc -l` |
| `_normalize_optional_str` 定义次数 | 10 | **1** | `grep -r "def _normalize_optional_str" \| wc -l` |
| 超 600 行后端文件数 | 7 个 >1000 行 | **0** | `find backend/src -name "*.py" -exec wc -l {} + \| awk '$1>600'` |
| 超 700 行前端文件数（非测试） | 12（+2 接近阈值） | **0** | `find frontend/src ... \| awk '$1>700'`（排除 `__tests__/`） |
| Schema-Model 覆盖率 | ~60% | **≥90%** | 有 CRUD/Service 层的 Model 必须有 Schema |
| 布尔检查 bug | 1 处 | **0** | FilenameValidator 修复 |
| `make check` 通过 | ✅ | ✅ | 门禁全绿 |

### 3.2 定性目标

1. 任何新增文件**禁止**重新定义 `_utcnow_naive` 或 `_normalize_optional_str`
2. 单文件不超过 **600 行**（放宽自 AGENTS.md 的 500 行规则，避免复杂模块过度碎片化）
3. 错误处理统一使用项目标准异常体系
4. 前端数据获取统一使用 React Query

---

## 4. 实施步骤

### Phase 0：Alembic 影响排查 — 预估 15min

> Phase 1 会将 Model 中的 `_utcnow_naive` 替换为公共导入。如果 Model 的 `Column(default=_utcnow_naive)` 被 Alembic 迁移文件直接引用，替换后可能导致迁移生成/执行失败。**必须先排查再动手。**

**步骤**：
```bash
# 1. 排查 Model 中 _utcnow_naive 作为 Column default/server_default 的用法
grep -rn "default.*_utcnow_naive\|server_default.*_utcnow_naive" backend/src/models/

# 2. 排查 Alembic 迁移文件中是否直接引用了 _utcnow_naive
grep -rn "_utcnow_naive" backend/alembic/versions/
```

**判断**：
- 若无命中 → 直接进入 Phase 1
- 若 Model 中存在 `default=_utcnow_naive` → Phase 1 替换时需同步更新 import，并确认 Alembic env 可解析 `src.utils.time`
- 若迁移文件中存在引用 → 需评估是否修改历史迁移（通常不应修改已执行的迁移）

---

### Phase 1：提取公共工具（消除重复）— 预估 3h

#### 4.1.1 后端：`_utcnow_naive` 收口

**目标**：32 处 → 1 处

**步骤**：
1. 创建 `backend/src/utils/time.py`：
   ```python
   from datetime import datetime, timezone
   
   def utcnow_naive() -> datetime:
       """返回 UTC 当前时间（naive，无 tzinfo）。"""
       return datetime.now(timezone.utc).replace(tzinfo=None)
   ```
2. 全量替换 32 个文件中的 `def _utcnow_naive` 为 `from src.utils.time import utcnow_naive`
3. 调用处：`_utcnow_naive()` → `utcnow_naive()`

**涉及文件清单**（32 个）：
- Models (9): `asset.py`, `party.py`, `project_asset.py`, `property_certificate.py`, `party_role.py`, `abac.py`, `asset_management_history.py`, `user_party_binding.py`, `certificate_party_relation.py`
- Services (15): `document/pdf_import_service.py`, `excel/excel_task_service.py`, `excel/excel_export_service.py`, `ownership/service.py`, `asset/batch_service.py`, `asset/asset_service.py`, `party/service.py`, `project/service.py`, `core/password_service.py`, `core/authentication_service.py`, `task/service.py`, `llm_prompt/prompt_manager.py`, `llm_prompt/auto_optimizer.py`, `llm_prompt/feedback_service.py`, `organization_permission_service.py`
- CRUD (3): `project_asset.py`, `party.py`, `asset_management_history.py`
- API (2): `documents/excel/export_ops.py`, `documents/excel/import_ops.py`
- Scripts (3): `scripts/migration/party_migration/backfill_*.py`

**验收**：`grep -r "def _utcnow_naive" backend/src/` 仅返回 1 处（utils/time.py）

#### 4.1.2 后端：`_normalize_optional_str` 收口

**目标**：10 处 → 1 处

**步骤**：
1. 创建 `backend/src/utils/str.py`：
   ```python
   from typing import Any

   def normalize_optional_str(value: Any) -> str | None:
       """将空字符串归一为 None。"""
       if value is None:
           return None
       stripped = str(value).strip()
       return stripped if stripped else None
   ```
   > 注意：保持入参类型为 `Any`，与现有 10 处签名一致。部分调用点可能传入非 str 类型。
2. 全量替换 10 个文件

**涉及文件清单**（10 个）：
- Services (1): `asset/asset_service.py`
- Middleware (1): `middleware/auth.py`
- API (8): `auth/roles.py`, `auth/organization.py`, `auth/auth_modules/users.py`, `assets/ownership.py`, `assets/property_certificate.py`, `assets/asset_import.py`, `assets/project.py`, `assets/assets.py`

**验收**：`grep -r "def _normalize_optional_str" backend/src/` 仅返回 1 处

#### 4.1.3 前端：`normalizeOptionalId` 收口

**目标**：5 处 → 1 处

**步骤**：
1. 创建 `frontend/src/utils/normalize.ts`：
   ```typescript
   /**
    * 将 id 值归一化：空值/空字符串 → undefined，有效值 → 去首尾空格后的字符串。
    */
   export const normalizeOptionalId = (value: unknown): string | undefined => {
     if (value == null) return undefined;
     const str = String(value).trim();
     return str === '' ? undefined : str;
   };
   ```
   > 注意：保持返回 `string | undefined`，与现有 5 处实现一致。部分用箭头函数定义，统一为 `const` 箭头函数。
2. 替换 5 个文件中的本地定义

**涉及文件清单**（5 个）：
- Services (2): `pdfImportService.ts`（箭头函数）, `asset/assetCoreService.ts`（箭头函数）
- Components (2): `Asset/AssetSearch.tsx`, `Forms/AssetForm.tsx`
- Pages (1): `Contract/ContractImportReview.tsx`（export const 箭头函数）

**验收**：`grep -rE "(function|const) normalizeOptionalId" frontend/src/` 仅返回 1 处（utils/normalize.ts）

> ⚠️ `grep -r "function normalizeOptionalId"` 无法检出箭头函数定义，必须用上述正则。

---

### Phase 2：修复逻辑错误 — 预估 0.5h

#### 4.2.1 FilenameValidator 布尔检查修复

**文件**：`frontend/src/components/Contract/FilenameValidator.tsx`

**问题**：第 85 行和第 93 行
```typescript
// 错误代码
if (hasChineseSpecial !== undefined && hasChineseSpecial !== null) {
  // 布尔值永远不会是 undefined 或 null
}

// 修复
if (hasChineseSpecial) {
  // 直接判断布尔值
}
```

**验收**：单元测试覆盖布尔值为 `true` / `false` 两种场景

---

### Phase 3：拆分超大文件 — 预估 12h

#### 4.3.1 后端文件拆分

| 原文件 | 行数 | 拆分方案 |
|--------|------|---------|
| `middleware/auth.py` | 1,574 | 拆为 `auth_core.py`（认证核心）+ `auth_middleware.py`（中间件）+ `auth_utils.py`（工具） |
| `services/permission/rbac_service.py` | 1,354 | 拆为 `rbac_service.py`（核心 CRUD）+ `rbac_policy.py`（策略计算）+ `rbac_cache.py`（缓存管理） |
| `services/asset/asset_service.py` | 1,307 | 拆为 `asset_service.py`（核心）+ `asset_query_service.py`（查询）+ `asset_validation.py`（校验） |
| `services/document/pdf_import_service.py` | 1,252 | 拆为 `pdf_import_service.py`（编排）+ `pdf_import_pipeline.py`（处理管线） |
| `services/contract/contract_group_service.py` | 1,123 | 拆为 `contract_group_service.py`（核心）+ `contract_group_query.py`（查询） |
| `security/logging_request.py` | 1,058 | 拆为 `logging_request.py`（核心）+ `logging_formatters.py`（格式化）或按日志类型拆分 |
| `crud/asset.py` | 1,056 | 拆为 `asset.py`（核心 CRUD）+ `asset_query.py`（复杂查询） |

**原则**：
- 每个文件不超过 600 行
- 拆分后原文件的公共接口保持不变（向后兼容）
- 通过 `__init__.py` 重新导出，确保外部 import 路径不变

#### 4.3.2 前端文件拆分

**Services 层（优先级最高，行数最多）**：

| 原文件 | 行数 | 拆分方案 |
|--------|------|--------|
| `services/pdfImportService.ts` | 1,447 | 拆为 `pdfImportService.ts`（编排）+ `pdfImportParser.ts`（解析）+ `pdfImportTypes.ts`（类型） |
| `services/dictionary/manager.ts` | 1,200 | 拆为 `manager.ts`（核心）+ `dictionaryCache.ts`（缓存）+ `dictionarySync.ts`（同步） |
| `services/excelService.ts` | 1,002 | 拆为 `excelExportService.ts` + `excelImportService.ts` |
| `api/client.ts` | 951 | 拆为 `client.ts`（核心）+ `interceptors.ts`（拦截器）+ `clientHelpers.ts`（工具） |
| `services/dictionary/index.ts` | 901 | 拆为按职责的子模块 |
| `services/dictionary/base.ts` | 882 | 拆为 `base.ts`（核心）+ `baseTypes.ts`（类型） |
| `services/monitoringService.ts` | 745 | 拆为 `monitoringService.ts`（核心）+ `monitoringMetrics.ts`（指标） |
| `services/organizationService.ts` | 705 | 拆为 `organizationService.ts`（核心）+ `organizationQuery.ts`（查询） |

**Pages / Components 层**：

| 原文件 | 行数 | 拆分方案 |
|--------|------|--------|
| `pages/Contract/ContractImportReview.tsx` | 1,060 | 拆为页面容器 + `ReviewTable.tsx` + `ReviewSummary.tsx` + `useReviewData.ts` |
| `pages/System/EnumFieldPage.tsx` | 887 | 拆为页面 + `EnumFieldList.tsx` + `EnumFieldValueManager.tsx` |
| `pages/System/DictionaryPage.tsx` | 748 | 拆为页面 + `DictionaryList.tsx` + `DictionaryEditor.tsx` |
| `pages/System/PromptListPage.tsx` | 717 | 拆为页面 + `PromptTable.tsx` + `PromptFilter.tsx` |
| `components/Asset/AssetList.tsx` | 697 | 拆为 `AssetTable.tsx` + `AssetActions.tsx` + `useAssetList.ts` |
| `components/Project/ProjectList.tsx` | 696 | 拆为 `ProjectTable.tsx` + `ProjectActions.tsx` |

> 注：测试文件（`__tests__/` 下 3 个 >700 行）不纳入本次拆分范围，但验收命令需排除测试目录。
> `utils/responseExtractor.ts`（681行）和 `services/backupService.ts`（684行）接近阈值，可视情况纳入。

---

### Phase 4：统一错误处理模式 — 预估 4h

#### 4.4.1 后端异常体系统一

**现状**：
- `HTTPException`（FastAPI 原生）— 36 处直接 raise
- `BaseBusinessError`（基类）— 已定义在 `core/exception_handler.py`
- `BusinessValidationError` / `ResourceNotFoundError` / `DuplicateResourceError` / `PermissionDeniedError` / `AuthenticationError` / `InvalidRequestError`（已有子类）
- `BusinessLogicError`（在 `exceptions.py` 中的包装类）

> ⚠️ 项目**已有完善的异常层次**，定义在 `backend/src/core/exception_handler.py`。本 Phase 的工作是**收口**到已有体系，而非重新定义。

**目标**：
```
Service 层 → 抛出 BaseBusinessError 子类（ResourceNotFoundError / BusinessValidationError 等）
    ↓
API 层 → 全局异常处理器（已有）自动转换为 HTTP 响应
    ↓
前端 → 统一错误格式处理
```

**步骤**：
1. **不新建异常类**。使用已有的 `core/exception_handler.py` 中的异常层次：
   - `ResourceNotFoundError` → 404
   - `BusinessValidationError` → 422
   - `PermissionDeniedError` → 403
   - `AuthenticationError` → 401
   - `DuplicateResourceError` → 409
   - `InvalidRequestError` → 400
2. 确认 `exception_handler.py` 中已注册全局处理器，`BaseBusinessError` 自动转换为标准 JSON 响应
3. API 端点中将 `raise HTTPException` 替换为对应的业务异常：
   - `HTTPException(404)` → `raise ResourceNotFoundError(...)`
   - `HTTPException(422)` → `raise BusinessValidationError(...)`
   - `HTTPException(403)` → `raise PermissionDeniedError(...)`
4. 重点收口：`property_certificate.py`（16 处）、`system_settings.py`（12 处）、`llm_prompts.py`（6 处）

**验收**：`grep -r "raise HTTPException" backend/src/` 趋近于 0（仅保留 `security/permissions.py` 中的 1 处认证守卫）

#### 4.4.2 前端状态管理统一

**步骤**：
1. 将 `NotificationCenter.tsx` 的 `useState` + `useEffect` 数据获取改为 React Query
2. 将 `ProfilePage.tsx` 的 `useEffect` 表单初始化改为 `useForm` 的 `defaultValues`
3. 在 `AGENTS.md` 中强化"禁止 useState + useEffect 获取数据"规则

---

### Phase 5：补齐 Schema — 预估 4h

#### 4.5.1 为审计/日志 Model 补 Schema

需要新增 Schema 的 Model：

| Model 文件 | 建议 Schema 文件 | 说明 |
|------------|-----------------|------|
| `models/operation_log.py` | `schemas/operation_log.py` | 操作日志查询 API |
| `models/asset_review_log.py` | `schemas/audit_log.py` | 审核日志查询（可复用） |
| `models/party_review_log.py` | `schemas/audit_log.py` | 同上 |
| `models/security_event.py` | `schemas/security_event.py` | 安全事件查询 |
| `models/pdf_import_session.py` | `schemas/pdf_import_session.py` | PDF 导入会话追踪 |

**验收**：有 CRUD/Service 层的 Model 覆盖率 ≥90%

---

### Phase 6：清理与防御 — 预估 2h

#### 4.6.1 清理死代码

- 删除 `frontend/src/pages/Contract/ContractImportUpload.tsx` 中注释掉的代码（第 44-50 行、第 193 行）
- 评估 `FriendlyErrorDisplay.tsx`、`EmptyState.tsx`、`ErrorState.tsx` 是否被使用，未使用则删除
- 清理 `api/v1/rent_contracts/` 空目录

#### 4.6.2 建立防御机制

1. **新增 lint 规则**（后端）：
   - 在 `pyproject.toml` 的 ruff 规则中添加自定义检查（或 pre-commit hook）
   - 禁止在 `backend/src/` 中新增 `def _utcnow_naive` 或 `def _normalize_optional_str`

2. **新增 lint 规则**（前端）：
   - 在 oxlint 或 eslint 配置中添加规则，禁止在非 utils 目录定义 `normalizeOptionalId`

3. **AGENTS.md 更新**：
   - 在"前端开发要点"中新增：
     ```
     ### 禁止重复定义工具函数
     - 时间工具：从 `utils/time.ts` 导入
     - 字符串工具：从 `utils/str.ts` 导入
     - ID 归一化：从 `utils/normalize.ts` 导入
     - 新增文件前必须 grep 检查是否已有实现
     ```

4. **PR 模板**：
   - 添加 checklist："是否检查了公共工具函数？"

---

## 5. 验收场景

### 5.1 全量回归

1. `make lint` 通过（前后端）
2. `make type-check` 通过
3. `make test` 通过（前后端）
4. `make docs-lint` 通过
5. `make check` 全量门禁通过

### 5.2 专项验证

1. **重复函数收口验证**：
   ```bash
   grep -r "def _utcnow_naive" backend/src/ | wc -l  # 应为 1
   grep -r "def _normalize_optional_str" backend/src/ | wc -l  # 应为 1
   grep -rE "(function|const) normalizeOptionalId" frontend/src/ | wc -l  # 应为 1
   ```

2. **文件大小验证**：
   ```bash
   find backend/src -name "*.py" -exec wc -l {} + | awk '$1>600' | wc -l  # 应为 0
   find frontend/src \( -name "*.tsx" -o -name "*.ts" \) -not -path "*__tests__*" | xargs wc -l | awk '$1>700' | wc -l  # 应为 0
   ```

3. **错误处理验证**：
   ```bash
   grep -r "raise HTTPException" backend/src/ | wc -l  # 应 ≤ 5
   ```

### 5.3 功能回归

1. 资产 CRUD 操作正常
2. 合同组创建、编辑、查询正常
3. PDF 导入流程正常
4. 用户登录、权限校验正常
5. 数据分析报表正常

---

## 6. 风险与依赖

### 6.1 风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 大范围修改引入回归 bug | 功能异常 | 每个 Phase 独立提交，可独立回滚；每个 Phase 前后跑 `make test` 基线 |
| 拆分文件破坏外部 import（Phase 3） | 编译失败 | 通过 `__init__.py` 保持原 import 路径 |
| Schema 补齐与前端字段不匹配 | API 响应格式变化 | 新增 Schema 仅用于查询端点，不修改已有响应 |
| Model 中 `_utcnow_naive` 作为 Column default 回调 | Alembic migration 解析失败 | 确认 `from src.utils.time import utcnow_naive` 在 Alembic env 中路径可解析 |

### 6.2 依赖

1. 无外部依赖
2. 不涉及数据库迁移
3. 不涉及 API 路径变更
4. 建议在 M1 收口完成后再实施

---

## 7. 工时估算

| Phase | 内容 | 工时 | 可并行 |
|-------|------|------|--------|
| Phase 0 | Alembic 影响排查 | 0.25h | — |
| Phase 1 | 提取公共工具 | 3h | ✅ 后端/前端可并行 |
| Phase 2 | 修复布尔 bug | 0.5h | ✅ |
| Phase 3 | 拆分超大文件（后端 7 + 前端 14^） | 12h | ⚠️ 需人工 review |
| Phase 4 | 统一错误处理 | 4h | ✅ 后端/前端可并行 |
| Phase 5 | 补齐 Schema | 4h | ✅ |
| Phase 6 | 清理与防御 | 2h | ✅ |
| **合计** | | **25.75h** | 建议 4-5 天完成 |

> ^ 前端 14 = 12 个 >700 行 + 2 个接近阈值（AssetList 697 行 / ProjectList 696 行）

---

## 8. 变更记录

| 日期 | 变更内容 | 作者 |
|------|---------|------|
| 2026-03-16 | 初始版本 | Codex |
| 2026-03-16 | 审阅修正：修正数据准确性（后端7/前端12+2超大文件）、修正 `_normalize_optional_str` 签名（Any→Any）和文件清单、修正 `normalizeOptionalId` 签名（保持返回string）和验收命令、Phase 4 收口到已有异常体系、补充 services 层拆分清单、补充风险项（Alembic 路径）、调整工时 | Review |
| 2026-03-16 | 评审确认：文件大小阈值放宽至 600 行、新增 Phase 0 Alembic 排查步骤、修复工时表 Markdown 格式、总工时 25.5h → 25.75h | Codex |

---

*本方案为 🔄 已确认状态，按 Phase 0 → Phase 6 顺序实施。*
