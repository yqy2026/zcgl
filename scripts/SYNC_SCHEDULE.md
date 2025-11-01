# 分支同步调度配置

**创建时间**: 2025-11-01 18:45:00 UTC
**项目**: 地产资产管理系统 (zcgl)
**用途**: 定期同步main分支的修复和改进到develop分支

## 🕒 调度策略

### 📅 定期同步计划

#### 🔄 每周同步 (推荐)
```bash
# 每周一早上自动执行
# Linux/macOS (crontab)
0 9 * * 1 /path/to/zcgl/scripts/sync-branches.sh

# Windows (任务计划程序)
# 创建任务计划程序任务，每周一 9:00 AM 执行
# 程序: C:\path\to\zcgl\scripts\sync-branches.bat
```

#### 📋 事件触发同步
- **main分支重大更新后**: 自动触发同步
- **安全修复发布后**: 立即同步到develop
- **性能优化合并后**: 同步到开发环境

### 📊 同步触发条件

#### ✅ 自动触发条件
1. **定期执行**: 按照配置的时间表
2. **重大发布**: main分支有重大更新
3. **安全更新**: 安全相关修复
4. **性能优化**: 重要性能改进

#### 🚫 跳过条件
1. **开发中功能**: develop分支有未完成的功能开发
2. **测试进行中**: 正在进行重要测试
3. **手动暂停**: 团队手动暂停同步
4. **冲突未解决**: 上次同步冲突未处理

## 🔧 同步配置

### 📋 配置文件位置
```
项目根目录/
├── scripts/
│   ├── sync-branches.sh          # Linux/macOS同步脚本
│   ├── sync-branches.bat         # Windows同步脚本
│   └── SYNC_SCHEDULE.md         # 本配置文件
├── .sync-config/
│   ├── sync-settings.json       # 同步配置
│   ├── sync-excludes.txt       # 排除文件列表
│   └── sync-hooks.json         # 同步钩子配置
```

### ⚙️ 同步配置示例
```json
{
  "sync_settings": {
    "auto_sync_enabled": true,
    "backup_enabled": true,
    "conflict_resolution": "manual",
    "verification_enabled": true,
    "notification_enabled": true
  },
  "schedule": {
    "frequency": "weekly",
    "day_of_week": 1,
    "time": "09:00",
    "timezone": "UTC"
  },
  "exclusions": [
    "*.log",
    "node_modules/",
    ".venv/",
    "dist/",
    "*.tmp"
  ],
  "notifications": {
    "email": ["dev-team@company.com"],
    "slack": "#dev-alerts",
    "webhook": "https://api.company.com/webhooks/sync"
  }
}
```

## 🔔 同步钩子

### 📋 钩子类型

#### 🔍 预同步钩子 (Pre-Sync)
```bash
#!/bin/bash
# pre-sync.sh
# 在同步前执行的检查

echo [HOOK] 执行预同步检查...

# 检查开发环境状态
cd backend && uv run python -c "from src.api.v1.system_monitoring import collect_system_metrics"

# 检查前端构建状态
cd frontend && npm run build > /dev/null

# 检查测试状态
cd backend && uv run python -m pytest tests/ --tb=short > /dev/null

echo [HOOK] 预同步检查完成
```

#### 📝 同步后钩子 (Post-Sync)
```bash
#!/bin/bash
# post-sync.sh
# 在同步成功后执行的操作

echo [HOOK] 执行同步后操作...

# 通知团队
echo "分支同步完成，请检查: $(git log --oneline -1)" | mail -s "分支同步通知" dev-team@company.com

# 更新文档
# git checkout main && git checkout develop && git merge main --no-ff

# 生成同步报告
echo "同步完成时间: $(date)" > SYNC_COMPLETION_REPORT.md

echo [HOOK] 同步后操作完成
```

## 📊 同步监控

### 📈 监控指标
- **同步频率**: 每周一次或按需
- **同步成功率**: 监控同步是否成功
- **冲突数量**: 跟踪合并冲突数量
- **解决时间**: 记录冲突解决耗时
- **构建状态**: 同步后构建验证状态

