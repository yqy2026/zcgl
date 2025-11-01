import React from 'react'
import { Card, Tag, Button, Space, Tooltip, Row, Col, Statistic, Progress } from 'antd'
import {
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  HistoryOutlined,
  EnvironmentOutlined,
  UserOutlined,
  HomeOutlined,
} from '@ant-design/icons'

import type { Asset } from '@/types/asset'
import { formatArea, formatPercentage, formatDate, getStatusColor, calculateOccupancyRate } from '@/utils/format'

interface AssetCardProps {
  asset: Asset
  onEdit: (asset: Asset) => void
  onDelete: (id: string) => void
  onView: (asset: Asset) => void
  selected?: boolean
  onSelect?: (asset: Asset, selected: boolean) => void
}

const AssetCard: React.FC<AssetCardProps> = ({
  asset,
  onEdit,
  onDelete,
  onView,
  selected = false,
  onSelect,
}) => {
  // 计算出租率
  const occupancyRate = asset.occupancy_rate
    ? asset.occupancy_rate
    : calculateOccupancyRate(asset.rented_area, asset.rentable_area)

  // 获取出租率颜色
  const getOccupancyColor = (rate: number) => {
    if (rate >= 80) return '#52c41a'
    if (rate >= 60) return '#faad14'
    return '#ff4d4f'
  }

  return (
    <Card
      className={`asset-card ${selected ? 'selected' : ''}`}
      hoverable
      style={{
        marginBottom: 16,
        border: selected ? '2px solid #1890ff' : '1px solid #d9d9d9',
      }}
      onClick={() => onSelect?.(asset, !selected)}
      actions={[
        <Tooltip title="查看详情" key="view">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={(e) => {
              e.stopPropagation()
              onView(asset)
            }}
          />
        </Tooltip>,
        <Tooltip title="编辑" key="edit">
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={(e) => {
              e.stopPropagation()
              onEdit(asset)
            }}
          />
        </Tooltip>,
        <Tooltip title="查看历史" key="history">
          <Button
            type="text"
            icon={<HistoryOutlined />}
            onClick={(e) => {
              e.stopPropagation()
              // 这里可以打开历史记录
            }}
          />
        </Tooltip>,
        <Tooltip title="删除" key="delete">
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={(e) => {
              e.stopPropagation()
              onDelete(asset.id)
            }}
          />
        </Tooltip>,
      ]}
    >
      {/* 卡片头部 */}
      <Card.Meta
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '16px', fontWeight: 'bold' }}>
              {asset.property_name}
            </span>
            <Space>
              <Tag color={getStatusColor(asset.ownership_status, 'ownership')}>
                {asset.ownership_status}
              </Tag>
              <Tag color={getStatusColor(asset.property_nature, 'property')}>
                {asset.property_nature}
              </Tag>
            </Space>
          </div>
        }
        description={
          <div>
            <div style={{ marginBottom: 8 }}>
              <EnvironmentOutlined style={{ marginRight: 4, color: '#8c8c8c' }} />
              <span style={{ color: '#8c8c8c' }}>{asset.address}</span>
            </div>
            <div style={{ marginBottom: 8 }}>
              <UserOutlined style={{ marginRight: 4, color: '#8c8c8c' }} />
              <span style={{ color: '#8c8c8c' }}>权属方：{asset.ownership_entity}</span>
            </div>
          </div>
        }
      />

      {/* 卡片内容 */}
      <div style={{ marginTop: 16 }}>
        {/* 面积信息 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Statistic
              title="土地面积"
              value={asset.land_area || 0}
              suffix="㎡"
              precision={2}
              valueStyle={{ fontSize: '14px' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="实际面积"
              value={asset.actual_property_area || 0}
              suffix="㎡"
              precision={2}
              valueStyle={{ fontSize: '14px' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="可出租面积"
              value={asset.rentable_area || 0}
              suffix="㎡"
              precision={2}
              valueStyle={{ fontSize: '14px' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="已出租面积"
              value={asset.rented_area || 0}
              suffix="㎡"
              precision={2}
              valueStyle={{ fontSize: '14px' }}
            />
          </Col>
        </Row>

        {/* 出租率进度条 */}
        {asset.rentable_area && asset.rentable_area > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: '12px', color: '#8c8c8c' }}>出租率</span>
              <span style={{ fontSize: '12px', fontWeight: 'bold', color: getOccupancyColor(occupancyRate) }}>
                {formatPercentage(occupancyRate)}
              </span>
            </div>
            <Progress
              percent={occupancyRate}
              strokeColor={getOccupancyColor(occupancyRate)}
              size="small"
              showInfo={false}
            />
          </div>
        )}

        {/* 状态标签 */}
        <div style={{ marginBottom: 12 }}>
          <Space wrap>
            <Tag color={getStatusColor(asset.usage_status, 'usage')}>
              {asset.usage_status}
            </Tag>
            {asset.is_litigated && (
              <Tag color="red">涉诉</Tag>
            )}
            {asset.certificated_usage && (
              <Tag color="blue">证载：{asset.certificated_usage}</Tag>
            )}
            {asset.actual_usage && asset.actual_usage !== asset.certificated_usage && (
              <Tag color="orange">实际：{asset.actual_usage}</Tag>
            )}
          </Space>
        </div>

        {/* 时间信息 */}
        <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
          <div>创建时间：{formatDate(asset.created_at)}</div>
          <div>更新时间：{formatDate(asset.updated_at)}</div>
        </div>
      </div>
    </Card>
  )
}

export default AssetCard