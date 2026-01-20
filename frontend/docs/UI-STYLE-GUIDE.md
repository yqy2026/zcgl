# UI 样式重构指南

## 概述

为了提升代码可维护性和一致性，我们创建了一套共享的样式类和可重用组件来替代内联样式。

## 📚 新增资源

### 1. 全局样式类 (`src/styles/common.css`)

提供了一系列实用的CSS类，用于常见的布局和间距需求。

#### 页面容器类

```css
.pageContainer          /* 标准页面容器: padding: 24px */
.pageContainerCenter    /* 居中的页面容器 */
.pageContainerCompact   /* 紧凑页面容器: padding: 16px */
.pageContainerSpacious  /* 宽松页面容器: padding: 32px */
.pageContainerResponsive /* 响应式页面容器: clamp(12px, 2vw, 24px) */
```

#### 状态容器类

```css
.loadingContainer       /* 加载状态容器: 居中布局 */
.emptyState            /* 空状态容器: 居中布局 */
.errorContainer        /* 错误状态容器 */
```

#### 间距工具类

```css
/* Margin Bottom */
.marginBottomSm  /* 8px */
.marginBottomMd  /* 16px */
.marginBottomLg  /* 24px */

/* Margin Top */
.marginTopSm     /* 8px */
.marginTopMd     /* 16px */
.marginTopLg     /* 24px */
```

#### 文本对齐类

```css
.textCenter   /* 居中对齐 */
.textLeft     /* 左对齐 */
.textRight    /* 右对齐 */
```

### 2. 可重用组件 (`src/components/Common/StateContainer.tsx`)

提供了一组预制的React组件，用于常见的页面状态。

#### LoadingContainer

统一的加载状态容器。

```tsx
import { LoadingContainer } from '@/components/Common/StateContainer';

// 基础用法
<LoadingContainer />

// 自定义加载文本
<LoadingContainer text="正在加载数据..." />

// 条件渲染
<LoadingContainer loading={isLoading}>
  <YourContent />
</LoadingContainer>
```

#### EmptyStateContainer

统一的空状态容器。

```tsx
import { EmptyStateContainer } from '@/components/Common/StateContainer';

<EmptyStateContainer
  description="暂无数据"
  action={<Button>创建新数据</Button>}
/>
```

#### ErrorStateContainer

统一的错误状态容器。

```tsx
import { ErrorStateContainer } from '@/components/Common/StateContainer';

<ErrorStateContainer
  title="加载失败"
  error={error}
  onRetry={() => refetch()}
/>
```

#### PageContainer

标准的页面容器组件。

```tsx
import { PageContainer } from '@/components/Common/StateContainer';

<PageContainer>
  <YourPageContent />
</PageContainer>

// 带额外的className
<PageContainer className="custom-class">
  <YourPageContent />
</PageContainer>
```

#### ContentSection

内容区块组件，自动添加底部间距。

```tsx
import { ContentSection } from '@/components/Common/StateContainer';

<ContentSection spacing="lg">
  <YourSectionContent />
</ContentSection>

// spacing选项: 'sm' | 'md' | 'lg' | 'xl'
```

## 🔄 从内联样式迁移

### 示例1: 简单的页面容器

**❌ 之前 (内联样式)**:
```tsx
<div style={{ padding: '24px' }}>
  <h1>页面标题</h1>
</div>
```

**✅ 之后 (CSS类)**:
```tsx
<div className="pageContainer">
  <h1>页面标题</h1>
</div>
```

### 示例2: 加载状态

**❌ 之前 (内联样式)**:
```tsx
{isLoading && (
  <div style={{ padding: '24px', textAlign: 'center' }}>
    <Spin size="large" />
    <div style={{ marginTop: '16px' }}>加载中...</div>
  </div>
)}
```

**✅ 之后 (组件)**:
```tsx
{isLoading && <LoadingContainer text="加载中..." />}
```

### 示例3: 错误状态

**❌ 之前 (内联样式)**:
```tsx
{error && (
  <div style={{ padding: '24px' }}>
    <Alert
      message="错误"
      description={error.message}
      type="error"
    />
  </div>
)}
```

**✅ 之后 (组件)**:
```tsx
{error && (
  <ErrorStateContainer
    error={error}
    onRetry={() => refetch()}
  />
)}
```

### 示例4: 内容区块

**❌ 之前 (内联样式)**:
```tsx
<div style={{ marginBottom: '24px' }}>
  <Card title="区块标题">
    内容...
  </Card>
</div>
```

**✅ 之后 (组件)**:
```tsx
<ContentSection spacing="lg">
  <Card title="区块标题">
    内容...
  </Card>
</ContentSection>
```

## 📋 迁移检查清单

当你重构组件以使用新的样式系统时，请确保：

- [ ] 移除所有 `style={{ padding: '24px' }}` → 使用 `className="pageContainer"`
- [ ] 移除所有 `style={{ textAlign: 'center' }}` → 使用 `className="textCenter"`
- [ ] 移除所有 `style={{ marginBottom: '24px' }}` → 使用 `className="marginBottomLg"`
- [ ] 加载状态使用 `<LoadingContainer>`
- [ ] 空状态使用 `<EmptyStateContainer>`
- [ ] 错误状态使用 `<ErrorStateContainer>`
- [ ] 页面容器使用 `<PageContainer>`

## 🎯 完整示例

这是一个完整重构的页面示例：

```tsx
import { PageContainer, ContentSection, LoadingContainer } from '@/components/Common/StateContainer';

const MyPage: React.FC = () => {
  const { data, isLoading, error } = useQuery(...);

  // 加载状态
  if (isLoading) {
    return <LoadingContainer text="正在加载数据..." />;
  }

  // 错误状态
  if (error) {
    return <ErrorStateContainer error={error} onRetry={() => refetch()} />;
  }

  // 主内容
  return (
    <PageContainer>
      <ContentSection spacing="lg">
        <h1>页面标题</h1>
      </ContentSection>

      <ContentSection spacing="md">
        <Card>内容...</Card>
      </ContentSection>
    </PageContainer>
  );
};
```

## 📊 收益

使用这套样式系统后，你将获得：

✅ **一致的UI** - 所有页面使用相同的间距和布局
✅ **更少的代码** - 减少重复的内联样式
✅ **更好的维护性** - 集中管理样式
✅ **更容易的主题定制** - 通过CSS变量
✅ **更好的可读性** - 代码更简洁清晰

## 🚀 下一步

1. **开始迁移** - 从新的页面开始使用这套系统
2. **渐进式重构** - 逐步重构现有页面
3. **扩展工具类** - 根据需要添加新的工具类
4. **团队协作** - 在团队中推广这些最佳实践

## ❓ 常见问题

**Q: 必须立即迁移所有代码吗？**
A: 不。这是一个渐进式的迁移。新代码应该使用新的样式系统，旧代码可以在维护时逐步迁移。

**Q: 可以创建自定义的工具类吗？**
A: 可以。如果发现重复使用的样式模式，将其添加到 `common.css` 中。

**Q: 这些类会影响性能吗？**
A: 不会。CSS类实际上比内联样式更高效，因为浏览器可以缓存样式规则。

**Q: 如何处理响应式布局？**
A: 使用 `pageContainerResponsive` 类，它使用 `clamp()` 函数提供响应式padding。
