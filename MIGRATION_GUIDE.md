# 迁移指南：v1.x → v2.0 技术栈升级

**最后更新**: 2026-01-17
**适用版本**: 从 v1.x 升级到 v2.0
**重大变更**: React 19, Vite 6, Ant Design 6, pnpm

---

## 📋 升级概述

本次升级涉及前端技术栈的全面现代化，包含以下主要变更：

| 组件 | 旧版本 | 新版本 | 破坏性变更 |
|------|--------|--------|-----------|
| **React** | 18.3.1 | **19.2.3** | 中等 |
| **Vite** | 5.4.20 | **6.0.0** | 低 |
| **Ant Design** | 5.27.5 | **6.2.0** | 中等 |
| **TypeScript** | 5.6.3 | **5.8.0** | 低 |
| **包管理器** | npm | **pnpm** | 低（仅开发工作流） |
| **构建目标** | ES2020 | **ES2022** | 高（浏览器支持） |

---

## 🚨 重要提示

> ⚠️ **在开始升级之前，请确保：**
> 1. 已备份当前代码和数据库
> 2. 在开发/测试环境中先验证升级
> 3. 通知团队成员关于浏览器支持的变化
> 4. 预留至少 2-4 小时完成升级和测试

---

## 第一部分：前端升级

### 1.1 环境准备

#### 安装 pnpm（如未安装）

```bash
# 使用 npm 安装 pnpm
npm install -g pnpm

# 验证安装
pnpm --version
```

#### 删除旧依赖

```bash
cd frontend

# 删除 node_modules 和旧锁文件
rm -rf node_modules
rm -f package-lock.json
```

### 1.2 安装新依赖

```bash
# 使用 pnpm 安装依赖
pnpm install

# 验证安装
pnpm list react vite ant-design
```

**预期输出**：
```
react@19.2.3
vite@6.0.0
ant-design@6.2.0
```

### 1.3 React 19 破坏性变更

#### 1.3.1 JSX Transform 自动配置

**变更**: React 19 默认使用新的 JSX 转换

**影响**: 无需手动配置，`vite.config.ts` 已更新

**迁移代码**（如需自定义）：

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [
    react({
      // React 19 默认使用 'react' 作为 JSX 源
      jsxImportSource: 'react', // ✅ 显式配置（可选）
    }),
  ],
})
```

#### 1.3.2 ErrorBoundary 改进

**变更**: ErrorBoundary 可能在 Router 上下文外渲染

**影响**: 需要使用 `window.history` API 作为回退方案

**已修复**（v2.0）：
```typescript
// frontend/src/components/ErrorHandling/ErrorBoundary.tsx
const handleGoBack = () => {
  // React 19 兼容性：检查历史记录长度
  if (window.history.length > 1) {
    window.history.back()
  } else {
    window.location.href = '/dashboard'
  }
}
```

**无需额外操作**，已自动兼容。

#### 1.3.3 移除的 API

以下 API 已从 React 19 中移除：

| API | 替代方案 | 状态 |
|-----|---------|------|
| `ReactDOM.render` | `createRoot` | ✅ 已在 v1.x 迁移 |
| `UNSAFE_` 生命周期 | `getDerivedStateFromProps` | ✅ 未使用 |
| `componentWillMount` | `componentDidMount` | ✅ 未使用 |

**检查代码**：
```bash
# 搜索已移除的 API（应返回空）
cd frontend/src
grep -r "ReactDOM.render" . || echo "✅ 未使用"
grep -r "componentWillMount" . || echo "✅ 未使用"
```

### 1.4 Ant Design 6 破坏性变更

#### 1.4.1 组件 API 变更

| 组件 | 变更 | 迁移指南 |
|------|------|---------|
| **Form** | `validateFields` 返回类型更严格 | 添加类型注解 |
| **Table** | `pagination` 属性重构 | 检查分页配置 |
| **Modal** | `destroyOnClose` 默认值变更 | 显式设置该属性 |
| **DatePicker** | 时区处理变更 | 验证日期选择行为 |

**迁移示例**：

```typescript
// ❌ 旧写法（Ant Design 5）
const handleSubmit = async () => {
  const values = await form.validateFields() // any 类型
  // ...
}

