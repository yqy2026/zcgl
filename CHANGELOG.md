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
- **Excel 异步任务状态修复** (Excel Async Task Status Fix)
  - 异步导入/导出任务改用 `TaskService` 更新状态与历史记录
  - 后台任务独立创建数据库会话，避免请求结束后的会话失效
- **Excel 配置创建修复** (Excel Config Create Fix)
  - Excel 配置创建时补齐 `task_type` 与格式配置，避免字段不匹配导致创建失败
  - 默认配置切换时自动取消同类型默认值，避免多默认配置
- **任务访问控制修复** (Task Access Control Fix)
  - 任务列表/详情/更新/删除/历史仅允许任务创建者或管理员访问
  - Excel 任务状态与导出下载接口需要认证并校验任务归属
  - 过期任务清理接口限制为管理员调用
- **租金台账更新逻辑修复** (Rent Ledger Update Logic Fix)
  - 单条台账更新改为服务层处理，自动计算逾期金额与服务费
  - 统一与批量更新的衍生字段逻辑，避免直接 CRUD 导致数据不一致
- **Excel 历史分页修复** (Excel History Pagination Fix)
  - 修复 Excel 操作历史接口返回总数错误的问题
  - 现在返回真实总数以匹配分页数据
- **租金合同 Excel 服务补齐** (Rent Contract Excel Service Restoration)
  - 恢复租金合同模板下载、导入与导出服务，避免模块缺失导致接口不可用
  - 支持合同/条款/台账多表导出与基础导入
- **运行依赖补齐** (Runtime Dependency Completion)
  - 添加 `cryptography` 与 `httpx` 到后端核心依赖，避免运行期导入失败
- **租金合同删除逻辑修复** (Rent Contract Delete Logic Fix)
  - 删除合同改为服务层软删除并记录历史，避免历史/关联表外键导致的删除失败
  - 租金合同查询默认排除已删除数据

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
- **配置验证去重** (Config Validation Deduplication)
  - 环境覆盖逻辑移入 `Settings` 校验阶段，避免运行时二次修改
  - 移除重复的 SECRET_KEY/Redis 校验，保留 DATABASE_URL 必填检查

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
- `docs/guides/components.md` - 前端组件导航与入口说明
- `frontend/src/components/index.ts` - 组件统一入口命名空间导出
- `frontend/src/components/Analytics/index.ts` - 分析模块统一入口
- `frontend/src/components/Common/index.ts` - 通用组件统一入口
- `frontend/src/components/Monitoring/index.ts` - 监控模块统一入口
- `frontend/src/components/Router/index.ts` - 路由模块统一入口
- `frontend/src/components/System/index.ts` - 系统管理模块统一入口
- `frontend/src/components/Auth/index.ts` - 认证模块统一入口
- `frontend/src/components/Dashboard/index.ts` - 仪表盘模块统一入口
- `frontend/src/components/Ownership/index.ts` - 权属方模块统一入口
- `frontend/src/components/Project/index.ts` - 项目模块统一入口
- `frontend/src/components/Rental/index.ts` - 租赁模块统一入口

#### Changed / 变更

- 修复文档引用路径:
  - `backend/docs/enhanced_database_guide.md`
  - `frontend/docs/type-safety-fix-summary.md`
  - `scripts/README.md`
- 更新文档入口与前端指南组件导航链接:
  - `docs/index.md`
  - `docs/guides/frontend.md`
- 更新组件导航表，补充 Auth/Dashboard/Ownership/Project/Rental/Router/Monitoring/System 入口:
  - `docs/guides/components.md`
- 修正组件入口导出冲突与默认导出错误:
  - `frontend/src/components/Analytics/index.ts`
  - `frontend/src/components/Common/index.ts`
- `backend/debug_import.py` 迁移至 `backend/scripts/dev/debug_import.py` 并补充路径初始化
- `.gitignore` 允许 `backend/docs` 下的分析/报告占位文档被追踪
- `.gitignore` 忽略前端测试输出文件（`frontend/test-results.txt`、`frontend/test_output.txt`、`frontend/vitest_stdout.txt`）

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
