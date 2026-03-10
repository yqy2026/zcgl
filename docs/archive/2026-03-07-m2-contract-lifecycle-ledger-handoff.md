# M2 Contract Lifecycle And Ledger Handoff

## 1. 背景与最初目标

本轮工作的最初目标是实施 `docs/plans/2026-03-06-m2-contract-lifecycle-and-ledger.md`，按新合同体系完成以下事项：

- 在新 `contracts / contract_groups` 模型上落地生命周期状态机
- 新建审计日志与新台账表，并在审核通过时自动生成台账
- 逐步下线旧 `rent_contract` 领域模型、API、service、schema、测试与前端入口
- 补齐前端合同组管理页面与双入口能力

补充说明：

- 当前 worktree 路径是 `/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger`
- 主工作区 `/home/y/projects/zcgl` 中存在一批重复脏改动，不应继续作为本任务的真相源
- 原始 plan 文件当前存在于主工作区 `docs/plans/2026-03-06-m2-contract-lifecycle-and-ledger.md`
- 当前 worktree 的 `docs/plans/` 未同步该文件，因此后续执行请以本交接文档 + worktree 当前代码状态为准

## 2. 当前完成状态

### 2.1 后端核心能力

已完成：

- 新合同生命周期核心已落地，包含 `submit_review / approve / reject / expire / terminate / void`
- `ContractAuditLog` 已落地并接入生命周期留痕
- `ContractRentTerm` 已落地，支持合同租金条款 CRUD
- `ContractLedgerEntry` 已落地，`approve()` 时会在同事务内自动生成台账
- 合同组批量提审已实现
- 新合同台账查询与批量更新接口已实现
- 催缴记录、权属财务汇总、资产删除守门、鉴权范围推断等关键运行时消费者已迁到新合同表
- 新合同 service / API 包路径已收口到：
  - `backend/src/services/contract/`
  - `backend/src/api/v1/contracts/`

关键文件：

- [contract_group.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/src/models/contract_group.py)
- [contract_group_service.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/src/services/contract/contract_group_service.py)
- [ledger_service_v2.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/src/services/contract/ledger_service_v2.py)
- [contract_groups.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/src/api/v1/contracts/contract_groups.py)

相关迁移：

- [20260306_m2_contract_lifecycle_core.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/alembic/versions/20260306_m2_contract_lifecycle_core.py)
- [20260306_m2_contract_ledger_entries.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/alembic/versions/20260306_m2_contract_ledger_entries.py)
- [20260307_m2_contract_number_on_contracts.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/alembic/versions/20260307_m2_contract_number_on_contracts.py)
- [20260307_m2_collection_records_contract_fk.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/alembic/versions/20260307_m2_collection_records_contract_fk.py)
- [20260307_m2_cleanup_legacy_contract_policy_rules.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/alembic/versions/20260307_m2_cleanup_legacy_contract_policy_rules.py)

### 2.2 旧后端合同域清理

已完成：

- 旧 `/api/v1/rental-contracts/*` 运行时入口已下线
- 旧 `rent_contract` API、service、Excel 服务、旧白名单、旧字段校验兼容层已基本退休
- 旧 `models/rent_contract.py`、`crud/rent_contract.py`、`schemas/rent_contract.py` 已从运行时主链路移除
- 旧 `rent_contract` 包路径已从活跃 backend service / API 层收口
- 旧 ABAC `rent_contract` 资源规则已有补充迁移负责清理存量数据

仍需注意：

- 清理范围很大，虽然大量 targeted tests 已跑，但还没有在“当前最终状态”上做一轮全量后端门禁复跑
- 主工作区中仍有重复脏改动，不要在主工作区继续清旧域

### 2.3 前端状态

已完成：

- 旧 `/rental/*` 页面入口已统一接到退休页
- 活跃前端权限资源口径已切到 `contract`
- 旧 `rentContractService`、`rentContractExcelService`、`RENT_CONTRACT_API`、旧 MSW handler 已从活跃运行时移除
- 权属详情页、模板页、通知中心、健康检查、导航、面包屑已收口为退休态
- 活跃 E2E 中与旧合同相关的 API token、旧路由 token、旧文件名前缀已集中收口到 helper
- 过时的旧合同创建工作流 E2E 已删除
- 用户可用性 E2E 已改为验证“旧租赁入口已退休但可达”

