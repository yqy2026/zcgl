# 代码质量自动化检查指南

## 📋 概述

本文档介绍如何使用代码质量自动化检查工具，确保代码符合项目标准。

## 🚀 快速开始

### 1. 本地代码质量检查

在提交代码前，运行以下命令进行代码质量检查：

```bash
cd backend
uv run python local_code_quality_check.py
```

### 2. 手动运行各项检查

#### Ruff 代码检查
```bash
# 检查关键错误类型
uv run ruff check src/ --select=F821,F811,E722,E402

# 检查所有问题
uv run ruff check src/

# 自动修复问题
uv run ruff check src/ --fix
```

#### 代码格式化
```bash
# 检查格式
uv run ruff format --check src/

# 自动格式化
uv run ruff format src/
```

#### MyPy 类型检查
```bash
# 检查核心文件
uv run mypy src/main.py src/core/config.py src/services/auth_service.py

# 检查整个项目
uv run mypy src/ --ignore-missing-imports
```

## 📊 检查项目说明

### ✅ 关键错误类型（必须修复）

| 错误代码 | 描述 | 影响 | 状态 |
|---------|------|------|------|
| **F821** | 未定义名称 | 导致运行时错误 | ✅ 已修复 (0个) |
| **F811** | 重复定义 | 代码逻辑混乱 | ✅ 已修复 (0个) |
| **E722** | 裸异常处理 | 错误处理不当 | ✅ 已修复 (0个) |

### ⚠️ 次要问题（建议修复）

| 错误代码 | 描述 | 影响 | 状态 |
|---------|------|------|------|
| **E402** | 导入顺序 | 代码组织性 | 🟡 部分修复 (881→~400个) |
| **格式问题** | 代码格式 | 可读性 | 🟡 需要格式化 |
| **类型问题** | 类型注解 | 类型安全 | 🟡 有待改善 |

## 🔧 自动化设置

### Git Hooks 集成

#### 方法 1: 使用本地脚本（推荐）

1. 将 `local_code_quality_check.py` 添加到 PATH
2. 在提交前运行检查：

```bash
python local_code_quality_check.py
```

#### 方法 2: 使用 Pre-commit（需要网络）

```bash
# 安装 hooks
uv run pre-commit install

# 手动运行
uv run pre-commit run --all-files
```

### CI/CD 集成

在 CI/CD 流程中添加以下步骤：

```yaml
- name: 代码质量检查
  run: |
    cd backend
    uv run python local_code_quality_check.py
```

## 📈 质量标准

### ✅ 通过标准

代码必须满足以下条件才能提交：

1. **无关键错误**: F821、F811、E722 错误数量为 0
2. **核心文件可导入**: main.py 等核心文件能正常导入
3. **基本功能正常**: 系统能启动并响应基本请求

### 📝 质量门禁

| 检查项目 | 通过标准 | 阻止提交 |
|---------|---------|----------|
| F821/F811/E722 | 0个 | ✅ 是 |
| 核心文件导入 | 成功 | ✅ 是 |
| 代码格式 | 建议修复 | ❌ 否 |
| E402导入 | 建议修复 | ❌ 否 |
| MyPy类型 | 建议修复 | ❌ 否 |

## 🛠️ 常见问题修复

### 1. 格式问题修复

```bash
# 自动格式化所有文件
uv run ruff format src/
```

### 2. 导入顺序修复

```bash
# 自动修复导入问题（仅限简单情况）
uv run ruff check src/ --select=E402 --fix
```

### 3. 未使用导入清理

```bash
# 自动移除未使用的导入
uv run ruff check src/ --select=F401 --fix
```

### 4. 类型错误修复

常见类型错误及修复方法：

```python
# 修复前
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price  # 类型不明确
    return total

# 修复后
from typing import List
from pydantic import BaseModel

class Item(BaseModel):
    price: float

def calculate_total(items: List[Item]) -> float:
    total = 0.0
    for item in items:
        total += item.price
    return total
```

## 📋 检查清单

在提交代码前，请确认：

- [ ] 运行 `uv run python local_code_quality_check.py`
- [ ] 所有关键错误（F821、F811、E722）已修复
- [ ] 核心文件可以正常导入
- [ ] 系统可以正常启动
- [ ] 基本功能测试通过

## 🎯 最佳实践

### 1. 开发流程

1. **编写代码** → 按照项目规范编写功能代码
2. **本地检查** → 运行 `python local_code_quality_check.py`
3. **修复问题** → 根据检查结果修复发现的问题
4. **功能测试** → 确保功能正常工作
5. **提交代码** → Git commit

### 2. 代码质量标准

- **命名规范**: 使用清晰、描述性的变量和函数名
- **类型注解**: 为公共接口添加类型注解
- **文档字符串**: 为复杂函数添加说明文档
- **错误处理**: 使用具体的异常类型
- **代码组织**: 保持导入在文件顶部

### 3. 持续改进

- 定期运行代码质量检查
- 及时修复发现的问题
- 参与代码审查，学习最佳实践
- 关注新的代码质量工具和技术

## 📞 获取帮助

如果遇到代码质量问题：

1. 查看检查工具的详细输出
2. 参考项目中的示例代码
3. 咨询团队成员或代码审查者
4. 查阅相关工具的官方文档

---

**更新日期**: 2025年11月3日
**维护者**: 开发团队
**版本**: 1.0