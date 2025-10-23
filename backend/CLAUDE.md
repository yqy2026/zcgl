[根目录](../../CLAUDE.md) > **backend**

# Backend 后端服务模块

## 变更记录 (Changelog)

### 2025-10-23 20:15:00 - 后端架构全面升级
- 🚀 新增：系统监控API模块 - 性能指标收集、健康检查、实时监控
- 🔧 新增：路由注册器系统 - 统一API管理、版本控制、中间件配置
- 🛡️ 新增：权限装饰器系统 - 细粒度权限控制、动态权限验证
- 📦 新增：API路径常量化 - 统一路径管理、避免硬编码
- 📈 新增：性能监控API - 路由性能追踪、用户体验指标
- 🎯 重构：API模块架构 - 从18个扩展到25个专业模块
- 🔍 新增：系统诊断API - 深度系统分析、瓶颈识别
- 🧪 优化：测试覆盖率 - 从15个增加到20+个测试文件
- 📊 增强：API文档完整性 - 所有模块完整OpenAPI规范

### 2025-10-23 10:45:44 - 模块架构初始化
- ✨ 新增：模块导航面包屑
- ✨ 新增：服务层架构文档
- ✨ 新增：API接口索引
- 📊 分析：25个API模块，40+核心服务
- 🔧 优化：依赖管理和开发配置

---

## 模块职责

Backend模块是地产资产管理系统的核心服务层，基于FastAPI框架构建，提供完整的RESTful API服务、业务逻辑处理、数据持久化和安全控制。

### 核心职责
- **API服务**: 25个专业API模块，覆盖资产、PDF、权限、监控、诊断等全业务场景
- **业务逻辑**: 40+核心服务，处理复杂业务规则、数据流转和性能监控
- **数据处理**: 58字段资产模型，PDF智能处理，Excel导入导出，实时数据分析
- **安全控制**: RBAC权限系统，装饰器权限控制，组织层级管理，审计日志
- **性能优化**: 缓存策略，异步处理，数据库优化，路由性能监控
- **系统监控**: 实时性能指标收集，健康检查，系统诊断，瓶颈识别

## 入口与启动

### 主入口文件
- **应用入口**: `src/main.py` - FastAPI应用实例和路由注册
- **开发启动**: `run_dev.py` - UVicorn开发服务器配置
- **配置管理**: `pyproject.toml` - UV包管理和依赖配置

### 启动命令
```bash
# 开发模式 (推荐)
uv run python run_dev.py            # 端口 8002，热重载

# 传统pip模式
python run_dev.py                   # 备用启动方式

# 健康检查
curl http://localhost:8002/api/v1/health
```

### 应用配置
- **端口**: 8002 (开发环境)
- **数据库**: SQLite (`./data/land_property.db`)
- **日志级别**: info (可配置)
- **CORS**: 开发环境允许所有来源

## 对外接口

### API模块概览

