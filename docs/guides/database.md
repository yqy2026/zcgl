# 数据库配置与初始化指南

## 📋 Purpose
本文档详细说明土地物业管理系统的数据库配置、初始化、迁移和运维操作。

## 🎯 Scope
- 数据库配置和连接
- 数据库初始化步骤
- Alembic 迁移使用
- 数据库备份和恢复
- 数据库性能优化
- 常见问题排除

## ✅ Status
**当前状态**: Active (2026-01-27 更新)
**适用版本**: v2.0.0
**支持数据库**: PostgreSQL (开发/测试/生产)。SQLite 已移除。

---

> ⚠️ SQLite 已移除。本文档以 PostgreSQL 为准。

## 🗄️ 数据库架构概述

### 数据库选择建议

| 数据库 | 开发环境 | 测试环境 | 生产环境 | 说明 |
|--------|----------|----------|----------|------|
| **PostgreSQL** | ✅ 推荐 | ✅ 推荐 | ✅ 强烈推荐 | 功能强大，支持高并发，数据一致性好 |

### 核心数据模型

```
资产管理系统 (zcgl)
├── users              # 用户表
├── roles              # 角色表
├── permissions        # 权限表
├── organizations      # 组织架构表
├── assets             # 资产表 (58字段)
├── ownerships         # 权属关系表
├── rent_contracts     # 租赁合同表
├── rent_schedule      # 租金计划表
├── dictionaries       # 数据字典表
├── audit_logs         # 审计日志表
└── tasks              # 任务表
```

---

## 🚀 快速开始

### 开发环境 (PostgreSQL)

```bash
# 1. 确保环境变量配置正确
cd backend
export DATABASE_URL="postgresql://postgres:your_password@localhost:5432/zcgl_db"
export TEST_DATABASE_URL="postgresql://postgres:your_password@localhost:5432/zcgl_test"

# 2. 创建数据库（如未创建）
python scripts/setup_postgresql.py

# 3. 运行迁移
alembic upgrade head

# 4. 验证当前版本
alembic current
```

### 生产环境 (PostgreSQL)

```bash
# 1. 安装 PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# 2. 创建数据库和用户
sudo -u postgres psql
CREATE DATABASE zcgl_prod;
CREATE USER zcgl_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE zcgl_prod TO zcgl_user;
\q

# 3. 配置环境变量
export DATABASE_URL="postgresql://zcgl_user:secure_password@localhost:5432/zcgl_prod"

# 4. 运行迁移
alembic upgrade head

# 5. 验证连接
python -c "from src.database import get_database_status; print(get_database_status())"
```

---

## 📦 数据库配置详解

### 配置文件位置
- **环境变量**: `backend/.env`
- **Alembic配置**: `backend/alembic.ini`
- **数据库模块**: `backend/src/database.py`
- **模型定义**: `backend/src/models/`

### PostgreSQL 配置

```bash
# backend/.env
DATABASE_URL=postgresql://zcgl_user:password@localhost:5432/zcgl_db
TEST_DATABASE_URL=postgresql://zcgl_user:password@localhost:5432/zcgl_test

# 连接池配置
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
DATABASE_POOL_PRE_PING=true
```

**连接池说明**:
- `pool_size`: 连接池大小（默认 20）
- `max_overflow`: 最大溢出连接数（默认 30）
- `pool_timeout`: 获取连接超时时间（秒）
- `pool_recycle`: 连接回收时间（秒），防止连接过期
- `pool_pre_ping`: 连接前测试可用性

## 🔄 Alembic 数据库迁移

### 迁移目录结构
```
backend/
├── alembic.ini                 # Alembic 配置文件
├── alembic/                    # 迁移脚本目录
│   ├── env.py                  # 迁移环境配置
│   ├── script.py.mako          # 迁移脚本模板
│   └── versions/               # 版本迁移文件
│       ├── e4c9e4968dd7_initial_schema_creation.py
│       ├── 20250118_add_user_id_to_extraction_feedback.py
│       ├── 20250118_add_property_cert_tables.py
│       ├── 20250120_add_security_events_table.py
│       ├── ca5d6adb0012_add_management_entity_to_asset.py
│       └── 8f37856a3aae_standardize_contract_status_to_enum.py
└── migrations/                 # 额外迁移工具
    └── migration/
```

### 常用迁移命令

```bash
# 1. 初始化 Alembic（首次使用）
alembic init alembic

# 2. 创建新迁移（自动生成）
alembic revision --autogenerate -m "描述性消息"

# 3. 创建新迁移（手动创建）
alembic revision -m "添加用户表"

# 4. 应用所有迁移
alembic upgrade head

# 5. 回滚一个版本
alembic downgrade -1

# 6. 回滚到特定版本
alembic downgrade <revision_id>

# 7. 查看当前版本
alembic current

# 8. 查看迁移历史
alembic history

# 9. 生成迁移 SQL（不执行）
alembic upgrade head --sql
```

