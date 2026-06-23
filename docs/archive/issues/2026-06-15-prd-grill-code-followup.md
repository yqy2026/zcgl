# 2026-06-15 PRD Grill 代码收口跟踪

`/grill-with-docs docs/prd.md`（2026-06-15）产出的代码层待实施项。文档基线（PRD / domain-model / CONTEXT / ADR-0006~0009 / trace / CHANGELOG）已对齐，本记录跟踪**代码改造**进度（按本目录约定，逐项进度以 git commit 追溯）。

详细文件:行证据、改造点与验收见实施详单：[`docs/plans/2026-06-15-prd-grill-code-followup.md`](../plans/2026-06-15-prd-grill-code-followup.md)。

## 补逻辑收口

| 项 | 内容 | 决策 | 关键证据 | 状态 |
|---|---|---|---|---|
| F1 | 通知接收人按主体绑定数据范围过滤（业务类通知不再全员广播；系统通知除外） | REQ-NTF-001 / §8 | `services/notification/scheduler.py`、`tests/unit/services/notification/test_scheduler.py` | ✅ 已实施 |
| F2 | 合同更正陈旧已收台账派生风险 `ledger_stale_after_correction` + 前端展示 `skipped_entries` | ADR-0008 / REQ-RNT-005 | `services/contract/ledger_service_v2.py`、`services/project/service.py`、`frontend/src/pages/ContractGroup/ContractGroupDetailPage.tsx` | ✅ 已实施 |
| F3 | 权限管理员授予边界：`perm_admin` 禁授业务角色（含授予自己），业务角色仅 `admin`/`system_admin` 可授予 | ADR-0009 / §5 / REQ-AUTH-001 | `services/permission/rbac_service.py`、`tests/unit/services/permission/test_rbac_service.py` | ✅ 已实施 |
| F4 | 项目分析端点在 `scope_mode=all` 下靶向抑制客户双指标（置空+标记），其余分析照常 | REQ-ANA-001 / 客户双指标视图口径 | `api/v1/assets/project.py`、`services/project/service.py`、`schemas/project.py`、`frontend/src/pages/Project/ProjectDetailPage.tsx` | ✅ 已实施 |

## 删除类拆除

| 项 | 内容 | 决策 | 状态 |
|---|---|---|---|
| D1 | 删催缴模块（model/crud/service/schema/API + 前端 `types/collection.ts` + 删表迁移 + 测试） | ADR-0006 | ✅ 已实施 |
| D2 | 删逾期手工 `overdue` 登记态、统一派生口径、补 `due_date` 过滤、存量迁移、前端去状态选项 | ADR-0007 | ✅ 已实施 |

## 验收

每项 F 的「验收」即可写成测试断言（见实施详单对应小节）。删除类 D1/D2 以「全库无残留引用 + 存量迁移行为明确（不可恢复迁移需显式失败）+ 相关测试通过」为完成标志。
