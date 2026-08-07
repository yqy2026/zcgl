# 2026-08-03 Organization-Party 与主体范围一次切换实施方案

**状态**：✅ 已完成（2026-08-07，全部阶段落地并归档）
**需求**：REQ-SYS-001、REQ-SYS-002、REQ-AUTH-002、REQ-PTY-001、REQ-PTY-002
**决策**：[ADR-0022](../architecture/ADR-0022-organization-party-scope-boundary.md)

## 目标

把内部 Organization、业务 Party 和用户数据范围收口为三个正交概念，并用唯一解析器替换当前猜测映射及多套冲突逻辑。迁移、后端和前端在同一发布门禁完成，不保留旧字段、旧 Party 类型或旧范围解析兼容。

## 非目标

- 不实现 Party 合并。
- 不实现母子公司、控股或关联企业关系。
- 不实现多 Organization 用户归属。
- 不实现主体范围审批流。
- 不实现 Organization 多 Party 关联或显式“阻断继承”第三模式。
- 不迁移无法明确分类的旧 `organization` Party。

## 阶段 1：ADR 与 SSOT 收口

- [x] 新增 ADR-0022，并在 ADR-0001 标记被部分取代的边界。
- [x] 更新 PRD、领域模型、API 契约、需求追踪、领域词典和索引。
- [x] 将 REQ-SYS-001、REQ-SYS-002、REQ-AUTH-002、REQ-PTY-001、REQ-PTY-002 改为开发中，不再用现有代码证明目标态已完成。
- [x] 通过 docs-lint 和字段漂移报告；报告按预期将 Party 统一标识列为 spec-only，并跳过尚未加入映射的 Organization、User、UserPartyBinding、EffectivePartyScope，不将其误判为已实现。

## 阶段 2：数据预检与模型迁移

### 2.1 先写失败用例

- Alembic 测试覆盖未决 `party_type=organization` 时迁移中止及引用清单。
- 模型测试覆盖 Organization 关系字段成对约束、法人/审核/启用目标约束，以及用户单 Organization 归属。
- Party 测试覆盖 `LE/NP` 并发编码、统一标识校验、自然人标识加密/脱敏/指纹唯一。
- UserPartyBinding 测试覆盖只允许 owner/manager、无 `headquarters`、无 `is_primary` 及有效期约束。
- User 测试覆盖不可变 `account_type=human|service|system`、human 启用前唯一有效 Organization 归属，以及 service/system 无组织且不继承范围。

### 2.2 模型切换

- `PartyType` 只保留 `legal_entity`、`individual`；删除 `PartyHierarchy` 及其表、关系和导出。
- Party 增加受 Party 类型约束的 `identifier_type`、加密/规范化的 `identifier_value` 和内部唯一指纹，按法人（类型，规范化值）/自然人（类型，指纹）建唯一约束；`code` 改由服务端生成且创建后不可变。
- Organization 增加 `represented_party_id` 与 `represented_party_perspective`，添加成对空值约束和 FK/索引。
- User 的 `default_organization_id` 直接重命名为 `organization_id`，增加创建后不可变的 `account_type`；迁移必须显式分类无组织账号，不按用户名或角色猜测。
- UserPartyBinding 删除 `headquarters`、`is_primary` 及对应部分唯一索引，保留有效期间。
- 扩展组织历史或统一操作日志，使所有敏感范围变更可记录原因与前后值。

### 2.3 数据处理

- 生成只含 ID、类型、名称和引用计数的预检报告，不输出自然人敏感标识。
- 清理明确可丢弃的本地旧数据；需要保留的记录使用人工确认映射重分类并更新引用。
- 迁移前后执行孤儿引用、重复统一标识、Organization 环和启用链完整性检查。

当前进度：

- [x] 新增只读预检 `make preflight-organization-party-scope`，覆盖必需源表、未决 `organization` Party 及动态外键引用计数、PartyHierarchy、`headquarters` 绑定、无组织未分类账号和 `LE/NP` 编码门禁；报告不读取或输出 Party metadata、正式标识与指纹。
- [x] 当前本地 PostgreSQL 快照确认旧 `organization` Party、PartyHierarchy 和 `headquarters` 绑定均为 0。
- [x] 人工确认并处置 1 个无组织活跃账号的 `human/service/system` 分类；`admin` 已按用户确认归类为 human 并归属根 Organization。
- [x] 人工确认保留 1 个法人主体，将旧编码移入统一社会信用代码标识并生成 `LE-000001`；主体保持草稿，Organization 关系未自动建立。
- [x] 预检九项门禁通过后执行不可逆 Alembic 迁移；迁移后旧字段和旧表不存在，人工处置结果复核通过。

