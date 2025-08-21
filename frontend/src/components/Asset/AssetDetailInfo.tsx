import React from 'react'
import { Card, Descriptions, Tag, Progress, Row, Col, Statistic, Divider } from 'antd'
import {
  HomeOutlined,
  EnvironmentOutlined,
  UserOutlined,
  CalendarOutlined,
  PercentageOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'

import type { Asset } from '@/types/asset'
import { formatArea, formatDate, getStatusColor, calculateOccupancyRate } from '@/utils/format'

interface AssetDetailInfoProps {
  asset: Asset
}

const AssetDetailInfo: React.FC<AssetDetailInfoProps> = ({ asset }) => {
  // 计算出租率
  const occupancyRate = asset.occupancy_rate 
    ? parseFloat(asset.occupancy_rate)
    : calculateOccupancyRate(asset.rented_area, asset.rentable_area)

  // 获取出租率颜色
  const getOccupancyColor = (rate: number) => {
    if (rate >= 80) return '#52c41a'
    if (rate >= 60) return '#faad14'
    return '#ff4d4f'
  }

  return (
    <div>
      {/* 基本信息卡片 */}
      <Card 
        title={
          <span>
            <InfoCircleOutlined style={{ marginRight: 8 }} />
            基本信息
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        <Descriptions
          bordered
          column={{ xs: 1, sm: 2, md: 3 }}
          labelStyle={{ width: '120px', fontWeight: 'bold' }}
          contentStyle={{ minWidth: '200px' }}
        >
          <Descriptions.Item 
            label={
              <span>
                <HomeOutlined style={{ marginRight: 4 }} />
                物业名称
              </span>
            }
          >
            <span style={{ fontSize: '16px', fontWeight: 'bold' }}>
              {asset.property_name}
            </span>
          </Descriptions.Item>
          
          <Descriptions.Item 
            label={
              <span>
                <UserOutlined style={{ marginRight: 4 }} />
                权属方
              </span>
            }
          >
            {asset.ownership_entity}
          </Descriptions.Item>
          
          <Descriptions.Item 
            label={
              <span>
                <UserOutlined style={{ marginRight: 4 }} />
                经营管理方
              </span>
            }
          >
            {asset.management_entity || '-'}
          </Descriptions.Item>
          
          <Descriptions.Item 
            label={
              <span>
                <EnvironmentOutlined style={{ marginRight: 4 }} />
                所在地址
              </span>
            }
            span={2}
          >
            {asset.address}
          </Descriptions.Item>
          
          <Descriptions.Item label="确权状态">
            <Tag color={getStatusColor(asset.ownership_status, 'ownership')}>
              {asset.ownership_status}
            </Tag>
          </Descriptions.Item>
          
          <Descriptions.Item label="物业性质">
            <Tag color={getStatusColor(asset.property_nature, 'property')}>
              {asset.property_nature}
            </Tag>
          </Descriptions.Item>
          
          <Descriptions.Item label="使用状态">
            <Tag color={getStatusColor(asset.usage_status, 'usage')}>
              {asset.usage_status}
            </Tag>
          </Descriptions.Item>
          
          <Descriptions.Item label="是否涉诉">
            <Tag color={asset.is_litigated ? 'red' : 'green'}>
              {asset.is_litigated ? '是' : '否'}
            </Tag>
          </Descriptions.Item>
          
          <Descriptions.Item 
            label={
              <span>
                <CalendarOutlined style={{ marginRight: 4 }} />
                创建时间
              </span>
            }
          >
            {formatDate(asset.created_at, 'datetime')}
          </Descriptions.Item>
          
          <Descriptions.Item 
            label={
              <span>
                <CalendarOutlined style={{ marginRight: 4 }} />
                更新时间
              </span>
            }
          >
            {formatDate(asset.updated_at, 'datetime')}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 面积信息卡片 */}
      <Card 
        title="面积信息" 
        style={{ marginBottom: 16 }}
        extra={
          asset.property_nature === '经营类' && (
            <span style={{ color: '#1890ff' }}>
              <PercentageOutlined style={{ marginRight: 4 }} />
              出租率: {occupancyRate.toFixed(2)}%
            </span>
          )
        }
      >
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="土地面积"
              value={asset.land_area || 0}
              suffix="㎡"
              precision={2}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="实际房产面积"
              value={asset.actual_property_area || 0}
              suffix="㎡"
              precision={2}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          
          {asset.property_nature === '经营类' && (
            <>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Statistic
                  title="可出租面积"
                  value={asset.rentable_area || 0}
                  suffix="㎡"
                  precision={2}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
              
              <Col xs={24} sm={12} md={8} lg={6}>
                <Statistic
                  title="已出租面积"
                  value={asset.rented_area || 0}
                  suffix="㎡"
                  precision={2}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              
              <Col xs={24} sm={12} md={8} lg={6}>
                <Statistic
                  title="未出租面积"
                  value={asset.unrented_area || 0}
                  suffix="㎡"
                  precision={2}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Col>
            </>
          )}
          
          {asset.property_nature === '非经营类' && asset.non_commercial_area && (
            <Col xs={24} sm={12} md={8} lg={6}>
              <Statistic
                title="非经营物业面积"
                value={asset.non_commercial_area}
                suffix="㎡"
                precision={2}
                valueStyle={{ color: '#722ed1' }}
              />
            </Col>
          )}
        </Row>

        {/* 出租率进度条 */}
        {asset.property_nature === '经营类' && asset.rentable_area && asset.rentable_area > 0 && (
          <div style={{ marginTop: 24 }}>
            <Divider orientation="left">出租率分析</Divider>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <div style={{ flex: 1 }}>
                <Progress
                  percent={occupancyRate}
                  strokeColor={getOccupancyColor(occupancyRate)}
                  format={(percent) => `${percent?.toFixed(2)}%`}
                />
              </div>
              <div style={{ minWidth: 120, textAlign: 'right' }}>
                <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
                  {asset.rented_area?.toLocaleString() || 0} / {asset.rentable_area?.toLocaleString() || 0} ㎡
                </div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* 用途和经营信息 */}
      <Card title="用途和经营信息" style={{ marginBottom: 16 }}>
        <Descriptions
          bordered
          column={{ xs: 1, sm: 2 }}
          labelStyle={{ width: '120px' }}
        >
          <Descriptions.Item label="证载用途">
            {asset.certificated_usage || '-'}
          </Descriptions.Item>
          
          <Descriptions.Item label="实际用途">
            {asset.actual_usage || '-'}
          </Descriptions.Item>
          
          <Descriptions.Item label="业态类别">
            {asset.business_category || '-'}
          </Descriptions.Item>
          
          <Descriptions.Item label="经营模式">
            {asset.business_model || '-'}
          </Descriptions.Item>
          
          <Descriptions.Item label="是否计入出租率">
            <Tag color={asset.include_in_occupancy_rate ? 'green' : 'default'}>
              {asset.include_in_occupancy_rate ? '是' : '否'}
            </Tag>
          </Descriptions.Item>
          
          <Descriptions.Item label="权属类别">
            {asset.ownership_category || '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 合同信息 */}
      {asset.usage_status === '出租' && (
        <Card title="合同信息" style={{ marginBottom: 16 }}>
          <Descriptions
            bordered
            column={{ xs: 1, sm: 2 }}
            labelStyle={{ width: '150px' }}
          >
            <Descriptions.Item label="租户名称">
              {asset.tenant_name || '-'}
            </Descriptions.Item>
            
            <Descriptions.Item label="承租合同">
              {asset.lease_contract || '-'}
            </Descriptions.Item>
            
            <Descriptions.Item label="合同开始日期">
              {asset.current_contract_start_date ? formatDate(asset.current_contract_start_date) : '-'}
            </Descriptions.Item>
            
            <Descriptions.Item label="合同结束日期">
              {asset.current_contract_end_date ? formatDate(asset.current_contract_end_date) : '-'}
            </Descriptions.Item>
            
            <Descriptions.Item label="现租赁合同">
              {asset.current_lease_contract || '-'}
            </Descriptions.Item>
            
            <Descriptions.Item label="终端出租合同">
              {asset.current_terminal_contract || '-'}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* 项目信息 */}
      {asset.wuyang_project_name && (
        <Card title="项目信息" style={{ marginBottom: 16 }}>
          <Descriptions
            bordered
            column={{ xs: 1, sm: 2 }}
            labelStyle={{ width: '150px' }}
          >
            <Descriptions.Item label="五羊项目名称">
              {asset.wuyang_project_name}
            </Descriptions.Item>
            
            <Descriptions.Item label="协议开始日期">
              {asset.agreement_start_date ? formatDate(asset.agreement_start_date) : '-'}
            </Descriptions.Item>
            
            <Descriptions.Item label="协议结束日期">
              {asset.agreement_end_date ? formatDate(asset.agreement_end_date) : '-'}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* 备注信息 */}
      {(asset.description || asset.notes) && (
        <Card title="备注信息">
          <Descriptions bordered column={1}>
            {asset.description && (
              <Descriptions.Item label="说明">
                <div style={{ whiteSpace: 'pre-wrap' }}>
                  {asset.description}
                </div>
              </Descriptions.Item>
            )}
            
            {asset.notes && (
              <Descriptions.Item label="其他备注">
                <div style={{ whiteSpace: 'pre-wrap' }}>
                  {asset.notes}
                </div>
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>
      )}
    </div>
  )
}

export default AssetDetailInfo