# 数据加密配置指南

## 概述

系统使用 AES-256 加密算法保护敏感 PII（个人身份信息）字段，如身份证号、手机号等。

## 配置项

| 环境变量 | 类型 | 默认值 | 说明 |
|----------|------|--------|------|
| `DATA_ENCRYPTION_KEY` | string | - | 加密密钥（格式: `base64_key:version`） |
| `REQUIRE_ENCRYPTION` | bool | `false` | 是否强制要求密钥（生产环境建议开启） |

## 生成加密密钥

```bash
cd backend
python -m src.core.encryption
```

输出示例：
```
DATA_ENCRYPTION_KEY="<base64_key>:1"
```

将生成的密钥添加到 `.env` 文件中。
> 说明：`DATA_ENCRYPTION_KEY` 必须是**标准 Base64**（含 `=` padding），格式为 `{base64_key}:{version}`。不要使用 `secrets.token_urlsafe` 生成。

## 环境行为

| 环境 | 密钥状态 | REQUIRE_ENCRYPTION | 行为 |
|------|----------|-------------------|------|
| 生产 | 无密钥 | true | **启动失败**，抛出配置错误 |
| 生产 | 无密钥 | false | 警告日志，明文存储（不推荐） |
| 生产 | 有密钥 | - | 正常加密 |
| 开发 | 无密钥 | false（默认） | 警告日志，明文存储 |
| 开发 | 有密钥 | - | 正常加密 |

## 加密算法

- **AES-256-GCM**：标准加密，每次产生不同密文（推荐用于非搜索字段）
- **AES-256-CBC**：确定性加密，相同明文产生相同密文（用于需要数据库搜索的字段）

## 健康检查

加密状态可通过健康检查 API 查看：

```bash
GET /api/v1/system/health
```

响应包含：
```json
{
  "components": {
    "encryption": {
      "status": "healthy",
      "key_available": true,
      "key_version": 1,
      "algorithms": ["AES-256-GCM", "AES-256-CBC"]
    }
  }
}
```

## 安全最佳实践

1. **永远不要将密钥提交到版本控制**
2. **生产环境使用安全的密钥管理服务**（如 AWS Secrets Manager、HashiCorp Vault）
3. **不同环境使用不同密钥**（开发、预发布、生产）
4. **定期轮换密钥**（增加版本号）
5. **在生产部署前测试密钥恢复流程**

## 密钥轮换

1. 生成新密钥，版本号 +1：
   ```
   DATA_ENCRYPTION_KEY="新base64密钥:2"
   ```
2. 部署新版本
3. 运行数据迁移脚本重新加密历史数据（如需要）

## 故障排除

### 启动失败：`CRITICAL: DATA_ENCRYPTION_KEY is required`

**原因**：生产环境未配置加密密钥

**解决方案**：
1. 生成密钥：`cd backend && python -m src.core.encryption`
2. 添加到环境变量或 `.env` 文件
3. 或设置 `REQUIRE_ENCRYPTION=false`（不推荐）

### 解密失败返回 None

**可能原因**：
- 密钥版本不匹配
- 密钥已更换但未迁移历史数据
- 数据损坏

**解决方案**：检查日志中的详细错误信息

### 启动报错：`Incorrect padding`

**原因**：使用了 URL-safe 或缺少 padding 的密钥（不是标准 Base64）。

**解决方案**：
1. 使用 `cd backend && python -m src.core.encryption` 重新生成
2. 确保密钥格式为 `{base64_key}:{version}`，末尾通常带一个或两个 `=`
