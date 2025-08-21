# 用户体验组件使用指南

## 概述

本指南介绍了土地物业资产管理系统中的用户体验（UX）组件库，包括错误处理、加载状态、用户反馈、确认对话框等组件的使用方法。

## 组件分类

### 1. 错误处理组件

#### GlobalErrorBoundary - 全局错误边界
用于捕获和处理React组件树中的JavaScript错误。

```tsx
import { GlobalErrorBoundary } from '@/components/ErrorHandling'

<GlobalErrorBoundary
  fallback={<CustomErrorUI />}
  onError={(error, errorInfo) => {
    // 自定义错误处理逻辑
    console.error('Error caught:', error, errorInfo)
  }}
>
  <App />
</GlobalErrorBoundary>
```

**特性：**
- 自动错误报告
- 开发环境显示详细错误信息
- 生产环境显示用户友好的错误页面
- 支持错误ID追踪

#### ErrorPage - 错误页面
用于显示各种类型的错误页面。

```tsx
import { ErrorPage } from '@/components/ErrorHandling'

<ErrorPage 
  type="404" 
  title="自定义标题"
  subTitle="自定义描述"
  showBackButton={true}
  showHomeButton={true}
  onBack={() => navigate(-1)}
  onHome={() => navigate('/')}
/>
```

**支持的错误类型：**
- `404` - 页面不存在
- `403` - 访问被拒绝
- `500` - 服务器错误
- `network` - 网络连接失败
- `timeout` - 请求超时
- `maintenance` - 系统维护

### 2. 加载状态组件

#### LoadingSpinner - 加载动画
用于显示加载状态的旋转动画。

```tsx
import { LoadingSpinner } from '@/components/Loading'

<LoadingSpinner 
  loading={isLoading}
  tip="正在加载数据..."
  size="large"
>
  <YourContent />
</LoadingSpinner>
```

#### SkeletonLoader - 骨架屏
用于在内容加载时显示占位符。

```tsx
import { SkeletonLoader } from '@/components/Loading'

<SkeletonLoader 
  type="list" 
  loading={isLoading}
  rows={5}
>
  <YourList />
</SkeletonLoader>
```

**支持的骨架屏类型：**
- `list` - 列表骨架屏
- `card` - 卡片骨架屏
- `form` - 表单骨架屏
- `table` - 表格骨架屏
- `chart` - 图表骨架屏
- `detail` - 详情页骨架屏

### 3. 用户反馈组件

#### SuccessNotification - 通知消息
用于显示各种类型的通知消息。

```tsx
import { SuccessNotification } from '@/components/Feedback'

// 预设的成功反馈
SuccessNotification.success.create('资产')
SuccessNotification.success.update('资产')
SuccessNotification.success.delete('资产')

// 预设的错误反馈
SuccessNotification.error.network()
SuccessNotification.error.server()
SuccessNotification.error.operation('保存')

// 自定义通知
SuccessNotification.notify({
  type: 'success',
  title: '操作成功',
  description: '数据已成功保存',
  duration: 4.5,
})
```

#### EmptyState - 空状态
用于显示无数据或错误状态。

```tsx
import { EmptyState, NoDataState } from '@/components/Feedback'

<EmptyState 
  type="no-data"
  showCreateButton={true}
  onCreateClick={() => navigate('/create')}
/>

// 或使用预设组件
<NoDataState 
  onCreateClick={() => navigate('/create')}
/>
```

#### ConfirmDialog - 确认对话框
用于显示确认操作的对话框。

```tsx
import { ConfirmDialog, showDeleteConfirm } from '@/components/Feedback'

// 组件方式
<ConfirmDialog 
  type="delete"
  visible={showDialog}
  itemName="测试资产"
  onConfirm={handleDelete}
  onCancel={() => setShowDialog(false)}
/>

// 函数方式
const confirmed = await showDeleteConfirm({
  itemName: '测试资产',
  onConfirm: handleDelete,
})
```

#### ProgressIndicator - 进度指示器
用于显示操作进度。

