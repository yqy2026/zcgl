import React, { Suspense } from 'react'
import { SkeletonLoader } from '@/components/Loading'

// 懒加载页面组件
const DashboardPage = React.lazy(() => import('@/pages/DashboardPage'))
const AssetListPage = React.lazy(() => import('@/pages/AssetListPage'))
const AssetDetailPage = React.lazy(() => import('@/pages/AssetDetailPage'))
const AssetFormPage = React.lazy(() => import('@/pages/AssetFormPage'))
const ImportExportPage = React.lazy(() => import('@/pages/ImportExportPage'))

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
  dashboard: () => import('@/pages/DashboardPage'),
  assetList: () => import('@/pages/AssetListPage'),
  assetDetail: () => import('@/pages/AssetDetailPage'),
  assetForm: () => import('@/pages/AssetFormPage'),
  importExport: () => import('@/pages/ImportExportPage'),
}

// 路由预加载钩子
export const useRoutePreload = () => {
  const preloadRoute = (routeName: keyof typeof preloadRoutes) => {
    preloadRoutes[routeName]().catch(console.error)
  }

  return { preloadRoute }
}