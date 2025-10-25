# 土地物业资产管理系统

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue.svg)](https://typescriptlang.org)
[![SQLite](https://img.shields.io/badge/SQLite-3.x-lightgrey.svg)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

专业的土地物业资产管理系统，专为资产管理经理设计的个人工作助手工具。系统提供完整的资产档案管理、出租率统计、财务分析、智能PDF合同导入等功能。

## ✨ 主要特性

- 🏢 **完整资产管理** - 全面资产档案
- 📄 **智能PDF导入** - AI驱动的合同信息提取，自动识别
- 📊 **智能出租率统计** - 实时计算和多维度分析
- 💰 **财务数据管理** - 收益、支出、净利润跟踪
- 🔐 **高级权限管理** - RBAC权限系统，多租户支持
- 📈 **统计分析** - 多维度数据统计和可视化
- 🔧 **自动计算** - 出租率、净收益等自动计算
- 📋 **数据验证** - 完善的数据一致性验证
- 🚀 **高性能** - 优化的数据库查询和API响应
- 🎯 **OCR支持** - 图片和PDF的文字识别功能
- 🏢 **组织架构管理** - 支持多层级组织架构管理
- 📝 **审计日志** - 完整的操作审计和安全日志
- 💾 **数据备份** - 自动数据备份和恢复机制

## 🏗️ 项目结构

```
zcgl/
├── backend/                    # 后端服务 (FastAPI + Python)
│   ├── src/                   # 源代码
│   │   ├── api/              # API接口层 (25个模块)
│   │   ├── services/         # 业务服务层 (40+服务)
│   │   ├── models/           # 数据模型层
│   │   ├── crud/             # 数据访问层
│   │   ├── core/             # 核心模块
│   │   ├── decorators/       # 装饰器系统
│   │   └── constants/        # 常量定义
│   ├── tests/                # 测试套件
│   ├── scripts/              # 脚本工具
│   │   ├── migration/        # 数据迁移脚本
│   │   ├── quality/          # 质量监控脚本
│   │   ├── documentation/    # 文档生成脚本
│   │   ├── setup/           # 初始化脚本
│   │   └── maintenance/     # 维护脚本
│   ├── config/               # 配置文件
│   └── data/                 # 数据文件
├── frontend/                  # 前端应用 (React + TypeScript)
│   ├── src/                  # 源代码
│   │   ├── components/       # 组件库 (80+组件)
│   │   │   ├── Asset/       # 资产组件
│   │   │   ├── Layout/      # 布局组件
│   │   │   ├── Charts/      # 图表组件
│   │   │   ├── Router/      # 路由组件
│   │   │   └── System/      # 系统组件
│   │   ├── pages/           # 页面组件
│   │   ├── services/        # API服务
│   │   ├── hooks/           # 自定义钩子
│   │   ├── monitoring/      # 性能监控
│   │   └── utils/           # 工具函数
│   └── tests/               # 测试套件
├── docs/                     # 项目文档
│   ├── reports/             # 项目报告
│   │   ├── test-coverage/   # 测试覆盖率报告
│   │   ├── test-automation/ # 测试自动化报告
│   │   ├── project-status/  # 项目状态报告
│   │   └── backend/         # 后端报告
│   ├── architecture/        # 架构文档
│   ├── api/                 # API文档
│   ├── development/         # 开发指南
│   ├── deployment/          # 部署文档
│   └── user-guide/          # 用户指南
├── scripts/                  # 项目脚本
│   ├── startup/             # 启动脚本
│   ├── unified_test_runner.py # 统一测试运行器
│   └── ...                  # 其他工具脚本
├── tools/                    # 开发工具
│   ├── development/         # 开发工具
│   ├── deployment/          # 部署工具
│   └── analysis/            # 分析工具
├── config/                   # 全局配置
│   ├── environments/        # 环境配置
│   ├── templates/           # 配置模板
│   └── root/                # 根目录配置
├── nginx/                    # 部署配置
└── database/                 # 数据库脚本
```

### 核心技术栈
- **后端**: FastAPI + Python 3.12 + SQLAlchemy + UV + Pydantic
- **前端**: React 18 + TypeScript + Vite + Ant Design + Zustand
- **数据库**: SQLite (支持扩展到PostgreSQL/MySQL)
- **AI处理**: pdfplumber + OCR + NLP (spaCy + jieba) + PaddleOCR
- **监控**: 路由性能监控 + 健康检查 + 实时指标
- **部署**: Docker + Nginx + 自动化部署

### 环境要求
- **Python**: 3.12+ (推荐使用 uv 包管理器)
- **Node.js**: 18.0+
- **数据库**: SQLite 3.x (开发环境，支持扩展到PostgreSQL生产环境)
- **缓存**: Redis (生产环境推荐，开发环境使用内存缓存)
- **内存**: 4GB+ (推荐8GB+用于PDF处理)
- **操作系统**: Windows 10+, macOS 10.15+, Linux

### 环境要求

### 安装启动

## 🚀 快速开始

### 方式一：统一测试运行器
```bash
# 运行所有测试（推荐）
python scripts/unified_test_runner.py

# 仅运行后端测试
python scripts/unified_test_runner.py --backend-only

# 仅运行前端测试
python scripts/unified_test_runner.py --frontend-only

# 不生成覆盖率报告
python scripts/unified_test_runner.py --no-coverage
```

### 方式二：手动启动
```bash
# 后端服务 (FastAPI + SQLAlchemy)
cd backend
uv sync                              # 安装依赖（推荐使用uv）
uv run python run_dev.py             # 开发模式 (端口 8002)

# 前端服务 (React + TypeScript + Vite)
cd frontend
npm install                          # 安装依赖
npm run dev                          # 开发服务器 (端口 5173)

# 测试数据库连接
uv run python -c "from src.database import engine; print('DB OK')"

# 访问系统
# 前端应用: http://localhost:5173
# API文档: http://localhost:8002/docs
# 健康检查: http://localhost:8002/health
```

#### 方式二：Docker启动
```bash
# 使用Docker Compose
docker-compose up -d

# 查看服务状态
docker-compose ps
```

## 📊 系统概览

### 数据规模
- **数据库字段**: 58个（完整资产信息）
- **测试数据**: 1,269条资产记录
- **API接口**: 40+个RESTful接口
- **统计维度**: 8个分析维度
- **PDF处理**: 支持智能合同信息提取
- **权限模型**: RBAC权限系统，支持动态权限分配

### 核心功能
- **资产管理**: 增删改查、批量操作、历史记录、资产分类
- **智能PDF导入**: AI驱动的58字段自动识别和提取
- **出租率统计**: 整体出租率、分类统计、趋势分析
- **财务分析**: 收益统计、成本分析、利润计算
- **权限管理**: 基于角色的访问控制(RBAC)、多租户支持
- **组织架构管理**: 多层级组织架构、部门管理、权限继承
- **数据导入导出**: Excel导入导出、PDF导入、模板管理
- **合同管理**: 租赁合同全生命周期管理
- **项目管理**: 项目维度的资产统计和管理
- **审计日志**: 完整的操作审计和数据变更追踪
- **数据备份**: 定期数据库备份、自动备份脚本、数据恢复流程

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端 (React)   │    │  后端 (FastAPI)  │    │   数据服务层     │    │ 数据库 (SQLite) │
│   Port: 5173    │◄──►│   Port: 8002    │◄──►│ PDF/OCR处理     │◄──►│  land_property  │
│   TypeScript    │    │   Python 3.12   │    │ 权限管理        │    │      .db        │
│   Vite构建      │    │   uv包管理      │    │ 审计日志        │    │   (支持PostgreSQL)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 技术栈
- **后端**: Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + UV包管理器
- **数据库**: SQLite（开发环境，支持扩展到PostgreSQL生产环境）
- **缓存**: Redis（生产环境，开发环境使用内存缓存）
- **前端**: React 18 + TypeScript + Ant Design 5 + Vite
- **部署**: Docker + Nginx + Gunicorn
- **AI增强**: PaddleOCR（OCR识别）、spaCy（NLP文本处理，可选）

## 📈 数据模型

### 核心字段分组
- **基本信息** (8字段): 权属方、权属类别、项目名称、物业名称、物业地址等
- **面积信息** (11字段): 土地面积、实际房产面积、可出租面积、已出租面积等
- **租户信息** (3字段): 租户名称、租户类型、租户联系方式
- **合同信息** (8字段): 租赁合同编号、合同期限、租金等
- **财务信息** (3字段): 年收益、年支出、净收益
- **管理信息** (6字段): 管理责任人、经营模式、项目等
- **系统信息** (6字段): 版本、状态、审核等

### 自动计算字段
- **出租率** = 已租面积 ÷ 可租面积 × 100%
- **未租面积** = 可租面积 - 已租面积
- **净收益** = 年收益 - 年支出

## 🔌 API接口

### 资产管理 (`/api/v1/assets`)
- `GET /api/v1/assets` - 获取资产列表（支持分页、搜索、筛选）
- `POST /api/v1/assets` - 创建新资产
- `GET /api/v1/assets/{id}` - 获取资产详情
- `PUT /api/v1/assets/{id}` - 更新资产信息
- `DELETE /api/v1/assets/{id}` - 删除资产
- `GET /api/v1/assets/{id}/history` - 获取资产变更历史
- `POST /api/v1/assets/batch` - 批量操作资产
- `GET /api/v1/assets/export` - 导出资产数据
- `POST /api/v1/assets/import` - 导入资产数据

### 智能PDF导入 (`/api/v1/pdf`)
- `POST /api/v1/pdf/process` - 处理PDF合同文件
- `POST /api/v1/pdf/extract-contract` - 提取合同信息
- `POST /api/v1/pdf/validate-contract` - 验证合同数据

### 统计分析 (`/api/v1/statistics`)
- `GET /api/v1/statistics/occupancy-rate/overall` - 整体出租率
- `GET /api/v1/statistics/occupancy-rate/by-category` - 分类出租率
- `GET /api/v1/statistics/area-summary` - 面积汇总
- `GET /api/v1/statistics/financial-summary` - 财务汇总

### 权限管理 (`/api/v1/auth` 和 `/api/v1/rbac`)
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/logout` - 用户登出
- `GET /api/v1/users` - 获取用户列表
- `POST /api/v1/users` - 创建用户
- `PUT /api/v1/users/{id}` - 更新用户
- `DELETE /api/v1/users/{id}` - 删除用户
- `GET /api/v1/roles` - 获取角色列表
- `POST /api/v1/roles` - 创建角色
- `PUT /api/v1/roles/{id}` - 更新角色
- `DELETE /api/v1/roles/{id}` - 删除角色
- `GET /api/v1/permissions` - 获取权限列表

### 组织架构 (`/api/v1/organizations`)
- `GET /api/v1/organizations` - 获取组织架构
- `POST /api/v1/organizations` - 创建组织
- `PUT /api/v1/organizations/{id}` - 更新组织
- `DELETE /api/v1/organizations/{id}` - 删除组织

### 数据导入导出 (`/api/v1/excel`)
- `POST /api/v1/excel/import` - Excel导入
- `GET /api/v1/excel/export` - Excel导出
- `GET /api/v1/excel/template` - 下载模板

详细API文档请访问: http://localhost:8002/docs

## 🛠️ 开发工具

### 后端开发命令
```bash
cd backend

# UV包管理器 (推荐)
uv sync                              # 安装依赖
uv run python run_dev.py             # 开发模式 (端口 8002)
uv run python -m pytest tests/ -v    # 运行测试
uv run mypy src/                     # 类型检查
uv run ruff check src/               # 代码检查

# 数据库测试
uv run python -c "from src.database import engine; print('DB OK')"
```

### 前端开发命令
```bash
cd frontend
npm install                          # 安装依赖
npm run dev                          # 开发服务器 (端口 5173)
npm run build                        # 生产构建
npm test                             # 运行测试
npm run lint                         # ESLint检查
```

### 系统管理脚本
```bash
# 健康监控
python scripts/health_monitor.py

# 环境设置
python scripts/environment_setup.py

# 性能测试
bash scripts/performance-test.sh

# 系统检查
python scripts/system_check.py
```

## 📚 文档资源

### 开发文档
- [开发指南](docs/guides/CLAUDE.md) - 开发指导文档
- [后端README](backend/README.md) - 后端开发文档
- [前端README](frontend/README.md) - 前端开发文档
- [文档中心](docs/README.md) - 完整文档导航

### 技术文档
- **API文档**: http://localhost:8002/docs - 交互式API文档
- **ReDoc**: http://localhost:8002/redoc - API参考文档

### 项目报告
- [API报告](docs/reports/api/) - API相关报告
- [数据模型报告](docs/reports/data-model/) - 数据模型相关报告
- [PDF导入报告](docs/reports/pdf-import/) - PDF导入功能报告
- [合同报告](docs/reports/contracts/) - 合同相关报告

## 🚀 部署方案

### Docker部署
```bash
# 使用Docker Compose
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 生产环境部署
- 使用Docker容器化部署
- Nginx反向代理和负载均衡
- Gunicorn作为WSGI服务器
- PostgreSQL作为生产数据库
- Redis作为缓存服务器

## 🔐 安全特性

- **JWT Token认证**: 用户认证和授权
- **数据验证**: 完善的输入验证和数据约束
- **访问控制**: 基于角色的权限管理（可扩展）
- **数据备份**: 自动备份和恢复机制
- **审计日志**: 完整的操作历史记录
- **密码安全**: 密码加密存储、安全策略
- **防护机制**: SQL注入防护、XSS防护、CSRF防护

## 📈 性能指标

- **API响应时间**: < 1秒（1000+记录查询）
- **数据库查询**: 优化索引，高效查询
- **并发支持**: 支持多用户同时访问
- **内存使用**: 合理的资源占用
- **扩展性**: 支持大规模数据和高并发

## 🤝 贡献指南

### 开发环境设置
```bash
# 克隆项目
git clone <repository-url>
cd zcgl

# 后端环境设置
cd backend
uv sync

# 前端环境设置
cd ../frontend
npm install
```

### 代码规范
- 后端遵循PEP 8代码规范和类型提示
- 前端使用ESLint和Prettier进行代码检查和格式化
- 实现单元测试和集成测试

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 支持与反馈

- **问题反馈**: 请提交 GitHub Issues
- **功能建议**: 欢迎提交 Pull Requests
- **文档改进**: 帮助完善项目文档

## 🎯 路线图

### v2.1 (计划中)
- [ ] 移动端适配 (响应式优化)
- [ ] 数据可视化仪表板
- [ ] 高级报表导出功能
- [ ] 工作流引擎
- [ ] 消息通知系统
- [ ] API限流和缓存优化

## 🏆 项目状态

- **开发状态**: ✅ 生产就绪 (持续迭代中)
- **核心功能**: ✅ 100%完成
- **PDF导入**: ✅ 智能提取功能已完成
- **权限系统**: ✅ RBAC完整实现
- **前端界面**: ✅ React现代化界面
- **测试覆盖**: ✅ 核心功能测试完成
- **文档完整性**: ✅ 完整开发文档体系
- **部署就绪**: ✅ 支持多种部署方式

---

**版本**: v2.1
**更新时间**: 2025年10月17日
**维护状态**: 🚀 活跃开发中
**技术栈**: Python 3.12 + FastAPI + React 18 + TypeScript

🎉 **感谢使用土地物业资产管理系统！**