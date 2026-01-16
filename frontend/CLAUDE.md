# Frontend CLAUDE.md

前端开发专用指南。通用信息请参阅根目录 `CLAUDE.md`。

---

## 快速开始

```bash
cd frontend
pnpm install            # 安装依赖
pnpm dev                # 启动开发服务器 (port 5173)
pnpm test               # 运行测试
pnpm lint               # ESLint 检查
pnpm type-check         # TypeScript 类型检查
```

---

## 导入路径规范 (重要!)

```typescript
// ✅ 正确 - 使用新路径 (2025-12-24)
import { enhancedApiClient } from '@/api/client';
import { API_CONFIG } from '@/api/config';
import { AssetForm, OwnershipForm } from '@/components/Forms';

// ❌ 已废弃 - 不推荐使用
import { enhancedApiClient } from '@/services';
import { AssetForm } from '@/components/Asset';
```

---

## 现代 TypeScript 语法规范 (重要!)

本项目使用 `@typescript-eslint/strict-boolean-expressions` 规则，要求显式的空值检查。

### 核心原则

1. **使用空值合并 (`??`) 代替逻辑或 (`||`)** - 只对 `null`/`undefined` 提供默认值
2. **使用显式空值检查 (`!= null`)** - 明确检查 `null` 和 `undefined`
3. **使用可选链 (`?.`)** - 安全访问可能为空的属性
4. **使用 `.trim()` 验证字符串** - 检查非空字符串

### 常见修复模式

| 场景 | ❌ 错误写法 | ✅ 正确写法 |
|------|-----------|-----------|
| **默认值** | `value \|\| default` | `value ?? default` |
| **空值检查** | `if (value)` | `if (value != null)` |
| **对象检查** | `if (obj)` | `if (obj != null)` |
| **字符串检查** | `if (str)` | `if (str?.trim() !== '')` |
| **布尔比较** | `if (bool)` | `if (bool === true)` |
| **数字零值** | `if (num)` | `if (num != null && num > 0)` |
| **数组长度** | `arr.length` | `arr?.length ?? 0` |

### 实际应用示例

#### 1. API 响应处理

```typescript
// ✅ 正确 - 使用 ?? 提供默认值
const items = response.data?.items ?? [];
const total = response.data?.total ?? 0;
const page = response.data?.page ?? 1;

// ❌ 错误 - || 会把 0 当作假值
const total = response.data?.total || 0;  // 如果 total 是 0，会被替换
```

#### 2. 可选参数默认值

```typescript
// ✅ 正确
function formatAmount(value: number | null | undefined): string {
  const amount = value ?? 0;
  return `¥${amount.toFixed(2)}`;
}

// ❌ 错误
function formatAmount(value: number | undefined): string {
  if (value) {  // 如果 value 是 0，会被跳过
    return `¥${value.toFixed(2)}`;
  }
  return '¥0.00';
}
```

#### 3. 字符串验证

```typescript
// ✅ 正确 - 显式检查
if (searchTerm?.trim() !== '') {
  performSearch(searchTerm.trim());
}

// ❌ 错误
if (searchTerm) {  // 可能匹配空字符串 " "
  performSearch(searchTerm);
}
```

#### 4. 数组操作

```typescript
// ✅ 正确 - 使用 ?? 默认空数组
{items?.map(item => <Item key={item.id} />) ?? <Empty />}

// 或显式检查
{items != null && items.length > 0 && items.map(item => <Item key={item.id} />)}

// ❌ 错误
{items.map(item => <Item key={item.id} />)}  // 如果 items 是 null/undefined 会崩溃
```

#### 5. 数字比较（重要！）

```typescript
// ✅ 正确 - 显式检查 > 0
if (progressEvent.total != null && progressEvent.total > 0) {
  const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
}

// ❌ 错误 - 如果 total 是 0 会被跳过
if (progressEvent.total) {
  const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
}
```

#### 6. 嵌套属性访问

```typescript
// ✅ 正确 - 使用可选链
const code = error.response.data?.code ?? 'UNKNOWN';
const message = error.response.data?.detail ?? error.message ?? '未知错误';

// ❌ 错误
const code = error.response && error.response.data && error.response.data.code || 'UNKNOWN';
```

#### 7. 布尔值检查

```typescript
// ✅ 正确 - 显式比较
if (user.isActive === true) {
  showActiveUser();
}

if (config.enabled === true) {
  enableFeature();
}

// ❌ 错误
if (user.isActive) {
  showActiveUser();
}
```

### React 组件中的常见模式

#### State 初始化

