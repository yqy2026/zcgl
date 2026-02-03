# V2 升级计划

## ✅ Status
**当前状态**: Draft (2026-02-03)

## 适用范围
从 v1.x 升级到 v2.x 的生产与测试环境。

## 升级步骤
1. 备份数据库与上传文件
2. 更新代码并同步配置
3. 确保数据库为 PostgreSQL（SQLite 已移除）
4. 运行数据库迁移：`make migrate`
5. 执行 Smoke Test（见 `docs/testing/v2-test-cases.md`）

## 回滚策略
- 保留升级前数据库备份
- 回滚代码到上一版本

## 参考
- [V2 发布说明](v2-release-notes.md)
