# CI失败问题诊断报告

## 问题摘要
所有GitHub Actions workflow在推送到main和develop分支时立即失败（0秒），显示"workflow file issue"错误。

## 根本原因 ✅ 已确认
**GitHub Actions配额/计费问题**，而非workflow语法错误。

### 诊断过程
1. **初始假设**：workflow YAML语法错误（`on`关键字问题）
2. **测试验证**：创建最小化测试workflow
   - 结果：运行了5秒（而非0秒），说明语法正确
   - 错误信息：`"The job was not started because recent account payments have failed or your spending limit needs to be increased"`

3. **仓库状态**：
   - 私有仓库 (`private: true`)
   - 非fork仓库
   - GitHub Actions在私有仓库需要付费配额

## 解决方案

### 选项1：增加GitHub Actions配额（推荐用于生产环境）
1. 访问 [GitHub Billing Settings](https://github.com/settings/billing/summary)
2. 导航到 "Billing & plans" → "Usage this month"
3. 检查Actions使用量和限制
4. 增加spending limit或添加付款方式
5. 文档：https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions

### 选项2：将仓库转为公开（免费使用Actions）
```bash
# 通过GitHub网页界面：Settings → Danger Zone → Change visibility
# 注意：这会使所有代码公开可见
```

### 选项3：使用Self-hosted runners（企业方案）
- 在自己的服务器上运行GitHub Actions
- 文档：https://docs.github.com/en/actions/hosting-your-own-runners

### 选项4：临时禁用CI（快速修复）
```bash
# 重命名workflow文件为.disabled后缀
cd .github/workflows
for file in *.yml; do mv "$file" "$file.disabled"; done
```

## Workflow文件状态

### 当前修改（可选择保留或恢复）
在诊断过程中对workflow文件做了以下修改：

1. **ci.yml, docs.yml**：
   - 将 `workflow_dispatch:` 改为 `workflow_dispatch: {}`
   - 原因：避免YAML解析器将null值传递给GitHub Actions

2. **所有workflow文件**：
   - 尝试了 `on:` 和 `"on":` 两种语法
   - 结论：两种都有效，本地YAML解析器差异不影响GitHub

### 推荐操作
**保持当前修改**，因为：
- `workflow_dispatch: {}` 比空值更明确
- YAML语法已验证正确
- 解决计费问题后，workflow将正常运行

## 验证步骤（解决计费问题后）

1. 检查Actions配额状态：
```bash
# 访问 https://github.com/yuist/zcgl/settings/actions
# 查看 "Allow all actions and reusable workflows"
```

2. 触发测试运行：
```bash
# 推送小改动
git commit --allow-empty -m "test: verify CI after billing fix"
git push origin develop
```

3. 监控运行状态：
```bash
gh run list --limit 3
gh run watch
```

## 相关文档
- [GitHub Actions Billing](https://docs.github.com/en/billing/managing-billing-for-github-actions)
- [GitHub Actions Usage Limits](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

## 分支状态
- 当前分支：`fix/ci-workflow-errors`
- 可以安全合并或删除（workflow文件改动是可选的优化）
- 主要问题在GitHub账号设置，而非代码本身

---
**创建时间**：2026-01-12
**诊断耗时**：约20分钟
**状态**：✅ 根本原因已确认
