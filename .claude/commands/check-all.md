# 完整项目检查命令

执行前端和后端的全面检查，包括代码质量、测试覆盖率、运行时错误等。

## 使用场景

- **提交 PR 前**: 确保代码质量，减少 review 时间
- **发布版本前**: 全面验证系统稳定性
- **重大功能完成后**: 确保没有引入问题
- **定期质量检查**: 每周或每次迭代结束

## 执行步骤

### 阶段 1: 代码质量检查

#### 前端代码质量

```bash
cd frontend

# 1. TypeScript 类型检查（严格模式）
pnpm type-check

# 2. ESLint 代码规范
pnpm lint

# 3. CSS/SCSS 样式规范
pnpm lint:css

# 4. 可访问性检查
pnpm lint:a11y

# 5. 代码格式检查
pnpm format:check
```

#### 后端代码质量

```bash
cd backend

# 1. Ruff 全量检查（lint + type）
ruff check .

# 2. Mypy 严格类型检查
mypy src --strict

# 3. 安全检查
bandit -r src/

# 4. 依赖漏洞检查
pip-audit
```

### 阶段 2: 测试套件

#### 单元测试

```bash
cd backend

# 运行所有单元测试
pytest -m unit -v --cov=src --cov-report=term-missing
```

**通过标准**:
- 代码覆盖率 > 80%
- 所有测试通过
- 无 skipped tests

#### 集成测试

```bash
cd backend

# 运行集成测试
pytest -m integration -v
```

**通过标准**:
- 所有测试通过
- 无数据库残留数据

#### 前端测试

```bash
cd frontend

# 运行单元测试 + 覆盖率
pnpm test:ci

# 可访问性测试
pnpm test:a11y
```

**通过标准**:
- 代码覆盖率 > 80%
- 所有测试通过

### 阶段 3: 运行时诊断

#### 前端运行时检查

```bash
cd frontend

# 1. 确保开发服务器运行
pnpm dev  # (在另一个终端)

# 2. 运行 Puppeteer 诊断
pnpm diagnose

# 3. 检查报告
pnpm diagnose:report
```

**通过标准**:
- 控制台错误 = 0
- 失败的 API 请求 = 0
- DOM加载 < 1s
- 完全加载 < 3s

#### 后端 API 检查

```bash
cd backend

# 1. 启动后端服务器
python run_dev.py  # (在另一个终端)

# 2. 健康检查
curl http://localhost:8002/api/v1/health

# 3. API 端点测试
pytest -m api -v
```

### 阶段 4: 构建验证

#### 前端生产构建

```bash
cd frontend

# 1. 清理旧构建
rm -rf dist/

# 2. 生产构建
pnpm build

# 3. 预览构建结果
pnpm preview

# 4. 检查构建输出
ls -lh dist/
```

**通过标准**:
- 构建成功，无错误
- 构建大小合理（< 5MB）
- 预览模式可正常访问

#### 后端打包测试

```bash
cd backend

# 1. 测试导入
python -c "from src.main import app; print('✓ 导入成功')"

# 2. 检查依赖
pip list | grep -E "fastapi|sqlalchemy|pydantic"
```

### 阶段 5: 性能基准

#### 前端性能

```bash
cd frontend

# 使用诊断报告查看性能指标
cat diagnostics/diagnostic-report-*.json | grep -E "domContentLoaded|loadComplete"
```

**基准要求**:
- DOM加载 < 1s (P50)
- 完全加载 < 3s (P50)
- 总请求数 < 50

#### 后端性能

```bash
cd backend

# 运行性能测试
pytest tests/performance/ -v
```

**基准要求**:
- API 响应时间 < 200ms (P95)
- 数据库查询 < 100ms (P95)

---

## 检查报告模板

完成所有检查后，生成如下报告：

