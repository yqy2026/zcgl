# 变更日志 (Changelog)

## [Unreleased] - 2026-01-18

### ⚙️ 配置管理优化 (Configuration Management Optimization)

#### Changed / 变更

- **配置文件标准化** (Configuration File Standardization)
  - 整合 `config/environments/backend.env` 到 `backend/.env`
  - 创建标准 `frontend/.env` 文件
  - 统一使用项目根目录的 `.env` 文件，符合工具链最佳实践

#### Removed / 删除

- **完全删除 config/ 目录** (Complete Removal of config/ Directory)
  - 删除 `config/environments/` - 未被代码引用
  - 删除 `config/shared/` - YAML文件无加载机制
  - 删除 `config/templates/` - 已有 `.env.example` 文件作为模板
  - 删除 `config/root/` - API检查脚本已在 `frontend/scripts/` 和 `backend/scripts/`

#### Added / 新增

- `backend/.env` - 完整的后端环境配置（合并所有必要配置）
- `frontend/.env` - 前端Vite环境变量
- 更新 `GEMINI.md` 环境配置文档，包含详细设置指南

### 🎯 代码质量重构 (Code Quality Refactoring)

#### Removed / 删除

- **移除AI风格命名** (Removed AI-Style Naming)
  - 删除 `backend/src/api/v1/CLAUDE.md` - 旧的AI助手文档
  - 移除所有 "Enhanced" 前缀的类名和组件名
  - 移除 "Unified" 前缀的类名

- **简化认证服务层** (Simplified Authentication Services)
  - 合并 `AuthService` 和 `AuthenticationService`
  - 移除冗余的服务包装层

#### Modified / 修改

**后端 (Backend) - 37 files**
- `backend/conftest.py` - 测试配置更新
- `backend/src/api/v1/auth_modules/authentication.py` - 认证端点重构
- `backend/src/api/v1/auth_modules/password.py` - 密码管理端点更新
- `backend/src/api/v1/auth_modules/sessions.py` - 会话管理端点更新
- `backend/src/api/v1/auth_modules/user_management.py` - 用户管理端点重构
- 多个测试文件更新以反映新的服务结构

**前端 (Frontend) - 42 files**
- `frontend/src/api/client.ts` - API客户端重命名
- `frontend/src/utils/responseExtractor.ts` - 响应提取器重命名
- `frontend/src/types/index.ts` - 类型定义更新
- 多个组件和页面更新以使用标准命名

#### Added / 新增

- `frontend/src/pages/Rental/PDFImportPage.tsx` - PDF导入功能页面
- `frontend/src/types/pdfImport.ts` - PDF导入类型定义
- `backend/src/core/database.py` - 数据库核心模块

### 📊 统计 (Statistics)

- **文件修改**: 79 files changed
- **代码增加**: +892 insertions
- **代码删除**: -6,415 deletions
- **净删除**: -5,523 lines (代码更简洁)

### 🎨 改进重点 (Key Improvements)

1. **命名规范化** - 移除AI生成的命名模式，采用业务领域术语
2. **架构简化** - 减少不必要的抽象层和服务包装
3. **代码精简** - 删除了超过6000行冗余代码
4. **可维护性提升** - 更清晰的代码结构和命名

### 🔗 相关文档 (Related Documentation)

- [架构重构分析](docs/architecture-refactoring.md)
- [测试标准](docs/TESTING_STANDARDS.md)

---

## [1.0.0] - 2026-01-15

### 初始版本 (Initial Release)

- ✅ 用户认证与权限管理 (RBAC)
- ✅ 资产基础信息管理
- ✅ 租赁合同基础管理
- ✅ 租金台账基础功能
- ✅ 权属方/项目列表管理
- ✅ 数据字典管理
