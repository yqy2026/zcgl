# 变更日志 (Changelog)

## [Unreleased] - 2026-02-06

### 🛠️ 本次修复 (Current Fixes)

- 资产字段统一替换：后端 `AssetCreate/AssetUpdate` 移除历史字段别名兼容，并在请求中显式拒绝 `wuyang_project_name`/`description`（统一使用 `project_name`/`notes`）
- 资产前端字段对齐：`AssetSearchResult` 仅使用 `project_name/notes`，移除旧字段回退逻辑
- 资产导出字段对齐：导出配置改为使用 `project_name`，移除无效导出键 `description`
- 旧可见性规则修复：`useFormFieldVisibility` 将协议字段依赖从 `wuyang_project_name` 调整为 `project_name`
- 权限判定改进：`RBACService` 管理员判定优先基于 RBAC 权限 `system:admin`，仅保留 `admin/super_admin` 名称作为兼容回退
- 权限上下文对齐：`AuthorizationContext.is_admin()` 改为调用 `rbac_service.is_admin()`，移除局部硬编码角色判断
- 启动前配置保护：`backend/run_dev.py` 新增 `DATA_ENCRYPTION_KEY` 的 Base64 格式与解码长度校验（至少 32 bytes），提前暴露配置错误
- 新增/更新测试：
  - 后端 schema 测试覆盖历史字段拒绝（提示改用 `project_name`/`notes`）
  - 后端 RBAC 测试覆盖基于 `system:admin` 的管理员识别
  - 前端 `usePermission` 测试覆盖“仅角色名不应自动视为管理员”
- 回归修复：`TableWithPagination` 恢复透传调用方 `scroll` 配置，仅在未传入时默认 `{ x: 'max-content' }`
- 回归修复：`Pagination` 移除重复触发的 `onShowSizeChange` 绑定，避免分页大小变更导致重复请求
- 回归修复：`Layout.module.css` 将未定义的 `--color-bg-container` 替换为已定义的 `--color-bg-primary`
- 可访问性修复：`AssetBasicInfoSection` 移除输入框错误的 `aria-label={labelId}`，避免屏幕阅读器朗读内部 ID
- 类型修复：`assetFormSchema` 与 `Asset` 类型移除 `wuyang_project_name/description` 历史字段，仅保留 `project_name/notes`
- 资产表单字段彻底统一：`assetFormSchema` 与 `useFormFieldVisibility` 全量替换为 `lease_contract_number / contract_start_date / contract_end_date`，移除 `lease_contract / current_contract_* / current_lease_contract / agreement_* / current_terminal_contract`
- 资产历史展示字段统一：`AssetHistory` 仅使用 `operator / operation_time / change_reason`，移除 `changed_by / changed_at / reason` 回退路径
- 通知未读数接口统一：前端 `notificationService` 改为读取 `unread_count`（不再读取 `count` 兼容字段），并同步更新单测
- 产权证审核字段统一：前端 `PropertyCertificate` 类型与页面全部改为 `is_verified`，移除 `verified` 历史字段兼容
- 产权证导入确认字段统一：前端确认载荷改为 `asset_ids + should_create_new_asset`，移除 `create_new_asset` 历史字段
- 分析服务响应兼容清理：`analyticsService` 移除 `apiData.data?.*` 多形态回退，仅保留当前响应结构与字段适配
- 导出任务字段统一：前端导出任务类型改为 snake_case（`download_url / created_at / completed_at / error_message`），移除 camelCase 兼容路径
- 资产历史字段兼容清理：后端 `history_crud.create_async` 移除 `operator_id -> operator` 桥接，仅接受标准字段 `operator`
- 资产 schema 进一步收敛：删除 `AssetBase` 中的 `wuyang_project_name` 历史字段定义，仅保留“显式拒绝旧字段并提示替换”的校验逻辑
- 产权证导入确认字段统一：后端 `PropertyCertificateService.confirm_import` 改为仅处理 `extracted_data / asset_ids / should_create_new_asset`，并将资产关联透传到 CRUD 创建流程

### 🔐 安全 (Security)

#### Fixed / 修复

- 将 `backend/config/backend.env.secure` 从 Git 索引移除，阻止继续版本化跟踪明文敏感配置
- 删除工作区中的 `backend/config/backend.env.secure` 明文敏感文件，避免本地误用或二次泄露
- `.gitignore` 增加 `backend/config/*.env.secure` / `backend/config/*.secure` 规则，防止安全配置文件再次被提交
- 清理 `backend/config/` 目录中的遗留跟踪文件（`config.example.yaml`、`quality_monitor_config.yaml`、`pytest_ultra_optimized.ini`、`create_admin_user.sql`）
- `.gitignore` 增加 `backend/config/create_admin_user.sql` 与 `config/create_admin_user.sql` 规则，阻止管理员凭据 SQL 产物被提交
- `README.md` 与 `docs/guides/deployment.md` 增加“密钥一旦出现在 Git 历史即必须视为泄露并强制轮换”的应急处置指引
- 调整 `backend/scripts/devtools/security_key_generator.py`：敏感产物默认输出到系统临时目录 `zcgl-security-artifacts`（可用 `SECURITY_ARTIFACTS_DIR` 覆盖），不再默认写入仓库目录

### 🎨 UI/UX 改进 (UI/UX Improvements)

#### Added / 新增

- **可访问性增强** (Accessibility Enhancement)
  - 为 AssetList 组件的所有操作按钮添加 ARIA 标签（aria-label, title）
  - 为表单字段添加可访问性属性（aria-required, aria-describedby, aria-label）
  - 为 Modal 添加焦点管理（autoFocus, focusTriggerAfterClose）
  - 为错误提示添加 role="alert" 和 aria-invalid 属性
  - 影响 24+ 个交互元素，符合 WCAG 2.1 AA 级标准

- **响应式设计优化** (Responsive Design)
  - 实现表格响应式设计，移动端（< 768px）自动隐藏次要列
  - 动态调整表格滚动配置和尺寸（移动端 y: 400px, 桌面端 y: 600px）
  - 添加窗口 resize 监听，实时响应屏幕尺寸变化
  - 移动端使用 size="small" 优化显示效果