## 阶段 3：唯一解析器、API 与授权

### 3.1 先写范围矩阵

覆盖以下结果：仅内建 admin/system_admin 全量、perm_admin 仍受范围限制、显式 owner、显式 manager、双视角解析 `all`、多 Party、组织直接关系、最近祖先继承、直接覆盖、无祖先失败关闭、无效直接关系阻断上溯、停用组织链、失效显式绑定不回退、全部显式绑定到期后回退，以及下一次时间边界。

敏感写测试另覆盖预览 token 绑定操作者/目标/规范化提议/相关版本，过期、换人、改提议和状态漂移均返回 `409 SCOPE_CHANGE_PREVIEW_STALE` 且零写入；成功消费、相同幂等键重试和批量事务全成全败也必须覆盖。

### 3.2 后端实现

- 新建单一 `PartyScopeResolver` 及结构化结果，替换 `party_scope.py`、`AuthzContextBuilder`、`resource_context` 中的并行用户范围解析。
- 删除 ID/`external_ref`/编码/名称映射和 `legacy_org_ids`；所有业务 service、搜索、通知和分析只消费解析结果。
- 新增 `organization:manage_party_scope`、`user:manage_party_scope`，更新 RBAC seed、授予边界和缓存失效事件。
- 提供 Organization 关系影响预览/变更、用户绑定影响预览/变更、Party 启停影响预览/动作，以及本人和管理员有效范围诊断端点。
- 提供 Organization 移动、human 用户调动和组织/用户范围批量预览与提交端点；普通资料更新拒绝写范围字段，批量提交幂等且事务内全成全败。
- 统一敏感变更协议：预览签发短期 opaque `preview_token`，提交携带 token、原因和幂等键并重算影响；token 过期或相关版本漂移时稳定返回 409，不执行部分写入。
- 冻结 `view_mode` 为唯一公开分析视角参数：双视角省略参数得到内部 `scope_mode=all`，不得从绑定顺序推断默认；诊断异常按节点类型、脱敏标签和受权可见的节点引用结构化返回。
- 业务接口对无效范围返回稳定 403 原因码；日志不写入统一标识明文。
- 预约绑定缓存 TTL 截止到 `next_transition_at`，边界后首次请求必须重新解析。

### 3.3 删除旧公共面

- 删除 Party hierarchy API。
- 用户绑定路由迁入用户管理资源，不保留 `/parties/users/*` 兼容入口。
- Organization API 不再构造同时含 owner/manager 的猜测 scope context。

当前进度：

- [x] 单一 `PartyScopeResolver` 与结构化结果已落地，原有 Party scope、Authz context 和 resource context 入口改为适配该解析器。
- [x] Party/Organization/User 基础模型、Schema、Service、API 和权限动作完成目标字段切换；运行时代码不再引用旧字段、旧枚举和 PartyHierarchy。
- [x] 组织代表主体单组织 preview/commit、原因、状态漂移拒绝、持久化幂等回执、组织历史和缓存失效已落地。
- [x] 单用户 `UserPartyBinding` create/update/close preview/commit、原因、状态漂移拒绝、持久化幂等回执、缓存失效和旧直写入口退役已落地。
- [x] 已审核 Party 的停用/重新启用 preview/commit、影响计数、原因、状态漂移拒绝、审核日志、持久化幂等回执和范围缓存失效已落地；普通创建、更新、导入与快捷创建不再接收状态写入。
- [x] human 用户调动的 preview/commit、原因、状态漂移拒绝、持久化幂等回执、用户范围缓存失效和完整启用 Organization 链写保护已落地。
- [x] 单组织移动的 preview/commit、原因、状态漂移拒绝、持久化幂等回执、子树路径更新和受影响用户范围缓存失效已落地；普通 Organization 更新不再写入 `parent_id`。
- [x] Organization 直接代表主体批量事务的 preview/commit、逐目标授权、祖先/子孙重叠拒绝、持久化回执和统一审计协议。
- [x] 用户显式 Party 范围批量事务的 preview/commit 和统一审计协议。
- [x] 无效范围稳定 403、本人/管理员诊断端点；前端已接入范围 403 阻断式异常、本人有效范围入口和管理员只读视图。
- [x] `next_transition_at` 缓存截止与主要业务消费方的失败关闭集成验证；授权决策缓存按下一时间边界截短 TTL。