```tsx
import { ProgressIndicator, LoadingProgress } from '@/components/Feedback'

<ProgressIndicator 
  type="line"
  percent={progress}
  status="active"
  title="上传进度"
  description={`已完成 ${progress}%`}
/>

// 预设组件
<LoadingProgress 
  title="正在处理"
  description="请稍候..."
  percent={progress}
/>
```

#### ActionFeedback - 操作反馈
用于显示操作结果的反馈。

```tsx
import { ActionFeedback, SuccessFeedback } from '@/components/Feedback'

<ActionFeedback 
  result={{
    status: 'success',
    message: '操作成功完成',
    details: ['已创建1个资产', '已更新相关数据'],
  }}
  showUndo={true}
  onUndo={handleUndo}
/>

// 预设组件
<SuccessFeedback 
  message="数据保存成功"
  showUndo={true}
  onUndo={handleUndo}
/>
```

### 4. UX增强Hooks

#### useUXEnhancement - 综合UX增强
提供完整的UX增强功能。

```tsx
import { useUXEnhancement } from '@/hooks/useUXEnhancement'

const MyComponent = () => {
  const ux = useUXEnhancement({
    trackPageView: 'asset-list',
    enableErrorHandling: true,
    enablePerformanceMonitoring: true,
  })

  const handleSave = async () => {
    try {
      ux.startMeasure('save-operation')
      await saveData()
      ux.showSuccess('保存成功')
      ux.trackAction('asset-saved')
    } catch (error) {
      ux.handleError(error)
    } finally {
      ux.endMeasure('save-operation')
    }
  }

  return (
    <div>
      <Button onClick={handleSave}>保存</Button>
    </div>
  )
}
```

#### useLoadingState - 加载状态管理
管理组件的加载状态。

```tsx
import { useLoadingState } from '@/hooks/useUXEnhancement'

const MyComponent = () => {
  const { loading, withLoading } = useLoadingState('my-operation')

  const handleOperation = () => {
    withLoading(async () => {
      await performAsyncOperation()
    })
  }

  return (
    <Button loading={loading} onClick={handleOperation}>
      执行操作
    </Button>
  )
}
```

#### useOperationState - 操作状态管理
管理异步操作的完整状态。

```tsx
import { useOperationState } from '@/hooks/useUXEnhancement'

const MyComponent = () => {
  const operation = useOperationState()

  const handleSave = () => {
    operation.execute(
      () => saveData(),
      {
        successMessage: '保存成功',
        errorMessage: '保存失败',
        trackAction: 'save-data',
      }
    )
  }

  return (
    <div>
      <Button 
        loading={operation.loading} 
        onClick={handleSave}
      >
        保存
      </Button>
      
      {operation.error && (
        <Alert 
          type="error" 
          message={operation.error.message} 
        />
      )}
    </div>
  )
}
```

#### useFormEnhancement - 表单增强
增强表单的用户体验。

```tsx
import { useFormEnhancement } from '@/hooks/useUXEnhancement'

const MyForm = () => {
  const form = useFormEnhancement()

  const handleInputChange = () => {
    form.markDirty()
  }

  const handleSave = () => {
    form.markClean()
  }

  const handleLeave = () => {
    form.confirmLeave(() => {
      navigate('/other-page')
    })
  }

  return (
    <Form>
      <Input onChange={handleInputChange} />
      <Button onClick={handleSave}>保存</Button>
      <Button onClick={handleLeave}>离开</Button>
      
      {form.isDirty && (
        <Alert message="有未保存的更改" type="warning" />
      )}
    </Form>
  )
}
```

### 5. UX管理器

#### uxManager - 全局UX管理
提供全局的UX管理功能。

```tsx
import { uxManager, showSuccess, showError } from '@/utils/uxManager'

// 显示反馈
showSuccess('操作成功', '数据已保存')
showError('操作失败', '请稍后重试')

// 记录用户行为
uxManager.recordUserAction('button-click', { button: 'save' })

// 性能监控
uxManager.startPerformanceMeasure('data-load')
// ... 执行操作
uxManager.endPerformanceMeasure('data-load')

// 错误处理
uxManager.handleError(new Error('Something went wrong'), { context: 'user-action' })

// 获取统计信息
const stats = uxManager.getStats()
console.log('错误数量:', stats.errorCount)
console.log('性能指标:', stats.performanceMetrics)
```