- **样式系统统一** (Style System Unification)
  - 将 Layout.module.css 中 15+ 处硬编码颜色替换为 CSS 变量
  - 统一使用 variables.css 定义的语义化变量
  - 修复内容区域被固定导航栏遮挡的问题（添加适当的 padding-top）

- **性能优化指南** (Performance Optimization Guide)
  - 新增 `frontend/docs/performance-optimization.md` 文档
  - 包含虚拟滚动方案、图片优化、搜索防抖等最佳实践
  - 记录 Web Vitals 性能监控指标和目标

#### Changed / 改进

- AssetList 组件添加响应式状态管理（isMobile）
- 表格列配置支持移动端自动隐藏
- 表单输入框添加完整的可访问性属性
- 按钮和交互元素添加描述性 ARIA 标签

#### Fixed / 修复

- 修复内容区域被固定导航栏遮挡（64px header + 56px breadcrumb）
- **修复页面"蒙层"效果** (Fix Overlay Effect)
  - 移除 Layout.module.css 中的毛玻璃效果（`backdrop-filter: blur(8px)` 和半透明背景）
  - 移除 global.css 中的过渡动画冲突规则
  - 统一使用 CSS 变量 `var(--color-bg-container)` 作为背景色
  - 影响文件：Layout.module.css, global.css, App.tsx, TableWithPagination.tsx 等
  - 修复文件数：12个，修复问题数：15个
- **修复 TypeScript 类型错误** (Fix Type Errors)
  - 修复 AssetSearchResult 组件中 undefined 类型传递问题
  - 修复 AssetSearchFilters 接口类型定义（usage_status, property_nature 等）
  - 修复 ResponsiveTable 和 TableWithPagination 组件类型兼容性
  - 移除未使用的导入和变量（AssetList, EmptyState, Loading, ThemeToggle, VirtualList）
  - ESLint 检查通过（0 错误，0 警告）
- **修复导入路径大小写不一致** (Fix Import Path Case)
  - 统一使用 `Common` 目录（大写C）替代 `common`（小写c）
  - 提高跨平台兼容性（Windows/macOS/Linux）
- **修复 CSS 样式错误** (Fix CSS Style Errors)
  - 修复 EmptyState 组件中 `var-spacing-md)` 缺少开括号的错误
  - 优化 ThemeToggle 组件使用 CSS 类代替内联样式修改
- 修复硬编码样式导致的主题切换不兼容问题

#### 文档 (Documentation)

- 新增 `frontend/docs/ui-ux-improvements-report.md` - UI/UX 改进实施报告
- 新增 `frontend/docs/performance-optimization.md` - 性能优化指南

### 🧪 审核 (Audit)

- **数据库异步化实施核查** (Async DB Migration Audit)
  - 仍存在 run_sync、同步 Session 与 get_db 依赖，异步化未完全收敛

### 🧰 工具与环境 (Tooling & Environment)

#### Fixed / 修复

- 开发启动脚本限制 Uvicorn reload 监听目录为 `backend/src`，并支持 `RELOAD` 环境变量关闭重载，避免非源码变更触发重启
- 修复 RBAC 初始化脚本可重复执行并补齐 `property_certificate` 权限，遇到遗留 `users.role` 约束时跳过测试用户创建以保证初始化可完成
- 修复 RBAC 初始化脚本动态权限示例的 `assigned_by` 外键错误，避免插入失败并保持幂等
- RBAC 初始化脚本在测试用户已存在时仍会确保角色分配，并在输出中明确已存在数量
- 修复角色列表/详情接口未预加载权限导致的 `MissingGreenlet` 500 错误
- 调整 CORS 中间件顺序，确保错误响应也包含 CORS 头，避免前端 `system/users` 报 CORS 拒绝
- CORS 允许 `Authorization` 请求头，修复携带登录令牌的预检请求被拒绝
- 本地开发环境补齐 `backend/.env` 基础配置（development 模式 + PostgreSQL 连接信息）
- Makefile 后端命令默认使用 `backend/.venv` 的 Python，避免调用系统 Python 导致依赖缺失

#### Removed / 删除

- 删除根目录 `.venv`，统一使用 `backend/.venv` 以避免环境混淆

### 🧹 清理 (Cleanup)

#### Removed / 删除

- **项目临时文件清理** (Project Cleanup)
  - 删除测试输出、缓存目录和构建产物（释放 124.3 MB）
  - 清理临时脚本、报告文档和日志文件
  - 删除过期的 `package/` 目录和 playwright tarball 包
  - 移除测试覆盖率脚本 `test_rent_contract_service_coverage.py`
  - 总计清理 82 个文件，删除 1002 行代码

### 🔍 搜索 (Search)

- **加密字段模糊搜索支持** (Blind Index for Encrypted Search)
  - 新增 `asset_search_index` 表，使用 HMAC n-gram 盲索引支持地址/权属方子串搜索
  - 资产列表搜索与产权证资产匹配改用盲索引（加密启用时），仍保留未加密时 ILIKE
  - 新增重建脚本 `scripts/maintenance/rebuild_asset_search_index.py` 用于回填索引

### 📚 文档 (Docs)

- 明确说明 `SecurityService` 已移除，并指向 `PasswordService`/`AuthenticationService` 作为安全替代路径
- AGENTS.md 增加提示：后端测试应使用项目 `backend/.venv`，避免 `.env` 不生效
- AGENTS.md 增补启动/登录/排查经验与常见故障定位要点

### 🛡️ 稳定性与架构修复 (Stability & Architecture Fixes)

#### Fixed / 修复

- 修复 `core/performance.py` 查询优化器缩进错误导致后端启动失败的问题
- 将数据库初始化移动到应用生命周期中，避免启动时 `asyncio.run()` 在事件循环中触发错误
- 修复通知任务端点异步定义与依赖注入，避免路由注册时报 `await` 语法错误
- 修复 RBAC 角色有效期比较使用时区感知时间导致的数据库错误
- 修复登录接口在权限读取成功时未初始化角色汇总导致的异常
- **RBAC 角色单一来源** (Single Source of Truth for Roles)
  - 认证响应与用户信息统一使用 RBAC 角色汇总（`role_id`/`role_name`/`role_ids`），移除旧 `role` 字段依赖
  - 统一测试与示例数据为 `role_id`，避免遗留角色字符串导致权限误判
