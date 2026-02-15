# TypeScript 严格布尔表达式规范

本文档说明项目中 TypeScript 的严格布尔表达式规范。当前通过 `tsgo` + `oxlint` + 代码评审执行，不依赖单一 lint 规则开关。

**最后更新**: 2026-02-10

---

## 核心原则

1. **使用空值合并 (`??`) 代替逻辑或 (`||`)** - 只对 `null`/`undefined` 提供默认值
2. **使用显式空值检查 (`!= null`)** - 明确检查 `null` 和 `undefined`
3. **使用可选链 (`?.`)** - 安全访问可能为空的属性
4. **使用 `.trim()` 验证字符串** - 检查非空字符串

---

## 常见修复模式

| 场景 | ❌ 错误写法 | ✅ 正确写法 |
|------|-----------|--------------|
| **默认值** | `value \|\| default` | `value ?? default` |
| **空值检查** | `if (value)` | `if (value != null)` |
| **对象检查** | `if (obj)` | `if (obj != null)` |
| **字符串检查** | `if (str)` | `if (str?.trim() !== '')` |
| **布尔比较** | `if (bool)` | `if (bool === true)` |
| **数字零值** | `if (num)` | `if (num != null && num > 0)` |
| **数组长度** | `arr.length` | `arr?.length ?? 0` |

---

## 实际应用示例

### 1. API 响应处理

```typescript
// ✅ 正确 - 使用 ?? 提供默认值
const items = response.data?.items ?? [];
const total = response.data?.total ?? 0;
const page = response.data?.page ?? 1;

// ❌ 错误 - || 会把 0 当作假值
const total = response.data?.total || 0;  // 如果 total 是 0，会被替换
```

### 2. 可选参数默认值

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

### 3. 字符串验证

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

### 4. 数组操作

```typescript
// ✅ 正确 - 使用 ?? 默认空数组
{items?.map(item => <Item key={item.id} />) ?? <Empty />}

// 或显式检查
{items != null && items.length > 0 && items.map(item => <Item key={item.id} />)}

// ❌ 错误
{items.map(item => <Item key={item.id} />)}  // 如果 items 是 null/undefined 会崩溃
```

### 5. 数字比较（重要！）

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

### 6. 嵌套属性访问

```typescript
// ✅ 正确 - 使用可选链
const code = error.response.data?.code ?? 'UNKNOWN';
const message = error.response.data?.detail ?? error.message ?? '未知错误';

// ❌ 错误
const code = error.response && error.response.data && error.response.data.code || 'UNKNOWN';
```

### 7. 布尔值检查

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

---

## React 组件中的常见模式

### State 初始化

```typescript
// ✅ 正确
const [assets, setAssets] = useState<Asset[] | null>(null);
const [loading, setLoading] = useState<boolean>(false);

// 加载状态检查
const isLoading = data === null;
const hasError = error != null;
```

### 条件渲染

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

### 表单值处理

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

---

## 为什么需要这些规则？

1. **类型安全** - 避免将 `0`、`''`、`false` 等合法值误判为"无值"
2. **代码清晰** - 明确表达意图：检查的是"是否为 null/undefined"而非"是否为真值"
3. **避免 Bug** - 特别是数字 `0` 和空字符串 `""` 的处理
4. **团队协作** - 统一的代码风格，降低理解成本

---

## 规则执行方式

```bash
# 类型检查（tsgo）
pnpm type-check

# 代码检查（oxlint）
pnpm lint
```

说明：严格布尔表达式作为团队编码约定执行；工具链迁移后采用“先可用再收敛”策略，按增量任务持续补齐 lint 等价规则。

---

## 参考资源

- [TypeScript 3.7+ 可选链](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-7.html#optional-chaining)
- [空值合并运算符](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-7.html#nullish-coalescing)