| API模块 | 路径前缀 | 端点数量 | 核心功能 | 状态 |
|---------|----------|----------|----------|------|
| **用户认证** | `/api/v1/auth` | 5 | JWT认证、登录登出、密码重置 | 🟢 完整 |
| **资产管理** | `/api/v1/assets` | 8 | CRUD操作、搜索过滤、批量操作 | 🟢 生产级 |
| **PDF导入** | `/api/v1/pdf_import` | 12 | 多引擎处理、AI识别、会话管理 | 🟢 企业级 |
| **权限管理** | `/api/v1/auth` | 10 | 动态权限、角色管理、组织架构 | 🟢 高级 |
| **数据分析** | `/api/v1/analytics` | 6 | 实时统计、图表数据、报表导出 | 🟢 丰富 |
| **系统监控** | `/api/v1/monitoring` | 8 | 性能监控、健康检查、指标收集 | 🟢 新增 |
| **系统管理** | `/api/v1/organization` | 8 | 组织架构、字典管理、系统配置 | 🟢 完整 |
| **租赁管理** | `/api/v1/rent_contract` | 7 | 租赁合同、台账管理、统计分析 | 🟢 业务完整 |
| **项目管理** | `/api/v1/project` | 5 | 项目信息、层级关系、统计分析 | 🟢 标准化 |
| **权属方管理** | `/api/v1/ownership` | 6 | 权属方信息、关联关系、统计分析 | 🟢 规范化 |
| **Excel处理** | `/api/v1/excel` | 6 | Excel导入导出、数据转换、模板管理 | 🟢 完整 |
| **历史记录** | `/api/v1/history` | 4 | 变更追踪、审计日志、版本管理 | 🟢 审计完整 |
| **系统设置** | `/api/v1/system_settings` | 5 | 系统配置、参数管理、环境设置 | 🟢 配置化 |
| **字典管理** | `/api/v1/dictionaries` | 6 | 数据字典、枚举值、系统配置 | 🟢 完整 |
| **备份恢复** | `/api/v1/backup` | 4 | 数据备份、恢复、迁移 | 🟢 安全 |
| **导出服务** | `/api/v1/export` | 5 | 多格式导出、报表生成 | 🟢 完整 |
| **自定义字段** | `/api/v1/custom_fields` | 4 | 动态字段配置、业务扩展 | 🟢 灵活 |
| **枚举字段** | `/api/v1/enum_field` | 3 | 枚举管理、选项配置 | 🟢 规范 |
| **中文OCR** | `/api/v1/chinese_ocr` | 4 | 中文识别、文字提取 | 🟢 智能化 |
| **系统字典** | `/api/v1/system_dictionaries` | 5 | 系统级字典管理 | 🟢 完整 |
| **任务管理** | `/api/v1/tasks` | 6 | 异步任务、任务队列 | 🟢 高效 |
| **占用率分析** | `/api/v1/occupancy` | 4 | 占用率统计、趋势分析 | 🟢 分析 |
| **性能分析** | `/api/v1/performance` | 5 | 系统性能、瓶颈分析 | 🟢 优化 |
| **统计服务** | `/api/v1/statistics` | 7 | 综合统计、报表服务 | 🟢 丰富 |
| **系统管理** | `/api/v1/admin` | 6 | 系统维护、数据库管理 | 🟢 管理 |

### 核心API端点

#### 资产管理API
```python
GET    /api/v1/assets/              # 资产列表 (支持分页、搜索、过滤)
POST   /api/v1/assets/              # 创建新资产
GET    /api/v1/assets/{id}          # 获取资产详情
PUT    /api/v1/assets/{id}          # 更新资产信息
DELETE /api/v1/assets/{id}          # 删除资产
POST   /api/v1/assets/batch         # 批量操作
GET    /api/v1/assets/search        # 高级搜索
POST   /api/v1/assets/export        # 导出数据
```

#### PDF智能导入API
```python
POST   /api/v1/pdf_import/upload    # 上传PDF文件
POST   /api/v1/pdf_import/process   # 处理PDF (多引擎)
GET    /api/v1/pdf_import/session/{id}  # 获取会话状态
POST   /api/v1/pdf_import/validate  # 验证提取数据
POST   /api/v1/pdf_import/confirm   # 确认导入数据库
GET    /api/v1/pdf_import/progress  # 获取处理进度
```

#### 权限管理API
```python
POST   /api/v1/auth/login           # 用户登录
POST   /api/v1/auth/logout          # 用户登出
GET    /api/v1/auth/me              # 获取当前用户信息
GET    /api/v1/rbac/permissions     # 获取权限列表
POST   /api/v1/rbac/assign          # 分配权限
GET    /api/v1/rbac/check           # 权限检查
```

#### 系统监控API
```python
GET    /api/v1/monitoring/health                    # 系统健康检查
GET    /api/v1/monitoring/metrics                   # 获取系统指标
POST   /api/v1/monitoring/performance-report        # 上报性能数据
GET    /api/v1/monitoring/route-performance         # 路由性能统计
GET    /api/v1/monitoring/user-experience           # 用户体验指标
POST   /api/v1/monitoring/error-report              # 错误报告
GET    /api/v1/monitoring/system-diagnostics        # 系统诊断
GET    /api/v1/monitoring/cache-status              # 缓存状态
```

#### 路由注册器API
```python
GET    /api/v1/admin/route-registry                 # 获取路由注册信息
POST   /api/v1/admin/register-route                # 动态注册路由
DELETE /api/v1/admin/unregister-route              # 注销路由
GET    /api/v1/admin/route-metrics                 # 路由性能指标
GET    /api/v1/admin/api-versions                  # API版本信息
```

### API文档
- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc
- **OpenAPI JSON**: http://localhost:8002/openapi.json

## 关键依赖与配置