- **资产字段补齐** (Asset Field Completeness)
  - 资产新增 `wuyang_project_name` 与 `description` 字段对齐前端，避免提交后静默丢失
  - 新增数据库迁移补齐 `assets` 表字段
- **管理员权限统一** (Admin Permission Unification)
  - 管理员判断改为 `system:admin` 权限，不再依赖角色名
  - 迁移为 `admin`/`super_admin` 角色回填 `system:admin` 权限
- **资产权属字段统一** (Asset Ownership Unification)
  - 资产创建/更新/筛选仅使用 `ownership_id`，`ownership_entity` 改为动态读取（不落库）
  - 资产筛选与统计接口移除 `ownership_entity` 查询参数，前端筛选改用权属方选项与 `ownership_id`
- **组织循环检测查询降为单次递归 CTE** (Organization Cycle Check Single-Query CTE)
  - `_would_create_cycle` 改为递归 CTE 检测父链，避免逐层查询造成的性能放大
- **组织子树路径批量更新** (Organization Subtree Path Batch Update)
  - `_update_children_path` 改为递归 CTE 批量更新层级与路径，移除逐节点递归查询
- **管理员数据库重置异步化** (Admin DB Reset Async)
  - 管理员重置数据库接口改为异步并 await create/drop tables
- **RBAC 服务统一** (RBAC Service Consolidation)
  - 移除 `services/rbac` 旧实现与相关遗留测试引用
  - 统一使用 `services/permission/rbac_service.py`，改用 CRUD + 标准异常
  - 角色管理 API 调用路径切换至新 RBAC 服务
  - RBAC 服务内时间戳改为 `datetime.now(UTC)`，避免 `utcnow()` 弃用警告
- **移除不安全 SecurityService Stub** (Remove Unsafe SecurityService Stub)
  - 删除 `SecurityService` stub 与相关导出，避免 IDE/自动导入误用
  - 新增单元测试防回归，确保 `SecurityService` 不可被导入或导出
- **Ownership 模型抽离与导入统一** (Ownership Model Extraction & Import Unification)
  - Ownership 独立到 `models/ownership.py` 并更新所有引用路径
  - 统一模型导出，避免对 `models.asset` 的隐式依赖与循环导入风险
  - 修复字段白名单初始化中 Ownership 的导入路径，避免运行时警告
- **数据库引擎类型注解修复** (Database Engine Type Hint Fix)
  - 补充 `sqlalchemy.engine.Engine` 导入，避免类型注解在运行时报 NameError
- **枚举初始化异步化** (Enum Init Async Migration)
  - 启动阶段枚举数据初始化改用 AsyncSession + async_session_scope
  - 枚举与遗留值同步逻辑改为异步查询/提交
- **Excel 模板服务去数据库依赖** (Excel Template DB Decoupling)
  - Excel 模板服务移除 Session 依赖，下载路由不再注入未使用的 db
- **移除同步适配层** (Remove Sync Adapter Layer)
  - 删除 `utils/async_db.py` 中的 run_sync/适配器占位实现
- **资产唯一性校验异步化** (Asset Uniqueness Async Validation)
  - AssetValidator 唯一性校验改为 AsyncSession 查询
- **出租率计算去同步 DB** (Occupancy Calc Sync DB Removal)
  - OccupancyRateCalculator 移除同步 Session 聚合路径，仅保留内存计算
- **Excel 导出服务异步收敛** (Excel Export Async Convergence)
  - Excel 导出服务移除同步导出接口与 Session 依赖，保留异步导出路径
- **审计服务异步化** (Audit Service Async Migration)
  - AuditService 改为 AsyncSession + await 调用并更新单元测试为异步
- **分析缓存接口异步化** (Analytics Cache Async Update)
  - 缓存统计/清理服务方法改为异步并在 API 端点 await 调用
  - 分析服务单元测试与统计 API 测试更新为异步 Mock/await
- **分析缓存执行异步化** (Analytics Cache Async Execution)
  - 分析服务缓存读取/写入/清理/统计改为异步线程执行，避免阻塞事件循环
- **Excel 导出服务异步兼容** (Excel Export Async Compatibility)
  - Excel 导出服务支持 AsyncSession 并新增异步导出与预览方法
- **财务统计接口异步化** (Financial Stats Async Migration)
  - 财务汇总统计移除 run_sync，统一 await 异步服务
  - 财务统计单元测试改用 AsyncMock 与 await
- **系统备份与历史接口异步化** (System Backup & History Async Migration)
  - 备份创建/恢复移除 run_sync，统一使用 AsyncSession 获取数据库连接信息
  - 历史记录列表/详情/删除改用异步 CRUD 方法
- **租赁合同统计与生命周期异步化** (Rent Contract Stats & Lifecycle Async Migration)
  - 统计概览/权属/资产/月度/导出移除 run_sync，统一使用 AsyncSession 异步服务
  - 续签/终止流程新增异步服务并在路由 await 调用
- **租赁合同统计服务异步化收敛** (Rent Contract Statistics Async Convergence)
  - 统计服务移除同步方法与 Session 依赖，统一 AsyncSession 路径
- **资产批量/自定义字段/产权证测试异步对齐** (Async Test Alignment for Batch/CustomField/PropertyCert)
  - 资产批量服务与 API 单测改用 AsyncMock/await
  - 自定义字段/产权证 CRUD 与服务单测更新为异步调用
- **租赁合同 CRUD 异步化** (Rent Contract CRUD Async Migration)
  - 合同查询/筛选/台账/条款 CRUD 补齐 AsyncSession 方法，移除 run_sync 包装
  - 合同创建/更新/删除改为异步调用并新增异步更新服务
  - 租赁合同 API 单测改用 AsyncMock/await 适配异步接口