关键文件：

- [LegacyRentalRetiredPage.tsx](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/frontend/src/pages/Rental/LegacyRentalRetiredPage.tsx)
- [routes.ts](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/frontend/src/constants/routes.ts)
- [AppRoutes.tsx](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/frontend/src/routes/AppRoutes.tsx)
- [menuConfig.tsx](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/frontend/src/config/menuConfig.tsx)
- [breadcrumb.ts](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/frontend/src/config/breadcrumb.ts)
- [frontend-legacy-contract-hygiene.test.ts](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/frontend/src/constants/__tests__/frontend-legacy-contract-hygiene.test.ts)
- [frontend-legacy-contract-e2e-hygiene.test.ts](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/frontend/src/constants/__tests__/frontend-legacy-contract-e2e-hygiene.test.ts)
- [legacyContract.ts](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/frontend/tests/e2e/helpers/legacyContract.ts)

### 2.4 文档与门禁

已完成：

- `CHANGELOG.md` 已持续记录各批次变更
- 部分 SSOT 文档和 field drift 脚本已更新
- `docs-lint` 在若干关键节点曾跑通

未完成：

- 尚未在“当前最新 worktree 状态”上统一重跑一次完整 `make check`
- 原始 M2 plan 还没有进入“已完成归档”状态，因为功能本身还没全部做完

## 3. 尚未完成的任务

以下是目前最重要、且还没有完成的任务。

### 3.1 必做任务

1. 实现真正的新前端合同组页面

- 目前前端做的是“旧租赁入口退休收口”
- 计划中的 `ContractGroupListPage / ContractGroupDetailPage / ContractGroupFormPage` 还没落地
- 这意味着 M2 的后端能力虽已存在，但前端还没有新的主操作入口

2. 重建 PDF 导入的“确认后创建新合同组/合同”流程

- 当前 `pdf_import_service.confirm_import()` 是 fail-closed 的退休态
- 旧 `RentContract` 创建链路已停掉
- 新 `ContractGroup + Contract + detail` 的确认落库流程还没接回去

3. 用新前端入口替换退休态导航

- 当前 `/rental/*` 仍是退休壳路由
- 等新合同组页面完成后，需要决定是否：
  - 把旧 `/rental/*` 继续保留为退休入口
  - 或者跳转到新 `/contract-groups/*`
- 这一步必须在新页面可用后再做

4. 补新体系的集成 / E2E 覆盖

- 旧合同工作流相关集成/E2E 已删除或改成退休态
- 新体系还缺一套等价验证：
  - `contract-groups -> contracts -> submit-review -> approve -> ledger`
  - 新 PDF 导入确认流程
  - 合同组与资产/项目双入口

5. 最终门禁与合并准备

- 需要在 worktree 上重跑一轮新的完整验证
- 完成后再决定如何把 worktree 合并回主工作区

### 3.2 条件性任务

1. 继续清理前端剩余低价值 legacy 命名

- 例如导航/面包屑/测试文件命名中仍保留一些 `/rental/*` 路由字面量
- 这些当前是“退休入口必须存在”的一部分，不应在没有替代入口前盲删

2. 审查 `frontend/src/components/Forms/RentContract/`

- 当前仍存在 `RentContract` 命名的表单组件
- 需要先确认是否还有真实消费者，再决定删除、迁移还是重命名
- 这块不应直接猜测处理

## 4. 建议的后续执行顺序

建议后续严格按下面顺序继续：

1. 继续只在 worktree `/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger` 上开发
2. 先实现新前端合同组页面和对应 service/types
3. 再接回 PDF 导入确认到新合同模型
4. 再补新的集成 / E2E 流程
5. 再决定旧 `/rental/*` 退休入口要保留多久
6. 最后跑完整门禁并准备合并

## 5. 当前验证状态

已经做过的大量 targeted verification 包括：

- 后端生命周期 / 台账 / collection / ownership / auth / migration 定向 `pytest`
- 前端退休态、权限元数据、导航、E2E hygiene、类型检查、定向 `vitest`
- 若干次 `oxlint` / `ruff check`
- 若干次 `make docs-lint`
- 一次 `playwright test --list` 用于确认 E2E 用例仍可装载

当前还没有做的最终验证：

