import React from 'react'
import { Empty, Button, Typography, Space } from 'antd'
import {
  FileTextOutlined,
  SearchOutlined,
  PlusOutlined,
  ReloadOutlined,
  InboxOutlined,
  DisconnectOutlined,
  FilterOutlined,
} from '@ant-design/icons'

const { Text } = Typography

export type EmptyStateType = 
  | 'no-data' 
  | 'no-search-results' 
  | 'no-filter-results'
  | 'network-error'
  | 'loading-error'
  | 'permission-denied'
  | 'maintenance'

interface EmptyStateProps {
  type?: EmptyStateType
  title?: string
  description?: string
  image?: React.ReactNode
  actions?: React.ReactNode
  showCreateButton?: boolean
  showRefreshButton?: boolean
  showClearFilterButton?: boolean
  onCreateClick?: () => void
  onRefreshClick?: () => void
  onClearFilterClick?: () => void
  style?: React.CSSProperties
  className?: string
}

const EmptyState: React.FC<EmptyStateProps> = ({
  type = 'no-data',
  title,
  description,
  image,
  actions,
  showCreateButton = false,
  showRefreshButton = false,
  showClearFilterButton = false,
  onCreateClick,
  onRefreshClick,
  onClearFilterClick,
  style,
  className,
}) => {
  // 预设配置
  const presetConfigs = {
    'no-data': {
      image: <InboxOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />,
      title: '暂无数据',
      description: '还没有任何数据，点击下方按钮开始添加',
      showCreate: true,
    },
    'no-search-results': {
      image: <SearchOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />,
      title: '无搜索结果',
      description: '没有找到符合条件的数据，请尝试其他关键词',
      showRefresh: true,
    },
    'no-filter-results': {
      image: <FilterOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />,
      title: '无筛选结果',
      description: '当前筛选条件下没有数据，请调整筛选条件',
      showClearFilter: true,
    },
    'network-error': {
      image: <DisconnectOutlined style={{ fontSize: 64, color: '#ff4d4f' }} />,
      title: '网络连接失败',
      description: '请检查网络连接，然后重试',
      showRefresh: true,
    },
    'loading-error': {
      image: <FileTextOutlined style={{ fontSize: 64, color: '#faad14' }} />,
      title: '加载失败',
      description: '数据加载失败，请稍后重试',
      showRefresh: true,
    },
    'permission-denied': {
      image: <InboxOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />,
      title: '权限不足',
      description: '您没有权限查看此内容',
      showCreate: false,
    },
    'maintenance': {
      image: <InboxOutlined style={{ fontSize: 64, color: '#1890ff' }} />,
      title: '系统维护中',
      description: '系统正在维护，请稍后再试',
      showRefresh: true,
    },
  }

  const config = presetConfigs[type]

  // 生成操作按钮
  const getActionButtons = () => {
    const buttons = []

    if ((showCreateButton || ('showCreate' in config && config.showCreate)) && onCreateClick) {
      buttons.push(
        <Button key="create" type="primary" icon={<PlusOutlined />} onClick={onCreateClick}>
          新增数据
        </Button>
      )
    }

    if ((showRefreshButton || ('showRefresh' in config && config.showRefresh)) && onRefreshClick) {
      buttons.push(
        <Button key="refresh" icon={<ReloadOutlined />} onClick={onRefreshClick}>
          刷新
        </Button>
      )
    }

    if ((showClearFilterButton || ('showClearFilter' in config && config.showClearFilter)) && onClearFilterClick) {
      buttons.push(
        <Button key="clear-filter" onClick={onClearFilterClick}>
          清除筛选
        </Button>
      )
    }

    return buttons
  }

  const actionButtons = getActionButtons()

  return (
    <div 
      style={{ 
        padding: '50px 20px',
        textAlign: 'center',
        ...style 
      }}
      className={className}
    >
      <Empty
        image={image || config.image}
        description={
          <div>
            <Text strong style={{ fontSize: 16, display: 'block', marginBottom: 8 }}>
              {title || config.title}
            </Text>
            <Text type="secondary">
              {description || config.description}
            </Text>
          </div>
        }
      >
        {(actions || actionButtons.length > 0) && (
          <Space wrap style={{ marginTop: 16 }}>
            {actions || actionButtons}
          </Space>
        )}
      </Empty>
    </div>
  )
}

// 预设的空状态组件
export const NoDataState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState type="no-data" {...props} />
)

export const NoSearchResultsState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState type="no-search-results" {...props} />
)

export const NoFilterResultsState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState type="no-filter-results" {...props} />
)

export const NetworkErrorState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState type="network-error" {...props} />
)

export const LoadingErrorState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState type="loading-error" {...props} />
)

export const PermissionDeniedState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState type="permission-denied" {...props} />
)

export const MaintenanceState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState type="maintenance" {...props} />
)

export default EmptyState