### 核心依赖 (pyproject.toml)
```toml
[dependencies]
# Web框架
fastapi=">=0.104.0"
uvicorn[standard]=">=0.24.0"

# 数据库和ORM
sqlalchemy=">=2.0.0"
alembic=">=1.12.0"

# 数据验证和序列化
pydantic=">=2.5.0"
pydantic-settings=">=2.0.0"

# PDF处理和AI
markitdown=">=0.1.0"
pdfplumber="==0.11.0"
spacy=">=3.6.0"
jieba=">=0.42.1"
paddleocr=">=3.2.0"

# 数据处理
pandas=">=2.0.0"
openpyxl=">=3.1.0"
polars=">=0.20.0"

# 缓存和会话
redis=">=5.0.0"
aioredis=">=2.0.0"

# 安全认证
python-jose[cryptography]=">=3.3.0"
passlib[bcrypt]=">=1.7.4"
```

### 开发依赖
```toml
[project.optional-dependencies.dev]
pytest=">=7.4.0"
pytest-asyncio=">=0.21.0"
mypy=">=1.7.0"
ruff=">=0.1.6"
pytest-cov=">=4.1.0"
```

### 环境配置
```bash
# 开发模式 (禁用认证)
DEV_MODE=true

# 数据库连接
DATABASE_URL=sqlite:///./data/land_property.db

# Redis缓存 (可选)
REDIS_URL=redis://localhost:6379/0

# API配置
API_TITLE=土地物业资产管理系统
CORS_ORIGINS=["*"]
```

## 数据模型

### 核心数据模型

| 模型 | 表名 | 字段数 | 主要功能 | 关联关系 |
|------|------|--------|----------|----------|
| **Asset** | `assets` | 58 | 58字段资产信息 | 1:N AssetHistory |
| **AssetHistory** | `asset_history` | 15 | 资产变更历史 | N:1 Asset |
| **RentContract** | `rent_contracts` | 20 | 租赁合同管理 | 1:N Asset |
| **Project** | `projects` | 12 | 项目层级管理 | 1:N Asset |
| **Ownership** | `ownerships` | 15 | 权属方信息 | 1:N Asset |
| **User** | `users` | 12 | 用户信息 | N:M Permission |
| **Role** | `roles` | 8 | 角色定义 | N:M Permission |
| **Permission** | `permissions` | 10 | 权限定义 | N:M User, N:M Role |
| **Organization** | `organizations` | 10 | 组织层级架构 | 1:N User |

### Asset模型核心字段 (58字段总计)
```python
# 基本信息字段 (8个)
ownership_entity          # 权属方
ownership_category        # 权属类别
project_name             # 项目名称
property_name            # 物业名称
address                  # 物业地址
ownership_status         # 确权状态
property_nature          # 物业性质
usage_status             # 使用状态

# 面积相关字段 (8个)
land_area                # 土地面积
actual_property_area     # 实际房产面积
rentable_area            # 可出租面积
rented_area              # 已出租面积
unrented_area            # 未出租面积 (自动计算)
occupancy_rate           # 出租率 (自动计算)
non_commercial_area      # 非经营物业面积
include_in_occupancy_rate # 是否计入出租率统计

# 财务相关字段 (12个)
annual_income            # 年收入
annual_expense           # 年支出
net_income               # 净收入 (自动计算)
rent_price_per_sqm       # 每平米租金
management_fee_per_sqm   # 每平米管理费
property_tax             # 房产税
insurance_fee            # 保险费
maintenance_fee          # 维修费
other_fees               # 其他费用
rent_income_tax          # 租金收入税
net_rental_income        # 净租金收入
total_cost               # 总成本

# 合同相关字段 (10个)
lease_contract_number    # 租赁合同编号
contract_start_date      # 合同开始日期
contract_end_date        # 合同结束日期
contract_term            # 合同期限
rent_payment_method      # 租金支付方式
deposit_amount           # 押金金额
rent_increase_clause     # 租金增长条款
termination_clause       # 终止条款
renewal_option           # 续租选择权
special_terms            # 特殊条款

# 自动计算字段
@property
def unrented_area(self):
    return (self.rentable_area or 0) - (self.rented_area or 0)

@property
def occupancy_rate(self):
    if self.rentable_area and self.rentable_area > 0:
        return (self.rented_area / self.rentable_area) * 100
    return 0.0

@property
def net_income(self):
    return (self.annual_income or 0) - (self.annual_expense or 0)
```

### 数据库连接
```python
# 测试数据库连接
uv run python -c "from src.database import engine; print('DB OK')"

# 测试模型导入
uv run python -c "from src.models.asset import Asset; print('Models OK')"
```

## 测试与质量

### 测试套件概览
- **测试文件数量**: 20+个测试文件
- **测试覆盖**: API端点、服务层、数据模型、工具函数、监控系统、路由注册器
- **测试框架**: pytest + pytest-asyncio + pytest-cov
- **新增测试**: 监控API测试、权限装饰器测试、性能监控测试

