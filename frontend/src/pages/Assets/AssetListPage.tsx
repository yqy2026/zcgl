import React, { useState } from 'react'
import { 
  Card, 
  Table, 
  Button, 
  Space, 
  Input, 
  Select, 
  Tag, 
  Tooltip, 
  Dropdown, 
  Row, 
  Col,
  Statistic,
  Typography,
  Switch,
} from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  FilterOutlined,
  ExportOutlined,
  ImportOutlined,
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  MoreOutlined,
  AppstoreOutlined,
  BarsOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAssetList } from './hooks/useAssetList'
import AssetFilters from './components/AssetFilters'
import AssetCard from './components/AssetCard'

const { Title, Text } = Typography
const { Search } = Input

const AssetListPage: React.FC = () => {
  const navigate = useNavigate()
  const [viewMode, setViewMode] = useState<'table' | 'card'>('table')
  const [showFilters, setShowFilters] = useState(false)
  
  const {
    assets,
    loading,
    pagination,
    filters,
    summary,
    handleSearch,
    handleFilter,
    handlePaginationChange,
    handleBatchDelete,
    handleExport,
  } = useAssetList()

  // 表格列配置
  const columns = [
    {
      title: '物业名称',
      dataIndex: 'propertyName',
      key: 'propertyName',
      width: 200,
      fixed: 'left' as const,
      render: (text: string, record: any) => (
        <Space direction="vertical" size={0}>
          <Button 
            type="link" 
            style={{ padding: 0, height: 'auto' }}
            onClick={() => navigate(`/assets/${record.id}`)}
          >
            <Text strong>{text}</Text>
          </Button>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.address}
          </Text>
        </Space>
      ),
    },
    {
      title: '权属方',
      dataIndex: 'ownershipEntity',
      key: 'ownershipEntity',
      width: 150,
    },
    {
      title: '物业性质',
      dataIndex: 'propertyNature',
      key: 'propertyNature',
      width: 100,
      render: (nature: string) => (
        <Tag color={nature === '经营类' ? 'green' : 'blue'}>
          {nature}
        </Tag>
      ),
    },
    {
      title: '使用状态',
      dataIndex: 'usageStatus',
      key: 'usageStatus',
      width: 100,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          '出租': 'success',
          '闲置': 'warning',
          '自用': 'processing',
          '公房': 'default',
          '其他': 'default',
        }
        return <Tag color={colorMap[status]}>{status}</Tag>
      },
    },
    {
      title: '面积信息',
      key: 'area',
      width: 150,
      render: (record: any) => (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: '12px' }}>
            总面积: {record.actualPropertyArea}㎡
          </Text>
          <Text style={{ fontSize: '12px' }}>
            可租: {record.rentableArea}㎡
          </Text>
          <Text style={{ fontSize: '12px' }}>
            已租: {record.rentedArea}㎡
          </Text>
        </Space>
      ),
    },
    {
      title: '出租率',
      dataIndex: 'occupancyRate',
      key: 'occupancyRate',
      width: 100,
      render: (rate: string) => (
        <Text strong style={{ 
          color: parseFloat(rate) > 80 ? '#52c41a' : 
                parseFloat(rate) > 50 ? '#faad14' : '#ff4d4f' 
        }}>
          {rate}%
        </Text>
      ),
    },
    {
      title: '确权状态',
      dataIndex: 'ownershipStatus',
      key: 'ownershipStatus',
      width: 100,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          '已确权': 'success',
          '未确权': 'error',
          '部分确权': 'warning',
        }
        return <Tag color={colorMap[status]}>{status}</Tag>
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      fixed: 'right' as const,
      render: (record: any) => (
        <Dropdown
          menu={{
            items: [
              {
                key: 'view',
                icon: <EyeOutlined />,
                label: '查看详情',
                onClick: () => navigate(`/assets/${record.id}`),
              },
              {
                key: 'edit',
                icon: <EditOutlined />,
                label: '编辑',
                onClick: () => navigate(`/assets/${record.id}/edit`),
              },
              {
                type: 'divider',
              },
              {
                key: 'delete',
                icon: <DeleteOutlined />,
                label: '删除',
                danger: true,
                onClick: () => handleBatchDelete([record.id]),
              },
            ],
          }}
          trigger={['click']}
        >
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题和统计 */}
      <div style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2} style={{ margin: 0 }}>
              资产清单
            </Title>
            <Text type="secondary">
              管理和查看所有物业资产信息
            </Text>
          </Col>
          <Col>
            <Space size="large">
              <Statistic 
                title="资产总数" 
                value={summary?.total || 0} 
                suffix="个"
              />
              <Statistic 
                title="出租中" 
                value={summary?.rented || 0} 
                suffix="个"
                valueStyle={{ color: '#52c41a' }}
              />
              <Statistic 
                title="平均出租率" 
                value={summary?.avgOccupancyRate || 0} 
                suffix="%"
                precision={1}
                valueStyle={{ color: '#1890ff' }}
              />
            </Space>
          </Col>
        </Row>
      </div>

      {/* 操作栏 */}
      <Card style={{ marginBottom: '16px' }}>
        <Row justify="space-between" align="middle">
          <Col flex="auto">
            <Space size="middle">
              {/* 搜索框 */}
              <Search
                placeholder="搜索物业名称、地址、权属方..."
                allowClear
                style={{ width: 300 }}
                onSearch={handleSearch}
                enterButton={<SearchOutlined />}
              />

              {/* 筛选按钮 */}
              <Button
                icon={<FilterOutlined />}
                onClick={() => setShowFilters(!showFilters)}
                type={showFilters ? 'primary' : 'default'}
              >
                筛选 {Object.keys(filters).length > 0 && `(${Object.keys(filters).length})`}
              </Button>
            </Space>
          </Col>

          <Col>
            <Space>
              {/* 视图切换 */}
              <Space.Compact>
                <Button
                  icon={<BarsOutlined />}
                  type={viewMode === 'table' ? 'primary' : 'default'}
                  onClick={() => setViewMode('table')}
                />
                <Button
                  icon={<AppstoreOutlined />}
                  type={viewMode === 'card' ? 'primary' : 'default'}
                  onClick={() => setViewMode('card')}
                />
              </Space.Compact>

              {/* 操作按钮 */}
              <Button
                icon={<ImportOutlined />}
                onClick={() => navigate('/assets/import')}
              >
                导入
              </Button>
              <Button
                icon={<ExportOutlined />}
                onClick={handleExport}
              >
                导出
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate('/assets/new')}
              >
                新增资产
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 筛选器 */}
        {showFilters && (
          <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #f0f0f0' }}>
            <AssetFilters
              filters={filters}
              onChange={handleFilter}
              onReset={() => handleFilter({})}
            />
          </div>
        )}
      </Card>

      {/* 数据展示区域 */}
      <Card>
        {viewMode === 'table' ? (
          <Table
            columns={columns}
            dataSource={assets}
            loading={loading}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => 
                `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              onChange: handlePaginationChange,
            }}
            scroll={{ x: 1200 }}
            rowKey="id"
            size="middle"
          />
        ) : (
          <Row gutter={[16, 16]}>
            {assets?.map((asset: any) => (
              <Col xs={24} sm={12} lg={8} xl={6} key={asset.id}>
                <AssetCard 
                  asset={asset} 
                  onView={() => navigate(`/assets/${asset.id}`)}
                  onEdit={() => navigate(`/assets/${asset.id}/edit`)}
                  onDelete={() => handleBatchDelete([asset.id])}
                />
              </Col>
            ))}
          </Row>
        )}
      </Card>
    </div>
  )
}

export default AssetListPage