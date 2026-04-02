# 方案设计索引

本目录仅存放**活跃方案**（进行中 / 搁置待定）。已完结方案统一归档至 `docs/archive/backend-plans/`。

> **规则**：方案进入 ✅ 状态后移入 `archive/backend-plans/`，本索引只保留 🔄 和 ⏸ 条目。

## 活跃方案

| 文件 | 主题 | 状态 | 备注 |
|------|------|------|------|
| [2026-02-11-approval-flowable-b-plan.md](2026-02-11-approval-flowable-b-plan.md) | Flowable 编排内核 B 方案 | ⏸ 搁置 | 审批流方向待定，暂不实施 |

## 已归档方案

见 [`docs/archive/backend-plans/`](../archive/backend-plans/)

| 文件 | 主题 | 最终状态 |
|------|------|----------|
| 2026-02-11-langextract-rollout-plan.md | langextract 灰度接入 PDF 链路 | ✅ 已采纳 |
| 2026-02-15-phone-first-login-and-username-retention.md | 手机号优先登录与用户名保留 | ✅ 已实现 |
| 2026-02-16-party-role-architecture-design.md | Party-Role 组织架构设计 | ✅ 已实现 |
| 2026-02-18-phase1-implementation-plan.md | Phase 1：DDL + ORM + ABAC 骨架 | ✅ 已完成 |
| 2026-02-19-phase2-implementation-plan.md | Phase 2：业务域迁移 + 数据隔离 | ✅ 已完成 |
| 2026-03-05-req-prj-002-project-active-assets.md | REQ-PRJ-002：项目详情按有效 project_assets 汇总 | ✅ 已完成 |
| 2026-03-05-project-field-enrichment-m1.md | Project 表字段收口（M1） | ✅ 已完成 |
| 2026-03-05-req-rnt-001-contract-group.md | REQ-RNT-001：合同组作为主业务对象（五层合同模型重构） | ✅ 已完成 |
| 2026-03-05-req-ast-004-asset-lease-summary.md | REQ-AST-004：资产详情租赁情况展示（按合同类型） | ✅ 已完成 |
| 2026-03-02-party-scope-isolation-fix-plan.md | 组织数据权限隔离修复（全量排查） | ✅ 已完成 |
| 2026-03-21-ci-baseline-restoration-plan.md | CI 基线恢复与格式治理 | ✅ 已完成 |
| 2026-03-22-perspective-simplification-v2-follow-up.md | 前端视角简化 v2 后续收口 | ✅ 已完成 |
| 2026-03-24-req-ana-001-export-closure-design.md | REQ-ANA-001 导出链路收口 | ✅ 已完成 |
| 2026-03-24-req-ana-001-export-closure-plan.md | REQ-ANA-001 导出链路收口实施计划 | ✅ 已完成 |
| 2026-03-24-req-rnt-006-ledger-m3-plan.md | REQ-RNT-006 M3：台账运营增强（导出/补偿任务/服务费台账） | ✅ 已完成 |
| 2026-03-25-req-auth-002-perspective-context-design.md | REQ-AUTH-002 视角上下文强制注入 | ✅ 已完成 |
| 2026-03-25-req-auth-002-perspective-context-plan.md | REQ-AUTH-002 视角上下文强制注入实施计划 | ✅ 已完成 |
| 2026-03-29-req-rnt-004-005-joint-review-and-correction-plan.md | REQ-RNT-004/005：关键合同联审与纠错链路 | ✅ 已完成 |
| 2026-04-01-req-sch-001-003-global-search-plan.md | REQ-SCH-001/002/003 全局搜索 | ✅ 已完成 |
| 2026-03-11-req-ast-003-asset-review.md | REQ-AST-003：资产主数据审核与反审核 | ✅ 已完成 |
| 2026-03-12-req-pty-001-002-party-remediation.md | REQ-PTY-001/002：主体主档管理 Gap 修复 | ✅ 已完成 |
| 2026-02-20-phase3-implementation-plan.md | Phase 3：前端全量迁移 + 策略包 UI | ✅ 已完成 |
| 2026-03-01-phase4-implementation-plan.md | Phase 4：发布窗口执行 + 旧字段物理删除 | ✅ 已完成 |
| 2026-03-06-m2-contract-lifecycle-and-ledger.md | M2：合同组生命周期、审核闭环与台账自动化 | ✅ 已实现 |
| 2026-03-11-m2-ledger-aggregate-and-recalc.md | M2 台账跨合同聚合查询 + 变更重算 | ✅ 已实现 |

## 状态说明

| 图标 | 含义 |
|------|------|
| 📋 待评审 | 方案已编写，等待评审确认后开始实施 |
| 🔄 进行中 | 当前正在实施 |
| ⏸ 搁置 | 暂不实施，保留供参考 |
| ✅ 已完成 / 已实现 | 方案已落地，已移入 archive/ |
| ❌ 已废弃 | 被更好的方案替代，已移入 archive/ |
