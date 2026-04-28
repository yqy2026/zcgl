# 文档中心

> 本目录是项目的唯一文档根目录（含原 `backend/docs/` 和 `frontend/docs/` 迁移内容）。

## 🎯 Purpose
本目录作为项目文档入口，提供统一导航。

## 🚀 快速入口

### 需求
- [**产品需求文档 PRD**](prd.md)
- [领域模型契约](specs/domain-model.md)
- [API 契约](specs/api-contract.md)
- [需求追踪矩阵](traceability/requirements-trace.md)
- [需求访谈与澄清记录](interviews/README.md)
- [旧需求规格兼容入口](requirements-specification.md)

### 架构与数据库
- [系统架构概览](architecture/system-overview.md)
- [数据库设计基线](architecture/database-design.md)
- [ADR-0001: Party-Role 组织架构](architecture/ADR-0001-party-role-architecture.md)

### 规格与追踪
- [规格文档索引](specs/README.md)
- [需求追踪索引](traceability/README.md)

### 开发指南
- [快速开始](guides/getting-started.md)
- [Codex 任务模板](guides/codex-task-template.md)
- [环境配置](guides/environment-setup.md)
- [后端开发](guides/backend.md)
- [前端开发](guides/frontend.md)
- [数据库指南](guides/database.md)
- [部署指南](guides/deployment.md)
- [部署运维手册](guides/deployment-operations.md)
- [代码质量规范](guides/code-quality.md)
- [数据库性能与测试覆盖](guides/database-performance.md)
- [开发工作流](guides/development-workflow.md)
- [命名规范](guides/naming-conventions.md)
- [TypeScript 规范](guides/typescript-conventions.md)
- [测试标准](guides/testing-standards.md)
- [组件导航](guides/components.md)

### API 与集成
- [API 总览](integrations/api-overview.md)
- [资产 API](integrations/assets-api.md)
- [认证 API](integrations/auth-api.md)
- [PDF 处理](integrations/pdf-processing.md)
- [新增 API 端点](integrations/new-api-endpoints.md)
- [监控 API](integrations/monitoring.md)
- [增强数据库管理器](integrations/enhanced-database-manager.md)

### 安全
- [数据加密](security/encryption.md)
- [后端安全指南](security/backend-security.md)
- [能力守卫环境配置](security/capability-guard-env.md)

### 前端参考文档
- [前端文档索引](../frontend/docs/README.md)（设计系统、可访问性、动画、性能优化）

### 方案设计
- [**方案状态索引**](plans/README.md)

## 🗂️ 历史归档
- [归档目录说明](archive/readme.md)
- `archive/evidence/` — 阶段性门禁证据、发布证据和本地验证快照
- `archive/guides/` — 历史指南和长版设计快照
- `archive/backend-plans/` — 后端已完结技术方案
- `archive/requirements-decisions/` — 需求访谈、评审、As-Built、迁移过程归档
- `archive/reviews/` — 方案或代码审阅记录归档

## 📚 文档结构

> 每个子目录均有 README，进入目录后可直接看到内容导航。

- `prd.md` — 产品需求文档（最终产品目标态）
- `specs/` — 领域模型与 API 契约
- `traceability/` — 需求到实现和测试证据的追踪
- `requirements-specification.md` — 旧需求规格兼容跳转页
- `features/` — 旧需求附录兼容跳转页
- `architecture/` — 架构设计（含 ADR）
- `guides/` — 开发指南（环境、后端、前端、代码质量、部署运维、测试）
- `integrations/` — API 接口规范与系统组件文档
- `security/` — 安全相关（加密、后端安全、能力守卫）
- `plans/` — 活跃方案（进行中 + 搁置）
- `interviews/` — 需求访谈、澄清与历史决策记录
- `incidents/` — 事故复盘（Post-Mortem）
- `issues/` — 项目技术债务排查记录
- `archive/` — 历史归档（不再维护，含 evidence / guides / backend-plans / requirements-decisions / reviews）

## 🧹 文档治理规则
- 产品目标态变更修改 `prd.md`
- 字段、状态、统计口径变更修改 `specs/domain-model.md`
- API 与权限契约变更修改 `specs/api-contract.md`
- 实现证据变更修改 `traceability/requirements-trace.md`
- 历史访谈、评审、As-Built、迁移过程追加到 `archive/requirements-decisions/`
- 同步更新 `CHANGELOG.md`
- 新通用文档统一放 `docs/`，不在 `backend/docs/` 中新建
- `frontend/docs/` 保留前端内部技术参考（设计系统、动画规范等与实现强绑定的内容）
- AI 任务执行报告（summary/report 类）直接进 `archive/`，不放 `guides/`
- 已完结方案（plans/ 中 ✅ 状态）须移入 `archive/backend-plans/`
- 历史版本通过 Git 追溯
- 单个文档超过 800 行需考虑拆分
