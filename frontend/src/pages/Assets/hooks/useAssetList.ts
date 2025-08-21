import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { message } from 'antd'

interface AssetFilters {
  propertyNature?: string
  usageStatus?: string
  ownershipStatus?: string
  ownershipEntity?: string
  occupancyRateRange?: [number, number]
}

interface AssetSummary {
  total: number
  rented: number
  vacant: number
  avgOccupancyRate: number
}

interface PaginationConfig {
  current: number
  pageSize: number
  total: number
}

// 模拟API调用
const fetchAssets = async (params: {
  page: number
  pageSize: number
  search?: string
  filters?: AssetFilters
}) => {
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  // 模拟数据
  const mockAssets = Array.from({ length: 50 }, (_, index) => ({
    id: `asset-${index + 1}`,
    propertyName: `物业${index + 1}`,
    address: `地址${index + 1}`,
    ownershipEntity: ['华润集团', '万科集团', '中信集团', '绿地集团'][index % 4],
    propertyNature: index % 3 === 0 ? '经营类' : '非经营类',
    usageStatus: ['出租', '闲置', '自用', '公房'][index % 4],
    actualPropertyArea: 100 + index * 10,
    rentableArea: 80 + index * 8,
    rentedArea: 60 + index * 6,
    occupancyRate: (75 + (index % 25)).toString(),
    ownershipStatus: ['已确权', '未确权', '部分确权'][index % 3],
  }))

  // 应用搜索和筛选
  let filteredAssets = mockAssets
  
  if (params.search) {
    filteredAssets = filteredAssets.filter(asset =>
      asset.propertyName.includes(params.search!) ||
      asset.address.includes(params.search!) ||
      asset.ownershipEntity.includes(params.search!)
    )
  }

  if (params.filters) {
    const { propertyNature, usageStatus, ownershipStatus, ownershipEntity } = params.filters
    
    if (propertyNature) {
      filteredAssets = filteredAssets.filter(asset => asset.propertyNature === propertyNature)
    }
    if (usageStatus) {
      filteredAssets = filteredAssets.filter(asset => asset.usageStatus === usageStatus)
    }
    if (ownershipStatus) {
      filteredAssets = filteredAssets.filter(asset => asset.ownershipStatus === ownershipStatus)
    }
    if (ownershipEntity) {
      filteredAssets = filteredAssets.filter(asset => asset.ownershipEntity === ownershipEntity)
    }
  }

  // 分页
  const start = (params.page - 1) * params.pageSize
  const end = start + params.pageSize
  const paginatedAssets = filteredAssets.slice(start, end)

  return {
    data: paginatedAssets,
    total: filteredAssets.length,
    page: params.page,
    pageSize: params.pageSize,
  }
}

const fetchAssetSummary = async (): Promise<AssetSummary> => {
  await new Promise(resolve => setTimeout(resolve, 500))
  
  return {
    total: 156,
    rented: 136,
    vacant: 20,
    avgOccupancyRate: 87.2,
  }
}

const deleteAssets = async (ids: string[]) => {
  await new Promise(resolve => setTimeout(resolve, 1000))
  return { success: true, deletedCount: ids.length }
}

const exportAssets = async (filters?: AssetFilters) => {
  await new Promise(resolve => setTimeout(resolve, 2000))
  // 模拟导出文件
  const blob = new Blob(['资产数据导出'], { type: 'application/vnd.ms-excel' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `资产清单_${new Date().toISOString().split('T')[0]}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

export const useAssetList = () => {
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<AssetFilters>({})
  const [pagination, setPagination] = useState<PaginationConfig>({
    current: 1,
    pageSize: 20,
    total: 0,
  })

  const queryClient = useQueryClient()

  // 获取资产列表
  const assetsQuery = useQuery({
    queryKey: ['assets', pagination.current, pagination.pageSize, search, filters],
    queryFn: () => fetchAssets({
      page: pagination.current,
      pageSize: pagination.pageSize,
      search,
      filters,
    }),
  })

  // 获取资产汇总信息
  const summaryQuery = useQuery({
    queryKey: ['asset-summary'],
    queryFn: fetchAssetSummary,
  })

  // 删除资产
  const deleteMutation = useMutation({
    mutationFn: deleteAssets,
    onSuccess: (data) => {
      message.success(`成功删除 ${data.deletedCount} 个资产`)
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['asset-summary'] })
    },
    onError: () => {
      message.error('删除失败，请重试')
    },
  })

  // 导出资产
  const exportMutation = useMutation({
    mutationFn: exportAssets,
    onSuccess: () => {
      message.success('导出成功')
    },
    onError: () => {
      message.error('导出失败，请重试')
    },
  })

  // 更新分页信息
  useEffect(() => {
    if (assetsQuery.data) {
      setPagination(prev => ({
        ...prev,
        total: assetsQuery.data.total,
      }))
    }
  }, [assetsQuery.data])

  const handleSearch = (value: string) => {
    setSearch(value)
    setPagination(prev => ({ ...prev, current: 1 }))
  }

  const handleFilter = (newFilters: AssetFilters) => {
    setFilters(newFilters)
    setPagination(prev => ({ ...prev, current: 1 }))
  }

  const handlePaginationChange = (page: number, pageSize: number) => {
    setPagination(prev => ({
      ...prev,
      current: page,
      pageSize,
    }))
  }

  const handleBatchDelete = (ids: string[]) => {
    deleteMutation.mutate(ids)
  }

  const handleExport = () => {
    exportMutation.mutate(filters)
  }

  return {
    assets: assetsQuery.data?.data || [],
    loading: assetsQuery.isLoading,
    error: assetsQuery.error,
    pagination,
    filters,
    summary: summaryQuery.data,
    handleSearch,
    handleFilter,
    handlePaginationChange,
    handleBatchDelete,
    handleExport,
    isDeleting: deleteMutation.isPending,
    isExporting: exportMutation.isPending,
  }
}