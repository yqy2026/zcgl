# 归档迁移脚本目录

本目录存放已执行过的一次性迁移脚本，仅供历史参考。

## 归档脚本

| 文件 | 归档时间 | 说明 |
|------|----------|------|
| `cleanup_redundant_fields.py` | 2026-01-01 | 清理前端不一致的冗余字段 |
| `migrate_relationships.py` | 2026-01-01 | 迁移资产关系数据 |
| `fix_data_model_inconsistency.py` | 2025-11-08 | 修复前后端数据模型不一致 |
| `001_add_new_asset_fields.sql` | - | 添加新资产字段 |
| `002_add_rent_management_indexes.sql` | - | 添加租赁管理索引 |

## 注意事项

1. **不要直接执行这些脚本**，它们已经运行过
2. 新迁移请使用 Alembic: `alembic revision --autogenerate -m "..."`
3. 如需参考实现方式，可查看这些脚本
