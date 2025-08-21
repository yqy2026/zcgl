import { lazy, ComponentType } from 'react'
import { SkeletonLoader } from '@/components/Loading'

// 懒加载组件的配置
interface LazyLoadOptions {
  fallback?: React.ComponentType
  delay?: number
  timeout?: number
}

// 创建懒加载组件
export const createLazyComponent = <T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  options: LazyLoadOptions = {}
): T => {
  const {
    fallback = () => <SkeletonLoader type="list" loading={true} />,
    delay = 200,
    timeout = 10000,
  } = options

  // 添加延迟和超时处理
  const delayedImport = () => {
    return Promise.race([
      // 添加最小延迟，避免闪烁
      new Promise<{ default: T }>((resolve) => {
        setTimeout(() => {
          importFunc().then(resolve).catch((error) => {
            console.error('Lazy load failed:', error)
            throw error
          })
        }, delay)
      }),
      // 超时处理
      new Promise<never>((_, reject) => {
        setTimeout(() => {
          reject(new Error(`Lazy load timeout after ${timeout}ms`))
        }, timeout)
      }),
    ])
  }

  return lazy(delayedImport) as T
}

// 预加载页面组件
export const preloadComponent = (importFunc: () => Promise<any>) => {
  // 在空闲时间预加载
  if ('requestIdleCallback' in window) {
    requestIdleCallback(() => {
      importFunc().catch(console.error)
    })
  } else {
    // 降级到setTimeout
    setTimeout(() => {
      importFunc().catch(console.error)
    }, 100)
  }
}

// 懒加载的页面组件
export const LazyAssetListPage = createLazyComponent(
  () => import('@/pages/AssetListPage'),
  { fallback: () => <SkeletonLoader type="table" loading={true} /> }
)

export const LazyAssetDetailPage = createLazyComponent(
  () => import('@/pages/AssetDetailPage'),
  { fallback: () => <SkeletonLoader type="detail" loading={true} /> }
)

export const LazyAssetFormPage = createLazyComponent(
  () => import('@/pages/AssetFormPage'),
  { fallback: () => <SkeletonLoader type="form" loading={true} /> }
)

export const LazyDashboardPage = createLazyComponent(
  () => import('@/pages/DashboardPage'),
  { fallback: () => <SkeletonLoader type="chart" loading={true} /> }
)

export const LazyImportExportPage = createLazyComponent(
  () => import('@/pages/ImportExportPage'),
  { fallback: () => <SkeletonLoader type="form" loading={true} /> }
)

// 预加载关键页面
export const preloadCriticalPages = () => {
  // 预加载最常用的页面
  preloadComponent(() => import('@/pages/AssetListPage'))
  preloadComponent(() => import('@/pages/DashboardPage'))
}

// 根据路由预加载相关页面
export const preloadRoutePages = (currentPath: string) => {
  switch (true) {
    case currentPath.startsWith('/assets'):
      preloadComponent(() => import('@/pages/AssetDetailPage'))
      preloadComponent(() => import('@/pages/AssetFormPage'))
      break
    case currentPath === '/dashboard':
      preloadComponent(() => import('@/pages/AssetListPage'))
      break
    default:
      break
  }
}

// 组件级别的懒加载
export const LazyAssetChart = createLazyComponent(
  () => import('@/components/Charts/AssetDistributionChart')
)

export const LazyOccupancyChart = createLazyComponent(
  () => import('@/components/Charts/OccupancyRateChart')
)

export const LazyAreaChart = createLazyComponent(
  () => import('@/components/Charts/AreaStatisticsChart')
)

// 工具函数：检查组件是否已加载
export const isComponentLoaded = (component: any): boolean => {
  return component && typeof component !== 'function'
}

// 工具函数：批量预加载组件
export const batchPreload = (importFuncs: Array<() => Promise<any>>) => {
  return Promise.allSettled(importFuncs.map(func => func()))
}

export default {
  createLazyComponent,
  preloadComponent,
  preloadCriticalPages,
  preloadRoutePages,
  isComponentLoaded,
  batchPreload,
}