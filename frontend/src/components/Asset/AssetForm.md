# AssetForm 组件文档

## 概述

AssetForm 是一个功能完整的资产表单组件，用于创建和编辑土地物业资产信息。该组件采用现代化的设计理念，提供了智能的字段显示、自动计算、数据验证等功能。

## 特性

- ✅ **动态字段显示**：根据用户选择自动显示/隐藏相关字段
- ✅ **智能计算**：自动计算出租率、未出租面积等指标
- ✅ **类型安全**：使用 TypeScript 和 Zod 确保数据类型安全
- ✅ **表单验证**：完整的客户端验证规则
- ✅ **完成度跟踪**：实时显示表单填写完成度
- ✅ **响应式设计**：适配不同屏幕尺寸
- ✅ **帮助系统**：内置填写帮助和字段说明
- ✅ **高级选项**：可展开/收起的高级字段

## 基本用法

```tsx
import { AssetForm } from '@/components/Asset'
import type { AssetFormData } from '@/schemas/assetFormSchema'

const MyComponent = () => {
  const handleSubmit = (data: AssetFormData) => {
    console.log('表单数据:', data)
    // 处理表单提交
  }

  const handleCancel = () => {
    // 处理取消操作
  }

  return (
    <AssetForm
      mode="create"
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      loading={false}
    />
  )
}
```

## Props

| 属性 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `mode` | `'create' \| 'edit'` | ✅ | - | 表单模式 |
| `onSubmit` | `(data: AssetFormData) => void` | ✅ | - | 表单提交回调 |
| `onCancel` | `() => void` | ✅ | - | 取消操作回调 |
| `initialData` | `Asset` | ❌ | - | 初始数据（编辑模式） |
| `loading` | `boolean` | ❌ | `false` | 加载状态 |

## 字段分组

### 基本信息
- 物业名称（必填）
- 权属方（必填）
- 经营管理方
- 所在地址（必填）

### 面积信息
- 土地面积
- 实际房产面积
- 经营性物业可出租面积
- 经营性物业已出租面积
- 经营性物业未出租面积
- 非经营物业面积

### 状态信息
- 确权状态（必填）
- 物业性质（必填）
- 物业使用状态（必填）
- 是否涉诉

### 用途信息
- 证载用途
- 实际用途
- 业态类别
- 接收模式
- 是否计入出租率
- 出租率

### 合同信息（高级选项）
- 承租合同
- 现合同开始日期
- 现合同结束日期
- 租户名称
- 权属类别
- 现租赁合同
- 五羊项目名称
- 接收协议开始日期
- 接收协议结束日期
- 现终端出租合同

### 描述信息（高级选项）
- 说明
- 其他备注

## 动态字段规则

### 物业性质相关
- **经营类物业**：显示可出租面积、已出租面积、未出租面积、出租率等字段
- **非经营类物业**：显示非经营物业面积字段

### 使用状态相关
- **出租状态**：显示租户名称、合同信息、合同日期等字段

### 其他条件
- **有业态类别**：显示接收模式字段
- **有五羊项目名称**：显示接收协议开始和结束日期字段

## 自动计算功能

### 出租率计算
```
出租率 = (已出租面积 / 可出租面积) × 100%
```

### 未出租面积计算
```
未出租面积 = 可出租面积 - 已出租面积
```

### 表单完成度计算
```
完成度 = (必填字段完成数 / 必填字段总数) × 60% + (可选字段完成数 / 可选字段总数) × 40%
```

## 验证规则

### 必填字段验证
- 物业名称：不能为空，最大200字符
- 权属方：不能为空，最大200字符
- 所在地址：不能为空，最大500字符
- 确权状态：必须选择
- 物业性质：必须选择
- 使用状态：必须选择

### 面积字段验证
- 所有面积字段必须为非负数
- 已出租面积不能大于可出租面积
- 未出租面积不能大于可出租面积

### 日期字段验证
- 合同结束日期必须晚于开始日期
- 接收协议结束日期必须晚于开始日期

### 字符长度限制
- 短文本字段：最大100-200字符
- 长文本字段（说明、备注）：最大1000字符

## 使用示例

### 创建模式
```tsx
<AssetForm
  mode="create"
  onSubmit={(data) => {
    // 调用创建API
    assetService.createAsset(data)
  }}
  onCancel={() => {
    // 返回列表页
    navigate('/assets')
  }}
  loading={createMutation.isLoading}
/>
```

### 编辑模式
```tsx
<AssetForm
  mode="edit"
  initialData={asset}
  onSubmit={(data) => {
    // 调用更新API
    assetService.updateAsset(asset.id, data)
  }}
  onCancel={() => {
    // 返回详情页
    navigate(`/assets/${asset.id}`)
  }}
  loading={updateMutation.isLoading}
/>
```

## 样式定制

组件使用 Ant Design 的样式系统，可以通过以下方式进行定制：

### CSS 类名
- `.asset-form` - 表单容器
- `.asset-form-section` - 字段分组容器
- `.asset-form-field` - 单个字段容器
- `.asset-form-actions` - 操作按钮容器

### 主题定制
```tsx
import { ConfigProvider } from 'antd'

<ConfigProvider
  theme={{
    token: {
      colorPrimary: '#1890ff',
      borderRadius: 6,
    },
  }}
>
  <AssetForm {...props} />
</ConfigProvider>
```

## 性能优化

### 字段可见性优化
- 使用 `useFormFieldVisibility` Hook 管理字段显示状态
- 避免不必要的重新渲染

### 表单验证优化
- 使用 `react-hook-form` 的 `mode: 'onChange'` 进行实时验证
- 使用 Zod schema 进行高效的数据验证

### 内存优化
- 使用 `useCallback` 和 `useMemo` 优化回调函数和计算值
- 合理使用 `useEffect` 的依赖数组

## 测试

### 单元测试
```bash
npm test -- AssetForm.test.tsx
```

### 集成测试
```bash
npm run test:integration -- AssetForm
```

### E2E 测试
```bash
npm run test:e2e -- AssetForm
```

## 故障排除

### 常见问题

1. **字段不显示**
   - 检查字段可见性规则
   - 确认依赖字段的值是否正确

2. **验证失败**
   - 检查 Zod schema 定义
   - 确认字段值的数据类型

3. **自动计算不工作**
   - 检查依赖字段的值
   - 确认计算逻辑是否正确

4. **性能问题**
   - 检查是否有不必要的重新渲染
   - 优化表单字段的依赖关系

### 调试技巧

1. 使用 React DevTools 检查组件状态
2. 在浏览器控制台查看表单数据
3. 使用 `console.log` 调试字段可见性逻辑
4. 检查网络请求和响应

## 更新日志

### v1.0.0
- ✅ 初始版本发布
- ✅ 支持创建和编辑模式
- ✅ 动态字段显示
- ✅ 自动计算功能
- ✅ 完整的表单验证
- ✅ 帮助系统
- ✅ 响应式设计

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 许可证

MIT License