// ✅ 新写法（Ant Design 6）
import type { FormInstance } from 'antd'

const handleSubmit = async (form: FormInstance) => {
  try {
    const values = await form.validateFields() // 推断类型
    // ...
  } catch (error) {
    console.error('验证失败:', error)
  }
}
```

#### 1.4.2 样式变量变更

**变更**: 全局样式变量命名规范化

**检查自定义样式**：
```bash
# 搜索可能受影响的自定义样式
cd frontend/src
grep -r "@ant-design" . || echo "✅ 未使用"
```

### 1.5 浏览器支持变更

#### 构建目标升级

```diff
- build: {
-   target: ['es2020', 'chrome87', 'firefox78', 'safari13']
- }
+ build: {
+   target: ['es2022', 'chrome90', 'firefox98', 'safari14']
+ }
```

#### 影响分析

| 浏览器 | 最低版本 | 发布日期 | 市场影响 |
|--------|---------|---------|---------|
| **Chrome** | 90 | 2021-03 | 低（<1%） |
| **Firefox** | 98 | 2022-03 | 极低（<0.5%） |
| **Safari** | 14 | 2020-09 | 低（<2%） |
| **Edge** | 90+ | 2021-03 | 低（<1%） |

**用户群体检查**（建议）：
```bash
# 如果你有用户分析数据，检查旧版浏览器占比
# 目标：<5% 用户使用不受支持的浏览器
```

#### 降级方案

如需支持更旧的浏览器，修改 `vite.config.ts`：

```typescript
build: {
  target: ['es2020', 'chrome87', 'firefox78', 'safari13'], // 回退到旧目标
}
```

**注意**: 这将增加打包体积并降低运行时性能。

### 1.6 开发工作流变更

#### 命令对照表

| 操作 | npm（旧） | pnpm（新） |
|------|----------|-----------|
| 安装依赖 | `npm install` | `pnpm install` |
| 添加依赖 | `npm add <pkg>` | `pnpm add <pkg>` |
| 开发模式 | `npm run dev` | `pnpm dev` |
| 构建 | `npm run build` | `pnpm build` |
| 测试 | `npm test` | `pnpm test` |
| Lint | `npm run lint` | `pnpm lint` |

**更新团队文档**：
- README.md
- CONTRIBUTING.md
- CI/CD 配置文件

---

## 第二部分：后端变更

### 2.1 API 响应模型标准化

**变更**: 系统设置 API 现在使用标准化的 Pydantic 响应模型

**影响**:
- ✅ OpenAPI 自动生成更完整
- ✅ 类型安全改进
- ⚠️ 响应结构可能略有变化

**验证**：
```bash
# 检查 OpenAPI 文档
curl http://localhost:8002/openapi.json | jq '.paths."/api/v1/system/settings"'
```

### 2.2 错误处理改进

**变更**: 移除过于宽泛的 `except Exception` 捕获

**影响**:
- ✅ 错误信息更准确
- ✅ 调试更简单
- ⚠️ 某些之前被隐藏的错误现在会暴露

**日志监控建议**：
- 升级后密切监控错误日志
- 某些"正常"的错误可能需要处理

### 2.3 加密配置

**变更**: PII 字段默认加密存储（见 `backend/CLAUDE.md`）

**操作**：

1. **生成加密密钥**：
```bash
cd backend
python -m src.core.encryption
```

2. **配置环境变量**：
```bash
# backend/.env
DATA_ENCRYPTION_KEY="<生成的密钥>"
```

3. **验证加密状态**：
```python
from src.crud.asset import asset_crud
print(f"Encryption enabled: {asset_crud.sensitive_data_handler.encryption_enabled}")
```

---

## 第三部分：验证清单

### 3.1 开发环境验证

```bash
# 1. 启动后端
cd backend
python run_dev.py

# 2. 启动前端（新窗口）
cd frontend
pnpm dev

# 3. 访问应用
open http://localhost:5173
```

### 3.2 功能验证

| 功能 | 测试步骤 | 预期结果 |
|------|---------|---------|
| **登录** | 输入用户名密码 | ✅ 正常登录 |
| **资产列表** | 查看资产数据 | ✅ 表格正常显示 |
| **表单提交** | 创建/编辑资产 | ✅ 表单验证工作 |
| **文件上传** | 上传 PDF/Excel | ✅ 上传成功 |
| **数据导出** | 导出 Excel | ✅ 下载正常 |
| **错误处理** | 触发错误（如网络断开） | ✅ ErrorBoundary 正确显示 |

### 3.3 测试套件验证

```bash
# 前端测试
cd frontend
pnpm test

