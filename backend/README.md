# 土地物业资产管理系统 - 后端

专为资产管理经理设计的个人工作助手工具后端服务。

## 技术栈

- **Python**: 3.12+
- **框架**: FastAPI
- **ORM**: SQLAlchemy 2.0
- **数据验证**: Pydantic v2
- **数据库**: SQLite（开发环境，支持扩展到PostgreSQL生产环境）
- **缓存**: Redis（生产环境，开发环境使用内存缓存）
- **包管理**: uv
- **代码质量**: mypy + ruff
- **AI增强**: PaddleOCR（OCR识别）、spaCy（NLP文本处理，可选）

## 核心功能模块

### 1. 资产管理
- 资产增删改查操作
- 58个字段的详细资产信息管理
- 批量操作支持
- 资产历史记录追踪
- 资产出租率自动计算
- 资产财务数据汇总
- 资产数据导入导出（Excel格式）

### 2. 统计分析
- 整体出租率统计
- 按分类的出租率分析
- 面积汇总统计
- 财务数据汇总
- 多维度数据可视化

### 3. 智能PDF合同导入
- 支持扫描件PDF的OCR识别
- 合同关键信息自动提取（合同编号、承租方、出租方、地址、租金、押金、期限等）
- 阶梯租金智能识别和处理
- 合同数据验证和匹配现有资产
- 支持大文件优化处理策略

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

### 6. 数据备份和恢复
- 定期数据库备份
- 自动备份脚本
- 数据恢复流程
- 备份文件管理

## 开发环境设置

### 1. 安装uv包管理器

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 安装依赖

```bash
# 安装项目依赖
uv sync

# 安装开发依赖
uv sync --dev
```

### 3. 运行开发服务器

```bash
# 启动FastAPI开发服务器 (端口 8002)
uv run python run_dev.py

# 或者使用uvicorn直接启动
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8002
```

### 4. 代码质量检查

```bash
# 类型检查
uv run mypy src/

# 代码格式化和检查
uv run ruff check src/
uv run ruff format src/

# 运行测试
uv run pytest tests/ -v --cov=src/
```

## API文档

启动服务器后，访问以下地址查看API文档：

- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc

## 项目结构

```
backend/
├── src/                    # 源代码
│   ├── __init__.py
│   ├── main.py            # FastAPI应用入口
│   ├── database.py        # 数据库配置
│   ├── models/            # 数据库模型
│   │   ├── asset.py       # 资产模型
│   │   ├── rbac.py        # 权限管理模型
│   │   └── ...
│   ├── schemas/           # Pydantic模型
│   │   ├── asset.py       # 资产数据模式
│   │   ├── rbac.py        # 权限管理数据模式
│   │   └── ...
│   ├── api/               # API路由
│   │   ├── v1/            # API v1版本
│   │   │   ├── assets.py  # 资产API
│   │   │   ├── statistics.py # 统计API
│   │   │   ├── pdf.py     # PDF处理API
│   │   │   ├── rbac.py    # 权限管理API
│   │   │   └── ...
│   │   └── ...
│   ├── services/          # 业务逻辑
│   │   ├── enhanced_pdf_extractor.py # PDF处理服务
│   │   └── ...
│   ├── utils/             # 工具函数
│   ├── core/              # 核心组件
│   ├── middleware/        # 中间件
│   └── config/            # 配置文件
├── tests/                 # 测试代码
├── alembic/               # 数据库迁移
├── migrations/            # 数据库迁移脚本
├── scripts/               # 脚本工具
├── data/                  # 数据文件
├── pyproject.toml         # 项目配置
└── README.md
```

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

### 代码质量
- 后端使用pytest进行测试
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
- 数据库配置：`backend/src/database.py`
- 环境变量：`backend/.env`

### 主要源文件
- 后端入口：`backend/src/main.py`
- 资产模型：`backend/src/models/asset.py`
- 资产API：`backend/src/api/v1/assets.py`
- 统计API：`backend/src/api/v1/statistics.py`
- PDF处理服务：`backend/src/services/enhanced_pdf_extractor.py`
- 权限管理：`backend/src/models/rbac.py`

## 系统访问

- API文档：http://localhost:8002/docs
- 健康检查：http://localhost:8002/health