# 快速开发检查命令

快速执行前端和后端的日常开发检查，确保代码质量。

## 使用场景

当你需要：
- 快速验证代码是否可用
- 提交代码前的快速检查
- 确认没有引入明显的错误
- 节省时间，不需要运行完整测试

## 执行步骤

### 步骤 1: 前端检查

```bash
cd frontend

# 1. TypeScript 类型检查
pnpm type-check

# 2. ESLint 代码规范检查
pnpm lint

# 3. CSS/SCSS 样式检查
pnpm lint:css
```

**预期结果**: 所有检查通过，无错误

### 步骤 2: 后端检查

```bash
cd backend

# 1. Ruff 代码规范和类型检查
ruff check .

# 2. Mypy 类型检查
mypy src

# 3. 单元测试（快速）
pytest -m unit -v
```

**预期结果**: 所有检查通过，测试通过

### 步骤 3: 快速构建测试

```bash
# 前端构建测试
cd frontend && pnpm build

# 后端导入测试
cd backend && python -c "from src import main; print('✓ 后端导入成功')"
```

**预期结果**: 构建成功，无导入错误

## 常见问题快速修复

### 前端 TypeScript 错误

**未使用的变量**:
```typescript
// ❌ 错误
const unused = 'hello';

// ✅ 删除或使用下划线前缀
const _unused = 'hello';
```

**类型错误**:
```typescript
// ❌ 错误
const name: string = null;

// ✅ 正确
const name: string | null = null;
const name = name ?? '';
```

### 后端类型错误

**Missing import**:
```python
# ❌ 错误
def get_user():
    return User.query.all()

# ✅ 添加导入
from src.models import User
```

## 退出码

- `0`: 所有检查通过 ✓
- `1`: 发现错误，需要修复 ✗

## 优化建议

如果检查太慢，可以：

1. **只检查修改的文件**
```bash
# 前端
pnpm lint src/components/YourComponent.tsx

# 后端
ruff check src/services/your_service.py
```

2. **并行运行检查**
```bash
# 前端
pnpm type-check & pnpm lint & wait

# 后端
ruff check . & mypy src & wait
```

3. **使用 watch 模式**
```bash
# 前端监听模式
pnpm lint --watch

# 后端监听模式
ruff check --watch .
```

## 与完整检查的对比

| 检查类型 | quick-dev | 完整检查 |
|---------|-----------|---------|
| TypeScript | ✓ | ✓ |
| ESLint/Ruff | ✓ | ✓ |
| 单元测试 | 快速 (`-m unit`) | 完整 (`pytest`) |
| 集成测试 | ✗ | ✓ |
| E2E 测试 | ✗ | ✓ |
| 前端诊断 | ✗ | ✓ (`pnpm diagnose`) |
| 执行时间 | ~30 秒 | ~5-10 分钟 |

## 何时使用完整检查

- 提交 PR 前
- 发布版本前
- 重大功能完成后
- 每周定期检查

命令: `pnpm audit:full` (前端) + `pytest -m "not e2e"` (后端)

---

**执行时间**: ~20-30 秒
**覆盖范围**: 类型检查 + 代码规范 + 快速单元测试
