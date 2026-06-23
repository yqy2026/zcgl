# ADR-0006: 删除催缴管理模块（催缴工单 / 状态机 / 成功率）

**状态**: ✅ 已实施（2026-06-15）
**决策日期**: 2026-06-12
**实施日期**: 2026-06-15
**相关需求**: REQ-RNT-006（台账实收登记为逾期处理唯一闭环）、PRD §4.2 新增 Out of Scope 条目

---

## 背景

后端存在一套完整但从未进入需求基线的催缴管理模块：

- `models/collection.py`：`CollectionRecord` 催缴记录 + `CollectionStatus` 状态机（`PENDING / IN_PROGRESS / SUCCESS`）。
- `crud/collection.py` / `services/collection/service.py`：催缴 CRUD、催缴任务摘要（逾期台账统计、待催缴数、本月催缴数、**催缴成功率**）。
- `schemas/collection.py`：`CollectionTaskSummary` 等契约。

交叉核对（2026-06-12）发现它处于**范围真空**：

- **PRD 零提及**：全文搜不到「催缴」，既不在 In Scope 也不在 Out of Scope。
- **api-contract 零条目**：契约文档没有催缴接口。
- **前端只有孤儿类型文件**：`frontend/src/types/collection.ts` 无任何页面或组件引用——后端建好、前端没接的半成品。

## 决策

**删除催缴管理模块**（删而非冻，对齐 ADR-0002 减法原则）：

1. **后端拆除**：删 `CollectionRecord` 模型、`CollectionStatus`、collection CRUD/service/schema 及对应 API 端点（如有注册）；写删表迁移。
2. **前端拆除**：删孤儿文件 `frontend/src/types/collection.ts`。
3. **PRD 补位**：§4.2 Out of Scope 增列「催缴管理」，明确逾期处理依靠台账逾期查询 + 台账实收登记闭环（REQ-RNT-006）。
4. **CONTEXT.md**：增「催缴管理（MVP 已删除）」词条。

删除理由：

1. **任务/待办外壳**：催缴单有状态机、有处理流程，本质是工单管理；本 PRD 在解析域反复确立「不生成任务、待办」的产品哲学，逾期处理没有理由例外。
2. **KPI 过度建模**：「催缴成功率」是没人天天看的指标，与已删的「台账覆盖率」同病（为 KPI 建精确口径属过度建模）。
3. **核心动作已闭环**：用户的真实动作是「看哪些条目逾期 → 去收钱 → 登记实收」，台账逾期筛选 + 实收登记（REQ-RNT-006，In Scope）即可完成；催缴记录只是给该动作加流程外壳。
4. **基线外代码即债**：不在需求基线里的已建成代码每多活一天，就多一天被前端接上的风险（同 Ownership、审批流处理先例）。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| 冻结保留（不删代码，不接前端） | 基线外代码持续吸引维护与误用；本模块无外部副作用依赖，拆除成本低，不适用 Ownership 式冻结 |
| 纳入 In Scope 补 PRD 条目 | 与「不生成任务、待办」哲学冲突；台账逾期查询 + 实收登记已覆盖核心闭环，催缴工单不解决 MVP 一票否决目标中的任何一项 |

## 关键冻结决策

1. **MVP 不建催缴工单**：无催缴记录、无催缴状态机、无催缴成功率统计。
2. **逾期处理唯一闭环**：台账逾期查询 → 线下催收 → 台账实收登记（REQ-RNT-006）。
3. **催收分派与跟踪若将来需要**：属 vNext，须以真实催收量与分派需求为前提另行设计，不直接复活本模块。

## 影响

- **后端**：已删 `models/collection.py`、`crud/collection.py`、`services/collection/`、`schemas/collection.py` 及 `api/v1/system/collection.py`；`api/v1/__init__.py` 不再导入催缴自注册路由；`models/__init__.py`、`crud/__init__.py`、CRUD 字段白名单与 authz runtime registry 已移除 `collection` 资源。
- **迁移**：新增 `backend/alembic/versions/20260615_drop_collection_module.py`，删除 `collection_records` 表、PostgreSQL enum 类型残留和 `collection` 的 ABAC/RBAC runtime 权限残留。
- **前端**：已删孤儿文件 `frontend/src/types/collection.ts`，并从能力类型 `frontend/src/types/capability.ts` 移除 `collection` 资源。
- **测试**：已删除催缴 API/CRUD/service 功能单测，新增路由删除护栏与删表/权限清理迁移测试；历史 `20260307_m2_collection_records_contract_fk.py` 迁移与测试保留用于旧库升级链。
- **PRD**：§4.2 已增列（本次决策随手落）。
- **CONTEXT.md**：已增词条（本次决策随手落）。
- **CHANGELOG.md**：记录本次变更。

## 参考

- `CONTEXT.md`：`催缴管理（MVP 已删除）`、`台账覆盖率（MVP 已删除）` 词条
- 相关簇：[ADR-0002](./ADR-0002-asset-review-no-approval-workflow.md)、[ADR-0003](./ADR-0003-contract-relation-direction-only.md)、[ADR-0004](./ADR-0004-settlement-rule-optional-at-creation.md)、[ADR-0005](./ADR-0005-drop-property-certificate-verification.md)（MVP 减法）
