import React from 'react'
import { 
  Typography, 
  Button, 
  Space, 
  Row, 
  Col,
  Spin,
  Alert
} from 'antd'
import { EditOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { assetService } from '@/services/assetService'
import AssetDetailInfo from '@/components/Asset/AssetDetailInfo'

const { Title } = Typography


const AssetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: asset, isLoading, error } = useQuery({
    queryKey: ['asset', id],
    queryFn: () => assetService.getAsset(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16' }}>加载资产详情中...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="数据加载失败"
          description={`错误详情: ${error instanceof Error ? error.message : '未知错误'}`}
          type="error"
          showIcon
        />
      </div>
    )
  }

  if (!asset) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="资产不存在"
          description="未找到指定的资产信息"
          type="warning"
          showIcon
        />
      </div>
    )
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button 
                icon={<ArrowLeftOutlined />} 
                onClick={() => navigate('/assets')}
              >
                返回列表
              </Button>
              <Title level={2} style={{ margin: 0 }}>
                {asset.property_name}
              </Title>
            </Space>
          </Col>
          <Col>
            <Button 
              type="primary" 
              icon={<EditOutlined />}
              onClick={() => navigate(`/assets/${id}/edit`)}
            >
              编辑资产
            </Button>
          </Col>
        </Row>
      </div>

      <AssetDetailInfo asset={asset} />
    </div>
  )
}

export default AssetDetailPage