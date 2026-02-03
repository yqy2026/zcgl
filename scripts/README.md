# Scripts 文档

本目录包含项目开发过程中使用的各种辅助脚本。

---

## 🚀 快速开始 - 项目检查入口

项目检查已统一到根目录 `Makefile`。

```bash
make check
```

默认包含：
- 代码质量检查（后端 Ruff、前端 ESLint、TS 类型检查）
- 后端单元测试与前端测试
- 前端构建与后端导入验证

默认输出到控制台；如需日志，请自行重定向到 `logs/`。

---

## 1. check_file_naming.py

**文件命名规范检查脚本** - 自动检查前端和后端文件是否符合项目命名规范。

### 功能特性

- ✅ 自动检测前端（TypeScript/TSX）文件命名
- ✅ 自动检测后端（Python）文件命名
- ✅ 根据文件路径智能应用不同的命名规则
- ✅ 提供清晰的错误提示和修复建议
- ✅ 支持 Windows/Linux/macOS 跨平台使用

### 使用方法

```bash
# 检查单个文件
python scripts/check_file_naming.py frontend/src/hooks/useAuth.ts

# 检查多个文件
python scripts/check_file_naming.py frontend/src/hooks/*.ts

# 检查整个目录
python scripts/check_file_naming.py frontend/src/components/**/*.tsx
```

### 命名规则

#### Frontend (TypeScript/TSX)

| 文件类型 | 路径位置 | 命名规则 | 示例 |
|---------|---------|---------|------|
| 组件文件 | `components/` | PascalCase | `AssetForm.tsx`, `Dashboard.tsx` |
| Hook 文件 | `hooks/` | `use` 前缀 + PascalCase | `useAuth.ts`, `useAssets.ts` |
| 页面文件 | `pages/` | PascalCase | `AssetListPage.tsx` |
| 测试文件 | `**/__tests__/` | `.test.` 后缀 | `AssetList.test.tsx` |
| Store 文件 | `store/` | `use` 前缀 + PascalCase | `useAppStore.ts` |
| Service/Util | `services/`, `utils/` | camelCase | `format.ts`, `authService.ts` |

#### Backend (Python)

| 文件类型 | 命名规则 | 示例 |
|---------|---------|------|
| 源代码文件 | snake_case | `asset_service.py`, `rent_contract.py` |
| 测试文件 | `test_` 前缀 或 `_test.py` 后缀 | `test_auth.py`, `auth_test.py` |

### 输出示例

**✅ 通过检查：**
```bash
$ python scripts/check_file_naming.py frontend/src/hooks/useAuth.ts
✅ 所有文件命名符合规范！
```

**❌ 未通过检查：**
```bash
$ python scripts/check_file_naming.py frontend/src/hooks/UseAuth.ts

❌ 发现 1 个文件命名问题：

❌ frontend/src/hooks/UseAuth.ts
   Hook 文件应使用 use 前缀 + PascalCase
   当前: UseAuth.ts
   期望: use{FeatureName}.ts
```

### 通过 Pre-commit 自动运行

安装后每次提交会自动检查：
```bash
pip install pre-commit
pre-commit install
```

详细文档请参考：[命名规范 - 文件命名规范](../docs/guides/NAMING_CONVENTIONS.md#9-文件命名规范)

---

## 2. cleanup_project.py

**智能项目清理脚本** - 使用模式匹配自动发现并清理临时文件、缓存文件和无效文件。

### 概述

## 核心特性

### 🧠 智能发现
- **自动模式匹配**：基于文件名和路径模式自动识别临时文件
- **无需维护列表**：不需要手动更新要删除的文件列表
- **适应性强**：自动适应项目结构变化

### 🔍 智能分类
- **测试输出**：覆盖率报告、JUnit报告、HTML报告等
- **临时数据库**：测试数据库、临时SQLite文件等
- **临时脚本**：基于命名模式识别的分析脚本
- **缓存目录**：各种工具的缓存目录
- **构建产物**：编译输出、报告文件等
- **调试产物**：调试工具生成的文件

## 使用方法

### 预览模式（推荐先运行）
```bash
python scripts/cleanup_project.py --dry-run
```

### 执行清理
```bash
python scripts/cleanup_project.py --confirm
```

### 带备份的清理
```bash
python scripts/cleanup_project.py --backup --confirm
```

## 智能匹配规则

### 文件模式匹配
```python
# 测试输出文件
r'\.coverage$'
r'coverage\.(json|xml)$'
r'junit-report\.xml$'

# 临时数据库文件
r'test.*\.db$'
r'.*\.db-(shm|wal|journal)$'

# 临时脚本（智能识别）
r'backend/(check|find|get|analyze)_.*\.py$'
r'backend/.*_coverage\.py$'
r'backend/.*_missing\.py$'

# 缓存目录
r'\..*_cache$'
r'__pycache__$'
```

### 保护机制
- **保护重要文件**：永远不会删除关键配置文件
- **排除系统目录**：自动跳过 `.git`、`node_modules` 等
- **深度限制**：防止过深递归扫描

## 示例输出

```
============================================================
智能项目清理脚本
模式: DRY RUN (预览)
============================================================

[扫描] 智能扫描项目文件...
  发现 114 个可清理文件

[测试输出] 清理 18 个文件/目录...
[临时数据库] 清理 8 个文件/目录...
[临时脚本] 清理 67 个文件/目录...
[缓存目录] 清理 7 个文件/目录...
[构建产物] 清理 14 个文件/目录...

[空目录] 智能检查空目录...
  发现 20 个空目录

[.gitignore] 智能更新 .gitignore...
  建议添加 8 个规则

============================================================
清理摘要
============================================================
删除的文件: 155
释放空间: 20.7 MB
```

## 优势对比

### 🆚 传统方式 vs 智能方式

| 特性 | 传统硬编码 | 智能模式匹配 |
|------|------------|--------------|
| 维护成本 | 需要手动更新文件列表 | **零维护** |
| 发现能力 | 只能删除预定义文件 | **自动发现新文件** |
| 适应性 | 项目变化需要更新脚本 | **自动适应** |
| 覆盖范围 | 有限 | **全面** |
| 误删风险 | 低但覆盖不全 | **智能保护** |

### 📊 实际效果
- **发现文件数量**：从72个提升到155个
- **释放空间**：从11MB提升到20.7MB
- **维护工作量**：从需要手动更新到零维护

## 安全特性

1. **默认预览模式**：不会意外删除文件
2. **智能保护**：自动保护重要文件和目录
3. **交互确认**：重要操作需要用户确认
4. **详细日志**：显示每个操作的详细信息
5. **错误处理**：优雅处理权限和访问错误

## 配置说明

脚本使用正则表达式模式匹配，主要配置在 `FILE_PATTERNS` 字典中：

```python
FILE_PATTERNS = {
    'test_outputs': [...],    # 测试输出文件模式
    'temp_databases': [...],  # 临时数据库模式
    'temp_scripts': [...],    # 临时脚本模式
    'cache_dirs': [...],      # 缓存目录模式
    'build_artifacts': [...], # 构建产物模式
    'debug_artifacts': [...], # 调试产物模式
}
```

## 注意事项

1. **首次使用**：建议先运行 `--dry-run` 查看效果
2. **定期清理**：可以定期运行保持项目整洁
3. **自定义模式**：可以根据项目需要调整匹配模式
4. **备份重要数据**：虽然有保护机制，但重要数据建议先备份
