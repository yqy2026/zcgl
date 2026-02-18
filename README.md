# 土地物业资产管理系统 - 文档中心

## 📋 Purpose
本文档中心作为土地物业管理系统的**单一可信来源（SSOT）**，确保团队所有成员、合作伙伴和AI助手都能基于一致、准确的信息进行协作和开发。

## 🎯 Scope
本文档中心涵盖：
- **开发指南**：环境搭建、工作流程、代码规范
- **架构决策**：技术选型、设计模式、接口约定
- **业务功能**：PRD文档、技术规格、验收标准
- **系统集成**：API文档、第三方依赖、部署运维
- **质量保障**：测试策略、性能基准、事故复盘

## ✅ Status
**当前状态**: Active (2026-01-15 更新)
**文档版本**: v1.4.0
**维护周期**: 每次功能发布后同步更新

---

## 🚀 快速开始

### 新成员入门
1. **[环境配置指南](docs/guides/environment-setup.md)** - 环境变量详细配置
2. **[数据库指南](docs/guides/database.md)** - 数据库初始化和迁移
3. **[快速开始指南](docs/guides/getting-started.md)** - 环境搭建和启动
4. **[开发工作流程](docs/guides/development-workflow.md)** - Git流程和代码规范

### 核心文档
- **[API 总览](docs/integrations/api-overview.md)** - API架构和规范
- **[认证 API](docs/integrations/auth-api.md)** - 登录、注册、权限管理

