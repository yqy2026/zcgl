# Phase 3 实施计划（v1.26）深度审阅报告

**审阅对象**: `docs/plans/2026-02-20-phase3-implementation-plan.md`  
**审阅日期**: 2026-02-21  
**审阅方式**: 文档逐段审读 + 代码仓实证核验（前后端路径、现状实现、命令可执行性、门禁一致性）

---

## 一、总体结论

结论：**有条件通过（需先处理 P0/P1 问题后再作为执行基线）**。

当前计划的总体方向正确，但存在以下会直接影响执行质量的问题：
- 部分基线统计与仓库现状不一致，会导致工作量与优先级误判。
- 少量门禁描述仍有“口径可被误解”的空隙，可能出现“文档通过但实现偏离”的假收口。
- Windows 团队执行体验存在命令可移植性风险（虽有注记，但仍不够工程化）。

---

## 二、关键问题清单（按严重级别）

## P0（必须先修）

### 1) §3.1 旧字段统计与实际代码不一致（会误导迁移范围）
- 文档声明：
  - `organization_id` 影响文件数为 **3**
  - `usePermission` 影响文件数为 **4**
- 实际复算（按文档声明口径：`frontend/src/**/*.ts(x)`，排除测试目录及 `*.test/spec.*`）：
  - `organization_id` 命中 **9** 个文件
  - `usePermission` 命中 **7** 个文件
- 影响：
  - 会低估系统管理链路迁移与风险（尤其 `UserManagement`、`types/auth.ts`、`organizationService` 等）。
  - 会低估权限迁移中的“非主链残留调用”清理工作量（`components/Router/*`）。
- 建议：立即修订 §3.1 数字及分布表，并区分“运行时主链命中”和“代码残留命中”两类统计。

### 2) “组织架构并行运行”与“旧字段零引用门禁”仍有执行歧义
- 文档已做了多处排除（如 `organizationService`、`OrganizationPage`、`systemService`），但排除规则散落在不同小节，执行者容易漏掉某条而造成误报或误改。
- 影响：
  - 可能触发“为过门禁而误改仍需保留的兼容字段”。
- 建议：补一个**统一的门禁排除单源清单**（单独小节），并要求所有 grep 命令引用同一组排除规则。

## P1（应在执行前修）

### 3) 权限迁移门禁对“死代码/非主链代码”处理策略不够收敛
- 现状确认：主链确实是 `App.tsx + routes/AppRoutes.tsx`，但 `usePermission` 仍被 `components/Router/*` 多处引用。
- 风险：
  - 若只按主链验收，可能遗留一批可编译但语义过时的权限调用；后续回流时再次污染。
- 建议：在 P3d Exit 增加“非主链权限残留处置结论”字段：
  - 明确是“物理删除”还是“统一 `@deprecated` + 禁止引用 + lint 规则兜底”。

### 4) feature flag 默认关闭 capability guard 的安全边界需再明确
- 文档定义了 `VITE_ENABLE_CAPABILITY_GUARD` 默认 off（保留认证，不做 capability deny）。
- 风险：
  - 若环境配置漂移，可能把本应 capability 控制的业务路由放宽为“仅登录可见”。
- 建议：补充一条发布门禁：
  - **生产环境必须显式声明 flag 值并在发布检查中验签**（例如 `.env.production` + 启动日志打印 + CI 断言）。

### 5) 静默 refresh 触发策略落地细节仍可再收紧
- 文档要求排除 capabilities 接口自身 403 递归触发，这是正确的；
- 但未要求“重放请求白名单/幂等限制”。
- 风险：
  - 对非幂等请求（如 POST）若盲目重放，存在业务副作用风险。
- 建议：在 §4.5 增加“仅自动重放 GET/HEAD 或显式标记可重放请求”的约束。

### 6) Windows 命令可执行性仍偏脆弱
- 文档虽声明“WSL/Git Bash 执行 grep”，但大量门禁命令仍以 bash 风格为主；
- 对 Windows-only 团队不够友好，且容易因 shell 差异导致误判。
- 建议：每条关键门禁命令给出 PowerShell 等价版，至少覆盖 P3b/P3d/P3e Entry/Exit 的核心命令。

## P2（建议优化）

### 7) 门禁证据“代码存在”与“行为正确”仍有少量混淆
- 某些 Entry/Exit 使用 grep 作为主要证据，可能出现“字符串存在但链路未生效”。
- 建议：对核心守卫链路（`AppRoutes` 元数据 + `App.tsx` 渲染）保留最小 E2E 的强制断言作为第一证据，grep 仅作辅证。

### 8) 统计/分析/历史模块的“REVIEW-only”项建议加抽样标准
- 当前写法是“经复核无命中，本阶段不改代码”。
- 建议补充“抽样接口 + 抽样页面 + 抽样字段”三元记录模板，避免后续无法复盘“为什么判定为无改造”。

---

## 三、实证核验摘要（关键证据）

### A. 路由主链现状
- `frontend/src/App.tsx` 当前只做认证守卫（未接 capability 元数据判定）。
- `frontend/src/routes/AppRoutes.tsx` 当前 `protectedRoutes` 仅 `{path, element}`，无 `permissions/adminOnly`。
- 说明计划中“必须改 `App.tsx + AppRoutes.tsx` 才生效”的判断是正确的。

### B. 旧字段统计复算（按计划口径）
- `organization_id`: 9 文件（非 3）
- `ownership_id`: 26 文件（与计划一致）
- `management_entity`: 8 文件（与计划一致）
- `ownership_entity`: 19 文件（与计划一致）
- `usePermission`: 7 文件（非 4）
- `canAccessOrganization`: 1 文件（与计划一致）

### C. `organization_id` 额外命中文件（计划表未完整覆盖）
- `frontend/src/pages/System/UserManagement/index.tsx`
- `frontend/src/pages/System/UserManagement/hooks/useUserManagementData.ts`
- `frontend/src/pages/System/UserManagement/components/UserFormModal.tsx`
- `frontend/src/types/auth.ts`
- 以及 `hooks/usePermission.tsx`、`services/systemService.ts`、`services/organizationService.ts`、`types/organization.ts`、`types/propertyCertificate.ts`

### D. `usePermission` 命中文件（计划表低估）
- `frontend/src/components/Asset/AssetList.tsx`
- `frontend/src/components/System/PermissionGuard.tsx`
- `frontend/src/components/Router/RouteBuilder.tsx`
- `frontend/src/components/Router/DynamicRouteContext.tsx`
- `frontend/src/components/Router/DynamicRouteLoader.tsx`
- `frontend/src/components/Router/index.ts`
- `frontend/src/hooks/usePermission.tsx`

---

## 四、建议整改顺序（最小阻断路径）

1. **先修 §3.1 统计与分布表**（P0）
2. **补统一排除清单与 PowerShell 等价命令**（P0/P1）
3. **补 production flag 门禁与发布验签项**（P1）
4. **补 refresh 重放幂等约束**（P1）
5. **再进入代码实施（P3a→P3e）**

---

## 五、最终审阅意见

该计划在架构方向、阶段依赖和主链识别上是正确的，但为了“严格、彻底、可执行”，必须先把统计基线和门禁口径再收紧一次。完成上述修订后，可作为 Phase 3 的正式执行基线。