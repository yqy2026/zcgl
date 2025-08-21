import React from 'react'
import { Card, Tag, Space, Button, Typography, Progress, Tooltip } from 'antd'
import { 
  EyeOutlined, 
  EditOutlined, 
  DeleteOutlined, 
  EnvironmentOutlined,
  BuildOutlined,
  UserOutlined
} from '@ant-design/icons'

const { Text, Title } = Typography
const { Meta } = Card

interface AssetCardProps {
  asset: any
  onView: () => void
  onEdit: () => void
  onDelete: () => void
}

const AssetCard: React.FC<AssetCardProps> = ({ asset, onView, onEdit, onDelete }) => {
  const occupancyRate = parseFloat(asset.occupancyRate || '0')
  
  const getOccupancyColor = (rate: number) => {
    if (rate > 80) return '#52c41a'
    if (rate > 50) return '#faad14'
    return '#ff4d4f'
  }

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      '出租': 'success',
      '闲置': 'warning',
      '自用': 'processing',
      '公房': 'default',
      '其他': 'default',
    }
    return colorMap[status] || 'default'
  }

  const getOwnershipColor = (status: string) => {
    const colorMap: Record<string, string> = {
      '已确权': 'success',
      '未确权': 'error',
      '部分确权': 'warning',
    }
    return colorMap[status] || 'default'
  }

  return (
    <Card
      hoverable
      actions={[
        <Tooltip title="查看详情" key="view">
          <Button type="text" icon={<EyeOutlined />} onClick={onView} />
        </Tooltip>,
        <Tooltip title="编辑" key="edit">
          <Button type="text" icon={<EditOutlined />} onClick={onEdit} />
        </Tooltip>,
        <Tooltip title="删除" key="delete">
          <Button type="text" danger icon={<DeleteOutlined />} onClick={onDelete} />
        </Tooltip>,
      ]}
    >
      <Meta
        title={
          <div>
            <Title level={5} style={{ margin: 0, marginBottom: '8px' }}>
              {asset.propertyName}
            </Title>
            <Space wrap>
              <Tag color={asset.propertyNature === '经营类' ? 'green' : 'blue'}>
                {asset.propertyNature}
              </Tag>
              <Tag color={getStatusColor(asset.usageStatus)}>
                {asset.usageStatus}
              </Tag>
              <Tag color={getOwnershipColor(asset.ownershipStatus)}>
                {asset.ownershipStatus}
              </Tag>
            </Space>
          </div>
        }
        description={
          <div style={{ marginTop: '12px' }}>
            {/* 地址信息 */}
            <div style={{ marginBottom: '8px' }}>
              <Space>
                <EnvironmentOutlined style={{ color: '#8c8c8c' }} />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {asset.address}
                </Text>
              </Space>
            </div>

            {/* 权属方 */}
            <div style={{ marginBottom: '8px' }}>
              <Space>
                <UserOutlined style={{ color: '#8c8c8c' }} />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {asset.ownershipEntity}
                </Text>
              </Space>
            </div>

            {/* 面积信息 */}
            <div style={{ marginBottom: '12px' }}>
              <Space>
                <BuildOutlined style={{ color: '#8c8c8c' }} />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  总面积: {asset.actualPropertyArea}㎡ | 
                  可租: {asset.rentableArea}㎡ | 
                  已租: {asset.rentedArea}㎡
                </Text>
              </Space>
            </div>

            {/* 出租率 */}
            <div>
              <div style={{ marginBottom: '4px' }}>
                <Space justify="space-between" style={{ width: '100%' }}>
                  <Text style={{ fontSize: '12px' }}>出租率</Text>
                  <Text 
                    strong 
                    style={{ 
                      fontSize: '12px',
                      color: getOccupancyColor(occupancyRate)
                    }}
                  >
                    {occupancyRate.toFixed(1)}%
                  </Text>
                </Space>
              </div>
              <Progress
                percent={occupancyRate}
                strokeColor={getOccupancyColor(occupancyRate)}
                size="small"
                showInfo={false}
              />
            </div>
          </div>
        }
      />
    </Card>
  )
}

export default AssetCard