### 6. UX提供者

#### UXProvider - UX提供者
为整个应用提供UX功能。

```tsx
import { UXProvider } from '@/components/ErrorHandling'

const App = () => {
  return (
    <UXProvider
      config={{
        theme: {
          primaryColor: '#1890ff',
          borderRadius: 6,
        },
        ux: {
          enableErrorReporting: true,
          enablePerformanceMonitoring: true,
          errorReportingEndpoint: '/api/errors',
        },
        errorBoundary: {
          onError: (error, errorInfo) => {
            console.error('Global error:', error, errorInfo)
          },
        },
      }}
    >
      <YourApp />
    </UXProvider>
  )
}
```

## 最佳实践

### 1. 错误处理
- 在应用根部使用 `GlobalErrorBoundary`
- 为异步操作提供适当的错误反馈
- 使用有意义的错误消息
- 提供恢复操作（重试、刷新等）

### 2. 加载状态
- 为所有异步操作提供加载指示
- 使用骨架屏提升感知性能
- 避免过短的加载状态闪烁

### 3. 用户反馈
- 及时提供操作结果反馈
- 使用适当的反馈类型（成功、警告、错误）
- 提供撤销操作的能力

### 4. 确认操作
- 对危险操作（删除、覆盖）使用确认对话框
- 提供清晰的操作描述
- 使用危险样式突出风险

### 5. 性能监控
- 监控关键操作的性能
- 记录用户行为用于分析
- 设置合理的性能阈值

## 示例应用

查看 `UXDemo` 组件了解所有功能的完整演示：

```tsx
import { UXDemo } from '@/components/ErrorHandling'

<UXDemo />
```

## 测试

所有UX组件都有完整的单元测试，位于 `__tests__` 目录中。运行测试：

```bash
npm test -- UXComponents.test.tsx
```

## 配置

### 全局配置
在应用启动时配置UX管理器：

```tsx
import { uxManager } from '@/utils/uxManager'

uxManager.updateConfig({
  enableErrorReporting: true,
  errorReportingEndpoint: '/api/errors',
  notificationDuration: 4.5,
  performanceThreshold: 1000,
})
```

### 主题配置
通过 `UXProvider` 配置主题：

```tsx
<UXProvider
  config={{
    theme: {
      primaryColor: '#1890ff',
      borderRadius: 6,
      fontSize: 14,
    },
  }}
>
  <App />
</UXProvider>
```

## 故障排除

### 常见问题

1. **错误边界不工作**
   - 确保 `GlobalErrorBoundary` 包装了可能出错的组件
   - 检查是否在事件处理器中抛出错误（需要手动处理）

2. **通知不显示**
   - 检查 `UXProvider` 是否正确配置
   - 确认 Ant Design 的样式已正确加载

3. **性能监控数据不准确**
   - 确保在正确的时机调用 `startMeasure` 和 `endMeasure`
   - 检查浏览器是否支持 Performance API

4. **表单状态不同步**
   - 确保在所有输入变化时调用 `markDirty`
   - 检查页面刷新监听器是否正确设置

### 调试技巧

1. 使用浏览器开发者工具查看错误报告
2. 检查控制台中的性能指标日志
3. 使用 React DevTools 查看组件状态
4. 查看 `uxManager.getStats()` 获取统计信息

## 更新日志

### v1.0.0
- ✅ 初始版本发布
- ✅ 完整的错误处理系统
- ✅ 加载状态管理
- ✅ 用户反馈组件
- ✅ 性能监控功能
- ✅ 表单增强功能
- ✅ 全局UX管理器

## 贡献指南

1. 遵循现有的代码风格
2. 为新功能添加测试
3. 更新相关文档
4. 确保向后兼容性