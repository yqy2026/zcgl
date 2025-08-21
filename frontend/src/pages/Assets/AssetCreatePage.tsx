import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Typography, Button, Space } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import AssetFormDemo from '../../components/Asset/AssetFormDemo'

const { Title } = Typography

const AssetCreatePage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = !!id

  const handleBack = () => {
    if (isEdit) {
      navigate(`/assets/${id}`)
    } else {
      navigate('/assets/list')
    }
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
            返回
          </Button>
          <Title level={2} style={{ margin: 0 }}>
            {isEdit ? '编辑资产' : '新增资产'}
          </Title>
        </Space>
      </div>

      {/* 表单内容 */}
      <AssetFormDemo />
    </div>
  )
}

export default AssetCreatePage