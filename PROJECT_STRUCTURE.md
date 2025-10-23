# 项目结构说明

## 📁 目录结构概览

```
zcgl/                                    # 项目根目录
├── CLAUDE.md                           # 项目总体架构文档
├── README.md                           # 项目说明文档
├── .gitignore                          # Git忽略文件配置
├── .env.example                        # 环境变量示例文件
├── PROJECT_STRUCTURE.md               # 项目结构说明（本文件）
│
├── backend/                            # 后端服务模块
│   ├── CLAUDE.md                      # 后端模块架构文档
│   ├── pyproject.toml                 # UV包管理配置
│   ├── run_dev.py                     # 开发服务器启动脚本
│   ├── src/                           # 源代码目录
│   │   ├── main.py                    # FastAPI应用入口
│   │   ├── api/                       # API路由层
│   │   │   └── v1/                    # API v1版本
│   │   │       ├── assets.py          # 资产管理API
│   │   │       ├── pdf_import.py      # PDF导入API
│   │   │       ├── rbac.py            # 权限管理API
│   │   │       └── ...                # 其他API模块
│   │   ├── services/                  # 业务服务层
│   │   │   ├── asset_service.py       # 资产业务服务
│   │   │   ├── pdf_service.py         # PDF处理服务
│   │   │   ├── rbac_service.py        # 权限业务服务
│   │   │   └── ...                    # 其他服务模块
│   │   ├── models/                    # 数据模型层
│   │   │   ├── asset.py               # 资产数据模型
│   │   │   ├── user.py                # 用户数据模型
│   │   │   ├── rbac.py                # 权限数据模型
│   │   │   └── ...                    # 其他数据模型
│   │   ├── crud/                      # 数据访问层
│   │   │   ├── base.py                # 基础CRUD操作
│   │   │   ├── asset.py               # 资产CRUD操作
│   │   │   └── ...                    # 其他CRUD操作
│   │   ├── schemas/                   # 数据验证层
│   │   │   ├── asset.py               # 资产数据验证
│   │   │   ├── user.py                # 用户数据验证
│   │   │   └── ...                    # 其他数据验证
│   │   ├── middleware/                # 中间件层
│   │   │   ├── auth.py                # 认证中间件
│   │   │   ├── rbac.py                # 权限中间件
│   │   │   └── ...                    # 其他中间件
│   │   ├── database.py                # 数据库连接配置
│   │   ├── dependencies.py            # 依赖注入配置
│   │   └── utils/                     # 工具函数
│   │       ├── security.py            # 安全工具函数
│   │       ├── pdf_processor.py       # PDF处理工具
│   │       └── ...                    # 其他工具函数
│   ├── tests/                         # 测试代码
│   │   ├── conftest.py                # pytest配置
│   │   ├── test_api/                  # API测试
│   │   ├── test_services/             # 服务测试
│   │   └── test_models/               # 模型测试
│   ├── data/                          # 数据文件目录
│   │   └── land_property.db           # SQLite数据库文件
│   └── logs/                          # 日志文件目录
│
├── frontend/                          # 前端应用模块
│   ├── CLAUDE.md                      # 前端模块架构文档
│   ├── package.json                   # npm包管理配置
│   ├── vite.config.ts                 # Vite构建配置
│   ├── tsconfig.json                  # TypeScript配置
│   ├── jest.config.js                 # Jest测试配置
│   ├── .env.example                   # 前端环境变量示例
│   ├── public/                        # 静态资源目录
│   │   ├── index.html                 # HTML模板
│   │   ├── favicon.ico                # 网站图标
│   │   └── ...                        # 其他静态资源
│   ├── src/                           # 源代码目录
│   │   ├── main.tsx                   # React应用入口
│   │   ├── App.tsx                    # 根组件
│   │   ├── components/                # 组件库
│   │   │   ├── Asset/                 # 资产相关组件
│   │   │   │   ├── AssetForm.tsx      # 资产表单组件
│   │   │   │   ├── AssetList.tsx      # 资产列表组件
│   │   │   │   ├── AssetDetail.tsx    # 资产详情组件
│   │   │   │   └── __tests__/         # 组件测试
│   │   │   ├── Layout/                # 布局组件
│   │   │   │   ├── Header.tsx         # 头部组件
│   │   │   │   ├── Sidebar.tsx        # 侧边栏组件
│   │   │   │   └── Footer.tsx         # 底部组件
│   │   │   ├── Charts/                # 图表组件
│   │   │   │   ├── BarChart.tsx       # 柱状图组件
│   │   │   │   ├── PieChart.tsx       # 饼图组件
│   │   │   │   └── LineChart.tsx      # 折线图组件
│   │   │   ├── ErrorHandling/         # 错误处理组件
│   │   │   │   ├── ErrorBoundary.tsx  # 错误边界组件
│   │   │   │   └── ErrorPage.tsx      # 错误页面组件
│   │   │   └── ...                    # 其他组件
│   │   ├── pages/                     # 页面组件
│   │   │   ├── Dashboard/             # 仪表板页面
│   │   │   ├── Assets/                # 资产管理页面
│   │   │   ├── Reports/               # 报表页面
│   │   │   ├── Settings/              # 设置页面
│   │   │   └── ...                    # 其他页面
│   │   ├── services/                  # API服务层
│   │   │   ├── api.ts                 # 基础API客户端
│   │   │   ├── assetService.ts        # 资产API服务
│   │   │   ├── authService.ts         # 认证API服务
│   │   │   └── ...                    # 其他API服务
│   │   ├── hooks/                     # 自定义Hook
│   │   │   ├── useAuth.ts             # 认证Hook
│   │   │   ├── useAssets.ts           # 资产Hook
│   │   │   └── ...                    # 其他Hook
│   │   ├── store/                     # 状态管理
│   │   │   ├── authStore.ts           # 认证状态
│   │   │   ├── assetStore.ts          # 资产状态
│   │   │   └── ...                    # 其他状态
│   │   ├── types/                     # 类型定义
│   │   │   ├── asset.ts               # 资产类型
│   │   │   ├── user.ts                # 用户类型
│   │   │   └── ...                    # 其他类型
│   │   ├── utils/                     # 工具函数
│   │   │   ├── format.ts              # 格式化工具
│   │   │   ├── validation.ts          # 验证工具
│   │   │   └── ...                    # 其他工具
│   │   ├── styles/                    # 样式文件
│   │   │   ├── globals.css            # 全局样式
│   │   │   ├── variables.css          # CSS变量
│   │   │   └── components.css         # 组件样式
│   │   └── test/                      # 测试配置
│   │       ├── setup.ts               # 测试设置
│   │       └── __mocks__/             # Mock文件
│   ├── dist/                          # 构建输出目录
│   └── node_modules/                  # npm依赖包
│
├── database/                          # 数据库模块
│   ├── CLAUDE.md                      # 数据库模块文档
│   ├── init.sql                       # 数据库初始化脚本
│   ├── migrations/                    # 数据库迁移脚本
│   │   └── versions/                  # 迁移版本文件
│   ├── land_property.db               # SQLite数据库文件
│   └── backups/                       # 数据库备份目录
│
├── nginx/                             # Nginx配置模块
│   ├── CLAUDE.md                      # Nginx模块文档
│   ├── nginx.conf                     # Nginx主配置
│   ├── sites-available/               # 站点配置目录
│   │   └── default.conf               # 默认站点配置
│   └── ssl/                           # SSL证书目录
│
├── tools/                             # 工具集模块
│   ├── CLAUDE.md                      # 工具集模块文档
│   ├── scripts/                       # 脚本工具
│   │   ├── backup.sh                  # 数据备份脚本
│   │   ├── deploy.sh                  # 部署脚本
│   │   └── health-check.sh            # 健康检查脚本
│   ├── pdf-samples/                   # PDF样本文件
│   └── utils/                         # 工具函数
│
├── docs/                              # 文档目录
│   ├── api/                           # API文档
│   ├── deployment/                    # 部署文档
│   ├── development/                   # 开发文档
│   └── user-guide/                    # 用户指南
│
├── logs/                              # 日志目录
│   ├── startup_*.log                  # 启动日志
│   ├── error_*.log                    # 错误日志
│   └── access_*.log                   # 访问日志
│
├── .claude/                           # Claude AI工具配置
│   ├── index.json                     # 工具索引配置
│   ├── commands/                      # 自定义命令
│   └── templates/                     # 文档模板
│
├── .spec-workflow/                    # 规范工作流配置
│   ├── agents/                        # AI代理配置
│   ├── commands/                      # 工作流命令
│   └── templates/                     # 工作流模板
│
└── docker/                            # Docker配置（可选）
    ├── Dockerfile.backend             # 后端Docker文件
    ├── Dockerfile.frontend            # 前端Docker文件
    └── docker-compose.yml             # Docker Compose配置
```

