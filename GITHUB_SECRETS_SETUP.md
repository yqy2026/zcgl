# GitHub Secrets 配置快速指南

## 待配置的 Secret

根据 JWT 安全修复要求，需要在 GitHub Repository Secrets 中添加以下配置：

---

## TEST_SECRET_KEY 配置

### 生成密钥

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**已生成密钥** (供参考):
```
JzJnGiEDSnPr4eeSmeH_piRssVa4M6E0UYq6euGJMNI
```

### 配置步骤

1. **访问 GitHub Repository**
   ```
   https://github.com/<your-username>/<your-repo>
   ```

2. **进入 Secrets 设置**
   - 点击 `Settings` 标签
   - 左侧菜单找到 `Secrets and variables`
   - 点击 `Actions`

3. **创建 New Secret**
   - 点击 `New repository secret` 按钮
   - 填写以下信息：

   | 字段 | 值 |
   |------|-----|
   | **Name** | `TEST_SECRET_KEY` |
   | **Value** | `JzJnGiEDSnPr4eeSmeH_piRssVa4M6E0UYq6euGJMNI` |

   - (可选) 添加描述：
     ```
     测试环境 JWT 密钥，用于 CI/CD 流水线
     生成时间: 2026-01-15
     ```

   - 点击 `Add secret` 保存

4. **验证配置**
   - 提交代码到 GitHub
   - 检查 Actions 工作流是否成功运行
   - 查看 CI 日志确认环境变量正确加载

---

## 验证清单

- [ ] GitHub Secret 已添加
- [ ] Secret 名称拼写正确 (TEST_SECRET_KEY)
- [ ] Secret 值长度 ≥ 32 字符
- [ ] CI 工作流成功运行
- [ ] 测试全部通过

---

## 故障排查

### 问题 1: CI 失败，提示 SECRET_KEY 相关错误

**解决方案**:
1. 检查 Secret 名称是否完全匹配 `TEST_SECRET_KEY`
2. 检查 Secret 值是否被正确复制（无空格或换行）
3. 重新生成密钥并更新 Secret

### 问题 2: pytest 失败，密钥验证错误

**解决方案**:
1. 确认测试在 conftest.py 中正确设置环境变量
2. 检查 GitHub Actions 日志中的实际密钥值
3. 验证密钥不包含弱模式（如 "test", "secret", "key"）

---

## 安全建议

⚠️ **重要安全提醒**:
1. 不要在任何地方公开或提交此密钥
2. 定期轮换测试密钥（建议每 90 天）
3. 使用不同的密钥用于不同环境（开发/测试/生产）
4. 监控 CI/CD 日志，确保密钥不会被意外记录

---

## 相关文件

- `.github/workflows/ci.yml` - CI 配置（已更新）
- `backend/tests/conftest.py` - 测试配置（已更新）
- `backend/.env.example` - 环境变量示例（已更新）
- `JWT_SECURITY_FIX_REPORT.md` - 完整修复报告

---

**配置完成后，删除此文件或移至 docs/ 目录归档**
