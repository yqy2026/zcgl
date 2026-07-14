# 已归档问题记录

本目录存放已经被 SSOT、代码实现或后续计划吸收的问题排查记录，仅用于历史追溯。

| 文档 | 内容 | 归档原因 |
|------|------|------|
| [2026-07-10-payment-flow-lifecycle-and-voucher-audit.md](./2026-07-10-payment-flow-lifecycle-and-voucher-audit.md) | 收付流水作废/更正状态机与凭证下载审计 | 生命周期、事务重算、凭证权限/审计和前端操作已实施并通过定向门禁 |
| [2026-07-06-operations-ledger-prd-revision.md](./2026-07-06-operations-ledger-prd-revision.md) | 经营台账、收付流水、四类经营口径与服务费结算修订 | 核心口径已被 PRD/spec/traceability 和实现吸收；拆出的流水生命周期与凭证审计已在 2026-07-13 完成并归档 |
| [2026-06-18-prd-grill-code-followup.md](./2026-06-18-prd-grill-code-followup.md) | 通知、资产/项目编码、产权证保存闸门与附件、合同号复合唯一等契约收口 | I1/I2①/I3~I9 代码项与门禁已收口；企业微信真实发送验证与正式 userid 映射拆至 `docs/issues/2026-06-23-wecom-userid-mapping-and-send-verification.md` |
| [2026-03-03-project-issues-analysis.md](./2026-03-03-project-issues-analysis.md) | 前后端 MyPy/Lint/构建历史排查 | 2026-06-22 复核时 `uv run mypy src --no-incremental` 已清零；原 148/49 errors 为历史快照 |
| [2026-04-06-requirements-specification-review.md](./2026-04-06-requirements-specification-review.md) | 旧 `requirements-specification.md` 业务分析审阅意见 | 已被 PRD/spec/traceability 文档体系重构吸收 |
| [2026-05-13-project-centered-phase0-audit.md](./2026-05-13-project-centered-phase0-audit.md) | 项目主轴资产运营 Phase 0 审计 | 已被项目主轴 Phase 1-4 的 SSOT 和实现收口吸收 |
| [2026-06-02-architecture-review.md](./2026-06-02-architecture-review.md) | Contact、Capability/RBAC、路由注册、浅服务与 React Query 架构复核 | 7 个候选项已完成；后续问题另行立案 |
| [2026-06-10-mvp-subtraction-engineering-followup.md](./2026-06-10-mvp-subtraction-engineering-followup.md) | MVP 减法工程 A-K | 全部落地，保留历史证据 |
| [2026-06-12-project-deep-analysis.md](./2026-06-12-project-deep-analysis.md) | 项目全景与需求状态快照 | 包含旧合同目录、旧 ADR 数量等时点信息，已被后续 SSOT 与实现取代 |
| [2026-06-15-prd-grill-code-followup.md](./2026-06-15-prd-grill-code-followup.md) | 通知数据范围、陈旧台账风险、授权边界、分析口径与逾期状态收口 | F1/F2/F3/F4/D1/D2 已实施，2026-06-22 全量门禁通过 |
| [2026-06-16-prd-grill-code-followup.md](./2026-06-16-prd-grill-code-followup.md) | 运营方派生、台账固化归属、合同组一致性与审批孤儿删除 | C1~C7、D-A/D-B 已实施，2026-06-22 全量门禁通过 |
| [2026-06-19-prd-grill-code-followup.md](./2026-06-19-prd-grill-code-followup.md) | payment_status 派生、审计枚举、主体名称快照与 rejected 状态 | K1-K6 已落地，实施详单已归档 |
| [2026-06-20-prd-document-quality-analysis.md](./2026-06-20-prd-document-quality-analysis.md) | PRD 详略、读者与成功观测分析 | P1/P6/P7 已收口、P2 已解决，P3/P4/P5 判定为低价值非阻塞 |
| [2026-06-20-rent-contract-dead-dir-cleanup.md](./2026-06-20-rent-contract-dead-dir-cleanup.md) | 旧租赁合同域空目录清理 | 空目录已删除且验证通过，新实现已由 contracts 域承接 |
