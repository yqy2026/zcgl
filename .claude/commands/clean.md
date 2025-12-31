# 项目文件清理任务

请整理项目文件目录结构，删除或移除已损坏、过期、重复或不再使用的无效文件，确保剩余文件组织有序、命名规范，以维护项目的整洁性和可维护性。

## 执行策略

本任务采用 **双阶段清理策略**：

### 阶段 1: 智能扫描（使用 cleanup_project.py）
首先使用项目的智能清理脚本进行自动化扫描：

```bash
# 预览模式 - 安全查看将清理的文件
python scripts/cleanup_project.py --dry-run

# 确认后执行实际清理
python scripts/cleanup_project.py --confirm
```

**脚本功能**：
- 基于正则模式智能匹配临时文件
- 自动分类：测试输出、临时数据库、缓存目录、构建产物
- 安全保护：保护核心配置文件，支持 DRY RUN 预览
- 智能更新 .gitignore 规则

### 阶段 2: 人工审查
审查脚本扫描结果，补充处理以下需要人工判断的文件：

**需要人工审查的文件类型**：
- `.md` 文档（合并后的分支文档）
- 备份变体文件（`.py.new_*`、`*_backup.py`）
- 已删除的测试文件（git status 中显示为 `D` 状态）
- 临时分析脚本和工具文件

---

## 执行步骤

### 步骤 1: 环境检查
```bash
# 确认 Git 工作区状态
git status

# 如果有未提交的更改，先处理或暂存
git stash    # 暂存更改
```

### 步骤 2: 智能扫描
```bash
# 运行清理脚本预览
python scripts/cleanup_project.py --dry-run
```

**审查脚本输出**：
- 检查发现的文件列表
- 确认分类是否正确
- 识别需要保留的文件

### 步骤 3: 人工补充审查
根据项目当前状态，检查以下文件：

**Git 状态中标记为删除的文件**（可安全清理）：
```
D .playwright-mcp/*.png
D frontend/docs/api-response-*.md
D frontend/scripts/*.js
D backend/tests/unit/final_*.py
```

**临时/变体文件**（需人工确认）：
- `backend/src/api/v1/auth.py.new_me_endpoint`
- `frontend/src/test-response-extraction.ts`
- `database/CLAUDE.md`（如果已合并到主文档）

### 步骤 4: 执行清理
```bash
# 确认无误后执行清理
python scripts/cleanup_project.py --confirm

# 或使用 git 清理已删除文件的跟踪
git clean -fd    # 清理未跟踪的文件
```

### 步骤 5: 验证结果
```bash
# 检查清理结果
git status
git diff --stat

# 确认项目仍可正常运行
npm run type-check    # 前端类型检查
pytest -m unit        # 后端单元测试
```

---

## 安全规则

### 禁止自动删除
以下文件类型需要人工确认后才能删除：
- 源代码文件：`.ts`、`.tsx`、`.py`、`.sql`
- 配置文件：`.env.example`、`*.toml`、`*.yaml`
- 核心文档：`CLAUDE.md`、`README.md`、`docs/` 目录
- Git 相关：`.gitignore`、`.gitattributes`

### 需要特别确认
- 任何 `.md` 文档（可能包含重要知识）
- 测试文件（确认未被引用）
- 包含业务逻辑的脚本

---

## 项目特定规则

### 土地物业资产管理系统特定清理

**可安全删除**：
- `.playwright-mcp/` - Playwright 调试截图
- `backend/htmlcov/` - 覆盖率 HTML 报告
- `backend/ruff-report.json` - Ruff 检查报告
- `frontend/scripts/api-response-*.js` - 临时分析脚本
- `frontend/docs/api-response-*.md` - 临时分析文档

**需确认后删除**：
- `backend/src/api/v1/auth.py.new_me_endpoint` - 确认新端点已实现
- `database/CLAUDE.md` - 确认内容已合并到 `docs/`
- `openspec/AGENTS.md` - 确认已合并到主文档

**定期清理**：
- PDF 导入会话文件：保留最近 30 天
- 数据库备份：保留最近 10 个（脚本自动处理）

---

## 清理报告模板

执行清理后，生成以下报告：

```
## 清理报告

### 清理统计
- 删除文件数: XX
- 删除目录数: XX
- 释放空间: XX MB
- 扫描耗时: XX 秒

### 清理分类
1. 测试输出: XX 文件
2. 临时数据库: XX 文件
3. 缓存目录: XX 目录
4. 构建产物: XX 文件
5. 调试产物: XX 文件

### 人工审查结果
- 保留文件: [列出保留的文件及原因]
- 特殊处理: [需要特殊处理的文件]

### 验证结果
- 前端类型检查: ✓/✗
- 后端单元测试: ✓/✗
- 项目构建: ✓/✗
```

---

## 清理脚本参数说明

```bash
python scripts/cleanup_project.py [选项]

选项:
  --dry-run    预览模式（默认），不实际删除文件
  --confirm    执行模式，实际删除文件
  --backup     在删除前创建备份
  --verbose    详细输出模式

示例:
  # 预览将要清理的文件
  python scripts/cleanup_project.py --dry-run

  # 确认后执行清理
  python scripts/cleanup_project.py --confirm

  # 带详细输出的清理
  python scripts/cleanup_project.py --confirm --verbose
```

---

## 智能模式匹配规则

清理脚本使用以下模式自动发现文件：

| 类别 | 模式示例 | 说明 |
|------|----------|------|
| 测试输出 | `.coverage$`, `htmlcov$` | 覆盖率报告 |
| 临时数据库 | `test.*\.db$`, `.*\.db-(shm|wal)$` | 测试数据库 |
| 临时脚本 | `.*_coverage\.py$`, `check_.*\.py$` | 分析脚本 |
| 缓存目录 | `__pycache__`, `..*_cache$` | Python/工具缓存 |
| 构建产物 | `*-report\.(json|xml)$` | 分析报告 |
| 调试产物 | `.playwright-mcp$` | 调试输出 |

---

## 故障恢复

如果清理后出现问题：

```bash
# 查看清理前的状态
git reflog

# 恢复到清理前的状态
git reset --hard HEAD@{N}

# 从备份恢复（如果使用了 --backup）
ls -la .cleanup_backup_*
```
