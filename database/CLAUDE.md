[根目录](../../CLAUDE.md) > **database**

# Database 数据库模块

## 变更记录 (Changelog)

### 2025-10-23 10:45:44 - 模块架构初始化
- ✨ 新增：模块导航面包屑
- ✨ 新增：数据库架构文档
- 📊 分析：SQLite生产就绪，支持MySQL/PostgreSQL迁移
- 🔧 优化：数据库连接和初始化脚本

---

## 模块职责

Database模块负责地产资产管理系统的数据持久化，基于SQLite构建，同时支持向MySQL/PostgreSQL的平滑迁移。提供完整的数据模型定义、迁移管理和备份恢复功能。

### 核心职责
- **数据存储**: SQLite默认配置，生产环境支持MySQL/PostgreSQL
- **模型定义**: 9个核心数据模型，支持58字段资产信息
- **迁移管理**: Alembic数据库迁移，版本控制和自动化
- **备份恢复**: 数据备份策略和恢复机制
- **性能优化**: 索引策略、查询优化、连接池管理

## 数据库架构

### 技术栈
- **默认数据库**: SQLite 3.x
- **ORM框架**: SQLAlchemy 2.0+
- **迁移工具**: Alembic
- **连接池**: SQLAlchemy内置连接池
- **备份工具**: SQLite原生工具 + 自定义脚本

### 数据库文件结构
```
database/
├── init.sql                 # 数据库初始化脚本
├── land_property.db        # SQLite数据库文件 (生产数据)
├── assets.db               # 备用数据库文件
└── backups/                # 数据库备份目录
    ├── manual_backup_20251023.sql
    └── auto_backup_20251023.sql
```

## 数据模型设计

### 核心数据表

#### 1. assets - 资产主表 (58字段)
```sql
CREATE TABLE assets (
    id VARCHAR(36) PRIMARY KEY,                    -- UUID主键

    -- 基本信息字段 (8个)
    ownership_entity VARCHAR(200) NOT NULL,        -- 权属方
    ownership_category VARCHAR(100),               -- 权属类别
    project_name VARCHAR(200),                     -- 项目名称
    property_name VARCHAR(200) NOT NULL,           -- 物业名称
    address VARCHAR(500) NOT NULL,                 -- 物业地址
    ownership_status VARCHAR(50) NOT NULL,         -- 确权状态
    property_nature VARCHAR(50) NOT NULL,          -- 物业性质
    usage_status VARCHAR(50) NOT NULL,             -- 使用状态

    -- 分类字段 (5个)
    business_category VARCHAR(100),                -- 业态类别
    certificated_usage VARCHAR(100),               -- 证载用途
    actual_usage VARCHAR(100),                     -- 实际用途
    tenant_name VARCHAR(200),                      -- 租户名称
    tenant_type VARCHAR(20),                       -- 租户类型

    -- 面积字段 (8个)
    land_area DECIMAL(12, 2),                     -- 土地面积
    actual_property_area DECIMAL(12, 2),           -- 实际房产面积
    rentable_area DECIMAL(12, 2),                 -- 可出租面积
    rented_area DECIMAL(12, 2),                   -- 已出租面积
    unrented_area DECIMAL(12, 2),                 -- 未出租面积
    non_commercial_area DECIMAL(12, 2),           -- 非经营物业面积
    occupancy_rate DECIMAL(5, 2),                 -- 出租率
    include_in_occupancy_rate BOOLEAN DEFAULT 1,  -- 是否计入出租率统计

    -- 财务字段 (12个)
    annual_income DECIMAL(15, 2),                  -- 年收入
    annual_expense DECIMAL(15, 2),                 -- 年支出
    net_income DECIMAL(15, 2),                    -- 净收入
    rent_price_per_sqm DECIMAL(10, 2),            -- 每平米租金
    management_fee_per_sqm DECIMAL(10, 2),        -- 每平米管理费
    property_tax DECIMAL(15, 2),                  -- 房产税
    insurance_fee DECIMAL(15, 2),                 -- 保险费
    maintenance_fee DECIMAL(15, 2),               -- 维修费
    other_fees DECIMAL(15, 2),                    -- 其他费用
    rent_income_tax DECIMAL(15, 2),               -- 租金收入税
    net_rental_income DECIMAL(15, 2),             -- 净租金收入
    total_cost DECIMAL(15, 2),                    -- 总成本

    -- 合同字段 (10个)
    lease_contract_number VARCHAR(100),            -- 租赁合同编号
    contract_start_date DATE,                     -- 合同开始日期
    contract_end_date DATE,                       -- 合同结束日期
    contract_term INTEGER,                        -- 合同期限
    rent_payment_method VARCHAR(50),              -- 租金支付方式
    deposit_amount DECIMAL(15, 2),                -- 押金金额
    rent_increase_clause TEXT,                     -- 租金增长条款
    termination_clause TEXT,                       -- 终止条款
    renewal_option BOOLEAN DEFAULT 0,             -- 续租选择权
    special_terms TEXT,                           -- 特殊条款

    -- 状态字段 (5个)
    is_litigated BOOLEAN DEFAULT 0,               -- 是否涉诉
    business_model VARCHAR(100),                  -- 经营模式
    operation_status VARCHAR(50),                 -- 运营状态
    notes TEXT,                                   -- 备注
    tenant_id VARCHAR(36),                        -- 租户ID (多租户)

    -- 系统字段 (4个)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36),

    -- 索引
    INDEX idx_ownership_entity (ownership_entity),
    INDEX idx_property_name (property_name),
    INDEX idx_address (address),
    INDEX idx_ownership_status (ownership_status),
    INDEX idx_created_at (created_at),
    INDEX idx_tenant_id (tenant_id)
);
```