### 主要测试文件
```
tests/
├── test_main.py                 # 主应用测试
├── test_api.py                  # API端点测试
├── test_advanced_search.py      # 高级搜索测试
├── test_excel_import.py         # Excel导入测试
├── test_excel_export.py         # Excel导出测试
├── test_history_tracker.py      # 历史追踪测试
├── test_statistics.py           # 统计分析测试
├── test_backup.py               # 备份恢复测试
├── test_occupancy_calculator.py # 出租率计算测试
├── test_organization_management.py # 组织管理测试
├── test_security.py             # 安全测试
└── test_database.py             # 数据库测试
```

### 测试命令
```bash
# 运行所有测试
uv run python -m pytest tests/ -v

# 运行特定测试文件
uv run python -m pytest tests/test_api.py -v

# 运行测试并生成覆盖率报告
uv run python -m pytest tests/ --cov=src

# 停在第一个失败
uv run python -m pytest tests/ -x

# 只运行上次失败的测试
uv run python -m pytest tests/ --lf
```

### 代码质量工具
```bash
# 代码检查和格式化
uv run ruff check src/           # 静态代码分析
uv run ruff format src/          # 代码格式化
uv run mypy src/                 # 类型检查

# 安全检查
uv run bandit -r src/            # 安全漏洞扫描
uv run safety check              # 依赖安全检查
```

## 常见问题 (FAQ)

### Q: 如何启动开发服务器？
A: 推荐使用 `uv run python run_dev.py`，支持热重载和调试。

### Q: 数据库连接失败怎么办？
A: 检查SQLite文件路径，确保 `backend/data/` 目录存在并有写权限。

### Q: PDF导入处理速度慢？
A: 系统采用多引擎处理策略：PyMuPDF → pdfplumber → OCR，确保准确性的同时可能影响速度。

### Q: 权限验证不生效？
A: 检查 `DEV_MODE` 环境变量，开发模式下可能禁用了认证。

### Q: 如何添加新的API端点？
A: 在 `src/api/v1/` 目录创建新模块，然后在 `__init__.py` 中注册路由。

### Q: 如何处理大文件上传？
A: 系统默认限制50MB，可在配置中调整，建议使用分块上传。

## 相关文件清单

### 核心文件
- `src/main.py` - FastAPI应用主入口
- `run_dev.py` - 开发服务器启动脚本
- `pyproject.toml` - 项目配置和依赖管理
- `alembic.ini` - 数据库迁移配置

### API层文件
- `src/api/v1/__init__.py` - API路由注册
- `src/api/v1/assets.py` - 资产管理API
- `src/api/v1/pdf_import_unified.py` - PDF导入API (统一版本)
- `src/api/v1/auth.py` - 认证授权API
- `src/api/v1/analytics.py` - 数据分析API
- `src/api/v1/monitoring.py` - 系统监控API (新增)
- `src/api/v1/performance.py` - 性能分析API (新增)
- `src/api/v1/admin.py` - 系统管理API (增强)

### 核心模块文件
- `src/core/router_registry.py` - 路由注册器 (新增)
- `src/core/config.py` - 配置管理器
- `src/core/exception_handler.py` - 异常处理器
- `src/core/security.py` - 安全核心模块
- `src/core/performance.py` - 性能监控核心
- `src/core/logging_security.py` - 日志安全模块

### 装饰器文件
- `src/decorators/permission.py` - 权限装饰器 (新增)

### 常量文件
- `src/constants/api_paths.py` - API路径常量 (新增)

### 服务层文件
- `src/services/pdf_import_service.py` - PDF导入核心服务
- `src/services/rbac_service.py` - RBAC权限服务
- `src/services/asset_calculator.py` - 资产计算服务
- `src/services/excel_import.py` - Excel导入服务

### 数据层文件
- `src/models/asset.py` - 资产数据模型
- `src/models/rbac.py` - 权限数据模型
- `src/database.py` - 数据库连接配置
- `src/crud/` - 数据访问层

### 测试文件
- `tests/test_api.py` - API测试
- `tests/test_excel_import.py` - 导入功能测试
- `tests/test_security.py` - 安全功能测试

### 配置文件
- `.env.example` - 环境变量模板
- `alembic/` - 数据库迁移脚本
- `logs/` - 应用日志目录

---

**模块状态**: 🟢 生产就绪，API完整，测试覆盖良好。

**最后更新**: 2025-10-23 20:15:00 (后端架构全面升级)