```typescript
// ✅ 正确
const [assets, setAssets] = useState<Asset[] | null>(null);
const [loading, setLoading] = useState<boolean>(false);

// 加载状态检查
const isLoading = data === null;
const hasError = error != null;
```

#### 条件渲染

```typescript
// ✅ 正确
{dashboardData?.health_status?.overall_score != null ? (
  <HealthGauge value={dashboardData.health_status.overall_score} />
) : (
  <Spin />
)}

// ❌ 错误
{dashboardData && dashboardData.health_status && (
  <HealthGauge value={dashboardData.health_status.overall_score} />
)}
```

#### 表单值处理

```typescript
// ✅ 正确
const initialValues = {
  name: project.name ?? '',
  code: project.code ?? '',
  area: project.area ?? 0,
  isActive: project.is_active ?? true,
};

// ❌ 错误
const initialValues = {
  name: project.name || '',
  area: project.area || 0,  // 如果 area 是 0 会被替换
};
```

### 为什么需要这些规则？

1. **类型安全** - 避免将 `0`、`''`、`false` 等合法值误判为"无值"
2. **代码清晰** - 明确表达意图：检查的是"是否为 null/undefined"而非"是否为真值"
3. **避免 Bug** - 特别是数字 `0` 和空字符串 `""` 的处理
4. **团队协作** - 统一的代码风格，降低理解成本

### ESLint 规则

- `@typescript-eslint/strict-boolean-expressions` - 强制显式布尔表达式
- 配置级别: `warn` (允许临时绕过，但需修复)

### 参考资源

- [TypeScript 3.7+ 可选链](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-7.html#optional-chaining)
- [空值合并运算符](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-7.html#nullish-coalescing)

---

## 状态管理策略

| 状态类型 | 使用工具 | 适用场景 |
|---------|---------|---------|
| **全局 UI** | Zustand | 主题、侧边栏、用户信息、通知 |
| **服务器数据** | React Query | API 数据获取、缓存、同步 |
| **表单状态** | React Hook Form | 表单验证、提交 |
| **局部 UI** | useState | 模态框开关、loading 状态 |

### React Query 示例

```typescript
// ✅ 正确 - 服务器数据用 React Query
const { data: assets, isLoading } = useQuery({
  queryKey: ['assets'],
  queryFn: () => enhancedApiClient.get('/assets'),
  staleTime: 5 * 60 * 1000,  // 5 分钟缓存
});

// ❌ 错误 - 不要用 useState 管理服务器数据
const [assets, setAssets] = useState([]);
useEffect(() => { fetch(...) }, []);
```

---

## 目录结构

```
src/
├── api/            # API 客户端 (enhancedApiClient)
├── components/     # 可复用组件
│   ├── Forms/      # 统一表单组件 (AssetForm, etc.)
│   ├── Asset/      # 资产相关组件
│   ├── Charts/     # 图表组件
│   ├── Router/     # 路由管理 (动态加载、性能监控)
│   └── Layout/     # 布局组件
├── pages/          # 页面组件 (按模块划分)
├── services/       # API 服务封装
├── hooks/          # 自定义 Hook
├── store/          # Zustand 状态管理
├── types/          # TypeScript 类型定义
└── utils/          # 工具函数
```

---

## 添加新功能

### 1. 类型定义 (`types/myFeature.ts`)
### 2. API 服务 (`services/myFeatureService.ts`)
### 3. 自定义 Hook (`hooks/useMyFeature.ts`)
### 4. 页面组件 (`pages/MyFeature/MyFeatureListPage.tsx`)

详细模式参考: `docs/guides/frontend.md`

---

## 路由系统

```
/dashboard              # 工作台
/assets/list            # 资产列表
/assets/new             # 创建资产
/rental/contracts       # 合同列表
/system/users           # 用户管理 (需权限)
```

**权限控制**: 使用 `PermissionGuard` 组件

---

## 测试

```bash
pnpm test                   # 运行测试
pnpm test:coverage          # 覆盖率报告
pnpm test:watch             # 监听模式
```

测试文件位置: `src/**/__tests__/*.test.tsx`

---

## 代码风格

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| 组件 | PascalCase | `AssetCard.tsx` |
| 服务 | camelCase | `assetService.ts` |
| Hook | use* | `useAssets.ts` |
| 常量 | UPPER_SNAKE | `API_BASE_URL` |

---

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| Port 5173 被占用 | 修改 `vite.config.ts` |
| API 请求失败 | 确保后端运行在 8002 端口 |
| TypeScript 错误 | `pnpm type-check` 查看详情 |


<claude-mem-context>
# Recent Activity

<!-- This section is auto-generated by claude-mem. Edit content outside the tags. -->

*No recent activity*
</claude-mem-context>