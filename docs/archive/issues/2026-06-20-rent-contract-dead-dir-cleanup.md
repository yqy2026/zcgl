# 技术债排查：rent_contract 旧合同域空目录残留清理

**状态**: ✅ 已闭环（空目录已删，验证通过）
**日期**: 2026-06-20
**触发**: AGENTS.md / CLAUDE.md 核对任务中发现 `api/v1/` 目录声明与实际代码不符

---

## 1. 结论

M2 合同组重构（REQ-RNT-001 / REQ-RNT-006）下线旧合同域时，源码 `.py` 已按 AD-4 删除，但 **3 个空目录壳 + `__pycache__` 编译缓存残留未清理**。本轮已删除空目录并验证无副作用。**无功能丢失** —— 新实现（`contracts/` 模型 + `services/contract/` 服务）已全部落地。

## 2. 发现与处理

### 2.1 已删除的空目录（仅含 `__pycache__`，零 `.py` 源码）

| 目录 | 残留内容 | 处理 |
|------|---------|------|
| `backend/src/api/v1/rent_contract/` | `__pycache__`（attachments/contracts/excel_ops/ledger/lifecycle/statistics/terms 的 .pyc，312/313 双版本） | 已删除 |
| `backend/src/api/v1/rent_contracts/` | `__pycache__`（同名 7 模块 .pyc，312 版本） | 已删除 |
| `backend/src/services/rent_contract/` | `__pycache__`（helpers/ledger_service/lifecycle_service/service/statistics_service 的 .pyc） | 已删除 |

### 2.2 删除前安全闸（全部通过）

1. **全后端 import 引用扫描**：`src/` + `tests/` 下无任何 `import rent_contract` / `import rent_contracts`。仅有的 6 处字符串匹配均为**迁移测试断言**，非活引用：
   - `tests/unit/migration/test_contract_group_legacy_backfill_migration.py` —— `FakeInspector.has_table("rent_contracts")` 喂给迁移测试的旧表名字面量
   - `tests/unit/migration/test_policy_package_seed_actions.py` —— `assert "rent_contract" not in _EXPANDED_RESOURCE_TYPES`，保护性断言（验证旧资源类型已移除）
2. **删除后 import 验证**：`uv run python -c "import src.main"` → `IMPORT OK`，无破坏。

### 2.3 功能未丢失的证据（对照 M2 方案 AD-4）

旧 `rent_contract/` 8 个模块的功能已被 M2/M3 新实现**有意替换**（方案 `docs/archive/backend-plans/2026-03-06-m2-contract-lifecycle-and-ledger.md` §AD-4 明确"旧合同域全量下线，不迁移数据"）：

| 旧模块 | 新实现落地证据 |
|--------|---------------|
| 旧 lifecycle（renew/terminate）| `contract_group_service.py` 新状态机（submit/approve/reject/expire/terminate/void）+ `ContractAuditLog`（`models/contract_group.py:622`）|
| 旧 ledger / deposit-ledger / service-fee-ledger | `ContractLedgerEntry`（`:737`）+ `ServiceFeeLedger`（`:863`）+ `services/contract/ledger_service_v2.py` + `service_fee_ledger_service.py` |
| 旧 terms | `ContractRentTerm`（`:671`）|
| 旧 statistics（asset/monthly/overview/ownership）| 新 analytics 全新设计（`/comprehensive` `/trend` `/distribution`），旧维度端点按重构弃用 |
| 旧 excel_ops | 迁至 `documents/excel/` |
| 旧 attachments | `ContractScanDocument` + `contract_groups.py` scan document 端点 |

**M2 计划文件落地核对全部 ✅**：`ContractAuditLog` / `ContractRentTerm` / `ContractLedgerEntry` / `ServiceFeeLedger` 四个 ORM 类均在 `models/contract_group.py`；`ledger_service_v2.py` / `service_fee_ledger_service.py` 均在 `services/contract/`。

## 3. 排查过程中的两处自我纠正

> 按 12-rule「Fail loud」「Surface conflicts」要求如实记录，避免错误结论进入 SSOT。

1. **首轮误判"4 项功能丢失"**：用 `renew` / `deposit-ledger` 关键字扫描"零匹配"得出"续约/押金台账/服务费台账/统计端点丢失"。**错误**——新模型用全新命名（`ServiceFeeLedger` 类而非 `deposit-ledger` 端点），M2 AD-4 明确旧域有意下线。纠正：查 M2 方案后确认非漏迁。
2. **首轮误判"route_registry spec-only"**：用 `findstr /s "register_router" api` 报"零匹配"得出"route_registry 机制文档有、代码无"。**错误**——findstr 把 `api` 当文件名而非目录。纠正：`findstr /s /n "register_router" *.py` 复扫确认 `core/router_registry.py:25` 定义、`authz.py:43` / `party.py:684` 真实自注册。route_registry 机制**真实存在且生效**，AGENTS.md §架构原则描述准确。

## 4. 遗留待办（不在本轮范围）

核对 AGENTS.md `api/v1/` 目录声明时，发现**声明不完整**（只列了 analytics/assets/auth/documents/rent_contracts/system 6 个，实际还有 authz/party/search/contracts/debug 等）。这是 SSOT 文档漂移，属下一轮「更新 AGENTS.md 目录声明」任务，单独处理。

## 5. 关联文档

- M2 方案：`docs/archive/backend-plans/2026-03-06-m2-contract-lifecycle-and-ledger.md`（§AD-4 旧域下线决策）
- M3 台账方案：`docs/archive/backend-plans/2026-03-24-req-rnt-006-ledger-m3-plan.md`
- 架构原则：`AGENTS.md` §架构原则（route_registry 自注册护栏）