- 没有在“当前最新 worktree 状态”上完整重跑 `make check`
- 没有在这最后一轮状态上真实跑新的 Playwright 浏览器用例

## 6. 关键风险与注意事项

1. 不要回主工作区继续做 M2

- 主工作区 `/home/y/projects/zcgl` 里存在之前误落的重复脏改动
- 当前 worktree 才是本任务的真相源

2. 不要把“退休入口”误当成“已完成新前端”

- 当前完成的是“旧入口显式退休”
- 不是“新合同组前端已完成”

3. 不要在未确认消费者前直接删 `RentContract` 命名组件

- 特别是 `frontend/src/components/Forms/RentContract/`
- 这块需要先做消费者检查，再拆小批次处理

4. 不要现在就归档原始 M2 plan

- 因为功能尚未完结
- 等新前端和新导入流程真正完成后，再把原计划文件从 `docs/plans/` 移到 `docs/archive/backend-plans/`

## 7. 接手时建议先执行的命令

```bash
cd /home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger
git status

cd backend
uv run pytest tests/unit/services/contract/test_contract_group_service.py tests/unit/services/contract/test_ledger_service_v2.py --no-cov -q

cd ../frontend
pnpm exec vitest run src/constants/__tests__/frontend-legacy-contract-hygiene.test.ts src/constants/__tests__/frontend-legacy-contract-e2e-hygiene.test.ts --no-coverage
pnpm type-check
```

如果要继续实现新前端主入口，建议从以下文件开始读：

- [contract_group_service.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/src/services/contract/contract_group_service.py)
- [contract_groups.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/src/api/v1/contracts/contract_groups.py)
- [ledger_service_v2.py](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/backend/src/services/contract/ledger_service_v2.py)
- [routes.ts](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/frontend/src/constants/routes.ts)
- [LegacyRentalRetiredPage.tsx](/home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger/frontend/src/pages/Rental/LegacyRentalRetiredPage.tsx)

## 8. 复核结论与建议

本次复核后的结论是：当前交接文档对“已经做了什么”和“还没做什么”描述基本准确，但为了让后续接手更稳，建议明确补充以下执行建议。

### 8.1 优先级建议

1. 暂停继续做低价值 legacy 文本清理

- 当前最关键的功能缺口不是再删几个 `/rental/*` 字符串
- 真正的阻塞是：
  - 新合同组前端页面缺失
  - 新 PDF 导入确认落库流程缺失
  - 新体系集成 / E2E 覆盖缺失
- 所以后续应优先补功能，不要继续把时间花在“退休入口文案再精修一层”

2. 新前端入口完成前，不要移除退休页

- 现在 `LegacyRentalRetiredPage` 是必要的 fail-closed 入口
- 在 `ContractGroupListPage / DetailPage / FormPage` 真正可用前，不应把旧 `/rental/*` 路由直接改跳新页或删除

### 8.2 合并建议

1. 在 worktree 完成最终验证前，不要回主工作区继续写代码

- 主工作区已有重复脏改动
- 继续在主工作区推进，只会让最终合并更难复核

2. 合并前先做一次“主工作区 vs worktree”文件清单对比

建议至少执行：

```bash
cd /home/y/projects/zcgl/.worktrees/m2-contract-lifecycle-ledger
git status
git diff --stat
git diff --name-status
```

如果准备回合主工作区，建议再在主工作区执行一次：

```bash
cd /home/y/projects/zcgl
git status
```

目的不是现在就处理，而是先确认哪些文件在两边都被改过，避免后面合并时误判。

### 8.3 文档与字段规格建议

1. 补一次 M2 范围内的字段规格回顾

当前 `make docs-lint` 虽然通过，但 `check_field_drift.py` 仍显示新合同体系有实际 drift，尤其是：

- `Contract.contract_number` 已存在于 ORM，但规格附录还没有完全对齐
- `ContractGroup.asset_ids` / `Contract.asset_ids` 在规格里是字段，但当前 ORM 口径更像关系/派生信息

这意味着后续在继续做前端和 API 时，文档与实现可能再次漂移。建议在恢复开发早期就补一轮字段规格澄清，而不是等最终收尾再修。

2. 不要把 field drift 的现有输出误判为本次 handoff 文档问题

