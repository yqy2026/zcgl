# Git Flow 工作流指南

## 📋 分支策略

本项目采用 **Git Flow** 分支管理策略，确保代码质量和发布流程的规范性。

```
main (生产)
  ↑
  ├── merge (release)
  ↑
develop (开发)
  ↑
  ├── merge (feature)
  ↑
feature/* (功能分支)
hotfix/* (紧急修复)
release/* (发布准备)
```

---

## 🌳 分支说明

### 主要分支 (Main Branches)

| 分支 | 用途 | 环境 | 保护规则 |
|------|------|------|----------|
| `main` | 生产环境代码 | Production | 🔒 受保护，仅接受 merge |
| `develop` | 日常开发集成分支 | Development/Staging | 🔒 受保护，仅接受 merge |

### 辅助分支 (Supporting Branches)

| 分支类型 | 命名规范 | 来源 | 合并到 |
|----------|----------|------|--------|
| `feature` | `feature/功能描述` | `develop` | `develop` |
| `hotfix` | `hotfix/问题描述` | `main` | `main` + `develop` |
| `release` | `release/x.y.z` | `develop` | `main` + `develop` |

---

## 🔄 工作流程

### 1. 开发新功能 (Feature)

```bash
# 从 develop 创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/添加用户登录功能

# 开发代码...
# 提交更改
git add .
git commit -m "feat: 添加用户登录功能"

# 推送到远程
git push -u origin feature/添加用户登录功能

# 完成后合并回 develop（通过 Pull Request）
# 合并后删除功能分支
git branch -d feature/添加用户登录功能
```

### 2. 修复生产问题 (Hotfix)

```bash
# 从 main 创建紧急修复分支
git checkout main
git pull origin main
git checkout -b hotfix/修复登录超时问题

# 修复代码...
git commit -m "fix: 修复登录超时问题"

# 推送并合并
git push -u origin hotfix/修复登录超时问题

# 同时合并到 main 和 develop
# 合并后打上版本标签
git tag -a v1.0.1 -m "Hotfix: 修复登录超时"
git push origin v1.0.1
```

### 3. 准备发布 (Release)

```bash
# 从 develop 创建发布分支
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0

# 发布准备：更新版本号、修复bug、生成文档
git commit -m "chore: 准备 v1.2.0 发布"

# 合并到 main（生产）
git checkout main
git merge release/v1.2.0
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin main v1.2.0

# 合并回 develop
git checkout develop
git merge release/v1.2.0
git push origin develop

# 删除发布分支
git branch -d release/v1.2.0
```

---

## 📝 提交规范

使用 **Conventional Commits** 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型 (Type)

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(auth): 添加 OAuth2 登录` |
| `fix` | Bug 修复 | `fix(api): 修复查询参数解析错误` |
| `docs` | 文档更新 | `docs: 更新 API 文档` |
| `style` | 代码格式 | `style: 统一代码缩进` |
| `refactor` | 重构 | `refactor(database): 优化查询性能` |
| `perf` | 性能优化 | `perf(frontend): 减少包体积` |
| `test` | 测试相关 | `test: 添加单元测试` |
| `chore` | 构建/工具 | `chore: 更新依赖版本` |

---

## 🛡️ 分支保护规则

### main 分支
- ✅ 需要Pull Request审查
- ✅ 需要通过所有CI检查
- ✅ 禁止直接推送
- ✅ 需要至少1个审查批准

### develop 分支
- ✅ 需要Pull Request审查
- ✅ 需要通过CI检查
- ✅ 禁止直接推送

---

## 🔧 安装 Git Flow 工具 (可选)

### Windows
```bash
# 使用 Windows Package Manager
winget install GitExtensionsTeam.GitFlow

# 或使用 scoop
scoop install git-flow
```

### macOS
```bash
brew install git-flow-avh
```

### Linux
```bash
# Ubuntu/Debian
sudo apt-get install git-flow

# Fedora
sudo dnf install gitflow
```

### 使用 Git Flow 工具
```bash
# 初始化 git flow
git flow init

# 开始新功能
git flow feature start 添加用户登录

# 完成功能
git flow feature finish 添加用户登录

# 开始发布
git flow release start v1.2.0

# 完成发布
git flow release finish v1.2.0
```

---

## 📌 常见场景

### 场景 1: 日常功能开发
```
1. git checkout develop
2. git checkout -b feature/your-feature
3. 开发并提交
4. 推送并创建 Pull Request 到 develop
5. 代码审查通过后合并
6. 删除功能分支
```

### 场景 2: 生产环境紧急修复
```
1. git checkout main
2. git checkout -b hotfix/critical-fix
3. 修复并提交
4. 推送并创建 Pull Request
5. 同时合并到 main 和 develop
6. 打标签推送
```

### 场景 3: 版本发布
```
1. git checkout develop
2. git checkout -b release/v1.0.0
3. 发布准备（版本号、文档、测试）
4. 合并到 main 并打标签
5. 合并回 develop
6. 部署到生产环境
```

---

## 🚀 当前分支状态

```
* main         - 生产环境 (430e327)
  develop      - 开发环境 (9d16e6f)
```

---

## 📚 参考资源

- [Git Flow 原文](https://nvie.com/posts/a-successful-git-branching-model/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Flow](https://docs.github.com/en/get-started/quickstart/github-flow)

---

**更新日期**: 2025-12-31
**维护者**: 开发团队
