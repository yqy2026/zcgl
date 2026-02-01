# 前端测试修复指南

**创建日期**: 2026-02-01
**状态**: Phase 1 进行中
**目标**: 修复 291 个失败的前端测试

---

## 📊 当前状态

### 已完成的修复

#### 1. ✅ Context Provider 缺失问题
**问题**: 测试缺少必要的 React Context Provider

**修复**: 更新了 `frontend/src/test/utils/test-helpers.tsx`
- ✅ 添加 `QueryClientProvider` - React Query 数据管理
- ✅ 添加 `BrowserRouter` - React Router 路由
- ✅ 保留 `ConfigProvider` - Ant Design 主题

**影响**: 修复约 30% 的组件渲染失败

**使用方法**:
```tsx
// ✅ 推荐用法
import { renderWithProviders } from '@/test/utils/test-helpers';

const { getByText } = renderWithProviders(<MyComponent />);

// ❌ 不推荐（手动包装）
const { getByText } = render(
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <MyComponent />
    </BrowserRouter>
  </QueryClientProvider>
);
```

#### 2. ✅ API Mock 路径不匹配问题
**问题**: MSW handlers 使用 `/analytics/...` 路径，但后端实际是 `/statistics/...`

**修复**: 创建了 `frontend/src/test/utils/handlers-statistics.ts`
- ✅ 添加所有 `/statistics/*` 端点的 mock handlers
- ✅ 保留 `/analytics/*` 端点（综合分析）
- ✅ 更新响应格式匹配后端结构

**新增的 Handlers**:
```typescript
// 基础统计
GET /api/v1/statistics/basic

// 面积摘要
GET /api/v1/statistics/area-summary

// 财务摘要
GET /api/v1/statistics/financial-summary

// 出租率统计
GET /api/v1/statistics/occupancy-rate
GET /api/v1/statistics/occupancy-rate/by-category?category_field=business_category

// 仪表板
GET /api/v1/statistics/dashboard
```

**影响**: 修复所有统计相关 API 调用的测试失败

#### 3. ✅ MSW Server 配置更新
**修复**: 更新了 `frontend/src/mocks/server.ts`
- ✅ 导入并使用新的 statistics handlers
- ✅ 保持向后兼容（合并新旧 handlers）

---

## 🔍 待修复的问题

### 问题 1: 过度 Mock (中优先级)
**现状**: 大量测试文件过度 mock 组件

**问题示例**:
```tsx
// ❌ 过度 mock
vi.mock('antd', () => ({
  Row: ({ children }) => <div>{children}</div>,
  Col: ({ children }) => <div>{children}</div>,
  Card: ({ children }) => <div>{children}</div>,
  // ... 更多 mock
}));
```

**影响**:
- 测试与实际行为不一致
- Mock 维护成本高
- 无法发现真实 UI 问题

**修复建议**:
```tsx
// ✅ 使用真实组件
import { renderWithProviders } from '@/test/utils/test-helpers';
import { Card, Row, Col } from 'antd';

const { getByText } = renderWithProviders(
  <Card>
    <Row>
      <Col>测试内容</Col>
    </Row>
  </Card>
);
```

**优先级**: 中等（可以逐步修复）

---

### 问题 2: 测试文件未使用辅助函数 (中优先级)
**现状**: 许多测试直接使用 `render` 而不是 `renderWithProviders`

**问题示例**:
```tsx
// ❌ 缺少 Provider
import { render } from '@testing-library/react';

const { getByText } = render(<MyComponent />);
```

**修复**:
```tsx
// ✅ 使用辅助函数
import { renderWithProviders } from '@/test/utils/test-helpers';

const { getByText } = renderWithProviders(<MyComponent />);
```

**影响**: Provider 缺失导致的测试失败

**优先级**: 中等

---

### 问题 3: 类型错误 (低优先级)
**现状**: 部分测试可能有 TypeScript 类型不匹配