### 迁移工作流程

#### 新功能开发流程
```bash
# 1. 修改数据模型
# 编辑 backend/src/models/xxx.py

# 2. 生成迁移脚本
alembic revision --autogenerate -m "添加新字段"

# 3. 审查生成的迁移脚本
# 编辑 backend/alembic/versions/xxxxx_add_new_field.py

# 4. 测试迁移（开发环境）
alembic upgrade head

# 5. 验证更改
python -c "from src.models import YourModel; print(YourModel.__table__.columns.keys())"

# 6. 回滚测试
alembic downgrade -1
alembic upgrade head
```

#### 生产环境部署流程
```bash
# 1. 备份数据库
pg_dump zcgl_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 查看待执行迁移
alembic history

# 3. 在测试环境验证
alembic upgrade head

# 4. 生产环境执行
alembic upgrade head

# 5. 验证数据完整性
python scripts/verify_migration.py
```

### 当前迁移版本
```bash
# 查看当前版本与头版本
alembic current
alembic heads
```

---

## 🔧 数据库初始化

### 方式一：自动初始化（推荐）

```bash
# 启动应用时自动初始化
cd backend
python run_dev.py

# 应用启动前建议执行:
# - alembic upgrade head
# - 初始化基础数据脚本（如有）
```

**证据来源**: `backend/src/main.py:309-312`
```python
# 初始化数据库
init_db()

# 创建数据库表
create_tables()
```

### 方式二：手动初始化

```bash
# 1. 进入后端目录
cd backend

# 2. 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 初始化数据库
python -c "from src.database import init_db, create_tables; init_db(); create_tables()"

# 4. 运行迁移
alembic upgrade head

# 5. 验证初始化
python -c "from src.database import get_database_status; print(get_database_status())"
```

### 方式三：使用 SQL 初始化脚本

```bash
# 使用 PostgreSQL 初始化脚本
cd database
psql -U zcgl_user -d zcgl_db -f init.sql
```

**证据来源**: `database/init.sql` 存在初始化 SQL 脚本

---

## 💾 数据库备份与恢复

### PostgreSQL 备份与恢复

```bash
# 备份整个数据库
pg_dump -U zcgl_user zcgl_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# 备份为自定义格式
pg_dump -U zcgl_user -F c -f backup_$(date +%Y%m%d_%H%M%S).dump zcgl_prod

# 仅备份结构
pg_dump -U zcgl_user -s zcgl_prod > schema_$(date +%Y%m%d_%H%M%S).sql

# 仅备份数据
pg_dump -U zcgl_user -a zcgl_prod > data_$(date +%Y%m%d_%H%M%S).sql

# 恢复
psql -U zcgl_user zcgl_prod < backup_xxxxxx.sql

# 或使用 pg_restore
pg_restore -U zcgl_user -d zcgl_prod backup_xxxxxx.dump
```

### 自动备份脚本

创建 `scripts/backup_db.sh`:
```bash
#!/bin/bash
# 数据库自动备份脚本

BACKUP_DIR="/path/to/backups"
DB_NAME="zcgl_prod"
DB_USER="zcgl_user"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份数据库
pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/backup_${TIMESTAMP}.sql.gz"

# 删除 30 天前的备份
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +30 -delete

echo "备份完成: backup_${TIMESTAMP}.sql.gz"
```

---

## 📊 数据库性能优化

### PostgreSQL 优化建议

#### 1. 连接池配置
```bash
# backend/.env
DATABASE_POOL_SIZE=20          # 根据并发需求调整
DATABASE_MAX_OVERFLOW=30       # 最大额外连接数
DATABASE_POOL_RECYCLE=3600     # 1小时回收连接
DATABASE_POOL_PRE_PING=true    # 连接前检查可用性
```

#### 2. 索引优化
```sql
-- 创建常用查询索引
CREATE INDEX idx_assets_ownership_status ON assets(ownership_status);
CREATE INDEX idx_assets_property_type ON assets(property_type);
CREATE INDEX idx_contracts_start_date ON rent_contracts(contract_start_date);
CREATE INDEX idx_contracts_end_date ON rent_contracts(contract_end_date);

-- 复合索引
CREATE INDEX idx_assets_status_type ON assets(ownership_status, property_type);
```

#### 3. 查询优化
```sql
-- 分析查询执行计划
EXPLAIN ANALYZE SELECT * FROM assets WHERE ownership_status = '自持';

-- 更新表统计信息
ANALYZE assets;
VACUUM ANALYZE assets;
```

### 数据库监控

