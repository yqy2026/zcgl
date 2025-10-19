import React, { useState } from 'react'
import { 
  Typography, 
  Button, 
  Space, 
  Row,
  Col,
  Spin,
  Alert,
  message
} from 'antd'
import { PlusOutlined, ExportOutlined, ImportOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { assetService } from '../../services/assetService'
import { analyticsService } from '../../services/analyticsService'
import AssetList from '../../components/Asset/AssetList'
import AssetSearch from '../../components/Asset/AssetSearch'
import AssetAreaSummary from '../../components/Asset/AssetAreaSummary'
import type { AssetSearchParams } from '../../types/asset'
import type { AnalyticsData } from '../../services/analyticsService'

const { Title } = Typography


const AssetListPage: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useState<AssetSearchParams>({
    page: 1,
    limit: 20,
  })
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([])

  // 获取资产列表
  const { data, isLoading, error } = useQuery({
    queryKey: ['assets', searchParams],
    queryFn: () => assetService.getAssets(searchParams),
  })

  
  // 获取统计分析数据
  const { data: analyticsData, isLoading: analyticsLoading, error: analyticsError } = useQuery({
    queryKey: ['analytics', searchParams],
    queryFn: () => analyticsService.getComprehensiveAnalytics(searchParams),
    // 暂时移除enabled条件来测试
  })

  // 调试信息
  console.log('AssetListPage Analytics 调试信息:', {
    data,
    hasData: !!data,
    hasItems: !!data?.items,
    itemsCount: data?.items?.length,
    analyticsData,
    hasAnalyticsData: !!analyticsData,
    analyticsLoading,
    analyticsError,
    searchParams
  })

  // 删除资产
  const deleteMutation = useMutation({
    mutationFn: (id: string) => assetService.deleteAsset(id),
    onSuccess: () => {
      message.success('删除成功')
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    },
    onError: (error: any) => {
      message.error(error.message || '删除失败')
    },
  })

  // 处理搜索
  const handleSearch = (params: AssetSearchParams) => {
    setSearchParams({
      ...params,
      page: 1,
    })
  }

  // 重置搜索
  const handleReset = () => {
    setSearchParams({
      page: 1,
      limit: 20,
    })
  }

  // 处理表格变化
  const handleTableChange = (pagination: any, filters: any, sorter: any) => {
    setSearchParams(prev => ({
      ...prev,
      page: pagination.current,
      limit: pagination.pageSize,
      sort_by: sorter.field,
      sort_order: sorter.order === 'ascend' ? 'asc' : 'desc',
    }))
  }

  // 处理编辑
  const handleEdit = (asset: any) => {
    navigate(`/assets/${asset.id}/edit`)
  }

  // 处理删除
  const handleDelete = (id: string) => {
    deleteMutation.mutate(id)
  }

  // 处理查看
  const handleView = (asset: any) => {
    navigate(`/assets/${asset.id}`)
  }

  // 处理查看历史
  const handleViewHistory = (asset: any) => {
    navigate(`/assets/${asset.id}/history`)
  }

  // 处理选择变化
  const handleSelectChange = (selectedRowKeys: string[]) => {
    setSelectedRowKeys(selectedRowKeys)
  }

  // 处理导出所有资产
  const handleExportAll = async () => {
    try {
      message.success('正在导出资产数据，请稍候...')
      const blob = await assetService.exportAssets({
        format: 'excel',
        filters: searchParams
      })

      // 创建下载链接
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `资产数据导出_${new Date().toISOString().split('T')[0]}.xlsx`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      message.success('资产数据导出成功')
    } catch (error: any) {
      console.error('导出失败:', error)
      message.error(error.message || '导出失败，请稍后重试')
    }
  }

  // 处理导出选中资产
  const handleExportSelected = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要导出的资产')
      return
    }

    try {
      message.success('正在导出选中的资产数据，请稍候...')
      const blob = await assetService.exportSelectedAssets(selectedRowKeys, 'excel')

      // 创建下载链接
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `选中资产数据导出_${new Date().toISOString().split('T')[0]}.xlsx`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      message.success('选中资产数据导出成功')
    } catch (error: any) {
      console.error('导出失败:', error)
      message.error(error.message || '导出失败，请稍后重试')
    }
  }

  if (isLoading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16' }}>加载资产数据中...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="数据加载失败"
          description={
            error instanceof Error
              ? error.message.includes('Network Error')
                ? '无法连接到服务器，请检查后端服务是否正常运行'
                : `错误详情: ${error.message}`
              : '未知错误'
          }
          type="error"
          showIcon
          action={
            <Button size="small" onClick={() => window.location.reload()}>
              重新加载
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2} style={{ margin: 0 }}>资产列表</Title>
          </Col>
          <Col>
            <Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate('/assets/new')}
              >
                新增资产
              </Button>
              <Button
                icon={<ImportOutlined />}
                onClick={() => navigate('/assets/import')}
              >
                导入资产
              </Button>
              <Button
                icon={<ExportOutlined />}
                onClick={handleExportAll}
              >
                导出全部
              </Button>
              {selectedRowKeys.length > 0 && (
                <Button
                  type="dashed"
                  icon={<ExportOutlined />}
                  onClick={handleExportSelected}
                >
                  导出选中 ({selectedRowKeys.length})
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </div>

      {/* 搜索组件 */}
      <AssetSearch
        onSearch={handleSearch}
        onReset={handleReset}
        initialValues={searchParams}
        loading={isLoading}
      />

      {/* 面积汇总组件 */}
      <AssetAreaSummary
        analyticsData={analyticsData?.data}
        loading={analyticsLoading}
      />

      {/* 资产列表组件 */}
      <AssetList
        data={data}
        loading={isLoading}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onView={handleView}
        onViewHistory={handleViewHistory}
        onTableChange={handleTableChange}
        selectedRowKeys={selectedRowKeys}
        onSelectChange={handleSelectChange}
      />
    </div>
  )
}

export default AssetListPage