# 后端测试
cd backend
pytest -m unit
pytest -m integration
```

**预期通过率**: >99%

### 3.4 构建验证

```bash
# 前端生产构建
cd frontend
pnpm build

# 预期结果：
# - 构建成功
# - 无 TypeScript 错误
# - 无 ESLint 错误
# - dist/ 目录生成
```

### 3.5 浏览器兼容性测试

**测试矩阵**：

| 浏览器 | 版本 | 测试结果 | 备注 |
|--------|------|---------|------|
| Chrome | 90+ | ✅ | 主要测试 |
| Chrome | <90 | ❌ | 不支持（预期） |
| Firefox | 98+ | ✅ | 主要测试 |
| Safari | 14+ | ✅ | 主要测试 |
| Edge | 90+ | ✅ | 兼容 Chrome |

**在线测试工具**:
- BrowserStack (https://www.browserstack.com)
- LambdaTest (https://www.lambdatest.com)

---

## 第四部分：常见问题

### Q1: pnpm install 失败，提示权限错误

**解决方案**：
```bash
# 清理缓存
pnpm store prune

# 重新安装
pnpm install --force
```

### Q2: React 19 构建失败，提示 JSX 错误

**解决方案**：
```bash
# 清理 Vite 缓存
rm -rf .vite
rm -rf node_modules/.vite

# 重新构建
pnpm build
```

### Q3: Ant Design 6 组件样式异常

**解决方案**：
```bash
# 检查是否覆盖了全局样式
cd frontend/src
grep -r "ant-design" . --include="*.css" --include="*.less"

# 如有自定义样式，参考 Ant Design 6 文档更新
```

### Q4: TypeScript 类型错误

**错误示例**：
```
Type 'unknown' is not assignable to type 'MyType'
```

**解决方案**：
```typescript
// 添加类型守卫
function isMyType(value: unknown): value is MyType {
  return (
    typeof value === 'object' &&
    value !== null &&
    'property' in value
  )
}
```

### Q5: 浏览器控制台出现 "Unsupported browser" 警告

**原因**: 用户使用旧版浏览器

**解决方案**：
1. 添加浏览器检测和用户提示
2. 或回退构建目标到 ES2020（见 1.5 节）

### Q6: 后端 API 响应格式变化

**错误**: 前端收到意外的响应格式

**解决方案**：
```typescript
// 检查 API 响应类型定义
// frontend/src/types/index.ts

// 确保与后端 Pydantic 模型匹配
// 查看后端 schemas/ 目录
```

---

## 第五部分：回滚计划

### 如果升级失败，执行以下步骤回滚：

```bash
# 1. 切换回升级前的分支
git checkout <upgrade前的分支或commit>

# 2. 恢复前端依赖
cd frontend
rm -rf node_modules pnpm-lock.yaml
npm install

# 3. 恢复后端依赖
cd backend
pip install -r requirements.txt

# 4. 验证回滚
npm test
pytest

# 5. 重新部署
npm run build
# ... 部署流程
```

---

## 第六部分：联系与支持

### 获取帮助

- **文档**: `docs/` 目录
- **问题反馈**: GitHub Issues
- **团队联系**: [项目维护者]

### 升级成功后

✅ **恭喜！** 请更新以下文档：
- README.md 版本号
- CHANGELOG.md（添加变更日志）
- 通知团队成员升级完成

---

## 附录：升级时间估算

| 任务 | 预计时间 | 实际时间 |
|------|---------|---------|
| 环境准备 | 15 分钟 | ___ |
| 依赖安装 | 10 分钟 | ___ |
| 代码修复（如有） | 30-60 分钟 | ___ |
| 本地测试 | 30 分钟 | ___ |
| 浏览器测试 | 30 分钟 | ___ |
| 部署 | 20 分钟 | ___ |
| **总计** | **2-3 小时** | ___ |

---

**祝升级顺利！** 🚀