- 当前 drift 是仓库已有实现状态的一部分
- 交接文档里应把它视作“待后续澄清事项”，不是“文档门禁失败”

### 8.4 恢复开发时的建议起手顺序

建议恢复开发时按下面顺序开工：

1. 先跑交接文档第 7 节里的最小回归命令
2. 确认 worktree 状态干净可继续
3. 先做新前端合同组页面的 service/types/list/detail/form
4. 再接回 PDF 导入确认后的新模型落库
5. 再补新的集成 / E2E
6. 最后再处理剩余 legacy 收口和合并

### 8.5 不要直接猜测处理的区域

以下区域后续不要直接删或直接重命名，必须先做消费者检查：

- `frontend/src/components/Forms/RentContract/`
- 前端导航与面包屑里仍保留的 `/rental/*` retired 路由常量
- 任何仍然引用 `LegacyRentalRetiredPage` 的入口

建议先用：

```bash
rg -n "Forms/RentContract|LegacyRentalRetiredPage|/rental/" frontend/src frontend/tests
```

确认消费者之后，再按小批次处理。

## 9. 边界情况与测试建议

在继续实现新前端和 PDF 导入流程时，需要特别注意以下边界情况，并确保测试覆盖：

### 9.1 合同组生命周期边界

- **空合同组提交审核**：合同组下无任何合同时，是否允许提审？预期：不允许，需前端校验。
- **混合状态合同提审**：合同组内合同状态不一致（部分 draft，部分 approved）时提审，预期：只提审 draft 状态的合同。
- **过期合同处理**：合同已过期但未终止时，是否仍可生成台账？预期：根据业务规则，可能仍需生成历史台账。
- **终止与作废区别**：终止是正常结束，作废是无效合同，两者对台账和审计日志的影响不同。

测试用例建议：
- 合同组批量提审时，验证只有 draft 合同进入审核状态。
- 审核通过后，验证台账自动生成，且包含所有租金条款。
- 合同过期后，验证生命周期状态正确更新。

### 9.2 PDF 导入确认边界

- **重复导入同一 PDF**：如何防止重复创建合同组？预期：基于 PDF 哈希或内容校验去重。
- **部分失败的确认**：确认过程中部分合同创建成功，部分失败，如何回滚？预期：事务性保证全部成功或全部失败。
- **字段映射错误**：PDF 提取字段与新合同模型不匹配，如何处理？预期：提供手动修正界面。
- **多资产合同**：一个 PDF 对应多个资产，如何映射到合同组？预期：支持一 PDF 多合同组。

测试用例建议：
- PDF 导入确认后，验证合同组、合同、租金条款正确创建。
- 模拟 PDF 提取失败，验证错误处理和用户提示。
- 重复导入相同 PDF，验证去重逻辑。

### 9.3 前端双入口边界

- **资产详情页入口**：从资产页进入合同组列表，过滤逻辑是否正确？
- **项目详情页入口**：从项目页进入，权限和数据隔离是否正确？
- **权限不足访问**：无权限用户访问合同组页，预期：403 或隐藏入口。
- **数据加载失败**：API 失败时，前端错误处理和重试机制。

测试用例建议：
- E2E 测试：资产页 → 合同组列表 → 详情 → 编辑 → 提审 → 审核。
- 权限测试：不同角色用户访问不同入口的可见性和操作权限。

### 9.4 集成测试覆盖

建议新增以下集成测试场景：
- 完整合同生命周期：创建 → 提审 → 审核通过 → 台账生成 → 催缴 → 过期。
- PDF 导入端到端：上传 PDF → 提取 → 确认 → 合同创建 → 台账生成。
- 并发操作：多个用户同时操作同一合同组，验证锁机制。

## 10. 总结

本手交文档总结了 M2 Contract Lifecycle And Ledger 的当前进展。后端核心能力已基本落地，前端旧域清理已完成，但新前端入口和 PDF 导入流程仍需实现。建议后续按优先级顺序推进，避免在主工作区继续开发，确保最终合并前进行完整验证。

关键提醒：
- 继续在 worktree 上开发
- 优先补新功能，而非继续清理 legacy 文本
- 在实现新入口前保留退休页
- 定期更新 CHANGELOG.md 和相关文档

如有疑问，请参考 AGENTS.md 或联系原开发人员。