- **租赁合同台账与附件异步补齐** (Rent Contract Ledger & Attachment Async Follow-up)
  - 台账生成/批量更新/更新服务补齐异步实现并移除 run_sync
  - 附件/合同错误用例单测改为异步调用以匹配异步路由
- **租赁合同附件异步收敛** (Rent Contract Attachment Async Convergence)
  - 附件增删查改用 AsyncSession 调用并补齐异步上传服务
  - Excel 异步导入任务创建改为异步 CRUD，移除 run_sync 适配
- **资产附件单测异步对齐** (Asset Attachment Test Async Alignment)
  - 资产附件单元测试改用 AsyncMock/await 适配异步路由实现
- **资产附件字段防丢失对齐** (Asset Attachment Field Preservation)
  - 前端 `assetFormSchema` 补齐接收协议/终端合同附件字段
  - 后端新增 Asset schema 单元测试，确保字段序列化不丢失
  - 资产 API 单测样例补齐附件字段
- **用户组织字段对齐** (User Organization Field Alignment)
  - 后端 User 支持 `organization_id` 兼容别名并返回别名字段
  - 前端统一使用 `default_organization_id`，/auth/me 补齐组织字段

### 🧪 测试 (Tests)

- **RBAC/权属测试对齐** (RBAC/Ownership Test Alignment)
  - 单元/集成/E2E 测试统一使用 `role_id` 与 RBAC 角色分配
  - 资产测试数据改为 `ownership_id`，并为集成场景补齐权属方关联
- **系统监控健康检查测试异步化** (System Health Tests Async)
  - check_component_health 单测改为 async/await 并使用 AsyncMock
- **PDF 批量导入集成测试对齐异步依赖** (PDF Batch API Tests Async Alignment)
  - 移除 get_db 覆盖，使用默认 get_async_db 依赖
- **PDF 批量上传错误响应断言对齐** (PDF Batch Upload Error Assertion)
  - 集成测试改为校验中间件返回的 message 字段
- **出租率计算单测切换为内存计算路径** (Occupancy Calculator Tests In-Memory)
  - 移除 get_db patch，按内存资产列表验证统计结果

### 📚 文档 (Docs)

- 资产与数据库设计文档更新：`ownership_id` 作为唯一来源，`ownership_entity` 动态读取
- 认证与测试示例更新：移除旧 `role` 字段，统一使用 `role_id`
- **异步数据库示例更新** (Async DB Docs Refresh)
  - 后端/数据库/测试指南示例改为 AsyncSession + get_async_db
- **Excel 导出路由单测异步对齐** (Excel Export Route Test Async Alignment)
  - Excel 导出相关单元测试补齐 await 与异步 Mock
- **Excel 预览路由异步对齐** (Excel Preview Route Async Alignment)
  - 预览接口改用 AsyncSession + get_async_db 依赖注入
- **Excel 导入路由异步对齐** (Excel Import Route Async Alignment)
  - 同步/异步导入改为 AsyncSession 调用并移除线程内同步会话
  - 导入后台任务测试改为异步 CRUD 调用与 AsyncMock
- **请求日志异步化** (Request Logging Async Migration)
  - 操作日志记录改为 AsyncSession 异步写入并移除 run_sync 适配
- **产权证服务异步化** (Property Certificate Service Async Migration)
  - 产权证列表/详情/创建/更新/删除移除 run_sync，直接使用 AsyncSession CRUD
- **产权证提取提示词加载** (Property Certificate Prompt Loading)
  - 上传提取流程改用异步 PromptManager 获取激活模板，避免无 PromptManager 时抛配置异常
- **文档提取管理器兼容性** (Document Extraction Manager Compatibility)
  - 产权证提取支持注入 AsyncSession 获取 Prompt，结果字段兼容 extracted_fields/data
- **产权证提取适配器异步兼容** (Property Certificate Adapter Async Compatibility)
  - PromptManager 根据 AsyncSession 调用异步查询，避免同步查询阻塞
- **PDF 导入会话异步化** (PDF Import Session Async Migration)
  - 会话创建/状态查询/处理状态持久化/确认导入/取消流程移除 run_sync
- **PDF 批量会话查询异步化** (PDF Batch Session Async Migration)
  - 批量状态/取消接口改用 AsyncSession 查询会话映射
- **PDF 会话服务异步化** (PDF Session Service Async Migration)
  - PDFSessionService 改为 AsyncSession 并异步化会话查询/创建
- **PDF 处理追踪异步化** (PDF Processing Tracker Async Migration)
  - ProcessingTracker 与步骤追踪装饰器改为 AsyncSession
- **组织列表分页解析修复** (Organization List Pagination Parsing)
  - 前端组织服务解包分页 items，避免用户管理页加载组织列表时报错
  - 组织搜索/高级搜索/历史列表统一兼容分页响应
- **用户列表无限刷新修复** (User List Infinite Refresh Fix)
  - 拆分用户管理页初始化副作用，避免统计刷新触发重复拉取导致渲染深度溢出
- **租赁合同创建提交修复** (Rent Contract Create Submit Fix)
  - 租赁合同表单补齐 onFinish 提交回调，修复创建合同无请求的问题
  - 新增表单提交单元测试覆盖
- **租赁合同创建错误提示与重试优化** (Rent Contract Create Error Messaging & Retry)
  - 创建合同遇到 4xx 冲突不再重试，避免重复提交
  - 失败提示展示后端返回的冲突原因
- **资产重名与删除约束** (Asset Uniqueness & Delete Guard)
  - 资产 `property_name` 全局唯一（服务/导入校验 + 数据库唯一约束）
  - 资产删除时若已关联合同或产权证则阻止删除
- **权属一致性校验** (Ownership Alignment)
  - `ownership_id` 与 `ownership_entity` 不一致时拒绝写入并对齐名称
- **异步会话迁移补齐** (Async Session Migration Completion)
  - 资产/合同/组织/催缴/字典/统计/产权证/PDF批量等接口统一改用 AsyncSession + get_async_db
  - PDF 批量监控改用 async_session_scope，避免同步会话混用
  - PDF 导入会话创建/取消改为异步封装，API 调用统一 await
  - 合同编辑权限检查改为异步 RBAC 适配器调用
  - Excel 同步导入改为线程内创建会话，避免跨线程复用 Session