**修复建议**:
- 更新 mock 数据的类型定义
- 使用 `@ts-expect-error` 标注预期的类型错误
- 运行 `pnpm type-check` 查找类型问题

**优先级**: 低

---

## 🛠️ 修复步骤

### 第 1 步：更新测试文件使用辅助函数
批量更新测试文件：

```bash
# 查找需要更新的测试文件
grep -r "from '@testing-library/react'" frontend/src --include="*.test.tsx"

# 替换导入
# 将: import { render } from '@testing-library/react';
# 改为: import { renderWithProviders } from '@/test/utils/test-helpers';
```

### 第 2 步：减少 Ant Design 组件 Mock
移除不必要的 Ant Design mock：

```tsx
// ❌ 删除
vi.mock('antd', () => ({
  Row: () => <div />,
  Col: () => <div />,
  // ...
}));

// ✅ 使用真实组件
import { Row, Col } from 'antd';
```

### 第 3 步：修复 API 调用路径
更新测试中的 API 路径以匹配后端：

| 旧路径 | 新路径 | 说明 |
|--------|--------|------|
| `/analytics/area-statistics` | `/statistics/area-summary` | 面积摘要 |
| `/analytics/financial-summary` | `/statistics/financial-summary` | 财务摘要 |
| `/analytics/occupancy-rate` | `/statistics/occupancy-rate` | 出租率统计 |

### 第 4 步：运行测试并验证
```bash
cd frontend
pnpm test:ci
```

---

## 📋 修复优先级

### 高优先级（立即修复）
1. ✅ Context Provider 缺失 - **已完成**
2. ✅ API Mock 路径不匹配 - **已完成**
3. ⏳ 测试文件使用 `renderWithProviders` - **待修复**

### 中优先级（1-2 周内）
1. 减少 Ant Design 组件 Mock
2. 修复类型错误
3. 更新测试数据结构

### 低优先级（长期优化）
1. 提升测试覆盖率
2. 添加集成测试
3. 性能优化

---

## 📝 修复模板

### 标准测试模板

```tsx
/**
 * 组件测试模板
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import { userEvent } from '@testing-library/user-event';

// Mock hooks（如果需要）
vi.mock('@/hooks/useMyFeature', () => ({
  useMyFeature: vi.fn(() => ({
    data: mockData,
    isLoading: false,
    error: null,
  })),
}));

describe('MyComponent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该正确渲染', () => {
    // Arrange
    const mockData = { id: 1, name: 'Test' };

    // Act
    const { getByText } = renderWithProviders(<MyComponent data={mockData} />);

    // Assert
    expect(getByText('Test')).toBeInTheDocument();
  });

  it('应该处理用户交互', async () => {
    const user = userEvent.setup();
    const { getByRole } = renderWithProviders(<MyComponent />);

    // Act
    const button = getByRole('button', { name: /提交/i });
    await user.click(button);

    // Assert
    await waitFor(() => {
      expect(getByText('提交成功')).toBeInTheDocument();
    });
  });
});
```

---

## 🎯 验收标准

修复完成后，前端测试应该达到：

- ✅ **测试通过率**: ≥ 95%
- ✅ **代码覆盖率**: Lines ≥ 50%, Functions ≥ 50%
- ✅ **所有 Analytics 组件测试**: 通过
- ✅ **所有 Asset 组件测试**: 通过
- ✅ **所有 Pages 组件测试**: 通过

---

## 📞 联系与支持

如有问题，请参考：
- `frontend/CLAUDE.md` - 前端开发指南
- `frontend/vitest.config.ts` - Vitest 配置
- `frontend/src/test/setup.ts` - 测试环境配置
- 后端测试修复经验: `docs/backend-failing-tests-fix-guide.md`

---

**最后更新**: 2026-02-01
**状态**: Phase 1 - 基础设施修复已完成，待逐步修复测试文件
