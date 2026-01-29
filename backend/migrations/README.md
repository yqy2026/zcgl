# 数据库迁移

## 迁移策略

本项目使用 **Alembic** 进行数据库迁移管理。

## 目录结构

```
migrations/
├── versions/           # Alembic 迁移版本 (标准迁移)
├── *.sql               # 初始设置脚本 (新环境部署用)
└── README.md           # 本文件
```

## 常用命令

```bash
# 查看当前版本
alembic current

# 生成新迁移
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1
```

## SQL 初始化脚本

以下 SQL 文件用于新环境初始部署：

| 文件 | 说明 |
|------|------|
| `001_add_authentication_tables.sql` | 创建用户、会话、审计表 |
| `002_add_rbac_tables.sql` | 创建 RBAC 权限表 |
| `004_add_password_security_fields.sql` | 添加密码安全字段 |
| `add_performance_indexes.sql` | 添加性能索引 |

## 注意事项

1. **新迁移**: 必须使用 Alembic 创建
2. **SQL 文件**: 仅用于新环境初始化，不要修改
3. **历史脚本**: 过期脚本不再保留于仓库，避免迁移链混乱