## 阶段 4：前端、数据录入与端到端点检

- 主体新建不再要求用户填写 `code`，改为正式统一标识字段；类型只显示法人主体、自然人。
- 组织新建/编辑提供“继承上级 / 直接关联”，直接关联时选择已审核启用法人及 owner/manager；展示有效 Party、视角和来源组织。
- [x] 主体详情增加只读“代表组织”反向列表；不提供双向编辑。
- [x] 用户管理普通创建只产生停用 human 账号；通过独立影响预览完成 Organization 归属后才允许启用。账号类型只读，用户调动不能复用普通资料编辑。
- [x] 组织页“主体绑定”改为“用户数据范围”。
- [x] 用户绑定 UI 删除 headquarters 和主关系，增加影响预览、原因、生效区间和关闭后的回退提示。
- [x] 增加本人及管理员有效范围只读视图；业务接口的范围 403 呈现为阻断式配置异常，不渲染空态。
- 按用户已确认的清理边界清除旧业务数据，重新录入广州国有资产管理集团有限公司为 `legal_entity`，再按主线顺序导入资产数据。
- 使用可视化浏览器完成登录、主体、组织、用户、资产、项目、合同与协议、台账、搜索、通知和分析点检。

当前进度：

- [x] 主体类型、服务端编码、正式标识、组织代表主体和用户组织字段的基础界面已切换并通过定向组件测试与生产构建。
- [x] 用户管理已提供仅 human 可见的组织调动动作：选择目标 Organization 后预览有效 Party 范围和影响，填写原因后提交；普通用户编辑不显示或写入 Organization。
- [x] 组织列表已提供独立迁移动作：目标父 Organization 选择会排除当前子树，预览子树路径和用户范围影响后必须填写原因提交；普通编辑不显示或写入上级 Organization。
- [x] 组织列表已提供多选的代表主体批量设置动作：至少选择两个启用且无祖先/子孙重叠的组织，以相同直接 Party/视角生成影响预览，填写原因后提交。
- [x] 用户管理已按后端规范字段映射账号状态、最近登录和直接 Organization 名称；普通创建不再暴露由服务端控制的启用状态。主体列表接口失败会呈现阻断式错误，不再显示为零记录。
- [x] 组织代表主体抽屉已接入影响预览、原因填写和提交确认。
- [x] 后端已提供本人 `GET /auth/me/party-scope` 与管理员 `GET /auth/users/{user_id}/party-scope` 只读范围诊断；前端阻断视图仍待接入。
- [x] 后端范围诊断与稳定 403 已接入前端阻断式异常、本人有效范围入口和管理员只读视图；用户/主体敏感变更预览保持单条/批量 API 覆盖。
- [x] 使用可视化浏览器完成登录、工作台、主体列表/详情、组织代表主体抽屉、用户归属/状态、资产、项目、合同中心、经营台账、搜索、通知和分析点检；草稿主体保持不可关联，未执行自动关联或审核。

## 发布门禁

1. 数据预检无未分类 `organization` Party、无孤儿引用、无无效启用组织链。
2. 旧字段、旧枚举、PartyHierarchy、`headquarters`、`is_primary`、猜测映射和 `legacy_org_ids` 均无运行时引用。
3. 范围矩阵单元/集成测试、权限与缓存边界测试全部通过，无跳过项。
4. 前端类型检查、测试与生产构建通过；关键流程浏览器点检通过。
5. `make check` 通过；若 Windows Makefile 仍不可用，必须逐项运行等价项目命令并如实记录。
6. 后端、前端和迁移作为一个协调发布单元，不部署中间兼容状态。

## 完成后

- 补齐代码与测试证据，将相关 REQ 状态改回“已有证据”。
- 将 ADR-0022 状态改为已实施。
- 将本方案移入 `docs/archive/backend-plans/` 并更新方案索引。
