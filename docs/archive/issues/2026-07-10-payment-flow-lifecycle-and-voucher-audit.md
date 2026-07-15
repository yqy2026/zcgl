# 收付流水作废更正与凭证审计后续项

**状态**：✅ 已实施（2026-07-14）
**来源**：经营台账与收付流水主计划收口后的非阻断增强项
**范围**：仅收付流水生命周期和凭证下载审计；不改变已落地的经营台账查询、分摊、服务费和统计口径。

## 背景

实收/实付已只允许通过 `OperationalPaymentFlow` 与 `PaymentAllocation` 写入，旧直接改 `paid_amount` 入口已下线。本项补齐流水登记错误后的显式作废/更正，以及可选凭证附件的下载审计证据。

## 已定方案

1. 不做财务红字冲销，不引入会计凭证概念。
2. `active` 流水可作废为 `voided`；原记录不删除，其分摊立即不再参与实收/实付汇总，所有受影响台账在同一事务中重算。
3. 更正为单一事务：原流水转 `corrected`，创建一条新 `active` 流水及其分摊，新记录通过 `corrected_from_flow_id` 指向原记录；新流水必须保持原类型以及项目/产权方/运营方/币种范围，新旧目标合并后按稳定 ID 顺序一次加锁。
4. 作废/更正记录操作人、操作时间和原因，并沿用收付流水所在项目/主体的数据范围鉴权。
5. 仓库原先没有通用 `Attachment` ORM，本次新增最小通用附件元数据表并首先用于 `payment_flow`；未新建凭证业务表，也未迁移资产、合同和产权证的既有附件存储。上传使用 20MB 有界读取及 MIME/扩展名/固定文件头校验；下载记录用户、流水、附件、时间和结果。
6. 租金台账与服务费台账继续使用分类查询载荷，不新增统一混合列表响应。

## 实现证据

- 生命周期模型与迁移：`backend/src/models/contract_group.py`、`backend/alembic/versions/20260713_payment_flow_lifecycle_audit.py`。
- 原流水行锁、唯一更正后继、终态审计、同事务新旧分摊重算与回滚：`backend/src/services/contract/payment_flow_service.py`。
- 通用附件元数据与凭证服务：`backend/src/models/attachment.py`、`backend/src/crud/attachment.py`、`backend/src/services/contract/payment_voucher_service.py`、`backend/alembic/versions/20260713_payment_voucher_attachments.py`。
- 独立下载权限与 API：`backend/alembic/versions/20260713_payment_voucher_download_permission.py`、`backend/src/api/v1/contracts/ledger.py`。
- 前端流水明细、作废、更正、凭证上传/下载和审计：`frontend/src/pages/OperationsLedger/OperationsLedgerPage.tsx`、`frontend/src/services/ledgerService.ts`。
- SSOT：`docs/specs/domain-model.md`、`docs/specs/api-contract.md`、`docs/traceability/requirements-trace.md`。

## 完成核对

- [x] ORM / migration / schema 表达原流水关联和操作审计字段。
- [x] Service 在一个事务内完成作废或更正、有效分摊切换和受影响台账重算。
- [x] API 和前端只暴露明确动作，不允许直接写 `status` 或 `paid_amount`。
- [x] 凭证下载有按流水可查询的审计证据，未授权主体不可读取附件或审计元数据。
- [x] 覆盖重复作废、更正作废流水、跨主体分摊、部分失败回滚、行锁与唯一更正后继约束。

## 验证证据

- 后端生命周期/凭证/迁移/API 定向回归 `95 passed`，最终凭证服务回归 `4 passed`；最终全量 unit `4668 passed, 50 skipped, 436 deselected`、覆盖率 `76.97%`。
- 前端 service 与页面定向回归 `29 passed`；全量 Vitest `189 files / 2292 passed`；全量 lint `0 warnings / 0 errors`，UI/权限元数据/格式守卫、应用与 E2E type-check、生产构建均通过。
- 后端全量 Ruff、迁移命名、唯一 Alembic head、应用导入、`check_requirements_authority.py` 与 `check_field_drift.py` 等价 docs-lint 通过；`Attachment` 已纳入字段漂移模型映射。
- 当前 Windows 环境没有 `make` 可执行文件，因此最终门禁按 Makefile 目标展开执行。

## 已知边界

- 下载审计的 `success` 表示服务端已完成授权且文件已就绪，不声明客户端已完整接收文件。
- 无分摊流水没有可验证的冻结项目/主体归属，详情、生命周期和凭证服务按不存在失败关闭；应先完成分摊。
- 原流水凭证保留在原流水；更正请求不得复制旧凭证 ID，新流水凭证在更正成功后重新上传。
