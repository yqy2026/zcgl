import React, { Suspense } from 'react'
import { SkeletonLoader } from '@/components/Loading'
import { createLogger } from '@/utils/logger'

const routeLogger = createLogger('LazyRoutes')

// 懒加载页面组件
const DashboardPage = React.lazy(() => import('@/pages/Dashboard/DashboardPage'))
const AssetListPage = React.lazy(() => import('@/pages/Assets/AssetListPage'))
const AssetDetailPage = React.lazy(() => import('@/pages/Assets/AssetDetailPage'))
const AssetFormPage = React.lazy(() => import('@/pages/Assets/AssetCreatePage'))
const ImportExportPage = React.lazy(() => import('@/pages/Assets/AssetImportPage'))

// 懒加载包装器
const LazyWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Suspense fallback={<SkeletonLoader type="detail" rows={5} />}>
    {children}
  </Suspense>
)

// 导出懒加载组件
export const LazyDashboardPage = () => (
  <LazyWrapper>
    <DashboardPage />
  </LazyWrapper>
)

export const LazyAssetListPage = () => (
  <LazyWrapper>
    <AssetListPage />
  </LazyWrapper>
)

export const LazyAssetDetailPage = () => (
  <LazyWrapper>
    <AssetDetailPage />
  </LazyWrapper>
)

export const LazyAssetFormPage = () => (
  <LazyWrapper>
    <AssetFormPage />
  </LazyWrapper>
)

export const LazyImportExportPage = () => (
  <LazyWrapper>
    <ImportExportPage />
  </LazyWrapper>
)

// 预加载函数
export const preloadRoutes = {
  dashboard: () => import('@/pages/Dashboard/DashboardPage'),
  assetList: () => import('@/pages/Assets/AssetListPage'),
  assetDetail: () => import('@/pages/Assets/AssetDetailPage'),
  assetForm: () => import('@/pages/Assets/AssetCreatePage'),
  importExport: () => import('@/pages/Assets/AssetImportPage'),
}

// 路由预加载钩子
export const useRoutePreload = () => {
  const preloadRoute = (routeName: keyof typeof preloadRoutes) => {
    preloadRoutes[routeName]().catch((error: unknown) => routeLogger.error(`Failed to preload route ${routeName}:`, error as Error))
  }

  return { preloadRoute }
}
