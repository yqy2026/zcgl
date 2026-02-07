# 性能优化指南

## 表格性能优化

### AssetList 组件优化措施

#### 已实施的优化

1. **React.memo 优化**
   - 组件已使用 `React.memo` 包装，避免不必要的重渲染

2. **响应式配置**
   - 移动端自动隐藏次要列，减少渲染负担
   - 动态调整滚动配置，优化不同屏幕尺寸下的性能

3. **useMemo 和 useCallback**
   - 列定义使用 `useMemo` 缓存
   - 事件处理函数使用 `useCallback` 优化

4. **分页加载**
   - 默认每页 20 条记录
   - 支持切换到 10/20/50/100 条每页
   - 避免一次性加载大量数据

#### 进一步优化建议

##### 1. 大数据量场景（1000+ 条记录）

如果数据量超过 1000 条，考虑以下方案：

**方案 A: 使用 Ant Design Table 的虚拟滚动**

```typescript
<Table
  columns={columns}
  dataSource={data}
  // 启用虚拟滚动
  scroll={{ x: 'max-content', y: 600 }}
  pagination={false} // 虚拟滚动时禁用分页
  // 其他配置...
/>
```

**方案 B: 使用 @tanstack/react-virtual 自定义虚拟列表**

```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

const VirtualizedList = () => {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 55, // 每行高度
    overscan: 5,
  });

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px` }}>
        {virtualizer.getVirtualItems().map(virtualRow => (
          <div
            key={virtualRow.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            {/* 渲染行 */}
          </div>
        ))}
      </div>
    </div>
  );
};
```

##### 2. 图片优化

如果表格中包含图片：

```typescript
import { useLazyImage } from '@/utils/optimization';

const ImageCell = ({ src }: { src: string }) => {
  const { imageSrc, imgRef, isLoaded } = useLazyImage(src);

  return (
    <img
      ref={imgRef}
      src={imageSrc}
      alt=""
      loading="lazy"
      style={{ opacity: isLoaded ? 1 : 0 }}
    />
  );
};
```

##### 3. 搜索防抖

为搜索输入添加防抖：

```typescript
import { useDebounce } from '@/utils/optimization';

const SearchInput = () => {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery) {
      performSearch(debouncedQuery);
    }
  }, [debouncedQuery]);

  return <Input value={query} onChange={e => setQuery(e.target.value)} />;
};
```

##### 4. 列宽优化

避免固定列宽，使用响应式列宽：

```typescript
const columns = [
  {
    title: '物业名称',
    dataIndex: 'property_name',
    width: 200, // ❌ 固定宽度
    // ✅ 改为
    // minWidth: 150,
    // flex: 1,
  },
];
```

##### 5. 数据缓存

使用 React Query 缓存数据：

```typescript
import { useQuery } from '@tanstack/react-query';

const useAssets = (params: AssetQueryParams) => {
  return useQuery({
    queryKey: ['assets', params],
    queryFn: () => fetchAssets(params),
    staleTime: 5 * 60 * 1000, // 5 分钟
    cacheTime: 10 * 60 * 1000, // 10 分钟
  });
};
```

## 性能监控

### 使用 Web Vitals 监控性能指标

项目已集成 Web Vitals 监控（`src/utils/performance.ts`），关键指标包括：

- **FCP** (First Contentful Paint): 首次内容绘制
- **LCP** (Largest Contentful Paint): 最大内容绘制
- **FID** (First Input Delay): 首次输入延迟
- **CLS** (Cumulative Layout Shift): 累积布局偏移

### 性能目标

- LCP < 2.5s
- FID < 100ms
- CLS < 0.1

### 性能分析工具

```bash
# 运行 Lighthouse 审计
npx lighthouse http://localhost:5173 --view

# 性能分析
npm run build -- --profile
```

## 内存优化

### 避免内存泄漏

```typescript
useEffect(() => {
  const subscription = someObservable.subscribe();

  return () => {
    // 清理订阅
    subscription.unsubscribe();
  };
}, []);
```

### 避免闭包陷阱

```typescript
// ❌ 错误：每次渲染都创建新函数
useEffect(() => {
  const handler = () => {
    console.log(data);
  };
  window.addEventListener('resize', handler);
  return () => window.removeEventListener('resize', handler);
}, [data]);

// ✅ 正确：使用 useCallback
const handler = useCallback(() => {
  console.log(data);
}, [data]);

useEffect(() => {
  window.addEventListener('resize', handler);
  return () => window.removeEventListener('resize', handler);
}, [handler]);
```

## 代码分割

### 路由级别代码分割

```typescript
// 使用 React.lazy 懒加载组件
const AssetList = React.lazy(() => import('@/components/Asset/AssetList'));

function App() {
  return (
    <Suspense fallback={<Spin />}>
      <AssetList />
    </Suspense>
  );
}
```

### 组件级别代码分割

```typescript
// 大型组件按需加载
const HeavyChart = React.lazy(() => import('./HeavyChart'));
```

## 总结

当前 AssetList 组件已经实施了多项性能优化措施：

1. ✅ 使用 React.memo 避免不必要的重渲染
2. ✅ 使用 useMemo 和 useCallback 优化计算和回调
3. ✅ 响应式设计，移动端隐藏次要列
4. ✅ 分页加载，避免大量数据同时渲染
5. ✅ 表格使用 sticky header，提升长列表体验

对于大数据量场景（1000+ 条），建议：
- 启用 Ant Design Table 的虚拟滚动
- 或使用 @tanstack/react-virtual 自定义虚拟列表
- 添加搜索防抖
- 使用图片懒加载
- 优化列宽配置

参考资源：
- [Ant Design Table 性能](https://ant.design/components/table#components-table-demo-virtual-list)
- [TanStack Virtual](https://tanstack.com/virtual/latest)
- [Web Vitals](https://web.dev/vitals/)