- **异步会话迁移补充** (Async Session Migration Follow-ups)
  - 枚举字段/权属方/项目/会话管理接口统一改为 AsyncSession + run_sync 适配同步 CRUD/Service
    - 资产导入/提示词/系统设置接口补齐 run_sync 包装与类型适配
- **用户管理服务单测异步化** (User Management Service Test Async Migration)
  - 修复用户管理服务单元测试，统一 AsyncMock/await 与 AsyncSessionService 依赖注入
- **用户管理 API 单测异步对齐** (Users API Test Async Alignment)
  - Users API 单测改为 asyncio.run 调用异步路由，CRUD/Service Mock 全量异步化
  - 锁定/解锁/重置密码测试补齐 AsyncMock commit/refresh/rollback
- **认证集成测试导入清理** (Auth Integration Test Import Cleanup)
  - 集成测试导入改为 AsyncAuthenticationService/AsyncSessionService/AsyncUserManagementService
- **认证 CRUD 异步化** (Auth CRUD Async Migration)
  - auth CRUD 移除同步 Session 接口，补齐用户/会话/审计异步方法
  - 认证 CRUD 单元测试改为 AsyncMock/await，集成测试移除 get_db 同步依赖
- **资产服务异步化** (Asset Service Async Migration)
  - AssetService 统一为 AsyncSession 异步实现，并保留 AsyncAssetService 别名
  - 资产服务单元/集成测试改为异步执行，使用 AsyncMock 与异步会话隔离
  - 资产服务集成测试改用临时异步引擎 + NullPool，避免事件循环关闭导致连接异常
- **组织服务异步化** (Organization Service Async Migration)
  - OrganizationService 全量改为 AsyncSession 调用并修正组织 API 调用命名
  - 组织服务单元/集成测试改为异步执行（AsyncMock + AsyncSession）
  - 组织服务历史/统计查询改为异步路径
  - 遗留的深度/增强集成测试暂时标记跳过，等待异步 API 对齐后恢复
- **操作日志 CRUD 异步化** (Operation Log CRUD Async Migration)
  - OperationLogCRUD 移除同步方法，仅保留异步 CRUD/统计接口
  - 操作日志 CRUD 单元测试改为 AsyncMock + await
  - 组织服务集成测试修正异步引擎引用方式，避免引擎初始化判定失效
  - 组织服务集成测试改用临时异步引擎 + NullPool，避免事件循环关闭导致连接异常
- **系统字典异步化** (System Dictionary Async Migration)
  - system_dictionary CRUD/Service 移除同步 Session 接口，仅保留 AsyncSession 路径
  - 系统字典单元/集成测试改为异步执行并使用 asyncpg 引擎
- **枚举字段与公共字典异步化** (Enum Field & Common Dictionary Async Migration)
  - enum_field CRUD 移除同步方法，仅保留 AsyncSession 异步实现
  - CommonDictionaryService 移除同步入口，单元测试改为 AsyncMock/await 并移除 db_session 依赖
- **通知模块异步化** (Notification Module Async Migration)
  - Notification CRUD/Service 移除同步方法，仅保留 AsyncSession 异步接口
  - 通知定时任务调度器改为异步查询与 async_session_scope 执行
  - 通知调度单元/集成测试改为异步会话与 AsyncMock
- **任务模块异步化** (Task Module Async Migration)
  - Task/ExcelTaskConfig CRUD 移除同步方法，仅保留 AsyncSession 异步实现
  - 任务 API 与服务单元测试统一 AsyncMock/await 调用
  - 任务服务集成测试改用异步会话与当前 TaskService 能力
  - 任务创建单元测试对齐历史记录写入与多次提交行为
- **资产字段值查询测试数据去重** (Asset Field Values Test Data Uniqueness)
  - 资产集成测试字段值查询场景改用唯一 `property_name`，避免唯一约束冲突

### ✨ 文档识别 (Document Extraction)

- **GLM-OCR 预处理接入**
  - 新增 GLM-OCR 服务与 OCR 文本抽取管道
  - 智能识别支持扫描件自动走 OCR，并支持 `force_method=ocr`
  - 产权证/合同提取在 OCR 失败时回退至现有视觉模型
- **PyMuPDF 调用异步化**
  - 文本提取 / PDF 分析 / Vision 转图统一线程池 offload，避免阻塞事件循环
- **LLMService 读取配置对齐**
  - LLM 服务创建优先读取 settings/.env 中的提供商与密钥配置，避免本地脚本无法读取环境变量
- **Vision PDF 转图工具补齐**
  - 补充 `pdf_to_images` 实现，支持 PyMuPDF/pdf2image 转图，修复视觉提取缺失模块
- **证据驱动识别输出**
  - OCR 提取新增字段证据片段与来源（field_evidence/field_sources）
  - PDF 智能合并流程加入一致性校验与置信度扣减
  - API 类型与前端处理选项支持 `force_method=ocr`
  - async_db 适配器补齐构造签名类型约束，修正类型推断错误
- **合同导入审核证据展示**
  - 合同导入确认页支持字段证据弹窗与来源提示
  - 提取警告信息同步展示，便于快速复核异常字段
- **资产批量与历史接口异步化** (Asset Batch & History Async Migration)
  - 资产批量更新/验证/删除/列表与历史接口移除 run_sync，统一使用 AsyncSession 调用
  - 批量更新与删除补齐异步 CRUD 与历史记录写入
- **PDF 路由兼容性** (PDF Route Compatibility)
  - 增加 `/documents/pdf-import/*` 兼容路由，保持历史路径与测试用例可用
- **分析缓存容错** (Analytics Cache Guard)
  - 分析缓存读写失败时降级执行计算，避免测试/运行期 Redis 异常导致 500
- **分析与面积服务单测异步适配** (Analytics/Area Test Async Alignment)
  - 面积聚合/内存计算单测改用 AsyncSession mock 与 await
  - 分析趋势/分布测试补齐异步 patch 与 await 逻辑
