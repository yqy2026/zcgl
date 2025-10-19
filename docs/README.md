# 土地物业资产管理系统 - 文档中心

## 📚 文档导航

### 👤 用户文档
- **[安装指南](user/installation.md)** - 系统安装和环境配置
- **[使用说明](user/usage.md)** - 功能使用和操作指南
- **[故障排除](user/troubleshooting.md)** - 常见问题和解决方案

### 👨‍💻 开发文档
- **[开发环境搭建](dev/setup.md)** - 开发环境配置说明
- **[架构设计](dev/architecture.md)** - 系统架构和技术选型
- **[贡献指南](dev/contributing.md)** - 代码规范和贡献流程
- **[API文档](dev/api.md)** - 接口文档和示例

### 🚀 部署文档
- **[Docker部署](deployment/docker.md)** - 容器化部署方案
- **[生产环境](deployment/production.md)** - 生产环境配置
- **[监控配置](deployment/monitoring.md)** - 系统监控和告警

### 📊 技术报告
- **[PDF导入报告](reports/pdf-import/)** - PDF智能导入功能测试报告
- **[性能测试报告](reports/performance/)** - 系统性能测试和分析
- **[架构优化报告](reports/architecture/)** - 项目架构优化和重构方案

### 📋 指南文档
- **[API废弃声明](API_DEPRECATION_NOTICE.md)** - 废弃API迁移指南
- **[API优化指南](API_OPTIMIZATION_GUIDE.md)** - API性能优化指导
- **[性能优化指南](PERFORMANCE_OPTIMIZATION_GUIDE.md)** - 系统性能优化策略
- **[文件名处理指南](FILENAME_HANDLING_GUIDE.md)** - 文件处理最佳实践
- **[PaddleOCR集成分析](PaddleOCR_Integration_Analysis.md)** - OCR功能技术分析

## 🎯 快速开始

### 新用户
1. 阅读 [安装指南](user/installation.md) 安装系统
2. 查看 [使用说明](user/usage.md) 了解基本功能
3. 遇到问题时查阅 [故障排除](user/troubleshooting.md)

### 开发者
1. 参考 [开发环境搭建](dev/setup.md) 配置开发环境
2. 阅读 [架构设计](dev/architecture.md) 了解系统结构
3. 查看 [API文档](dev/api.md) 进行接口开发
4. 遵循 [贡献指南](dev/contributing.md) 提交代码

### 运维人员
1. 使用 [Docker部署](deployment/docker.md) 快速部署
2. 配置 [生产环境](deployment/production.md) 正式上线
3. 设置 [监控配置](deployment/monitoring.md) 保障系统稳定

## 🏗️ 系统架构

### 技术栈
- **后端**: Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + UV包管理器
- **数据库**: SQLite（开发环境，支持扩展到PostgreSQL生产环境）
- **缓存**: Redis（生产环境，开发环境使用内存缓存）
- **前端**: React 18 + TypeScript + Ant Design 5 + Vite
- **部署**: Docker + Nginx + Gunicorn
- **AI增强**: PaddleOCR（OCR识别）、spaCy（NLP文本处理，可选）

### 核心功能模块
- **资产管理**: 58个字段的全面资产档案管理
- **智能PDF导入**: AI驱动的合同信息提取
- **统计分析**: 多维度数据统计和可视化
- **权限管理**: 基于RBAC的角色权限控制
- **组织架构**: 支持多层级组织架构管理
- **数据备份**: 自动数据备份和恢复机制

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

## 📈 数据模型

### 核心字段分组
- **基本信息** (8字段): 权属方、权属类别、项目名称、物业名称、物业地址等
- **面积信息** (11字段): 土地面积、实际房产面积、可出租面积、已出租面积等
- **租户信息** (3字段): 租户名称、租户类型、租户联系方式
- **合同信息** (8字段): 租赁合同编号、合同期限、租金等
- **财务信息** (3字段): 年收益、年支出、净收益
- **管理信息** (6字段): 管理责任人、经营模式、项目等
- **系统信息** (6字段): 版本、状态、审核等

## 📝 文档更新日志

### 2025-10-17
- 更新文档中心内容，与项目最新架构保持一致
- 添加API接口清单
- 完善系统架构说明

### 2025-10-14
- 创建文档中心导航页面
- 整理技术报告分类
- 优化文档目录结构

### 2025-10-09
- 添加PDF导入功能文档
- 完善API接口说明
- 更新部署指南

## 🔗 相关链接

- **项目主页**: [README.md](../README.md)
- **开发指南**: [CLAUDE.md](../CLAUDE.md)
- **后端文档**: [backend/README.md](../backend/README.md)
- **前端文档**: [frontend/README.md](../frontend/README.md)
- **GitHub仓库**: [项目地址]
- **问题反馈**: [Issues页面]

## 💡 文档贡献

欢迎参与文档改进：
- 发现错误或不清楚的地方请提交Issue
- 有改进建议请提交Pull Request
- 新功能开发请同步更新相关文档

---

*最后更新: 2025-10-17*