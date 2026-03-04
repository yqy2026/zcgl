# 安全文档索引

本目录包含系统安全设计、数据保护与运维安全相关文档。

## 文档列表

| 文档 | 说明 |
|------|------|
| [encryption.md](./encryption.md) | 数据加密方案（AES-256-CBC、PII 保护） |
| [backend-security.md](./backend-security.md) | 后端安全指南（认证、RBAC、防注入） |
| [capability-guard-env.md](./capability-guard-env.md) | 能力守卫环境配置（Feature Flag 与权限隔离） |

## 安全原则速查

- `SECRET_KEY` 必须为 32+ 字符强随机密钥
- `DATA_ENCRYPTION_KEY` 控制 PII 字段加密，缺失则降级为明文
- 永远不要提交 `.env` 文件
- 凭证泄露应急流程见 [部署指南 - 凭证泄露处置](../guides/deployment.md)