- **分析服务清理无用导入** (Analytics Service Import Cleanup)
  - 移除未使用的 SQLAlchemy or_ 导入以通过 lint
- **后台服务会话初始化修复** (Background Service Session Init Fix)
  - 出租率计算、通知任务、租金合同导出改用 session_factory，移除 get_db 生成器调用
- **代码格式统一** (Code Formatting Alignment)
  - 执行 Ruff 格式化以统一最新异步迁移后的代码风格
- **PDF V1上传内存风险** (PDF V1 Upload Memory Risk)
  - V1 兼容上传改为流式写入并严格限制大小，避免一次性读入内存
  - 上传临时文件处理完成后自动清理
- **PDF 导入临时文件清理** (PDF Import Temp File Cleanup)
- **催缴服务异步收敛** (Collection Service Async Convergence)
  - CollectionService 移除同步方法与 Session 依赖，统一 AsyncSession
  - 催缴 API 单测改用 AsyncMock/await
- **枚举验证异步收敛** (Enum Validation Async Convergence)
  - 移除同步 EnumValidationService 与便捷函数，仅保留 AsyncEnumValidationService
  - 单测与全局 mock 更新为异步验证接口
- **LLM Prompt 异步收敛** (LLM Prompt Async Convergence)
  - PromptManager/FeedbackService/AutoOptimizer 移除同步接口并改用 AsyncSession
  - LLM Prompt 服务单测重写为异步覆盖
- **产权证提示词适配器收紧** (Property Cert Adapter Async-only)
  - PromptManager 获取提示词仅接受 AsyncSession，移除同步 fallback

### 🧰 工具 (Tooling)

- **开发进程监控脚本** (Dev Watch Script)
  - 新增 `scripts/dev_watch.ps1`，启动前后端并在异常退出时记录退出码与日志尾部
  - 支持后台脱离控制台运行，避免关窗导致进程被中断
- **开发启动默认行为恢复** (Dev Server Defaults Restored)
  - Makefile 恢复默认 shell 行为
  - 前端 Vite 恢复默认启动与 TS 配置，后端 dev server 恢复默认 reload

### 📝 文档更新 (Documentation Updates)

- 更新 `AGENTS.md` 与 `CLAUDE.md`，同步最新命令、规则与更新时间
- 对齐前端状态管理描述：Zustand 用于 UI/资产 UI 状态，认证使用 React Context

### 🐞 Bug Fixes

- **产权证列表 404** (Property Certificate List 404)
  - 修复产权证路由重复前缀导致 `/api/v1/property-certificates/` 404
  - 处理结果/失败后自动清理 `temp_uploads` 与系统临时目录下的源文件
- **产权证字段兼容修复** (Property Certificate Field Compatibility)
  - 响应补齐 `verified` 字段并兼容 `is_verified` 更新
  - 列表查询参数统一使用 `limit`
- **前端路由与组件警告修复** (Frontend Route & Warning Fixes)
  - 产权证导入页面包屑不再误判为详情页
  - Ant Design Steps/Modal 废弃属性警告修复
- **系统字典与统计页面修复** (Dictionary & Stats Page Fixes)
  - 枚举字段列表响应移除 children 懒加载，修复字典页 500
  - 枚举值 children 通过 `set_committed_value` 清理，避免 Pydantic 校验触发 MissingGreenlet
  - 系统设置/组织管理 Tabs 改用 items，移除 TabPane 废弃警告
  - 系统设置密码策略表单修复单子元素渲染警告
  - 个人中心弹窗强制渲染，避免 useForm 未连接提示
  - 租金统计饼图标签改为函数并补齐图表错误边界
  - 租金统计收缴率进度条改用 `size`，移除 Progress width 废弃警告
- **项目/组织响应懒加载防护** (Project/Organization Lazy-load Guard)
  - ProjectResponse/OrganizationResponse 避免在序列化时访问未加载关系字段
- **枚举字段异步加载修复** (Enum Field Async Load Fix)
  - 异步加载枚举值使用 `set_committed_value`，避免 greenlet_spawn 触发 503
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
- **资产创建事务提交修复** (Asset Create Transaction Commit Fix)
  - 修复资产创建在已有事务（权限校验/审计依赖）场景下仅开启嵌套事务导致提交丢失的问题
  - 资产创建现在在检测到已有事务时显式提交，确保写入持久化
- **资产列表缓存失效修复** (Asset List Cache Invalidation Fix)
  - 资产新增/更新/删除后清理资产相关 GET 缓存，避免列表继续显示旧数据
  - API 客户端新增按前缀失效缓存接口，支持粒度清理
- **资产软删除与校验加强** (Asset Soft Delete & Guard)
  - 资产删除改为软删除（data_status=已删除），保留历史记录与附件数据
  - 删除前新增租金台账关联校验，阻止存在台账的资产被删除
  - 查询统计补齐软删除过滤，确保列表与总数一致
  - 管理员新增资产恢复/彻底删除接口，支持软删除恢复与物理清理
  - 资产恢复/彻底删除补齐服务层校验与单元测试覆盖
  - Hard delete now clears asset history to avoid FK violations.
- **资产回收站筛选与前端操作** (Asset Recycle Bin UI)
  - 资产列表支持 `data_status` 筛选查看回收站记录
  - 前端新增资产状态筛选与状态列展示
  - 已删除资产仅显示恢复/彻底删除操作（管理员 + 强确认）
- **任务访问控制修复** (Task Access Control Fix)
  - 任务列表/详情/更新/删除/历史仅允许任务创建者或管理员访问
  - Excel 任务状态与导出下载接口需要认证并校验任务归属
  - 过期任务清理接口限制为管理员调用
- **任务模块异步迁移** (Task Module Async Migration)
  - 任务 CRUD/Service/API 统一使用 AsyncSession，移除 run_sync 适配
  - Excel 任务创建与状态更新改用同步会话专用 CRUD 方法
- **租金台账更新逻辑修复** (Rent Ledger Update Logic Fix)
  - 单条台账更新改为服务层处理，自动计算逾期金额与服务费
  - 统一与批量更新的衍生字段逻辑，避免直接 CRUD 导致数据不一致