#### 2. asset_history - 资产变更历史表
```sql
CREATE TABLE asset_history (
    id VARCHAR(36) PRIMARY KEY,
    asset_id VARCHAR(36) NOT NULL,                -- 关联资产ID
    operation_type VARCHAR(20) NOT NULL,          -- 操作类型: CREATE/UPDATE/DELETE
    old_values JSON,                              -- 变更前数据
    new_values JSON,                              -- 变更后数据
    changed_fields JSON,                          -- 变更字段列表
    reason TEXT,                                  -- 变更原因
    operator_id VARCHAR(36),                      -- 操作人ID
    operator_name VARCHAR(100),                   -- 操作人姓名
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    INDEX idx_asset_id (asset_id),
    INDEX idx_operation_type (operation_type),
    INDEX idx_created_at (created_at)
);
```

#### 3. rent_contracts - 租赁合同表
```sql
CREATE TABLE rent_contracts (
    id VARCHAR(36) PRIMARY KEY,
    contract_number VARCHAR(100) UNIQUE NOT NULL, -- 合同编号
    asset_id VARCHAR(36),                         -- 关联资产
    tenant_name VARCHAR(200) NOT NULL,            -- 租户名称
    tenant_type VARCHAR(20),                      -- 租户类型
    start_date DATE NOT NULL,                     -- 合同开始日期
    end_date DATE NOT NULL,                       -- 合同结束日期
    monthly_rent DECIMAL(15, 2) NOT NULL,         -- 月租金
    deposit_amount DECIMAL(15, 2),                -- 押金金额
    payment_method VARCHAR(50),                   -- 支付方式
    payment_cycle VARCHAR(20),                    -- 支付周期
    increase_rate DECIMAL(5, 2),                  -- 增长率
    contract_status VARCHAR(20) DEFAULT 'ACTIVE', -- 合同状态
    contract_file VARCHAR(500),                   -- 合同文件路径
    notes TEXT,                                   -- 备注

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36),

    FOREIGN KEY (asset_id) REFERENCES assets(id),
    INDEX idx_contract_number (contract_number),
    INDEX idx_asset_id (asset_id),
    INDEX idx_tenant_name (tenant_name),
    INDEX idx_status (contract_status),
    INDEX idx_start_end_date (start_date, end_date)
);
```

