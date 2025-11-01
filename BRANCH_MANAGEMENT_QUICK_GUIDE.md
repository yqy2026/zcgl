# 分支管理快速操作指南

## 常用分支操作命令

### 创建分支
```bash
# 创建功能分支 (基于develop)
git checkout develop
git pull origin develop
git checkout -b feature/功能描述-用户名-$(date +%Y%m%d)

# 创建热修复分支 (基于main)
git checkout main
git pull origin main
git checkout -b hotfix/问题描述-$(date +%Y%m%d)

# 创建发布分支 (基于develop)
git checkout develop
git pull origin develop
git checkout -b release/v版本号-$(date +%Y%m%d)
```

### 提交规范
```bash
# 格式: type(scope): description
git commit -m "feat(assets): 添加资产监控功能

- 实现实时性能指标收集
- 添加系统健康状态监控
- 集成RBAC权限控制

Closes #123"

# 提交类型:
# feat: 新功能
# fix: 修复bug
# docs: 文档更新
# style: 代码格式调整
# refactor: 重构
# test: 测试相关
# chore: 构建/工具相关
```

### PR创建模板
```markdown
## 变更类型
- [ ] 新功能 (feature)
- [ ] 修复 (fix)
- [ ] 文档 (docs)
- [ ] 样式 (style)
- [ ] 重构 (refactor)
- [ ] 测试 (test)
- [ ] 构建 (chore)

## 变更描述
简要描述本次变更的内容和目的

## 测试结果
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试完成
- [ ] 性能测试通过

## 检查清单
- [ ] 代码符合项目规范
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] 考虑了向后兼容性
- [ ] 所有CI检查通过

## 相关Issue
Closes #issue_number
```

### 分支同步
```bash
# 定期同步develop到main
git checkout main
git pull origin main
git checkout develop
git merge main
git push origin develop

# 同步远程分支变更
git checkout feature/your-branch
git fetch origin
git rebase origin/develop
```

### 分支清理
```bash
# 删除已合并的本地分支
git branch --merged develop | grep -v "develop" | xargs git branch -d

# 删除已合并的远程分支
git remote prune origin

# 清理无效分支引用
git fetch --prune
```

## 紧急修复流程
```bash
# 1. 创建热修复分支
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-fix-$(date +%Y%m%d)

# 2. 快速修复和测试
# ... 修复代码 ...
git add .
git commit -m "hotfix: 修复关键登录问题

影响用户无法正常登录系统
立即修复，需要紧急发布"

# 3. 推送并创建PR到main
git push origin hotfix/critical-bug-fix-$(date +%Y%m%d)
# 创建PR到main分支，请求紧急审查

# 4. 合并到main后，同步到develop
git checkout main
git merge hotfix/critical-bug-fix-$(date +%Y%m%d)
git tag -a v版本号.hotfix.1 -m "Hotfix: 修复关键问题"
git push origin main --tags

git checkout develop
git merge main
git push origin develop

# 5. 删除热修复分支
git branch -d hotfix/critical-bug-fix-$(date +%Y%m%d)
git push origin --delete hotfix/critical-bug-fix-$(date +%Y%m%d)
```

## 发布流程
```bash
# 1. 创建发布分支
git checkout develop
git pull origin develop
git checkout -b release/v2.1.0-$(date +%Y%m%d)

# 2. 发布准备
# - 更新版本号
# - 更新CHANGELOG.md
# - 完善文档
# - 最终测试

# 3. 推送发布分支
git push origin release/v2.1.0-$(date +%Y%m%d)
# 创建PR到main进行最终审查

# 4. 合并到main并打标签
git checkout main
git merge release/v2.1.0-$(date +%Y%m%d)
git tag -a v2.1.0 -m "Release v2.1.0: 添加资产监控和分支管理优化"
git push origin main --tags

# 5. 同步到develop
git checkout develop
git merge main
git push origin develop

# 6. 删除发布分支
git branch -d release/v2.1.0-$(date +%Y%m%d)
git push origin --delete release/v2.1.0-$(date +%Y%m%d)
```

## 常见问题解决

### CI检查失败
```bash
# 检查代码格式
cd backend && uv run ruff format src/
cd frontend && npm run lint:fix

# 检查类型错误
cd backend && uv run mypy src/
cd frontend && npm run type-check

# 运行测试
cd backend && uv run python -m pytest tests/ -v
cd frontend && npm test
```

### 合并冲突
```bash
# 解决合并冲突
git checkout develop
git pull origin develop
git merge feature/your-branch

# 手动解决冲突后
git add .
git commit -m "resolve: 解决合并冲突"
git push origin develop
```

### 分支状态检查
```bash
# 查看分支状态
git branch -vv
git log --oneline --graph --decorate --all

# 检查分支是否落后
git fetch origin
git status
```

---

**重要提醒**:
- 始终基于正确的分支创建新分支
- 遵循提交信息规范
- 及时同步远程变更
- 定期清理无用分支
- 保持分支生命周期简短