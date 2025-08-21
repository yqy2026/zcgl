# 土地物业资产管理系统 - 后端

专为资产管理经理设计的个人工作助手工具后端服务。

## 技术栈

- **Python**: 3.12+
- **框架**: FastAPI
- **数据库**: SQLAlchemy + SQLite/PostgreSQL
- **数据处理**: Polars
- **包管理**: uv
- **代码质量**: mypy + ruff

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
# 启动FastAPI开发服务器
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
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

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
backend/
├── src/                    # 源代码
│   ├── __init__.py
│   ├── main.py            # FastAPI应用入口
│   ├── models/            # 数据库模型
│   ├── schemas/           # Pydantic模型
│   ├── api/               # API路由
│   ├── services/          # 业务逻辑
│   └── utils/             # 工具函数
├── tests/                 # 测试代码
├── alembic/               # 数据库迁移
├── pyproject.toml         # 项目配置
└── README.md
```