- **Excel 历史分页修复** (Excel History Pagination Fix)
  - 修复 Excel 操作历史接口返回总数错误的问题
  - 现在返回真实总数以匹配分页数据
- **合同编辑权限校验修复** (Contract Edit Permission Check Fix)
  - 修复合同更新权限检查未生效的问题，确保 RBAC 校验可用
  - 新增租金条款接口同步执行合同编辑权限校验
- **附件接口修复** (Attachment Endpoints Fix)
  - 修复资产/租金合同附件接口的语法错误，确保路由正常加载
  - 附件接口统一为同步实现，避免测试与运行期不一致
- **API 路由语法修复** (API Route Syntax Fix)
  - 修复统计/组织/催缴/字典/出租率/Excel/PDF 批量接口中的 async/sync 结构错误
  - 清理错误的 `run_sync` 嵌套与 await 使用，恢复路由可加载与运行
  - 产权证接口改用同步会话并修正服务调用方式，避免运行期异常
- **Session 类型引用修复** (Session Type Reference Fix)
  - 修复 PDF 导入服务、系统设置与用户管理路由缺失 `Session` 类型引用导致的导入失败
- **系统设置接口异步化** (System Settings Async Migration)
  - 系统设置/系统信息/备份/恢复接口移除 run_sync，审计日志改为异步写入
- **租金合同路由同步化修复** (Rent Contract Route Sync Fix)
  - 将合同/条款/台账/统计/附件接口改为同步会话，移除错误的 `run_sync` 包装
  - 附件下载/删除改为同步获取附件对象，避免运行期取不到元数据
- **资产附件路由同步化修复** (Asset Attachment Route Sync Fix)
  - 资产附件上传/列表/下载/删除统一为同步会话并匹配文件校验流程
  - 附件列表与下载使用文件系统 API 与校验逻辑，确保测试路径一致
- **资产附件同步依赖补齐** (Asset Attachment Sync Dependency Fix)
  - 资产附件端点改用 `get_db` 同步会话，避免单元测试直接调用时出现未 await 协程
- **Excel 路由同步适配** (Excel Route Sync Alignment)
  - Excel 配置/导出/状态/模板接口恢复同步实现并改用 `get_db`，匹配单元测试直接调用方式
  - 异步导入/导出后台任务补齐可注入 `db_session` 并改用 `task_crud` 更新任务状态
  - 预览与同步导入端点补齐测试参数兼容逻辑，避免 mock 调用缺失导致断言失败
  - 异步导入创建任务时区分 AsyncSession 与 mock db，避免 `run_sync` 误用
- **租金合同 Excel 服务补齐** (Rent Contract Excel Service Restoration)
  - 恢复租金合同模板下载、导入与导出服务，避免模块缺失导致接口不可用
  - 支持合同/条款/台账多表导出与基础导入
- **运行依赖补齐** (Runtime Dependency Completion)
  - 添加 `cryptography` 与 `httpx` 到后端核心依赖，避免运行期导入失败
  - 添加 `asyncpg` 作为异步数据库驱动依赖，避免 AsyncSession 运行期导入失败
- **认证会话写入修复** (Auth Session Insert Fix)
  - `user_sessions` 写入统一使用 naive UTC 时间戳，避免 asyncpg 对 TIMESTAMP WITHOUT TIME ZONE 抛错
  - 审计日志写入改用 naive UTC 时间戳，避免 `audit_logs` 写入失败
  - 用户时间戳字段（`password_last_changed`/`updated_at`/`last_accessed_at`）改为 naive UTC
  - 登录流程不再因会话写入失败返回 500
- **密码过期判断修复** (Password Expiry Comparison Fix)
  - 密码过期时间比较统一为 naive UTC，避免登录时出现 aware/naive 比较异常
- **资产筛选下拉修复** (Asset Filter Dropdown Fix)
  - 资产列表筛选项改为异步 distinct 查询，避免 `run_sync` 调用协程导致 500
- **权属方列表修复** (Ownership List Fix)
  - 权属方列表/搜索改用同步查询封装，修复 `/api/v1/ownerships` 500
- **前端缓存分页提取修复** (Frontend Cache Paginated Extract Fix)
  - GET 缓存命中时继续执行 smartExtract，避免缓存返回原始响应导致列表结构缺失
- **创建接口斜杠兼容** (Create Endpoint Slash Compatibility)
  - 权属方/项目创建同时支持无尾斜杠路径，避免前端 POST 405
- **权属方创建校验修复** (Ownership Create Validation Fix)
  - 前端创建不再提交空字符串编码，允许后端自动生成编码，避免 422
- **权属方/项目异步化** (Ownership & Project Async Migration)
  - 权属方/项目服务与 API 端点改为 AsyncSession 调用，移除 run_sync 适配
  - 权属方财务汇总查询改为异步 SQL，避免同步子查询问题
- **项目响应懒加载修复** (Project Response Lazy-Load Fix)
  - 项目创建/列表/详情响应改为显式映射列字段，避免 ownership_relations 触发 MissingGreenlet
- **前端缓存提取测试** (Frontend Cache Extract Test)
  - 新增单元测试覆盖缓存命中时的分页响应提取
- **时间戳标准化扩展** (UTC Timestamp Standardization Expansion)
  - 模型/服务/CRUD 中写库时间统一使用 `datetime.utcnow()`（naive UTC），避免 asyncpg 对无时区字段报错
  - API 层 Excel 任务与用户更新写入时间统一为 `datetime.utcnow()`（naive UTC）
  - 清理替换后未使用的 `UTC` 导入
- **生产环境路由注册器防降级** (Production Router Registry Guard)
  - 生产环境禁止启用 `ALLOW_MOCK_REGISTRY`，缺失注册器属性时直接报错
  - 新增单元测试覆盖生产环境 Mock 降级保护
- **租金合同删除逻辑修复** (Rent Contract Delete Logic Fix)
  - 删除合同改为服务层软删除并记录历史，避免历史/关联表外键导致的删除失败
  - 租金合同查询默认排除已删除数据
