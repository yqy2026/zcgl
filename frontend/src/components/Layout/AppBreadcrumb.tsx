import React from 'react'
import { Breadcrumb } from 'antd'
import {
  HomeOutlined,
  DashboardOutlined,
  UnorderedListOutlined,
  PlusOutlined,
  SearchOutlined,
  FileExcelOutlined,
  UploadOutlined,
  DownloadOutlined,
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  SettingOutlined,
  EditOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import { useLocation, Link } from 'react-router-dom'

const AppBreadcrumb: React.FC = () => {
  const location = useLocation()
  const pathname = location.pathname

  // 面包屑配置映射
  const breadcrumbNameMap: Record<string, { name: string; icon?: React.ReactNode }> = {
    '/': { name: '首页', icon: <HomeOutlined /> },
    '/dashboard': { name: '数据看板', icon: <DashboardOutlined /> },
    '/assets': { name: '资产列表', icon: <UnorderedListOutlined /> },
    '/assets/new': { name: '新增资产', icon: <PlusOutlined /> },
    '/assets/search': { name: '高级搜索', icon: <SearchOutlined /> },
    '/data/import': { name: '数据导入', icon: <UploadOutlined /> },
    '/data/export': { name: '数据导出', icon: <DownloadOutlined /> },
    '/data/import-export': { name: '导入导出', icon: <FileExcelOutlined /> },
    '/analytics/occupancy': { name: '出租率分析', icon: <LineChartOutlined /> },
    '/analytics/distribution': { name: '资产分布', icon: <PieChartOutlined /> },
    '/analytics/area': { name: '面积统计', icon: <BarChartOutlined /> },
    '/system/users': { name: '用户管理', icon: <SettingOutlined /> },
    '/system/roles': { name: '角色管理', icon: <SettingOutlined /> },
    '/system/logs': { name: '操作日志', icon: <SettingOutlined /> },
    '/system/dictionaries': { name: '枚举值字段', icon: <SettingOutlined /> },
    '/ownership': { name: '权属方管理', icon: <SettingOutlined /> },
  }

  // 生成面包屑项
  const generateBreadcrumbItems = () => {
    const pathSnippets = pathname.split('/').filter(i => i)
    
    // 首页面包屑
    const breadcrumbItems = [
      {
        title: (
          <Link to="/dashboard">
            <HomeOutlined style={{ marginRight: 4 }} />
            首页
          </Link>
        ),
      },
    ]

    // 处理特殊路径
    if (pathname === '/dashboard' || pathname === '/') {
      return [
        {
          title: (
            <span>
              <DashboardOutlined style={{ marginRight: 4 }} />
              数据看板
            </span>
          ),
        },
      ]
    }

    // 处理资产详情页面
    const assetDetailMatch = pathname.match(/^\/assets\/(\d+)$/)
    if (assetDetailMatch) {
      const _assetId = assetDetailMatch[1]
      return [
        ...breadcrumbItems,
        {
          title: (
            <Link to="/assets">
              <UnorderedListOutlined style={{ marginRight: 4 }} />
              资产管理
            </Link>
          ),
        },
        {
          title: (
            <Link to="/assets">
              <UnorderedListOutlined style={{ marginRight: 4 }} />
              资产列表
            </Link>
          ),
        },
        {
          title: (
            <span>
              <EyeOutlined style={{ marginRight: 4 }} />
              资产详情
            </span>
          ),
        },
      ]
    }

    // 处理资产编辑页面
    const assetEditMatch = pathname.match(/^\/assets\/(\d+)\/edit$/)
    if (assetEditMatch) {
      const assetId = assetEditMatch[1]
      return [
        ...breadcrumbItems,
        {
          title: (
            <Link to="/assets">
              <UnorderedListOutlined style={{ marginRight: 4 }} />
              资产管理
            </Link>
          ),
        },
        {
          title: (
            <Link to="/assets">
              <UnorderedListOutlined style={{ marginRight: 4 }} />
              资产列表
            </Link>
          ),
        },
        {
          title: (
            <Link to={`/assets/${assetId}`}>
              <EyeOutlined style={{ marginRight: 4 }} />
              资产详情
            </Link>
          ),
        },
        {
          title: (
            <span>
              <EditOutlined style={{ marginRight: 4 }} />
              编辑资产
            </span>
          ),
        },
      ]
    }

    // 构建普通路径的面包屑
    let currentPath = ''
    
    pathSnippets.forEach((snippet, index) => {
      currentPath += `/${snippet}`
      const isLast = index === pathSnippets.length - 1
      const breadcrumbConfig = breadcrumbNameMap[currentPath]
      
      if (breadcrumbConfig !== null && breadcrumbConfig !== undefined) {
        if (isLast) {
          // 最后一项不添加链接
          breadcrumbItems.push({
            title: (
              <span>
                {(breadcrumbConfig.icon !== null && breadcrumbConfig.icon !== undefined) && (
                  <span style={{ marginRight: 4 }}>{breadcrumbConfig.icon}</span>
                )}
                {breadcrumbConfig.name}
              </span>
            ),
          })
        } else {
          // 中间项添加链接
          breadcrumbItems.push({
            title: (
              <Link to={currentPath}>
                {(breadcrumbConfig.icon !== null && breadcrumbConfig.icon !== undefined) && (
                  <span style={{ marginRight: 4 }}>{breadcrumbConfig.icon}</span>
                )}
                {breadcrumbConfig.name}
              </Link>
            ),
          })
        }
      }
    })

    // 添加分类面包屑
    if (pathname !== null && pathname !== undefined && pathname !== '' && pathname.startsWith('/assets') && !breadcrumbItems.some((item: { title: string | React.ReactNode }) =>
      typeof item.title === 'object' &&
      React.isValidElement(item.title) &&
      ((item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children !== null && (item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children !== undefined) &&
      typeof (item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children === 'string' &&
      ((item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children as string).includes('资产管理')
    )) {
      breadcrumbItems.splice(1, 0, {
        title: (
          <span>
            <UnorderedListOutlined style={{ marginRight: 4 }} />
            资产管理
          </span>
        ),
      })
    }

    if (pathname !== null && pathname !== undefined && pathname !== '' && pathname.startsWith('/data') && !breadcrumbItems.some((item: { title: string | React.ReactNode }) =>
      typeof item.title === 'object' &&
      React.isValidElement(item.title) &&
      ((item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children !== null && (item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children !== undefined) &&
      typeof (item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children === 'string' &&
      ((item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children as string).includes('数据管理')
    )) {
      breadcrumbItems.splice(1, 0, {
        title: (
          <span>
            <FileExcelOutlined style={{ marginRight: 4 }} />
            数据管理
          </span>
        ),
      })
    }

    if (pathname !== null && pathname !== undefined && pathname !== '' && pathname.startsWith('/analytics') && !breadcrumbItems.some((item: { title: string | React.ReactNode }) =>
      typeof item.title === 'object' &&
      React.isValidElement(item.title) &&
      ((item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children !== null && (item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children !== undefined) &&
      typeof (item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children === 'string' &&
      ((item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children as string).includes('数据分析')
    )) {
      breadcrumbItems.splice(1, 0, {
        title: (
          <span>
            <BarChartOutlined style={{ marginRight: 4 }} />
            数据分析
          </span>
        ),
      })
    }

    if (pathname !== null && pathname !== undefined && pathname !== '' && pathname.startsWith('/system') && !breadcrumbItems.some((item: { title: string | React.ReactNode }) =>
      typeof item.title === 'object' &&
      React.isValidElement(item.title) &&
      ((item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children !== null && (item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children !== undefined) &&
      typeof (item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children === 'string' &&
      ((item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children as string).includes('系统管理')
    )) {
      breadcrumbItems.splice(1, 0, {
        title: (
          <span>
            <SettingOutlined style={{ marginRight: 4 }} />
            系统管理
          </span>
        ),
      })
    }

    if (pathname !== null && pathname !== undefined && pathname !== '' && pathname.startsWith('/ownership') && !breadcrumbItems.some((item: { title: string | React.ReactNode }) =>
      typeof item.title === 'object' &&
      React.isValidElement(item.title) &&
      ((item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children !== null && (item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children !== undefined) &&
      typeof (item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children === 'string' &&
      ((item.title as React.ReactElement<{ children?: React.ReactNode }>).props?.children as string).includes('资产管理')
    )) {
      breadcrumbItems.splice(1, 0, {
        title: (
          <span>
            <UnorderedListOutlined style={{ marginRight: 4 }} />
            资产管理
          </span>
        ),
      })
    }

    return breadcrumbItems
  }

  return (
    <Breadcrumb
      items={generateBreadcrumbItems()}
      style={{
        fontSize: '14px',
      }}
    />
  )
}

export default AppBreadcrumb