#### 4. projects - 项目表
```sql
CREATE TABLE projects (
    id VARCHAR(36) PRIMARY KEY,
    project_name VARCHAR(200) NOT NULL,           -- 项目名称
    project_code VARCHAR(50) UNIQUE,              -- 项目编码
    parent_project_id VARCHAR(36),                 -- 父项目ID
    project_level INTEGER DEFAULT 1,              -- 项目层级
    project_type VARCHAR(50),                     -- 项目类型
    location VARCHAR(500),                        -- 项目位置
    total_area DECIMAL(12, 2),                    -- 总面积
    total_assets INTEGER DEFAULT 0,               -- 资产总数
    description TEXT,                             -- 项目描述
    project_status VARCHAR(20) DEFAULT 'ACTIVE',  -- 项目状态

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (parent_project_id) REFERENCES projects(id),
    INDEX idx_project_name (project_name),
    INDEX idx_parent_project (parent_project_id),
    INDEX idx_project_level (project_level),
    INDEX idx_status (project_status)
);
```

#### 5. ownerships - 权属方表
```sql
CREATE TABLE ownerships (
    id VARCHAR(36) PRIMARY KEY,
    ownership_name VARCHAR(200) NOT NULL,         -- 权属方名称
    ownership_code VARCHAR(50) UNIQUE,            -- 权属方编码
    ownership_type VARCHAR(50),                   -- 权属方类型
    legal_person VARCHAR(100),                    -- 法人代表
    contact_phone VARCHAR(20),                    -- 联系电话
    contact_email VARCHAR(100),                   -- 联系邮箱
    registration_address VARCHAR(500),            -- 注册地址
    business_license VARCHAR(100),                -- 营业执照号
    tax_number VARCHAR(50),                       -- 税号
    ownership_status VARCHAR(20) DEFAULT 'ACTIVE', -- 权属方状态
    notes TEXT,                                   -- 备注

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_ownership_name (ownership_name),
    INDEX idx_ownership_code (ownership_code),
    INDEX idx_ownership_type (ownership_type),
    INDEX idx_status (ownership_status)
);
```

#### 6. organizations - 组织架构表
```sql
CREATE TABLE organizations (
    id VARCHAR(36) PRIMARY KEY,
    org_name VARCHAR(200) NOT NULL,               -- 组织名称
    org_code VARCHAR(50) UNIQUE,                  -- 组织编码
    parent_org_id VARCHAR(36),                    -- 父组织ID
    org_level INTEGER DEFAULT 1,                  -- 组织层级
    org_type VARCHAR(50),                         -- 组织类型
    manager_id VARCHAR(36),                       -- 负责人ID
    contact_phone VARCHAR(20),                    -- 联系电话
    contact_email VARCHAR(100),                   -- 联系邮箱
    address VARCHAR(500),                         -- 组织地址
    org_status VARCHAR(20) DEFAULT 'ACTIVE',      -- 组织状态

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (parent_org_id) REFERENCES organizations(id),
    INDEX idx_org_name (org_name),
    INDEX idx_org_code (org_code),
    INDEX idx_parent_org (parent_org_id),
    INDEX idx_org_level (org_level),
    INDEX idx_status (org_status)
);
```

