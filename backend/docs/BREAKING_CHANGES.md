# Breaking Changes 记录

本文档记录所有向后不兼容的API变更，帮助开发者升级代码。

---

## 2026-01-17 - PR #23 安全修复

### 1. 数据库健康检查API变更

**影响范围**: 所有使用 `DatabaseManager.run_health_check()` 的代码

**变更内容**:
- `run_health_check()` 方法不再抛出异常
- 调用者必须检查返回值中的 `healthy` 字段

**迁移前 (旧代码)**:
```python
from src.database import get_database_manager

mgr = get_database_manager()

try:
    health_status = mgr.run_health_check()
    # 健康检查成功，继续处理
    process_request()
except Exception as e:
    # 健康检查失败，发送警报
    send_alert(f"Database unhealthy: {e}")
    return error_response()
```

**迁移后 (新代码)**:
```python
from src.database import get_database_manager

mgr = get_database_manager()

health_status = mgr.run_health_check()

if health_status["healthy"]:
    # 健康检查成功，继续处理
    process_request()
else:
    # 健康检查失败，检查具体错误
    checks = health_status.get("checks", {})
    error_details = checks.get("connection_test", {}).get("error_details", "Unknown error")
    send_alert(f"Database unhealthy: {error_details}")
    return error_response()
```

**返回值结构**:
```python
{
    "healthy": bool,          # True = 健康, False = 不健康
    "checks": {
        "basic_connection": {
            "status": "healthy" | "degraded" | "failed",
            "response_time_ms": float,
            "error": str,        # 仅在失败时存在
            "error_details": str # 仅在失败时存在
        },
        # ... 其他检查项
    },
    "metrics": {
        "active_connections": int,
        "total_queries": int,
        "avg_response_time": float
    },
    "timestamp": str
}
```

**升级检查清单**:
- [ ] 搜索所有调用 `run_health_check()` 的代码
- [ ] 将 `try-except` 模式改为检查 `healthy` 字段
- [ ] 更新错误处理逻辑使用 `checks` 字段中的详细信息
- [ ] 测试健康检查失败场景

---

### 2. 生产环境DATABASE_URL验证

**影响范围**: 生产环境部署配置

**变更内容**:
- 生产环境 (`ENVIRONMENT=production`) 必须使用 PostgreSQL
- SQLite URL 在生产环境将被拒绝，应用将启动失败
- 强制验证 `DATABASE_URL` 格式和有效性

**错误消息示例**:
```
ValueError: 生产环境必须使用PostgreSQL数据库！
当前配置: SQLite
请配置DATABASE_URL为PostgreSQL连接字符串
帮助文档: docs/POSTGRESQL_MIGRATION.md
```

**正确配置 (生产环境)**:
```bash
# .env
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@host:5432/database
```

**替代配置 (使用单独环境变量)**:
```bash
# .env
ENVIRONMENT=production
PGHOST=db.example.com
PGPORT=5432
PGUSER=zcgl_user
PGPASSWORD=secure_password
PGDATABASE=zcgl_prod
```

**开发环境配置**:
```bash
# .env (development)
ENVIRONMENT=development
# 可选: 不设置 DATABASE_URL 将使用默认 SQLite
DATABASE_URL=sqlite:///./data/land_property.db
```

**升级检查清单**:
- [ ] 检查所有生产环境配置文件
- [ ] 确认生产环境设置 `DATABASE_URL` 为 PostgreSQL
- [ ] 移除生产环境中的 SQLite 配置
- [ ] 测试生产环境启动流程
- [ ] 更新部署文档和CI/CD配置

---

## 升级工具

### 自动检测工具

运行以下命令检测可能的Breaking Changes使用:

```bash
# 检测 run_health_check() 的使用
cd backend
grep -r "run_health_check" --include="*.py" src/ tests/

# 检测 try-except 包装的健康检查
grep -r "try:.*run_health_check" --include="*.py" src/ tests/
```

### 测试验证

```bash
# 运行相关测试
pytest tests/integration/test_postgresql_migration.py::TestPostgreSQLHealthCheck -v

# 验证生产环境配置拒绝SQLite
ENVIRONMENT=production DATABASE_URL=sqlite:///test.db python -c "from src.database import get_database_url"
```

---

## 回滚方案

如果升级后遇到问题需要回滚:

### 临时回滚健康检查API (不推荐)

```python
# 创建包装函数模拟旧行为
def run_health_check_legacy(mgr):
    try:
        result = mgr.run_health_check()
        if not result["healthy"]:
            raise Exception(f"Database unhealthy: {result['checks']}")
        return result
    except Exception as e:
        raise e
```

**警告**: 这只是临时方案，请尽快迁移到新API。

---

## 需要帮助?

- 📧 技术支持: 提交 GitHub Issue
- 📖 文档: `docs/enhanced_database_guide.md`
- 🔍 示例代码: `tests/integration/test_postgresql_migration.py`
