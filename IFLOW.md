# 土地物业资产管理系统 - iFlow上下文

## 项目概述

这是一个专业的土地物业资产管理系统，专为资产管理经理设计的个人工作助手工具。系统提供完整的资产档案管理、出租率统计、财务分析、智能PDF合同导入等功能。

### 核心特性
- 完整资产管理：支持资产增删改查、历史记录追踪、附件管理等
- 智能出租率统计：实时计算和多维度分析
- 财务数据管理：收益、支出、净利润跟踪
- 统计分析：多维度数据统计和可视化
- 自动计算：出租率、净收益等自动计算
- 数据验证：完善的数据一致性验证
- 高性能：优化的数据库查询和API响应，支持缓存机制
- 智能PDF导入：支持扫描件PDF的OCR识别和合同信息自动提取
- 权限管理：基于RBAC的角色权限控制系统，支持多租户
- 组织架构：支持多层级组织架构管理
- 审计日志：完整的操作审计和安全日志
- 缓存优化：Redis缓存提升系统性能
- 数据备份：自动数据备份和恢复机制

### 技术栈
- **后端**: Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + UV包管理器
- **数据库**: SQLite（开发环境）/ PostgreSQL（生产环境）
- **缓存**: Redis（生产环境，开发环境使用内存缓存）
- **前端**: React 18 + TypeScript + Ant Design 5 + Vite
- **部署**: Docker + Nginx + Gunicorn
- **AI增强**: PaddleOCR（OCR识别）、spaCy（NLP文本处理，可选）

## 目录结构
```
zcgl/
├── backend/           # 后端服务
│   ├── src/           # 源代码
│   │   ├── api/       # API路由
│   │   ├── models/    # 数据模型
│   │   ├── schemas/   # 数据模式
│   │   ├── crud/      # 数据访问层
│   │   ├── services/  # 业务逻辑层
│   │   ├── utils/     # 工具函数
│   │   ├── core/      # 核心组件
│   │   ├── middleware/# 中间件
│   │   └── config/    # 配置文件
│   ├── tests/         # 测试代码
│   ├── scripts/       # 脚本工具
│   ├── alembic/       # 数据库迁移
│   ├── data/          # 数据文件
│   └── migrations/    # 数据库迁移脚本
├── frontend/          # 前端应用
│   ├── src/           # 源代码
│   │   ├── components/ # 组件
│   │   ├── pages/      # 页面
│   │   ├── routes/     # 路由
│   │   ├── services/   # 服务
│   │   ├── store/      # 状态管理
│   │   └── utils/      # 工具函数
│   └── public/        # 静态资源
├── docs/              # 文档
├── database/          # 数据库相关
├── deployment/        # 部署配置
├── config/            # 配置文件
├── scripts/           # 脚本工具
├── tools/             # 工具和实用程序
└── nginx/             # Nginx配置
```

## 核心功能模块

### 1. 资产管理
- 资产增删改查操作
- 详细的资产信息管理（包含权属方、物业信息、面积、租户、合同、财务等字段）
- 批量操作支持
- 资产历史记录追踪
- 资产附件管理（支持PDF文件上传和下载）
- 资产出租率自动计算
- 资产财务数据汇总
- 资产数据导入导出（Excel格式）

### 2. 统计分析
- 整体出租率统计
- 按分类的出租率分析（按业态、物业性质等维度）
- 面积汇总统计
- 财务数据汇总
- 多维度数据可视化
- 实时数据仪表板

### 3. 智能PDF合同导入
- 支持扫描件PDF的OCR识别
- 合同关键信息自动提取（合同编号、承租方、出租方、地址、租金、押金、期限等）
- 阶梯租金智能识别和处理
- 合同数据验证和匹配现有资产
- 支持大文件优化处理策略
- 多种OCR引擎支持（PaddleOCR为主，Tesseract为备选）

### 4. 权限管理（RBAC）
- 用户认证和授权（JWT Token）
- 角色权限管理
- 组织架构权限继承
- 动态权限控制
- 审计日志记录
- 密码安全策略
- 多租户支持

### 5. 组织架构管理
- 多层级组织架构
- 部门管理
- 用户组织归属
- 组织权限继承
- 组织架构可视化

### 6. 数据模型
资产模型包含以下主要字段分组：
- 基本信息：权属方、权属类别、项目名称、物业名称、物业地址等
- 面积信息：土地面积、实际房产面积、可出租面积、已出租面积等
- 租户信息：租户名称、租户类型、租户联系方式
- 合同信息：租赁合同编号、合同期限、租金等
- 财务信息：年收益、年支出、净收益
- 管理信息：管理责任人、经营模式、项目等

## 构建和运行

### 环境要求
- Python 3.12+
- Node.js 18+
- SQLite 3.x（开发环境）
- Docker（可选，用于部署）
- Redis（生产环境推荐）

