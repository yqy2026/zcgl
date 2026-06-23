# 2026-06-16 PRD Grill 代码收口跟踪

`/grill-with-docs docs/prd.md`（2026-06-16）产出的代码层收口项。文档基线（PRD / domain-model / CONTEXT / ADR-0010~0014 / trace / CHANGELOG）已对齐，本记录跟踪**代码改造**进度（逐项进度以 git commit 追溯）。

详细文件:行证据、改造点与验收见实施详单：[`docs/plans/2026-06-16-prd-grill-code-followup.md`](../plans/2026-06-16-prd-grill-code-followup.md)。

本轮主题是「建模口径修正 + 删孤儿」，因果链：re-org 可发生（C1）→ 台账须固化归属（C2~C4）→ 合同关系须锁单项目保固化唯一（C5~C7）→ 顺带删两套孤儿/越界 vNext 残留（D-A/D-B）。

## 口径修正 / 加固化

| 项 | 内容 | 决策 | 关键证据 | 状态 |
|---|---|---|---|---|
| C1 | `Asset.manager_party_id` 改派生（= 当前项目运营方）；manager 绑定数据范围过滤改读「资产当前项目运营方」，无项目资产对运营绑定用户不可见；`owner_party_id` 不动 | ADR-0010 | `models/asset.py`、`crud/asset.py`、`middleware/resource_context.py`、`services/asset/asset_service.py`、`services/asset/batch_service.py` | ✅ 已实施 |
| C2 | `ContractLedgerEntry` 增固化列 `attributed_project_id/owner_party_id/operator_party_id/asset_ids`；生成与重算新建条目写入（`asset_ids` 取 `Contract.asset_ids`，空=整租回退组 `asset_ids`）；`ServiceFeeLedger` 继承来源台账固化 | ADR-0011 | `services/contract/ledger_service_v2.py`、`services/contract/service_fee_ledger_service.py`、`models/`（台账模型 + 迁移） | ✅ 已实施 |
| C3 | 项目/产权方维度历史与分析聚合改读条目固化归属，**禁 join 合同组/资产当前归属** | ADR-0011 | `services/analytics/analytics_service.py`、`services/project/service.py`、`crud/contract_group.py` | ✅ 已实施 |
| C4 | 存量台账条目一次性回填固化归属（按当前关联回填，接受 = 当时归属的近似） | ADR-0011 | `backend/alembic/versions/20260618_backfill_ledger_frozen_attribution.py` | ✅ 已实施 |
| C5 | 补「合同组覆盖资产的当前项目 == ContractGroup.project_id」校验（按 active `project_assets` 当前绑定判定） | ADR-0012 | `crud/contract_group.py`、`services/contract/contract_group_service.py`、`tests/unit/services/contract/test_contract_group_service.py` | ✅ 已实施 |
| C6 | 补 `Contract.asset_ids ⊆ ContractGroup.asset_ids` 子集校验（留空=整租跳过） | ADR-0012 | `crud/contract_group.py`、`services/contract/contract_group_service.py`、`tests/unit/services/contract/test_contract_group_service.py` | ✅ 已实施 |
| C7 | 代理合同跨项目共享盖章扫描件：同一份扫描件单存、多项目下同号 `Contract` 共享引用；联动范围收窄为同合同号 + 同委托方 + 同受托方 + 正常代运营受托角色，写入前逐条鉴权，复用既有 `storage_key` 时拒绝范围外链接；合同号按项目复合唯一且正常合同必须落项目 | ADR-0012 | `models/contract_group.py`、`crud/contract.py`、`services/contract/contract_group_service.py`、`api/v1/contracts/contract_groups.py`、`20260620_contract_number_project_scan_documents.py` | ✅ 已实施 |

## 删除类拆除

| 项 | 内容 | 决策 | 状态 |
|---|---|---|---|
| D-A | 删合同审批流：`ContractReviewStatus` 列 + `PENDING_REVIEW` 态、`submit_review`/`approve`/驳回/`reverse`-as-review/`submit_group_review`/`_requires_joint_review` 及端点；`start_correction` 门禁改绑生命周期状态；组「生效中」派生改读收缩状态集；补录直接置生效；存量 `review_status`/`PENDING_REVIEW` 迁移；删 `test_contract_joint_review.py`；护栏测试。**是 REQ-RNT-004 联审残留的补完清理** | ADR-0013 | ✅ 已实施 |
| D-B | 删 `Project.review_status`/`review_by`/`reviewed_at`/`review_reason` 列 + `ProjectReviewStatus` 枚举、drop 列迁移、字段白名单清理、护栏测试 | ADR-0014 | ✅ 已实施 |

## 验收

- **C1**：manager 绑定用户只看到「其绑定运营方当前所运营项目下的资产」；资产挪项目后可见性随之翻；无项目资产不进 manager 视角、产权绑定视角照看；资产 distinct 下拉、导入 create 鉴权和通用 update 旁路均不再信任独立 `Asset.manager_party_id`。（已实施：Ruff 通过；pytest 受本地 venv 解释器缺失阻塞）
- **C2~C4**：新生成/重算新建台账条目已带固化归属，服务费台账已继承来源固化；项目/产权方历史聚合、项目台账摘要、项目分析趋势、全局经营分析项目拆分已改读 `attributed_*`；存量回填迁移按当前关联一次性补齐，且回填后仍有空归属会失败暴露。验收覆盖把合同组挪到别的项目后，**历史月份的项目/产权方报表数字不变**（账本语义回归测试）。
- **C5/C6**：资产绑到与自身当前项目不符的合同组被拒；合同覆盖资产超出关系范围被拒；合同 `asset_ids` 留空按整租处理。（已实施：Ruff 通过；pytest 受本地 venv 解释器缺失阻塞）
- **C7**：一份委托协议覆盖 N 个项目时，扫描件只存一份，N 条合同记录共享引用；同 `contract_number` 可在不同项目各建一条，同一项目内仍被复合唯一约束拦截，正常合同缺项目由 DB check constraint 拦截；替换/删除只影响同合同号 + 同委托方 + 同受托方 + 正常代运营受托角色的兄弟记录，并对全部受影响合同逐条鉴权；复用既有扫描件时若该 `storage_key` 已链接到范围外合同会拒绝，删除共享扫描件时受影响合同都至少保留 1 份盖章扫描件。（已实施：Ruff/py_compile/docs-lint 可用校验通过；pytest 受本地 venv/uv 环境阻塞）
- **D-A/D-B**：全库无 `ContractReviewStatus`/`_requires_joint_review`/`ProjectReviewStatus` 残留引用；存量迁移行为明确（不可恢复迁移显式失败）；合同补录即生效、更正门禁绑生命周期状态仍可用；路由/模型/迁移护栏已覆盖。