### 📊 报告生成
```bash
# 生成同步报告
./scripts/generate-sync-report.sh

# 查看同步历史
git log --oneline --grep="同步" | head -10
```

### 🚨 告警机制
- **同步失败**: 立即通知团队
- **大量冲突**: 需要团队协助解决
- **构建失败**: 同步后构建验证失败
- **性能影响**: 同步对开发环境的影响

## 🛠️ 安全配置

### 🔒 访问控制
- **执行权限**: 只有授权用户可执行同步
- **日志记录**: 记录所有同步操作日志
- **审计追踪**: 完整的操作审计日志

### 📝 日志配置
```bash
# 日志文件位置
logs/
├── sync/
│   ├── sync-$(date +%Y%m%d).log
│   ├── sync-errors.log
│   └── sync-report.log
```

### 🔍 日志格式
```bash
[2025-11-01 09:00:01] [INFO] 开始分支同步
[2025-11-01 09:00:02] [INFO] 当前分支: develop
[2025-11-01 09:00:03] [INFO] 检测到main分支有5个新提交
[2025-11-01 09:00:05] [INFO] 开始同步...
[2025-11-01 09:00:15] [SUCCESS] 同步完成
[2025-11-01 09:00:16] [INFO] 后端构建验证: 通过
[2025-11-01 09:00:18] [INFO] 前端构建验证: 通过
[2025-11-01 09:00:20] [SUCCESS] 同步流程完成
```

## 📞 通知配置

### 📧 邮件通知
```bash
# 发送同步结果邮件
echo "分支同步完成" | mail -s "地产资产管理系统 - 分支同步通知" dev-team@company.com
```

### 📱 Slack通知
```bash
# 发送Slack消息
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"分支同步完成，请检查更新"}' \
  https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

### 🌐 Webhook通知
```bash
# 发送自定义webhook
curl -X POST -H 'Content-type: application/json' \
  --data '{"event":"sync_completed","branch":"develop","status":"success"}' \
  https://api.company.com/webhooks/sync-status
```

## 📋 故障排除

### 🔧 常见问题

#### 问题1: 同步失败
**症状**: 同步脚本执行失败
**解决方案**:
1. 检查网络连接
2. 验证Git权限
3. 查看错误日志

#### 问题2: 构建验证失败
**症状**: 同步后构建验证失败
**解决方案**:
1. 检查依赖安装
2. 验证代码语法
3. 查看详细错误信息

#### 问题3: 合并冲突
**症状**: 出现大量合并冲突
**解决方案**:
1. 手动解决冲突
2. 使用冲突解决工具
3. 团队协作解决

### 🚨 应急处理

#### 📋 紧急恢复流程
1. **停止自动同步**: 暂停自动同步调度
2. **回滚到备份**: 使用备份分支恢复
3. **手动同步**: 手动执行同步操作
4. **通知团队**: 通知相关团队

#### 🔄 恢复步骤
```bash
# 1. 停止自动同步
# crontab -e "# 注释掉自动同步任务"

# 2. 恢复到备份
git checkout develop-backup-latest

# 3. 手动同步
git checkout develop
git merge origin/main --no-ff

# 4. 验证结果
./scripts/verify-sync.sh

# 5. 恢复自动同步
# crontab -e "0 9 * * 1 /path/to/zcgl/scripts/sync-branches.sh"
```

## 📊 同步效果评估

### 📈 成功指标
- **同步成功率**: > 95%
- **自动解决率**: > 80%
- **构建通过率**: > 90%
- **团队满意度**: > 4.5/5

### 📈 改进方向
- **自动化程度**: 提高自动化程度
- **冲突处理**: 优化冲突解决机制
- **监控能力**: 增强监控和报告
- **团队协作**: 改善协作流程

---

**配置版本**: v1.0
**创建时间**: 2025-11-01 18:45:00 UTC
**维护团队**: 开发团队
**审核人**: 技术负责人

*本配置将根据实际使用情况定期更新和改进*

🔄 **定期同步机制已建立，确保分支间功能一致性！**