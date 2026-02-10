# 文档中心

## 🎯 Purpose
本目录作为项目文档入口，提供统一导航，并区分“当前基线文档”与“历史归档文档”。

## 🚀 快速入口
- [需求规格说明书（权威）](requirements-specification.md)
- [需求附录：模块与接口清单](features/requirements-appendix-modules.md)
- [需求评审清单（签字版）](requirements-review-checklist.md)
- [系统架构概览](architecture/system-overview.md)
- [产权证使用指南](guides/property-certificate.md)
- [快速开始](guides/getting-started.md)
- [环境配置](guides/environment-setup.md)
- [部署指南](guides/deployment.md)
- [组件导航](guides/components.md)
- [API 总览](integrations/api-overview.md)
- [数据库设计](database-design.md)
- [测试标准](guides/testing-standards.md)

## 🗂️ 历史归档
- [归档目录说明](archive/readme.md)
- [V2 发布说明（归档）](archive/releases/v2-release-notes-2026-01.md)

## 📚 文档结构
- `requirements-specification.md` 代码证据驱动的主需求规格（SSOT）
- `requirements-review-checklist.md` 需求评审与签字清单
- `guides/` 开发与运维指南
- `integrations/` API 与系统集成说明
- `features/` PRD 与规格文档
- `architecture/` 架构设计与概览
- `security/` 安全与加密
- `incidents/` 事故复盘与模板
- `tooling/` 工具元数据说明
- `archive/` 历史草稿、旧计划、调研资料归档

## 🧹 文档治理规则（简版）
- 需求与验收以 `requirements-specification.md` 为唯一基线
- 历史草稿必须标注 `Historical` 或迁入 `archive/`
- 目录变更需同步更新 `docs/index.md` 与 `CHANGELOG.md`