```bash
# PostgreSQL 实时监控
psql -U zcgl_user -d zcgl_prod

# 查看活动连接
SELECT * FROM pg_stat_activity WHERE datname = 'zcgl_prod';

# 查看表大小
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

# 查看慢查询
SELECT
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

---

## 🚨 常见问题排除

### Q1: 数据库连接失败
**问题**: `OperationalError: could not connect to server`

**解决方案**:
```bash
# 1. 检查 DATABASE_URL 配置
echo $DATABASE_URL

# 2. 确认 PostgreSQL 服务运行
pg_isready -h host -p port

# 3. 验证连接和权限
psql "$DATABASE_URL" -c "SELECT 1;"
```

### Q2: PostgreSQL 连接被拒绝
**问题**: `FATAL: password authentication failed for user`

**解决方案**:
```bash
# 1. 检查 pg_hba.conf 配置
sudo nano /etc/postgresql/14/main/pg_hba.conf

# 2. 添加或修改:
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5

# 3. 重启 PostgreSQL
sudo systemctl restart postgresql

# 4. 重置用户密码
sudo -u postgres psql
ALTER USER zcgl_user WITH PASSWORD 'new_password';
```

### Q3: 迁移冲突
**问题**: `alembic.util.exc.CommandError: Target database is not up to date`

**解决方案**:
```bash
# 1. 查看当前版本
alembic current

# 2. 查看迁移历史
alembic history

# 3. 检查数据库中的版本
psql -c "SELECT * FROM alembic_version;"

# 4. 手动同步版本（如果确定可以）
alembic stamp head

# 5. 然后重新运行迁移
alembic upgrade head
```

### Q4: 表已存在错误
**问题**: `sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateTable) relation "assets" already exists`

**解决方案**:
```bash
# 方案一：删除现有表（谨慎使用）
python -c "from src.database import drop_tables; drop_tables()"

# 方案二：使用迁移
alembic upgrade head

# 方案三：标记为已应用
alembic stamp head
```

### Q5: 外键约束错误
**问题**: `IntegrityError: FOREIGN KEY constraint failed`

**解决方案**:
```bash
# 1. 检查外键定义
psql -d zcgl_db -c "\d+ ownerships"

# 2. 检查数据完整性
python -c "
from src.database import SessionLocal
from src.models import Asset, Ownership
db = SessionLocal()
# 检查孤立记录
orphans = db.query(Ownership).filter(~Ownership.asset_id.in_(db.query(Asset.id))).all()
print(f'Found {len(orphans)} orphaned ownerships')
"

# 3. 清理孤立数据或修复关系
```

### Q6: 数据库锁定
**问题**: `psycopg2.errors.LockNotAvailable` 或 `deadlock detected`

**解决方案**:
```bash
# 1. 查看阻塞会话
psql -d zcgl_db -c "SELECT pid, state, wait_event_type, wait_event, query FROM pg_stat_activity WHERE state <> 'idle';"

# 2. 终止阻塞会话（谨慎使用）
psql -d zcgl_db -c "SELECT pg_terminate_backend(<pid>);"

# 3. 为应用设置锁超时（可选）
psql -d zcgl_db -c "ALTER DATABASE zcgl_db SET lock_timeout = '5s';"
```

---

## 📋 数据库检查清单

### 开发环境初始化
- [ ] 环境变量 `DATABASE_URL` 已配置
- [ ] PostgreSQL 数据库已创建
- [ ] 数据库 schema 已初始化
- [ ] Alembic 迁移已应用
- [ ] 基础数据已导入（如有）
- [ ] 应用能正常连接数据库

### 生产环境部署
- [ ] PostgreSQL 已安装并配置
- [ ] 数据库和用户已创建
- [ ] 连接池参数已调优
- [ ] 索引已创建
- [ ] 备份计划已设置
- [ ] 监控已配置
- [ ] 迁移脚本已测试
- [ ] 数据库权限已最小化

---

## 🔗 相关链接

### 配置文件
- [环境配置指南](environment-setup.md)
- [数据库配置](../../backend/.env.example)
- [Alembic 配置](../../backend/alembic.ini)
- [数据库模块](../../backend/src/database.py)

### 相关文档
- [API 文档](../integrations/api-overview.md)
- [部署指南](deployment.md)

### 外部资源
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Alembic 文档](https://alembic.sqlalchemy.org/)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)

## 📋 Changelog

### 2025-12-23 v1.0.0 - 初始版本
- ✨ 新增：数据库配置和初始化完整指南
- 🗄️ 新增：PostgreSQL 配置说明
- 🔄 新增：Alembic 迁移工作流程
- 💾 新增：备份和恢复操作指南
- 📊 新增：性能优化建议
- 🚨 新增：常见问题排除方案

## 🔍 Evidence Sources
- **数据库模块**: `backend/src/database.py`
- **Alembic 配置**: `backend/alembic.ini`
- **迁移文件**: `backend/alembic/versions/`
- **初始化 SQL**: `database/init.sql`
- **环境配置**: `backend/src/core/config.py`
