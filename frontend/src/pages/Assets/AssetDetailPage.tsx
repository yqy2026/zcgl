import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  Card, 
  Descriptions, 
  Button, 
  Space, 
  Tag, 
  Divider,
  Row,
  Col,
  Statistic,
  Typography,
  Tabs,
  Timeline,
  Empty
} from 'antd'
import {
  EditOutlined,
  DeleteOutlined,
  ArrowLeftOutlined,
  HistoryOutlined,
  FileTextOutlined,
  BarChartOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { apiRequest, API_ENDPOINTS } from '../../config/api'

const { Title, Text } = Typography
const { TabPane } = Tabs

// 获取资产详情
const fetchAssetDetail = async (id: string) => {
  const result = await apiRequest<any>(API_ENDPOINTS.assetDetail(id))
  
  // 转换数据格式
  return {
    id: result.id,
    propertyName: result.property_name,
    ownershipEntity: result.ownership_entity,
    managementEntity: result.management_entity,
    address: result.address,
    landArea: result.land_area,
    actualPropertyArea: result.total_area,
    rentableArea: result.usable_area,
    rentedArea: result.usable_area, // 暂时使用可用面积
    unrentedArea: 0, // 需要计算
    nonCommercialArea: 0, // 需要计算
    ownershipStatus: result.ownership_status,
    certificatedUsage: result.certificated_usage,
    actualUsage: result.actual_usage,
    businessCategory: result.business_category,
    usageStatus: result.usage_status,
    isLitigated: result.is_litigated,
    propertyNature: result.property_nature,
    businessModel: result.business_model,
    includeInOccupancyRate: result.include_in_occupancy_rate,
    occupancyRate: result.usage_status === '出租' ? '100.00%' : '0.00%',
    leaseContract: result.lease_contract,
    tenantName: result.tenant_name,
    description: result.notes || result.description,
    createdAt: result.created_at,
    updatedAt: result.updated_at,
  }
}

const AssetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: asset, isLoading } = useQuery({
    queryKey: ['asset', id],
    queryFn: () => fetchAssetDetail(id!),
    enabled: !!id,
  })

  if (!id) {
    return <div>资产ID不存在</div>
  }

  const handleEdit = () => {
    navigate(`/assets/${id}/edit`)
  }

  const handleDelete = () => {
    // 实现删除逻辑
    console.log('删除资产:', id)
  }

  const handleBack = () => {
    navigate('/assets/list')
  }

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面头部 */}
      <div style={{ marginBottom: '24px' }}>
        <Space>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={handleBack}
          >
            返回列表
          </Button>
          <Title level={2} style={{ margin: 0 }}>
            {asset?.propertyName || '资产详情'}
          </Title>
        </Space>
      </div>

      {/* 操作按钮 */}
      <Card style={{ marginBottom: '16px' }}>
        <Space>
          <Button 
            type="primary" 
            icon={<EditOutlined />}
            onClick={handleEdit}
          >
            编辑资产
          </Button>
          <Button 
            danger 
            icon={<DeleteOutlined />}
            onClick={handleDelete}
          >
            删除资产
          </Button>
        </Space>
      </Card>

      {/* 关键指标 */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总面积"
              value={asset?.actualPropertyArea || 0}
              suffix="㎡"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="可出租面积"
              value={asset?.rentableArea || 0}
              suffix="㎡"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已出租面积"
              value={asset?.rentedArea || 0}
              suffix="㎡"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="出租率"
              value={parseFloat(asset?.occupancyRate || '0')}
              suffix="%"
              precision={2}
              valueStyle={{ 
                color: parseFloat(asset?.occupancyRate || '0') > 80 ? '#52c41a' : '#faad14' 
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 详细信息标签页 */}
      <Card>
        <Tabs defaultActiveKey="basic">
          <TabPane tab="基本信息" key="basic">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="物业名称" span={2}>
                {asset?.propertyName}
              </Descriptions.Item>
              <Descriptions.Item label="权属方">
                {asset?.ownershipEntity}
              </Descriptions.Item>
              <Descriptions.Item label="经营管理方">
                {asset?.managementEntity || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="所在地址" span={2}>
                {asset?.address}
              </Descriptions.Item>
              <Descriptions.Item label="物业性质">
                <Tag color={asset?.propertyNature === '经营类' ? 'green' : 'blue'}>
                  {asset?.propertyNature}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="使用状态">
                <Tag color="success">{asset?.usageStatus}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="确权状态">
                <Tag color="success">{asset?.ownershipStatus}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="是否涉诉">
                <Tag color={asset?.isLitigated === '否' ? 'success' : 'error'}>
                  {asset?.isLitigated}
                </Tag>
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Descriptions bordered column={2} title="面积信息">
              <Descriptions.Item label="土地面积">
                {asset?.landArea ? `${asset.landArea}㎡` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="实际房产面积">
                {asset?.actualPropertyArea}㎡
              </Descriptions.Item>
              <Descriptions.Item label="可出租面积">
                {asset?.rentableArea}㎡
              </Descriptions.Item>
              <Descriptions.Item label="已出租面积">
                {asset?.rentedArea}㎡
              </Descriptions.Item>
              <Descriptions.Item label="未出租面积">
                {asset?.unrentedArea}㎡
              </Descriptions.Item>
              <Descriptions.Item label="非经营物业面积">
                {asset?.nonCommercialArea}㎡
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Descriptions bordered column={2} title="用途信息">
              <Descriptions.Item label="证载用途">
                {asset?.certificatedUsage || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="实际用途">
                {asset?.actualUsage}
              </Descriptions.Item>
              <Descriptions.Item label="业态类别">
                {asset?.businessCategory || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="经营模式">
                {asset?.businessModel || '-'}
              </Descriptions.Item>
            </Descriptions>
          </TabPane>

          <TabPane tab="合同信息" key="contract">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="承租合同">
                {asset?.leaseContract || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="租户名称">
                {asset?.tenantName || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="出租率">
                {asset?.occupancyRate}
              </Descriptions.Item>
              <Descriptions.Item label="是否计入出租率">
                {asset?.includeInOccupancyRate}
              </Descriptions.Item>
            </Descriptions>
          </TabPane>

          <TabPane tab="变更历史" key="history">
            <Timeline>
              <Timeline.Item color="green">
                <Text strong>2024-01-15 10:30</Text>
                <br />
                <Text>更新了出租面积信息</Text>
              </Timeline.Item>
              <Timeline.Item color="blue">
                <Text strong>2024-01-10 14:20</Text>
                <br />
                <Text>修改了租户信息</Text>
              </Timeline.Item>
              <Timeline.Item>
                <Text strong>2024-01-01 00:00</Text>
                <br />
                <Text>创建了资产记录</Text>
              </Timeline.Item>
            </Timeline>
          </TabPane>

          <TabPane tab="相关文档" key="documents">
            <Empty 
              description="暂无相关文档"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default AssetDetailPage