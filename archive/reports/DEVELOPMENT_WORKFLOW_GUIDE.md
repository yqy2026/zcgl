# 开发工作流指南

**创建时间**: 2025-11-01 18:45:00 UTC
**项目**: 地产资产管理系统 (zcgl)
**适用**: 所有开发团队成员
**版本**: v1.0

## 🎯 工作流概述

本文档定义了地产资产管理系统的标准化开发工作流，基于我们完善的分支管理架构，确保团队协作高效、代码质量优秀、部署流程顺畅。

## 🌳 分支架构回顾

### 📋 分支职责
```
🌟 main                          # 主分支 (生产环境)
├── 用途: 生产环境部署
├── 特点: 企业级监控系统完整
├── 更新: 仅来自develop分支的合并
└── 保护: 直接推送受限

🚀 develop                       # 开发分支 (开发环境)
├── 用途: 功能开发和集成测试
├── 特点: 企业级功能 + 项目结构优化
├── 更新: 功能开发和定期同步
└── 状态: 持续开发中
```

## 🔄 标准开发工作流

### 阶段一：功能开发

#### 📝 创建功能分支
```bash
# 1. 确保在最新develop分支
git checkout develop
git pull origin develop

# 2. 创建功能分支
git checkout -b feature/新功能描述

# 3. 推送远程分支
git push -u origin feature/新功能描述
```

#### ✅ 功能分支命名规范
- **格式**: `feature/功能简述`
- **示例**: `feature/user-authentication`
- **示例**: `feature/pdf-ocr-enhancement`
- **示例**: `feature/system-monitoring`

#### 🛠️ 开发环境启动
```bash
# 后端开发
cd backend
uv run python run_dev.py  # 端口 8002

# 前端开发
cd frontend
npm run dev               # 端口 5173

# 验证功能
curl http://localhost:8002/api/v1/health
```

### 阶段二：代码质量检查

#### 🔍 本地质量检查
```bash
# 后端质量检查
cd backend
uv run ruff check src/           # 代码风格检查
uv run mypy src/                # 类型检查
uv run python -m pytest tests/ -v  # 运行测试

# 前端质量检查
cd frontend
npm run lint                   # ESLint检查
npm run type-check             # TypeScript检查
npm test                      # 运行测试
```

#### 📊 质量标准
- **Ruff**: 0个错误，< 5个警告
- **MyPy**: 类型检查通过率 > 95%
- **ESLint**: 0个错误，< 3个警告
- **测试覆盖**: 核心功能必须有测试

### 阶段三：代码提交

#### 📝 提交规范
```bash
# 添加文件
git add .

# 提交代码
git commit -m "🎯 添加用户认证功能

## 主要变更
- 实现用户登录和注册API
- 添加JWT token认证机制
- 完善用户权限验证

## 测试验证
- [x] 单元测试通过
- [x] 集成测试通过
- [x] 手动测试通过

## 文档更新
- [x] API文档更新
- [x] 用户指南更新
```

#### ✅ 提交消息规范
- **标题**: 简洁描述变更内容
- **正文**: 详细说明变更细节
- **测试**: 列出测试验证项
- **文档**: 标注文档更新状态

### 阶段四：创建Pull Request

#### 📋 PR创建流程
```bash
# 1. 推送到远程
git push origin feature/新功能描述

# 2. 创建PR (通过GitHub界面或CLI)
gh pr create --title "🎯 添加用户认证功能" --body "$(cat pr_template.md)"
```

#### 📝 PR模板
```markdown
## 🎯 功能概述
[简明描述功能和业务价值]

## 📊 主要变更
- **新增功能**: [具体新增功能]
- **改进优化**: [具体改进内容]
- **修复问题**: [修复的具体问题]
- **技术债务**: [解决的技术债务]

## 🧪 测试验证
- [x] 单元测试通过
- [x] 集成测试通过
- [x] 手动测试通过
- [x] 性能测试通过

## 📋 部署注意事项
1. [ ] 数据库迁移脚本
2. [ ] 环境变量更新
3. [ ] 依赖更新要求
4. [ ] 配置文件变更
5. [ ] 回滚方案准备

## 🎯 影响评估
- **兼容性**: ✅ 向后兼容
- **风险等级**: 🟢 低风险
- **测试覆盖**: ✅ 充分
```

### 阶段五：代码审查

#### 👀 审查检查清单
- [ ] **代码结构**: 符合项目架构规范
- [ ] **命名规范**: 遵循命名约定
- [ ] **错误处理**: 完善的异常处理机制
- [ ] **日志记录**: 适当的日志记录
- [ ] **性能考虑**: 性能优化和资源使用
- [ ] **安全性**: 输入验证和权限检查
- [ ] **可维护性**: 代码清晰易于维护
- [ ] **测试覆盖**: 核心功能有测试验证

#### 🔍 审查流程
1. **自动检查**: CI/CD系统自动验证
2. **代码审查**: 至少一名团队成员审核
3. **功能测试**: 功能和集成测试
4. **技术审查**: 架构和技术设计审核
5. **最终批准**: 负责人最终批准