#### 7. users - 用户表
```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,         -- 用户名
    email VARCHAR(100) UNIQUE,                    -- 邮箱
    password_hash VARCHAR(255) NOT NULL,          -- 密码哈希
    full_name VARCHAR(100) NOT NULL,              -- 全名
    phone VARCHAR(20),                            -- 电话
    avatar_url VARCHAR(500),                      -- 头像URL
    organization_id VARCHAR(36),                  -- 所属组织
    is_active BOOLEAN DEFAULT 1,                  -- 是否激活
    is_superuser BOOLEAN DEFAULT 0,               -- 是否超级用户
    last_login_at TIMESTAMP,                      -- 最后登录时间
    login_count INTEGER DEFAULT 0,                -- 登录次数

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_full_name (full_name),
    INDEX idx_organization (organization_id),
    INDEX idx_is_active (is_active)
);
```

#### 8. roles - 角色表
```sql
CREATE TABLE roles (
    id VARCHAR(36) PRIMARY KEY,
    role_name VARCHAR(100) NOT NULL,              -- 角色名称
    role_code VARCHAR(50) UNIQUE NOT NULL,        -- 角色编码
    description TEXT,                             -- 角色描述
    parent_role_id VARCHAR(36),                   -- 父角色ID
    role_level INTEGER DEFAULT 1,                 -- 角色层级
    is_system_role BOOLEAN DEFAULT 0,             -- 是否系统角色
    role_status VARCHAR(20) DEFAULT 'ACTIVE',     -- 角色状态

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (parent_role_id) REFERENCES roles(id),
    INDEX idx_role_name (role_name),
    INDEX idx_role_code (role_code),
    INDEX idx_parent_role (parent_role_id),
    INDEX idx_role_level (role_level),
    INDEX idx_status (role_status)
);
```

#### 9. permissions - 权限表
```sql
CREATE TABLE permissions (
    id VARCHAR(36) PRIMARY KEY,
    permission_name VARCHAR(100) NOT NULL,        -- 权限名称
    permission_code VARCHAR(50) UNIQUE NOT NULL,  -- 权限编码
    resource VARCHAR(50) NOT NULL,                -- 资源类型
    action VARCHAR(50) NOT NULL,                  -- 操作类型
    description TEXT,                             -- 权限描述
    parent_permission_id VARCHAR(36),             -- 父权限ID
    permission_level INTEGER DEFAULT 1,           -- 权限层级
    is_system_permission BOOLEAN DEFAULT 0,       -- 是否系统权限
    permission_status VARCHAR(20) DEFAULT 'ACTIVE', -- 权限状态

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (parent_permission_id) REFERENCES permissions(id),
    INDEX idx_permission_name (permission_name),
    INDEX idx_permission_code (permission_code),
    INDEX idx_resource_action (resource, action),
    INDEX idx_parent_permission (parent_permission_id),
    INDEX idx_status (permission_status)
);
```

#### 10. user_roles - 用户角色关联表
```sql
CREATE TABLE user_roles (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,                 -- 用户ID
    role_id VARCHAR(36) NOT NULL,                 -- 角色ID
    assigned_by VARCHAR(36),                      -- 分配人ID
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                         -- 过期时间
    is_active BOOLEAN DEFAULT 1,                  -- 是否激活

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users(id),
    UNIQUE KEY uk_user_role (user_id, role_id),
    INDEX idx_user_id (user_id),
    INDEX idx_role_id (role_id),
    INDEX idx_assigned_at (assigned_at),
    INDEX idx_expires_at (expires_at)
);
```

#### 11. role_permissions - 角色权限关联表
```sql
CREATE TABLE role_permissions (
    id VARCHAR(36) PRIMARY KEY,
    role_id VARCHAR(36) NOT NULL,                 -- 角色ID
    permission_id VARCHAR(36) NOT NULL,           -- 权限ID
    granted_by VARCHAR(36),                       -- 授权人ID
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scope VARCHAR(100),                           -- 权限范围
    conditions JSON,                              -- 权限条件

    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id),
    UNIQUE KEY uk_role_permission (role_id, permission_id),
    INDEX idx_role_id (role_id),
    INDEX idx_permission_id (permission_id),
    INDEX idx_granted_at (granted_at),
    INDEX idx_scope (scope)
);
```