```
╔══════════════════════════════════════════════════════════╗
║              完整项目检查报告                              ║
║              2026-01-20 10:30:00                         ║
╚══════════════════════════════════════════════════════════╝

【阶段 1: 代码质量】
✓ 前端 TypeScript 类型检查     (0 errors)
✓ 前端 ESLint                  (0 errors, 2 warnings)
✓ 前端 CSS 规范                (0 errors)
✓ 后端 Ruff 检查               (0 errors)
✓ 后端 Mypy 类型检查           (0 errors)
✓ 后端安全检查                 (0 issues)

【阶段 2: 测试套件】
✓ 后端单元测试                 (156/156 passed, 85% coverage)
✓ 后端集成测试                 (42/42 passed)
✓ 前端单元测试                 (89/89 passed, 82% coverage)

【阶段 3: 运行时诊断】
✓ 前端运行时检查               (0 errors, 3 warnings)
✓ 前端网络请求                 (0 failed requests)
✓ 后端 API 健康检查            (200 OK)

【阶段 4: 构建验证】
✓ 前端生产构建                 (dist/: 2.3MB)
✓ 后端导入测试                 (成功)

【阶段 5: 性能基准】
✓ 前端 DOM 加载                (平均: 650ms)
✓ 前端完全加载                 (平均: 1.8s)
✓ 后端 API 响应                (平均: 120ms)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【总结】
✅ 所有检查通过
⏱️  总耗时: 8 分钟 32 秒
📊 代码覆盖率: 前端 82% | 后端 85%
🚀 系统状态: 可以发布

【注意事项】
• 前端有 3 个 deprecation 警告，建议下个版本修复
• 后端覆盖率未达到 90% 目标，建议增加测试
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 常见失败原因及修复

### 代码质量检查失败

**问题**: ESLint/Ruff 报错

**修复**:
```bash
# 前端自动修复
pnpm lint:fix

# 后端自动修复
ruff check --fix .
```

### 测试失败

**问题**: 单元测试失败

**调试**:
```bash
# 运行单个测试并输出详细信息
pytest tests/unit/test_specific.py -v -s

# 进入调试模式
pytest tests/unit/test_specific.py --pdb
```

### 前端诊断失败

**问题**: 控制台错误

**修复步骤**:
1. 打开 HTML 报告
2. 查看错误堆栈
3. 定位到文件和行号
4. 修复后重新诊断

### 构建失败

**问题**: 生产构建报错

**调试**:
```bash
# 清理缓存重新构建
rm -rf node_modules/ dist/ .vite/
pnpm install
pnpm build
```

## 自动化脚本

创建 `scripts/check-all.sh`:

```bash
#!/bin/bash
set -e  # 遇到错误立即退出

echo "🔍 开始完整项目检查..."

# 阶段 1: 代码质量
echo "📋 阶段 1: 代码质量检查"
cd frontend && pnpm check && cd ..
cd backend && ruff check . && mypy src && cd ..

# 阶段 2: 测试
echo "🧪 阶段 2: 测试套件"
cd backend && pytest -m "not e2e" -v && cd ..
cd frontend && pnpm test:ci && cd ..

# 阶段 3: 前端诊断
echo "🌐 阶段 3: 前端运行时诊断"
cd frontend && pnpm diagnose && cd ..

# 阶段 4: 构建
echo "🏗️  阶段 4: 构建验证"
cd frontend && pnpm build && cd ..

echo "✅ 所有检查通过！"
```

使用:
```bash
chmod +x scripts/check-all.sh
./scripts/check-all.sh
```

## CI/CD 集成

```yaml
# .github/workflows/full-check.yml
name: Full Project Check

on:
  pull_request:
    branches: [develop, main]

jobs:
  full-check:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          cd frontend && pnpm install
          cd ../backend && pip install -r requirements.txt

      - name: Run full check
        run: ./scripts/check-all.sh

      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: check-reports
          path: |
            frontend/coverage/
            backend/htmlcov/
            frontend/diagnostics/
```

---

**执行时间**: 8-15 分钟（取决于项目规模）
**覆盖范围**: 全面（代码质量 + 测试 + 运行时 + 构建 + 性能）
**适用场景**: PR 提交前、版本发布前