### 阶段六：合并部署

#### 🚀 合并到develop分支
```bash
# 1. 合并到develop (自动或手动)
# 自动化：CI/CD自动合并
# 手动：代码审查通过后手动合并

# 2. 更新develop分支
git checkout develop
git pull origin develop
```

#### 🔄 定期同步到main分支
```bash
# 每周执行一次或重大功能完成后
git checkout main
git pull origin main
git merge develop --no-ff
git push origin main
```

## 🛡️ 质量门禁

### 🔒 强制要求
- **代码质量**: 必须通过所有自动化检查
- **测试覆盖**: 核心功能必须有测试验证
- **文档更新**: 相关文档必须同步更新
- **向后兼容**: 不破坏现有API接口
- **安全检查**: 必须通过安全扫描检查

### 📊 CI/CD检查项
```yaml
CI检查项目:
  - ✅ 代码风格检查 (Ruff, ESLint)
  - ✅ 类型检查 (MyPy, TypeScript)
  - ✅ 安全扫描 (bandit, 依赖检查)
  - ✅ 单元测试执行
  - ✅ 集成测试执行
  - ✅ 构建验证
  - ✅ API一致性检查
```

## 🚨 应急处理流程

### 🔄 热修复流程
```bash
# 1. 创建热修复分支
git checkout main
git checkout -b hotfix/问题描述

# 2. 快速修复
# 进行紧急修复...

# 3. 测试验证
# 快速测试验证...

# 4. 合并和部署
git checkout main
git merge hotfix/问题描述 --no-ff
git push origin main

# 5. 同步到develop
git checkout develop
git merge main --no-ff
git push origin develop
```

### 📋 问题分级
- **🔴 严重**: 生产环境故障，立即修复
- **🟡 中等**: 功能异常，24小时内修复
- **🟢 轻微**: 体验问题，一周内修复

## 📚 协作规范

### 👥 团队协作
- **并行开发**: 不同功能可在不同分支并行开发
- **代码审查**: 每个PR必须有代码审查
- **知识共享**: 重要决策和架构变更需要团队讨论
- **文档维护**: 代码变更必须同步更新文档

### 📝 沟通规范
- **PR描述**: 清晰描述变更内容和测试方法
- **Issue管理**: 使用GitHub Issues跟踪问题和任务
- **会议纪要**: 重要会议需要记录纪要
- **技术分享**: 定期进行技术分享和培训

## 🔧 开发工具配置

### 🛠️ 必需工具
- **IDE**: VS Code (推荐配置已提供)
- **Git**: 最新版本Git
- **Node.js**: 18.0+
- **Python**: 3.12+ with UV
- **Docker**: 容器化部署支持

### ⚙️ IDE配置
```json
// VS Code 推荐插件
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.mypy-type-checker",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-vscode.vscode-typescript-next"
  ]
}
```

### 📋 环境配置
```bash
# 环境变量配置
cp .env.example .env
# 编辑环境变量...

# 开发环境配置
./scripts/setup-dev.sh

# 测试环境配置
./scripts/setup-test.sh
```

## 📊 性能监控

### 📈 监控指标
- **系统性能**: CPU、内存、磁盘、网络
- **应用性能**: API响应时间、错误率
- **用户体验**: 页面加载时间、交互响应
- **代码质量**: 技术债务、测试覆盖率

### 🛡️ 告警机制
- **系统告警**: 资源使用超过阈值
- **应用告警**: 错误率超过阈值
- **性能告警**: 响应时间超过阈值
- **安全告警**: 安全检测到异常

## 🔄 持续改进

### 📅 定期活动
- **每日**: 代码质量检查、监控报告
- **每周**: 分支状态检查、性能优化
- **每月**: 技术债务清理、架构评审
- **每季度**: 工具升级、流程优化

### 🎯 改进目标
- **代码质量**: 持续提升代码质量标准
- **开发效率**: 优化开发工具和流程
- **团队协作**: 改进沟通和协作机制
- **技术栈**: 跟进新技术和最佳实践

## 📋 快速参考

### 🚀 常用命令
```bash
# 开发环境启动
cd backend && uv run python run_dev.py
cd frontend && npm run dev

# 质量检查
cd backend && uv run ruff check src/
cd frontend && npm run lint

# 测试执行
cd backend && uv run python -m pytest tests/
cd frontend && npm test

# 分支操作
git checkout develop
git pull origin develop
git checkout -b feature/新功能
git push -u origin feature/新功能
```

### 📞 联系支持
- **技术问题**: GitHub Issues
- **流程问题**: 团队沟通渠道
- **培训需求**: 技术负责人
- **紧急情况**: 项目经理

---

**文档版本**: v1.0
**最后更新**: 2025-11-01 18:45:00 UTC
**维护团队**: 开发团队全体
**审核人**: 技术负责人

*本工作流将根据实际使用情况定期更新和改进*

🚀 **遵循此工作流，确保高质量、高效率的软件开发！**