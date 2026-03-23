# 2026-03-06 M2 合同生命周期与台账方案审阅报告

## 审阅对象

- 目标方案：`docs/plans/2026-03-06-m2-contract-lifecycle-and-ledger.md`
- 主基线：`docs/requirements-specification.md`
- 对照附录：`docs/features/requirements-appendix-fields.md`
- 现状代码：`backend/src/models/contract_group.py`、`backend/src/api/v1/rent_contracts/contract_groups.py`、`backend/src/services/rent_contract/contract_group_service.py`

## 审阅结论

结论：**暂不建议直接按当前方案执行（No-Go）**。

阻断原因不是实现难度，而是方案与现行 SSOT、附录冻结口径、路由装配现状之间仍有关键偏差。若不先修文档与契约，M2 即使开发完成，也无法稳妥地将 `REQ-RNT-003/004/005/006` 标记为完成。

## 主要问题

### 1. 高风险：`REQ-RNT-003` 完成定义与当前方案不一致

`docs/requirements-specification.md` 仍将“合同组状态最小集”定义为 `草稿 -> 待审 -> 生效 -> 变更中 -> 已到期 / 已终止`，而当前方案明确采用“合同组纯容器 + 派生状态、审核在合同级进行”的附录口径，只设计了合同级状态机，没有承接合同组 `变更中` 状态，也没有安排先修订需求文档。

影响：

- 按当前方案实现后，`REQ-RNT-003` 仍无法根据需求文档验收。
- 需求、附录、实现三者会继续漂移，后续追踪矩阵无法可靠收口。

建议：

- 先明确以哪份文档为准。
- 若以附录为准，应先同步修订 `docs/requirements-specification.md` 的 `REQ-RNT-003` 描述和验收条件，再进入开发。

### 2. 高风险：`REQ-RNT-004` 的“合同组主审 + 关键合同联审”没有被真正建模

方案当前只有“批量提交组内草稿合同”的 `submit-review`，以及简化版 `ContractAuditLog`。但需求明确要求：

- 支持混合联审策略。
- 关键变更走强联审，非关键文本类改动可单审。
- 审核记录包含审核范围、审核结论、关联合同清单。

当前方案未定义：

- “关键变更”的判定规则。
- 联审范围的数据结构。
- 审核结论的结构化字段。
- 关联合同清单的留痕模型。

影响：

- 只能实现“批量提审”，不能实现需求中的“主审 + 联审”。
- 审计数据无法支撑未来复盘和审批追踪。

建议：

- 在方案中补充联审领域模型，至少明确 `review_scope`、`review_conclusion`、`related_contract_ids` 的落点。
- 明确哪些字段变化触发强联审，哪些变化允许单审。

### 3. 高风险：`REQ-RNT-006` 被缩窄，且与附录冻结口径冲突

方案将台账生成口径改为基于 `LeaseContractDetail.monthly_rent_base`，而附录和需求文档冻结的口径是“按 `RentTerm` 生成月度台账”。同时，方案只设计了合同维度查询与批量状态更新，没有覆盖需求中已经写明的能力：

- 按合同、资产、主体、时间区间查询。
- 导出能力。
- 变更重算。
- 每日补偿任务扫描缺失条目。

影响：

- `REQ-RNT-006` 无法按现有需求文档验收。
- 若后续回归 `RentTerm` 口径，M2 新设计的 `ContractLedgerEntry` 生成逻辑需要再次返工。

建议：

- 先决定是修订需求/附录，还是按现有 `RentTerm` 口径补全方案。
- 在追踪矩阵中不要把当前缩窄版本直接标成 `✅`。

### 4. 高风险：`REQ-RNT-005` 目前只有守门，没有形成“纠错闭环”

方案的 M2 目标是：

- 无台账时允许 `void`
- 有台账时拒绝 `void`
- 冲销留到 M3

这只能算“反审核拦截”，不是需求要求的“纠错闭环”。`REQ-RNT-005` 还要求：

- 必须先作废/冲销后再重建。
- 全流程强制留痕（原因、操作人、审批人、前后值、关联单号）。

当前 `ContractAuditLog` 字段也无法完整承载这些信息。

影响：

- `REQ-RNT-005` 不能在 M2 结束时标记为完成。
- 后续如果补冲销对象、关联单号和审批链，现有审计表很可能要扩表。

建议：

- 将 M2 目标调整为“守门 + 留痕基建”，不要在矩阵里提前收口到 `✅`。
- 或者把冲销对象、关联单号和审批字段一并前置设计。

### 5. 中风险：`ledger_v2.py` 的路由路径与现有装配方式不一致

方案写的是 `GET/PATCH /api/v1/contracts/{id}/ledger`，但当前 `backend/src/api/v1/rent_contracts/__init__.py` 只聚合现有 `contracts/lifecycle/terms/ledger/...` 子路由，并统一挂在 `/api/v1/rental-contracts` 前缀下。若只是新增 `ledger_v2.py` 而不调整装配：

- 新路由可能不会被注册。
- 或者实际路径会落到 `/api/v1/rental-contracts/contracts/{id}/ledger`，与方案文档不一致。

建议：

- 在方案里明确路由注册方式。
- 明确该接口是走独立 `api_router.include_router(...)`，还是继续挂在 `/rental-contracts` 下。

### 6. 中风险：兼容策略与项目当前“0 到 1 不做兼容保留”的约束冲突

方案明确写了：

- 旧 `rent_ledger` 不删。
- 旧 `rent_contracts` 数据与新 `contracts` 双表兼容共存。
- 旧 API 不迁移。

但 `AGENTS.md` 当前给出的仓库级约束是“项目目前在从 0 到 1 阶段的开发中，不要做兼容保留操作”。如果此处确实要例外保留兼容层，方案必须写清楚：

- 为什么必须保留。
- 兼容层的退出时间点。
- 清理动作归属到哪个里程碑。

否则 M2 会被默认推向长期双轨。

## 待确认项

1. `REQ-RNT-003` 之后到底以 `requirements-specification` 还是以附录第 8/11 节为准。
2. `REQ-PRJ-002` 的双入口后端契约是扩展 `asset_id` 过滤，还是新增 `project_id` 聚合接口。当前方案仍停留在二选一，前端页面任务因此没有稳定依赖。
3. `REQ-RNT-006` 是否接受 M2 先做缩窄版。如果接受，应同步把需求文档改成阶段性交付，而不是直接写最终态验收。

## 修订建议

建议先做文档收口，再做实现：

1. 先修订 `docs/requirements-specification.md` 中 `REQ-RNT-003/004/005/006` 的阶段性目标，确保与附录和计划一致。
2. 在方案中补齐联审模型、纠错链路留痕字段、路由装配方式。
3. 明确 M2 与 M3 的能力边界，不要把 M2 未交付能力提前记为 `✅`。
4. 双入口接口契约先拍板，再推进前端任务拆分。

## 备注

- 本报告只覆盖文档与现状代码的一致性审阅，不包含实现改动。
- 本报告归档于 `docs/archive/reviews/`，不作为当前需求或实现基线。
