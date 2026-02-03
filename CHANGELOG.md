# 变更日志 (Changelog)

## [Unreleased] - 2026-02-03

### 🛡️ 稳定性与架构修复 (Stability & Architecture Fixes)

#### Fixed / 修复

- **PDF V1上传内存风险** (PDF V1 Upload Memory Risk)
  - V1 兼容上传改为流式写入并严格限制大小，避免一次性读入内存
  - 上传临时文件处理完成后自动清理
- **PDF 导入临时文件清理** (PDF Import Temp File Cleanup)
  - 处理结果/失败后自动清理 `temp_uploads` 与系统临时目录下的源文件
- **PDF 批量上传内存风险** (PDF Batch Upload Memory Risk)
  - 批量上传改为流式写入 `temp_uploads`，避免一次性读取到内存
  - 超限/空文件即时清理，失败时回收临时文件
- **Excel 导出临时文件清理** (Excel Export Temp File Cleanup)
  - 异步导出文件统一落盘到 `temp_uploads/excel_exports`
  - 任务删除或清理过期任务时回收导出文件

#### Changed / 变更

- **产权证 API 层依赖规范化** (Property Certificate API Layer Normalization)
  - API 端点改为通过 `PropertyCertificateService` 访问 CRUD

#### Added / 新增

- **缺失的 CRUD 类补齐** (Missing CRUD Classes Added)
  - 新增 `collection_crud`、`dynamic_permission_crud`、`prompt_template_crud`
- **白名单补齐** (Field Whitelist Coverage)
  - 为 `CollectionRecord`、`DynamicPermission`、`PromptTemplate` 增加字段白名单
  - 为 `Project`、`Organization`、`PropertyCertificate`、`PropertyOwner`、`RentTerm`、`RentLedger`、`UserRoleAssignment`、`ResourcePermission`、`PermissionAuditLog` 增加字段白名单
  - 为 `AsyncTask`、`ExcelTaskConfig` 增加字段白名单

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

### 🧹 文档清理 (Documentation Cleanup)

#### Removed / 删除

- 删除过期/未引用的阶段性报告与计划文档:
  - `docs/project-comprehensive-analysis-2026-02-02.md`
  - `docs/project-issues-report-2026-02-02.md`
  - `docs/test-coverage-improvement-phase1-report.md`
  - `docs/test-coverage-improvement-plan.md`
  - `docs/todo-debt-plan.md`
  - `docs/property-certificate-feature-plan.md`
  - `docs/property-certificate-implementation-summary.md`

### 🧩 文档补全 (Documentation Completion)

#### Added / 新增

- 新增缺失的文档与模板，补齐文档树结构:
  - `docs/index.md`
  - `docs/guides/getting-started.md`
  - `docs/guides/deployment.md`
  - `docs/integrations/api-overview.md`
  - `docs/integrations/auth-api.md`
  - `docs/integrations/assets-api.md`
  - `docs/integrations/pdf-processing.md`
  - `docs/features/prd-asset-management.md`
  - `docs/features/prd-rental-management.md`
  - `docs/features/spec-data-models.md`
  - `docs/features/spec-user-permissions.md`
  - `docs/incidents/incident-template.md`
  - `docs/testing/v2-test-cases.md`
  - `docs/v2_upgrade_plan.md`
  - `docs/architecture-refactoring.md`

#### Fixed / 修复

- 修复文档锚点与引用错误，确保内部链接有效

### 🧾 文档与工具维护 (Docs & Tooling Maintenance)

#### Added / 新增

- `backend/docs/API_DOCUMENTATION_ANALYSIS.md` - API 文档分析报告占位与生成说明
- `backend/docs/COVERAGE_IMPROVEMENT_REPORT.md` - 覆盖率报告占位与生成指引
- `docs/tooling/assistant-metadata.md` - 根目录工具元数据说明

#### Changed / 变更

- 修复文档引用路径:
  - `backend/docs/enhanced_database_guide.md`
  - `frontend/docs/type-safety-fix-summary.md`
  - `scripts/README.md`
- `backend/debug_import.py` 迁移至 `backend/scripts/dev/debug_import.py` 并补充路径初始化
- `.gitignore` 允许 `backend/docs` 下的分析/报告占位文档被追踪

### 🗑️ 文档站点移除 (Docs Site Removal)

#### Removed / 删除

- 移除 MkDocs 站点构建相关配置与依赖:
  - `backend/mkdocs.yml`
  - `docs/includes/mkdocs.md`
  - `backend/pyproject.toml` 中的 docs 可选依赖
  - `backend/uv.lock` 中的 mkdocs 相关锁定项

---
## [1.0.0] - 2026-01-15

### 初始版本 (Initial Release)

- ✅ 用户认证与权限管理 (RBAC)
- ✅ 资产基础信息管理
- ✅ 租赁合同基础管理
- ✅ 租金台账基础功能
- ✅ 权属方/项目列表管理
- ✅ 数据字典管理