### 后端启动
```bash
# 进入后端目录
cd backend

# 安装依赖（推荐使用uv）
uv sync

# 运行开发服务器
uv run python run_dev.py
```

### 前端启动
```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 运行开发服务器
npm run dev
```

### Docker启动
```bash
# 使用Docker Compose
docker-compose up -d
```

### 测试运行
```bash
# 后端测试
cd backend
uv run pytest

# 前端测试
cd frontend
npm run test
```

## API接口

### 资产管理
- `GET /api/v1/assets` - 获取资产列表
- `POST /api/v1/assets` - 创建资产
- `GET /api/v1/assets/{id}` - 获取资产详情
- `PUT /api/v1/assets/{id}` - 更新资产
- `DELETE /api/v1/assets/{id}` - 删除资产
- `GET /api/v1/assets/{id}/history` - 获取资产历史记录
- `GET /api/v1/assets/ownership-entities` - 获取权属方列表
- `GET /api/v1/assets/business-categories` - 获取业态类别列表
- `GET /api/v1/assets/usage-statuses` - 获取使用状态列表
- `GET /api/v1/assets/property-natures` - 获取物业性质列表
- `GET /api/v1/assets/ownership-statuses` - 获取确权状态列表
- `GET /api/v1/assets/statistics/summary` - 获取资产统计摘要

### 统计分析
- `GET /api/v1/statistics/basic` - 基础统计数据
- `GET /api/v1/statistics/summary` - 统计摘要
- `GET /api/v1/statistics/occupancy-rate/overall` - 整体出租率
- `GET /api/v1/statistics/occupancy-rate/by-category` - 分类出租率
- `GET /api/v1/statistics/area-summary` - 面积汇总
- `GET /api/v1/statistics/financial-summary` - 财务汇总

### PDF合同处理
- `POST /api/v1/pdf/upload_and_extract` - 上传并提取PDF合同信息
- `POST /api/v1/pdf/extract` - 从文本提取合同信息
- `POST /api/v1/pdf/confirm_and_save` - 确认并保存提取的数据

### 权限管理
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

### 组织架构
- `GET /api/v1/organizations` - 获取组织架构
- `POST /api/v1/organizations` - 创建组织
- `PUT /api/v1/organizations/{id}` - 更新组织
- `DELETE /api/v1/organizations/{id}` - 删除组织

### 健康检查
- `GET /health` - 系统健康状态
- `GET /` - API根路径

## 开发约定

### 后端开发
- 使用FastAPI框架
- SQLAlchemy 2.0 ORM进行数据库操作
- Pydantic v2进行数据验证
- 遵循RESTful API设计原则
- 使用Alembic进行数据库迁移
- 使用UV进行依赖管理
- 遵循PEP 8代码规范
- 使用类型提示
- 实现单元测试和集成测试

### 前端开发
- 使用React 18和TypeScript
- Ant Design 5组件库
- Vite构建工具
- 遵循组件化开发模式
- 使用ESLint和Prettier进行代码检查和格式化
- 实现单元测试和端到端测试

### 代码质量
- 后端使用pytest进行测试
- 前端使用Jest进行测试
- ESLint进行代码检查
- Black进行Python代码格式化
- 使用pre-commit钩子保证代码质量

## 部署和运维

### 生产环境部署
- 使用Docker容器化部署
- Nginx反向代理和负载均衡
- Gunicorn作为WSGI服务器
- PostgreSQL作为生产数据库
- Redis作为缓存服务器
- 配置环境变量和密钥管理

### 监控和日志
- 系统健康检查端点
- 操作审计日志
- 错误日志记录
- 性能监控指标
- API调用日志

### 数据备份和恢复
- 定期数据库备份
- 自动备份脚本
- 数据恢复流程
- 备份文件管理

### 安全考虑
- JWT Token认证
- 密码加密存储
- SQL注入防护
- XSS防护
- CSRF防护
- 安全头设置

## 重要文件位置

### 配置文件
- 后端依赖：`backend/pyproject.toml`
- 前端依赖：`frontend/package.json`
- 数据库配置：`backend/src/database.py`
- 环境变量：`backend/.env`

### 主要源文件
- 后端入口：`backend/src/main.py`
- 资产模型：`backend/src/models/asset.py`
- 资产API：`backend/src/api/v1/assets.py`
- 统计API：`backend/src/api/v1/statistics.py`
- PDF处理服务：`backend/src/services/pdf_import_service.py`
- 合同信息提取器：`backend/src/services/contract_extractor.py`
- 权限管理：`backend/src/models/rbac.py`

### 文档
- 用户文档：`docs/`目录下
- API文档：访问`/docs`或`/redoc`路径

## 系统访问

- 前端应用：http://localhost:5173
- API文档：http://localhost:8002/docs
- 健康检查：http://localhost:8002/health