## 数据库初始化

### 初始化脚本 (init.sql)
```sql
-- 创建数据库结构
-- 基础数据插入
-- 索引创建
-- 约束设置

-- 插入默认系统数据
INSERT INTO organizations (id, org_name, org_code, org_type) VALUES
('org-root', '根组织', 'ROOT', 'SYSTEM');

INSERT INTO users (id, username, email, password_hash, full_name, is_superuser) VALUES
('user-admin', 'admin', 'admin@example.com', '$2b$12$...', '系统管理员', 1);

INSERT INTO roles (id, role_name, role_code, is_system_role) VALUES
('role-super-admin', '超级管理员', 'SUPER_ADMIN', 1),
('role-admin', '管理员', 'ADMIN', 1),
('role-user', '普通用户', 'USER', 1);

INSERT INTO permissions (id, permission_name, permission_code, resource, action) VALUES
('perm-asset-view', '查看资产', 'ASSET_VIEW', 'ASSET', 'VIEW'),
('perm-asset-create', '创建资产', 'ASSET_CREATE', 'ASSET', 'CREATE'),
('perm-asset-edit', '编辑资产', 'ASSET_EDIT', 'ASSET', 'EDIT'),
('perm-asset-delete', '删除资产', 'ASSET_DELETE', 'ASSET', 'DELETE');
```

### 数据库连接配置
```python
# src/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 数据库URL配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/land_property.db")

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False  # 设置为True可查看SQL日志
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()

# 创建所有表
def create_tables():
    Base.metadata.create_all(bind=engine)

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## 数据迁移管理

### Alembic配置
```ini
# alembic.ini
[alembic]
script_location = migrations
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = sqlite:///./data/land_property.db

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 迁移命令
```bash
# 生成迁移文件
alembic revision --autogenerate -m "描述变更"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看迁移历史
alembic history

# 查看当前版本
alembic current

# 查看迁移详情
alembic show <revision_id>
```

## 备份与恢复

### 备份策略
```bash
# SQLite数据库备份
sqlite3 backend/data/land_property.db ".backup backup/backup_$(date +%Y%m%d_%H%M%S).db"

# SQL导出备份
sqlite3 backend/data/land_property.db ".dump" > backup/backup_$(date +%Y%m%d_%H%M%S).sql

# 压缩备份
gzip backup/backup_$(date +%Y%m%d_%H%M%S).sql
```

### 恢复策略
```bash
# 从备份文件恢复
cp backup/backup_20251023_120000.db backend/data/land_property.db

# 从SQL文件恢复
sqlite3 backend/data/land_property_new.db < backup/backup_20251023_120000.sql

# 验证数据完整性
sqlite3 backend/data/land_property.db "SELECT COUNT(*) FROM assets;"
```

### 自动备份脚本
```python
# scripts/auto_backup.py
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

def auto_backup_database():
    """自动备份数据库"""
    source_db = "backend/data/land_property.db"
    backup_dir = Path("database/backups")
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"auto_backup_{timestamp}.db"

    # 创建备份
    shutil.copy2(source_db, backup_file)

    # 验证备份
    conn = sqlite3.connect(backup_file)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM assets")
    count = cursor.fetchone()[0]
    conn.close()

    print(f"备份完成: {backup_file}, 资产记录数: {count}")

    # 清理旧备份 (保留最近30天)
    cleanup_old_backups(backup_dir, days=30)

def cleanup_old_backups(backup_dir, days=30):
    """清理旧备份文件"""
    cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)

    for backup_file in backup_dir.glob("auto_backup_*.db"):
        if backup_file.stat().st_mtime < cutoff_time:
            backup_file.unlink()
            print(f"删除旧备份: {backup_file}")
```

## 性能优化