## 🔐 密钥泄露处置（必须执行）
- 任何 `SECRET_KEY`、`API_KEY`、`SESSION_SECRET`、数据库密码等凭证，只要曾出现在 Git 历史（即使后续删除或已轮换），一律按“已泄露”处理。
- 发现后必须立即轮换受影响凭证，并强制旧会话/旧令牌失效。
- 处置流程见：[部署指南 - 凭证泄露应急处置](docs/guides/deployment.md#凭证泄露应急处置)。

---

## 📚 文档导航

### 🚀 快速开始
| 文档 | 描述 | 状态 |
|------|------|------|
| [getting-started.md](docs/guides/getting-started.md) | 环境搭建和启动指南 | ✅ 已规划 |
| [development-workflow.md](docs/guides/development-workflow.md) | 开发流程和代码规范 | ✅ **已完成** |
| [environment-setup.md](docs/guides/environment-setup.md) | 环境变量详细配置 | ✅ **已完成** |
| [database.md](docs/guides/database.md) | 数据库初始化和迁移 | ✅ **已完成** |
| [frontend.md](docs/guides/frontend.md) | 前端开发完整指南 | ✅ **新增** |
| [backend.md](docs/guides/backend.md) | 后端开发完整指南 | ✅ **新增** |
| [deployment.md](docs/guides/deployment.md) | 部署和运维指南 | ✅ **新增** |

### 🏗️ 技术架构
| 文档 | 描述 | 状态 |
|------|------|------|
| [system-overview.md](docs/architecture/system-overview.md) | 系统架构和技术栈 | ✅ **已完成** |
| [ADR列表](docs/architecture/) | 架构决策记录 | ✅ 已创建（待补充） |

### 🔌 接口集成
| 文档 | 描述 | 状态 |
|------|------|------|
| [api-overview.md](docs/integrations/api-overview.md) | API总览和认证 | ✅ **新增** |
| [auth-api.md](docs/integrations/auth-api.md) | 认证接口文档 | ✅ **新增** |
| [assets-api.md](docs/integrations/assets-api.md) | 资产管理接口 | 📝 计划中 |
| [pdf-processing.md](docs/integrations/pdf-processing.md) | PDF处理服务 | 📝 计划中 |

### 📋 业务功能
| 文档 | 描述 | 状态 |
|------|------|------|
| [资产管理PRD](docs/features/prd-asset-management.md) | 资产管理功能需求 | 📝 计划中 |
| [租赁管理PRD](docs/features/prd-rental-management.md) | 租赁管理功能需求 | 📝 计划中 |
| [权限系统规格](docs/features/spec-user-permissions.md) | 用户权限设计 | 📝 计划中 |
| [数据模型规格](docs/features/spec-data-models.md) | 实体关系和字段定义 | 📝 计划中 |

### 🚨 事故复盘
| 文档 | 描述 | 状态 |
|------|------|------|
| [事故模板](docs/incidents/incident-template.md) | 标准事故复盘模板 | 📝 计划中 |
| [事故列表](docs/incidents/) | 历史事故记录 | 📝 计划中 |

---

## 🎯 系统概览

**项目名称**: 土地物业资产管理系统 (Real Estate Asset Management & Operations System)

**技术架构**: React 19 + TypeScript (Frontend) + FastAPI + Python 3.12 (Backend)

**核心功能**:
- 🏢 资产管理 (58字段资产信息管理)
- 📋 租赁合同管理 (PDF智能识别+数据提取)
- 👥 用户权限管理 (RBAC权限控制)
- 📊 数据分析报表 (可视化图表+统计分析)
- 🏗️ 组织架构管理 (层级结构管理)

**服务端口**:
- Frontend: 5173 (开发环境), 3000 (生产环境)
- Backend: 8002
- Nginx: 80/443
- Redis: 6379

---

## 🔍 快速定位

### 按角色查找
| 角色 | 推荐文档 |
|------|----------|
| **新成员** | [getting-started.md](docs/guides/getting-started.md) |
| **前端开发** | [environment-setup.md](docs/guides/environment-setup.md), [api-overview.md](docs/integrations/api-overview.md) |
| **后端开发** | [database.md](docs/guides/database.md), [auth-api.md](docs/integrations/auth-api.md) |
| **运维工程师** | [environment-setup.md](docs/guides/environment-setup.md), [database.md](docs/guides/database.md) |
| **产品经理** | [PRD文档](docs/features/) (计划中) |
| **QA工程师** | [development-workflow.md](docs/guides/development-workflow.md) |

### 按问题查找
| 问题类型 | 推荐文档 |
|----------|----------|
| **环境配置** | [environment-setup.md](docs/guides/environment-setup.md) |
| **数据库问题** | [database.md](docs/guides/database.md) |
| **API调用** | [api-overview.md](docs/integrations/api-overview.md), [auth-api.md](docs/integrations/auth-api.md) |
| **权限问题** | [auth-api.md](docs/integrations/auth-api.md#权限控制) |

---

## 📈 系统健康状态

| 指标 | 状态 | 说明 |
|------|------|------|
| **API版本** | ✅ `/api/v1/*` | 统一版本化架构 |
| **核心功能** | ✅ 95%+ | 主要业务模块正常运行 |
| **测试覆盖** | ✅ CI门槛 | 后端≥70%，前端≥50%（目标85%/75%） |
| **部署状态** | ✅ Ready | Docker Compose 就绪 |

---

## 📊 文档统计

### 已完成文档 (9个)
- ✅ [环境配置指南](docs/guides/environment-setup.md) - 完整的环境变量配置说明
- ✅ [数据库指南](docs/guides/database.md) - 数据库初始化、迁移、备份
- ✅ [前端开发指南](docs/guides/frontend.md) - React 开发完整指南
- ✅ [后端开发指南](docs/guides/backend.md) - FastAPI 开发完整指南
- ✅ [部署文档](docs/guides/deployment.md) - Docker 部署和运维指南
- ✅ [API总览](docs/integrations/api-overview.md) - API架构和认证规范
- ✅ [认证API](docs/integrations/auth-api.md) - 登录、注册、权限管理
- ✅ [文档中心](README.md) - 文档导航和快速定位
- ✅ [V2发布说明（归档）](docs/archive/releases/v2-release-notes-2026-01.md) - 合同v2功能更新说明

### 计划中文档 (10+个)
- 📝 快速开始指南
- 📝 开发工作流程
- 📝 系统架构文档
- 📝 资产管理API
- 📝 PDF处理文档
- 📝 业务功能PRD
- 📝 数据模型规格
- 📝 部署指南
- 📝 事故复盘模板

---

## 🔗 相关链接

### 代码仓库
- **主仓库**: `./`
- **前端代码**: `./frontend/`
- **后端代码**: `./backend/`
- **配置文件**: `./config/`
- **数据库**: `./database/`

### 外部依赖
- **Ant Design**: https://ant.design/
- **FastAPI**: https://fastapi.tiangolo.com/
- **React**: https://react.dev/
- **Docker**: https://docs.docker.com/
- **PostgreSQL**: https://www.postgresql.org/docs/

---

## 📝 文档贡献指南

### 文档更新流程
1. **代码变更**: 任何功能变更都必须同步更新相关文档
2. **证据要求**: 所有技术性陈述必须包含证据来源路径
3. **版本控制**: 使用 Changelog 记录每次变更
4. **审核流程**: 重要架构文档需要团队审核

### 文档规范
- 使用 Markdown 格式，支持中文和英文
- 所有路径使用相对路径，确保内部链接有效
- 代码示例必须可复制、可验证
- 使用【待确认】标注不确定的信息，并给出验证路径

---

## 📋 Changelog

### 2026-01-15 v1.4.0 - 2026 技术栈升级
- ✨ 升级：React 18 → React 19
- ✨ 升级：Ant Design 5 → Ant Design 6
- ✨ 升级：Vite 5 → Vite 6
- 🔄 迁移：npm → pnpm (前端包管理器)
- 📝 更新：所有文档命令同步更新为 pnpm

### 2026-01-08 v1.3.0 - 项目统计更新
- 📊 更新：后端 API 端点数量从 33 更新到 37
- 📊 更新：后端服务子目录从 7 更新到 19
- 📊 更新：前端组件数量统计 (114+ TSX 文件)
- 📝 更新：文档统计从 8 增加到 9 个文档
- ✨ 新增：[V2发布说明](docs/archive/releases/v2-release-notes-2026-01.md)

### 2025-12-23 v1.2.0 - 立即行动项完成
- ✨ 新增：[前端开发指南](docs/guides/frontend.md) - React 开发完整教程
- ✨ 新增：[后端开发指南](docs/guides/backend.md) - FastAPI 开发完整教程
- ✨ 新增：[部署文档](docs/guides/deployment.md) - Docker 部署和运维指南
- 📊 更新：文档统计从 4 个增加到 8 个文档
- 📈 提升：文档覆盖率从 40% 提升到 60%

### 2025-12-23 v1.1.0 - 文档体系完善
- ✨ 新增：环境配置详细指南 ([environment-setup.md](docs/guides/environment-setup.md))
- ✨ 新增：数据库配置和初始化指南 ([database.md](docs/guides/database.md))
- ✨ 新增：API总览和架构文档 ([api-overview.md](docs/integrations/api-overview.md))
- ✨ 新增：认证API完整文档 ([auth-api.md](docs/integrations/auth-api.md))
- 📁 创建：完整的文档目录结构 (6大目录)
- 📊 完善：文档导航和快速定位索引
- 🔗 完善：证据来源链接和外部依赖参考

### 2025-12-22 v1.0.0 - 初始版本
- ✨ 新增：文档中心完整框架和导航结构
- 📋 新增：6大核心目录架构 (guides, integrations, features, architecture, incidents, archive)
- 🎯 新增：按角色和问题的快速定位索引
- 📊 新增：系统健康状态和关键技术指标

---

## 🔍 Evidence Sources
- **项目信息**: `CLAUDE.md`, `openspec/project.md`
- **技术架构**: `frontend/package.json`, `backend/pyproject.toml`
- **服务配置**: `docker-compose.yml`
- **API结构**: `backend/src/api/v1/` 目录
- **前端组件**: `frontend/src/components/` 目录
- **开发脚本**: `frontend/package.json.scripts`, `backend/pyproject.toml`