## 🏗️ 架构层次说明

### 后端架构（FastAPI）
- **API层** (`/api/v1/`): RESTful API端点，路由定义
- **服务层** (`/services/`): 业务逻辑处理，服务编排
- **数据层** (`/models/`, `/crud/`): 数据模型定义，数据库操作
- **中间件层** (`/middleware/`): 认证、权限、日志等横切关注点

### 前端架构（React + TypeScript）
- **组件层** (`/components/`): 可复用UI组件
- **页面层** (`/pages/`): 路由级页面组件
- **服务层** (`/services/`): API调用封装
- **状态层** (`/store/`): 全局状态管理
- **工具层** (`/utils/`): 通用工具函数

### 数据层（SQLite + Alembic）
- **模型定义**: SQLAlchemy ORM模型
- **迁移管理**: Alembic数据库版本控制
- **备份策略**: 定期数据备份和恢复

## 🚀 快速导航

- **项目总览**: [CLAUDE.md](./CLAUDE.md)
- **后端文档**: [backend/CLAUDE.md](./backend/CLAUDE.md)
- **前端文档**: [frontend/CLAUDE.md](./frontend/CLAUDE.md)
- **数据库文档**: [database/CLAUDE.md](./database/CLAUDE.md)
- **部署文档**: [nginx/CLAUDE.md](./nginx/CLAUDE.md)

## 📋 开发规范

### 命名约定
- **文件名**: kebab-case (`asset-form.tsx`)
- **目录名**: kebab-case (`asset-management/`)
- **组件名**: PascalCase (`AssetForm`)
- **函数名**: camelCase (`getUserAssets`)
- **常量名**: UPPER_SNAKE_CASE (`API_BASE_URL`)

### 提交规范
```
type(scope): description

[optional body]

[optional footer]
```

类型说明：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

### 分支策略
- `main`: 生产环境分支
- `develop`: 开发环境分支
- `feature/*`: 功能开发分支
- `hotfix/*`: 紧急修复分支
- `release/*`: 发布准备分支

## 🔧 开发工具配置

### 代码质量工具
- **后端**: ruff (代码检查), mypy (类型检查), pytest (测试)
- **前端**: ESLint (代码检查), Prettier (代码格式), Jest (测试)

### 构建工具
- **后端**: UV (包管理), FastAPI (Web框架)
- **前端**: Vite (构建工具), TypeScript (类型系统)

### 版本控制
- **Git**: 分布式版本控制
- **GitHub**: 代码托管和协作
- **Conventional Commits**: 提交信息规范

---

最后更新：2025-10-23
维护者：项目开发团队