### 索引策略
```sql
-- 核心查询索引
CREATE INDEX idx_assets_ownership_status ON assets(ownership_status);
CREATE INDEX idx_assets_property_nature ON assets(property_nature);
CREATE INDEX idx_assets_usage_status ON assets(usage_status);
CREATE INDEX idx_assets_area_combined ON assets(rentable_area, rented_area);
CREATE INDEX idx_assets_financial ON assets(annual_income, annual_expense);

-- 复合索引
CREATE INDEX idx_assets_search ON assets(ownership_entity, property_name, address);
CREATE INDEX idx_assets_date_range ON assets(contract_start_date, contract_end_date);

-- 历史查询索引
CREATE INDEX idx_asset_history_asset_created ON asset_history(asset_id, created_at);
CREATE INDEX idx_asset_history_operation ON asset_history(operation_type, created_at);
```

### 查询优化
```python
# 分页查询优化
def get_assets_paginated(db: Session, page: int, size: int, filters: dict):
    query = db.query(Asset)

    # 应用筛选条件
    if filters.get("ownership_status"):
        query = query.filter(Asset.ownership_status == filters["ownership_status"])

    # 计算总数 (优化：使用子查询)
    total = query.count()

    # 分页查询
    assets = query.offset((page - 1) * size).limit(size).all()

    return {"items": assets, "total": total, "page": page, "size": size}

# 批量操作优化
def bulk_update_assets(db: Session, asset_updates: List[dict]):
    """批量更新资产信息"""
    db.bulk_update_mappings(Asset, asset_updates)
    db.commit()

# 统计查询优化
def get_occupancy_statistics(db: Session):
    """获取出租率统计 (使用聚合查询)"""
    result = db.query(
        func.sum(Asset.rentable_area).label('total_rentable'),
        func.sum(Asset.rented_area).label('total_rented'),
        func.count(Asset.id).label('total_assets')
    ).filter(
        Asset.include_in_occupancy_rate == True
    ).first()

    return {
        "occupancy_rate": (result.total_rented / result.total_rentable * 100) if result.total_rentable else 0,
        "total_assets": result.total_assets
    }
```

## 常见问题 (FAQ)

### Q: 如何迁移到MySQL/PostgreSQL？
A: 修改DATABASE_URL环境变量，运行`alembic upgrade head`即可自动迁移。

### Q: 数据库文件很大怎么办？
A: 定期运行VACUUM命令清理碎片，使用PRAGMA optimize优化索引。

### Q: 如何处理并发访问？
A: SQLite支持并发读，但写操作会串行化。高并发场景建议使用MySQL/PostgreSQL。

### Q: 备份文件损坏如何恢复？
A: 维护多个备份副本，使用`sqlite3 .recover`命令尝试数据恢复。

### Q: 如何监控数据库性能？
A: 使用EXPLAIN QUERY PLAN分析查询，监控数据库文件大小和查询响应时间。

## 相关文件清单

### 数据库文件
- `land_property.db` - 主数据库文件 (生产数据)
- `assets.db` - 备用数据库文件
- `init.sql` - 数据库初始化脚本

### 迁移文件
- `../backend/alembic.ini` - Alembic配置
- `../backend/alembic/` - 迁移脚本目录
- `../backend/alembic/env.py` - 迁移环境配置

### 备份文件
- `backups/` - 备份文件目录
- `backups/auto_backup_*.db` - 自动备份文件
- `backups/manual_backup_*.sql` - 手动备份文件

### 配置文件
- `../backend/src/database.py` - 数据库连接配置
- `../backend/src/models/` - SQLAlchemy模型定义

### 脚本文件
- `../scripts/auto_backup.py` - 自动备份脚本
- `../scripts/migrate_to_mysql.py` - MySQL迁移脚本
- `../scripts/data_cleanup.py` - 数据清理脚本

---

**模块状态**: 🟢 生产就绪，SQLite稳定运行，支持平滑迁移到其他数据库。

**最后更新**: 2025-10-23 10:45:44 (模块架构初始化)