# V2 升级计划

## ✅ Status
**当前状态**: Archived Draft (2026-02-09)

> ⚠️ 本文档已归档，仅作历史留痕。  
> 当前需求与验收基线请参考：`docs/requirements-specification.md`。

## 适用范围
从 v1.x 升级到 v2.x 的生产与测试环境。

## 升级步骤
1. 备份数据库与上传文件
2. 更新代码并同步配置
3. 确保数据库为 PostgreSQL（SQLite 已移除）
4. 运行数据库迁移：`make migrate`
5. 执行 Smoke Test（归档用例见 `docs/archive/testing/v2-test-cases-2026-02.md`）

## 回滚策略
- 保留升级前数据库备份
- 回滚代码到上一版本

## 参考
- [V2 发布说明（归档）](../releases/v2-release-notes-2026-01.md)