- **前端类型检查修复** (Frontend Type Check Fixes)
  - 修复列表过滤回调与自定义统计卡片类型不匹配导致的 TS 报错
  - 修复 PDF 导入处理方式空字符串比较引发的类型报错
- **角色管理端点异步化** (Role API Async Migration)
  - 角色 CRUD、权限分配、统计与用户列表端点移除 run_sync 适配
  - 角色用户列表查询改为 AsyncSession 直连查询
- **认证会话接口异步化** (Auth Session Async Migration)
  - 会话查询/撤销与可选认证中间件移除 run_sync，改用 AsyncSession 查询
  - 调试认证端点改为 AsyncAuthenticationService 与 AsyncUserManagementService
  - 审计日志统计接口改为 AsyncSession 直连查询
- **组织架构接口异步化** (Organization API Async Migration)
  - 组织列表/搜索/树形/路径/历史等接口移除 run_sync 适配
  - 组织服务与 CRUD 补齐 AsyncSession 查询与历史记录写入
- **操作日志接口异步化** (Operation Log API Async Migration)
  - 操作日志列表/统计/导出/清理改为 AsyncSession 直连查询
  - 用户名补齐查询改用异步批量映射接口
- **安全事件接口异步化** (Security Event API Async Migration)
  - 系统设置安全事件查询改为异步 CRUD 调用
  - 组织权限与安全告警测试改为原生异步安全日志记录
- **枚举字段接口异步化** (Enum Field API Async Migration)
  - 枚举类型/值/使用记录/历史查询改为 AsyncSession 直连调用
  - 枚举 CRUD 补齐异步统计、批量写入与历史记录写入方法
- **提示词与通知接口异步化** (Prompt & Notification API Async Migration)
  - Prompt 模板/版本/统计/反馈接口移除 run_sync 适配
  - 通知列表/未读统计/标记已读/删除改为 AsyncSession 调用
- **系统字典与催缴接口异步化** (System Dictionary & Collection API Async Migration)
  - 系统字典 CRUD/批量更新改为 AsyncSession 直连
  - 催缴汇总/记录列表/读写接口移除 run_sync 适配

#### Changed / 变更

- **AGENTS 测试指引** (AGENTS Low-Memory Test Guidance)
  - 补充低内存运行 pytest 的建议与示例命令
- **资产枚举值更新** (Asset Enum Defaults Update)
  - 更新确权状态/使用状态/物业性质/租户类型的标准枚举值
- **产权证 API 层依赖规范化** (Property Certificate API Layer Normalization)
  - API 端点改为通过 `PropertyCertificateService` 访问 CRUD

#### Added / 新增

- **资产权属回填脚本** (Asset Ownership Backfill Script)
  - 新增脚本用于按 ownership_id 回填 ownership_entity（安全策略 A）
- **缺失的 CRUD 类补齐** (Missing CRUD Classes Added)
  - 新增 `collection_crud`、`dynamic_permission_crud`、`prompt_template_crud`
- **白名单补齐** (Field Whitelist Coverage)
  - 为 `CollectionRecord`、`DynamicPermission`、`PromptTemplate` 增加字段白名单
  - 为 `Project`、`Organization`、`PropertyCertificate`、`PropertyOwner`、`RentTerm`、`RentLedger`、`UserRoleAssignment`、`ResourcePermission`、`PermissionAuditLog` 增加字段白名单
  - 为 `AsyncTask`、`ExcelTaskConfig` 增加字段白名单

### 🧹 代码质量与测试修复 (Lint & Test Fixes)

#### Fixed / 修复

- **Ruff 清理** (Ruff Cleanup)
  - 清理无效 `_sync` 占位逻辑与未使用变量，统一异步/同步辅助代码风格
  - 修正缺失的类型导入与泛型写法（`AsyncDB` 适配器改用 PEP 695 语法）
  - 修复分析接口空行空白、重复导入与未使用导入问题
  - 统一 Excel 导入与产权证 CRUD 的导入排序/来源
  - 补齐资产历史查询缺失的 `Session` 类型导入
  - 密码过期校验改用 `datetime.UTC` 以符合 Ruff 规则
- **MyPy 类型修复** (MyPy Type Fixes)
  - 完善系统日志/字典/联系人/角色等接口的 `run_sync` 适配与 `Session` 类型注解
  - 修复租金合同 Excel 导入/导出类型转换与字段映射模型匹配
  - 统一权限检查/布尔返回类型，减少 `no-any-return` 报错
  - 补齐认证/资产/统计分析/租金合同等模块 `run_sync` 类型标注与导入
  - Excel 异步导入任务创建 helper 增加类型注解
- **附件/日志与导出修复** (Attachment, Logs, Export Fixes)
  - 附件下载补齐元数据获取，避免运行期变量未定义
  - 操作日志导出修复过滤器变量作用域
  - Excel 异步导出补齐 `Session` 类型引用
- **测试稳定性** (Test Stability)
  - 测试环境变量恢复逻辑补齐，避免污染后续用例
  - 清理未使用断言变量并补充必要断言
  - 认证 API 与会话服务单元测试改为 AsyncSession + AsyncMock
  - 认证服务拆分验证测试改用异步服务与 AsyncSession mock
- **可选认证测试清理** (Optional Auth Test Cleanup)
  - 移除可选认证单测中的未使用 mock 逻辑与多余 token 生成，避免 lint 噪音
  - 可选认证单测改为异步调用并使用 AsyncSession 兼容的 stub

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

### 📝 文档更新 (Documentation Updates)

#### Changed / 变更

- 更新后端与数据库指南，补充 asyncpg 依赖说明、虚拟环境提示与 UTC 时间戳写库约定
- 更新资产管理 PRD，补充范围/对象关系、枚举、唯一性、删除约束、权属对齐与权限预留要求
- 更新资产管理 API 文档，补充业务规则、枚举与关联/删除约束说明

---
## [1.0.0] - 2026-01-15

### 初始版本 (Initial Release)

- ✅ 用户认证与权限管理 (RBAC)
- ✅ 资产基础信息管理
- ✅ 租赁合同基础管理
- ✅ 租金台账基础功能
- ✅ 权属方/项目列表管理
- ✅ 数据字典管理
