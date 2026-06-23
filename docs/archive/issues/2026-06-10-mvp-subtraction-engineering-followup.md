# MVP 减法工程清理 Followup（2026-06-10）

**来源**: `/grill-with-docs docs/prd.md` 会话产出的 MVP 减法决策。
**状态**: A/B/C/D/E/F/G/H/I/J/K 已落地。
**用途**: 记录本轮工程清理范围和完成证据，后续不再作为活跃计划推进。

---

## 完成项

### A. 删除资产路由审批流（ADR-0002）

- [x] 删除 approval 模型、CRUD、schema、service 和 API。
- [x] 路由注册、模型导出、通知服务和 RBAC seed 去除审批相关内容。
- [x] 新增迁移清理审批三表、旧审批通知和审批权限数据。
- [x] 删除旧审批正向测试，补充路由退役、迁移和 RBAC seed 护栏测试。

### B. 资产确认权限门控与批量提交/确认

- [x] 资产确认仅按复核权限门控，不限制审核人必须不同于提交人。
- [x] 新增批量提交 `draft -> pending` 与批量确认 `pending -> approved`。
- [x] 前端资产列表增加批量提交/确认入口。
- [x] 补充 API、service、前端和权限相关测试。

### C. 删除合同上下游逐对配对与覆盖风险（ADR-0003）

- [x] 删除运行时 `ContractRelation` / `ContractRelationType.RENEWAL`。
- [x] 清理 CRUD、schema、service 中的配对关系和续签父子查询入口。
- [x] 纠错草稿来源改为 `contracts.correction_source_contract_id`。
- [x] 删除 `missing_primary_contract` / `coverage_conflict` 风险分支。
- [x] 新增迁移删除 `contract_relations` 表并补纠错来源字段。

### D. settlement_rule 选填可缓填（ADR-0004）

- [x] `ContractGroupCreate.settlement_rule` 改为可空。
- [x] 数据库 `contract_groups.settlement_rule` 放宽为 nullable。
- [x] 创建/更新路径允许缺省或清空结算规则。
- [x] 移除 `predecessor_group_id` 续签残留。
- [x] 前端表单和详情支持未配置结算规则。

### E. 客户双指标口径与 customer_type 解耦

- [x] 经营指标只统计终端 lessee。
- [x] 上游产权方和委托运营对手方不进入客户主体数/客户合同数。
- [x] `customer_type` 降为展示标签，不参与经营指标过滤。
- [x] 分析接口拒绝 `view_mode=all` 混合口径。

### F/G. 台账覆盖率删除与实收登记正名

- [x] 删除台账覆盖率指标残留。
- [x] 明确台账实收登记属于 In Scope。
- [x] 前端财务台账提供单条实收登记入口。
- [x] 收缴率以 `paid_amount` 为事实来源。

### H. 删除产权证 is_verified（ADR-0005）

- [x] 后端模型、schema、导入默认写值、白名单和校验常量删除核验状态。
- [x] 新增迁移删除 `property_certificates.verified`。
- [x] 前端产权证列表/详情移除审核状态列、徽标和切换按钮。
- [x] 产权证质量风险只保留客观触发条件。

### I. 乐观锁范围收口

- [x] 删除 `ContractGroup.version` 与 `Contract.version` 误导性列和相关写入。
- [x] Asset 乐观锁保持不变。
- [x] 新增迁移删除合同组/合同表中的 `version` 列。

### J. PartyContact 电话加密补漏

- [x] `CRUDParty` 接入 `SensitiveDataHandler`。
- [x] `PartyContact.contact_phone` 写入确定性加密、读取解密。
- [x] 新增迁移加密存量电话并清理 `Party.metadata_json` 联系人 PII。
- [x] 同步 `docs/security/encryption.md` 与 `backend/CLAUDE.md`。

### K. 客户主体数与项目 tenant 去重修正

- [x] 全局 `customer_entity_count` 只累计终端 lessee。
- [x] 项目租户汇总按 `party_id` 去重。
- [x] 补充 analytics/project 回归测试。

## 验收备注

- 本轮 targeted checks 已覆盖关键后端文件 py_compile、定向 ruff、前端定向 lint/format 和 `ProjectDetailPage` Vitest。
- 当前本机环境缺少可用 `make`，后端 venv 存在 Python/二进制依赖不匹配，无法执行完整 `make check` 或完整 backend pytest。
- 提交前已用 `scripts/check_requirements_authority.py`、`scripts/check_field_drift.py` 和 `git diff --cached --check` 复核文档门禁与暂存区。
