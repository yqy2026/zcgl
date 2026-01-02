import React, { useState, useCallback, useEffect, useRef } from 'react'
import {
  Card,
  Row,
  Col,
  Typography,
  Select,
  DatePicker,
  Button,
  Space,
  Tag,
  Input,
  message,
  Empty,
  Tooltip
} from 'antd'
import {
  FilterOutlined,
  ClearOutlined,
  SaveOutlined,
  HistoryOutlined,
  ReloadOutlined,
  DownOutlined,
  UpOutlined
} from '@ant-design/icons'
import { debounce } from 'lodash'
import { useQuery } from '@tanstack/react-query'
import { createLogger } from '@/utils/logger'
import { assetService } from '@/services/assetService'

import { useSearchHistory } from '@/hooks/useSearchHistory'
import type { AssetSearchParams } from '../../types/asset'
import { UsageStatus, PropertyNature, OwnershipStatus } from '../../types/asset'
import type { FilterPreset } from '../../types/analytics'

const { Text } = Typography
const { RangePicker } = DatePicker
const { Option } = Select
const { Search } = Input

const logger = createLogger('AnalyticsFilters')


interface AnalyticsFiltersProps {
  filters: AssetSearchParams
  onFiltersChange: (filters: AssetSearchParams) => void
  onApplyFilters?: () => void
  onResetFilters?: () => void
  onPresetSelect?: (presetKey: string) => void
  loading?: boolean
  showAdvanced?: boolean
  onToggleAdvanced?: () => void
  realTimeUpdate?: boolean
}

// 筛选预设配置
const FILTER_PRESETS: FilterPreset[] = [
  {
    key: 'all',
    label: '全部资产',
    filters: {},
    description: '显示所有资产数据'
  },
  {
    key: 'rented',
    label: '出租资产',
    filters: { usage_status: UsageStatus.RENTED },
    description: '仅显示已出租的资产'
  },
  {
    key: 'commercial',
    label: '经营性物业',
    filters: { property_nature: PropertyNature.COMMERCIAL },
    description: '仅显示经营性物业'
  },
  {
    key: 'confirmed',
    label: '已确权资产',
    filters: { ownership_status: OwnershipStatus.CONFIRMED },
    description: '仅显示已确权的资产'
  },
  {
    key: 'vacant',
    label: '空置资产',
    filters: { usage_status: UsageStatus.VACANT },
    description: '仅显示空置的资产'
  },
  // {
  //   key: 'high_value',
  //   label: '高价值资产',
  //   filters: { min_rent: 1000000 },
  //   description: '价值超过100万的资产'
  // },
  // {
  //   key: 'high_occupancy',
  //   label: '高出租率资产',
  //   filters: { /* min_occupancy_rate: 80 */ },
  //   description: '出租率超过80%的资产'
  // },
]

export const AnalyticsFilters: React.FC<AnalyticsFiltersProps> = ({
  filters,
  onFiltersChange,
  onApplyFilters,
  onResetFilters,
  onPresetSelect,
  loading = false,
  showAdvanced = false,
  onToggleAdvanced,
  realTimeUpdate = true
}) => {
  const [localFilters, setLocalFilters] = useState<AssetSearchParams>(filters)
  const [selectedPreset, setSelectedPreset] = useState<string>('all')
  const [searchText, setSearchText] = useState<string>('')
  const [showHistory, setShowHistory] = useState<boolean>(false)
  const [saveName, setSaveName] = useState<string>('')

  // 搜索历史Hook
  const {
    searchHistory,
    addSearchHistory,
    removeSearchHistory
  } = useSearchHistory()

  // 获取筛选选项数据
  useQuery({
    queryKey: ['analytics-filter-options'],
    queryFn: async () => {
      try {
        const [ownershipEntities, businessCategories] = await Promise.all([
          assetService.getOwnershipEntities(),
          assetService.getBusinessCategories()
        ])
        return {
          ownershipEntities,
          businessCategories
        }
      } catch (error) {
        logger.warn('获取筛选选项失败:', { error: error instanceof Error ? error.message : String(error) })
        return {
          ownershipEntities: [],
          businessCategories: []
        }
      }

    },
    staleTime: 30 * 60 * 1000 // 30分钟缓存
  })

  // 初始化时应用默认筛选值
  useEffect(() => {
    if (Object.keys(filters).length === 0) {
      const defaultPreset = FILTER_PRESETS.find(preset => preset.key === 'all')
      if (defaultPreset) {
        setLocalFilters(defaultPreset.filters)
        setSelectedPreset('all')
        onFiltersChange(defaultPreset.filters)
      }
    }
  }, [filters, onFiltersChange])


  // 同步localFilters和selectedPreset状态与外部filters
  useEffect(() => {
    setLocalFilters(filters)

    const matchingPreset = FILTER_PRESETS.find(preset =>
      JSON.stringify(preset.filters) === JSON.stringify(filters)
    )
    if (matchingPreset) {
      setSelectedPreset(matchingPreset.key)
    } else if (Object.keys(filters).length === 0) {
      setSelectedPreset('all')
    } else {
      setSelectedPreset('custom')
    }
  }, [filters])

  // 防抖处理筛选器变化
  const debouncedFilterChange = useCallback(
    (newFilters: AssetSearchParams) => {
      onFiltersChange(newFilters)
    },
    [onFiltersChange]

  )

  // 创建防抖函数
  const debouncedFilterChangeRef = useRef(debounce(debouncedFilterChange, 500))

  useEffect(() => {
    debouncedFilterChangeRef.current = debounce(debouncedFilterChange, realTimeUpdate ? 500 : 0)
  }, [debouncedFilterChange, realTimeUpdate])

  const handleFilterChange = (field: string, value: unknown) => {
    const newFilters = { ...localFilters, [field]: value }
    setLocalFilters(newFilters)
    debouncedFilterChangeRef.current(newFilters)
  }

  const handleDateRangeChange = (_dates: unknown, dateStrings: [string, string]) => {

    const newFilters = {
      ...localFilters,
      start_date: dateStrings[0] || undefined,
      end_date: dateStrings[1] || undefined
    }
    setLocalFilters(newFilters)
    debouncedFilterChangeRef.current(newFilters)
  }

  const handleSearch = (value: string) => {
    setSearchText(value)
    const newFilters = { ...localFilters, search_keyword: value || undefined }
    setLocalFilters(newFilters)
    debouncedFilterChange(newFilters)
  }


  // const handleOccupancyRangeChange = (values: [number, number] | null) => {
  //   const newFilters = {
  //     ...localFilters,
  //     // min_occupancy_rate: values?.[0] || undefined,
  //     // max_occupancy_rate: values?.[1] || undefined
  //   }
  //   setLocalFilters(newFilters)
  //   debouncedFilterChange(newFilters)
  // }

  const handleReset = () => {
    const resetFilters = {}
    setLocalFilters(resetFilters)
    setSelectedPreset('all')
    setSearchText('')
    onResetFilters?.()
    message.success('筛选条件已重置')
  }

  const handleApply = () => {
    onApplyFilters?.()
    message.success('筛选条件已应用')
  }

  // 保存当前筛选条件
  const handleSaveFilters = () => {
    if (!saveName.trim()) {
      message.warning('请输入保存名称')
      return
    }

    const activeFiltersCountValue = (Object.keys(localFilters) as (keyof AssetSearchParams)[]).filter(key => {
      const val = localFilters[key];
      return val !== undefined && val !== null && val !== '';
    }).length



    if (activeFiltersCountValue === 0) {
      message.warning('请先设置筛选条件')
      return
    }


    addSearchHistory({
      id: Date.now().toString(),
      name: saveName,
      conditions: localFilters,
      createdAt: new Date().toISOString()
    })

    setSaveName('')
    message.success('筛选条件已保存')
  }

  // 应用历史筛选条件
  const handleApplyHistory = (historyId: string) => {
    const history = searchHistory.find(h => h.id === historyId)
    if (history) {
      setLocalFilters(history.conditions)
      onFiltersChange(history.conditions)


      // 找到匹配的预设
      const matchingPreset = FILTER_PRESETS.find(preset =>
        JSON.stringify(preset.filters) === JSON.stringify(history.conditions)
      )
      if (matchingPreset) {
        setSelectedPreset(matchingPreset.key)
      } else {
        setSelectedPreset('custom')
      }

      setShowHistory(false)
      message.success(`已应用历史筛选条件: ${history.name}`)
    }
  }

  const handlePresetSelect = (presetKey: string) => {
    const preset = FILTER_PRESETS.find(p => p.key === presetKey)
    if (preset) {
      setLocalFilters(preset.filters)
      setSelectedPreset(presetKey)
      onFiltersChange(preset.filters)

      if (onPresetSelect) {
        onPresetSelect(presetKey)
      }
    }
  }

  // 获取当前激活的筛选条件数量
  const activeFiltersCountValue = (Object.keys(localFilters) as (keyof AssetSearchParams)[]).filter(key => {
    const val = localFilters[key];
    return val !== undefined && val !== null && val !== '';
  }).length



  return (
    <Card
      size="small"
      title={
        <Space>
          <FilterOutlined />
          <span>数据筛选</span>
          {activeFiltersCountValue > 0 && (
            <Tag color="blue">
              {activeFiltersCountValue} 个筛选条件
            </Tag>
          )}
        </Space>
      }
      extra={
        <Space>
          <Tooltip title="保存筛选条件">
            <Button
              type="text"
              icon={<SaveOutlined />}
              onClick={() => setSaveName('')}
              disabled={activeFiltersCountValue === 0}

              size="small"
            />
          </Tooltip>

          <Tooltip title="筛选历史">
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => setShowHistory(!showHistory)}
              size="small"
            />
          </Tooltip>

          <Tooltip title="重置筛选">
            <Button
              type="text"
              icon={<ClearOutlined />}
              onClick={handleReset}
              disabled={activeFiltersCountValue === 0}

              size="small"
            />
          </Tooltip>

          <Tooltip title="刷新数据">
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={handleApply}
              loading={loading}
              size="small"
            />
          </Tooltip>

          {onToggleAdvanced && (
            <Button
              type="text"
              icon={showAdvanced ? <UpOutlined /> : <DownOutlined />}
              onClick={onToggleAdvanced}
              size="small"
            >
              {showAdvanced ? '收起' : '高级'}
            </Button>
          )}
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      {/* 保存筛选条件输入框 */}
      {saveName !== undefined && (
        <div style={{ marginBottom: 16, padding: '12px', background: '#f5f5f5', borderRadius: 6 }}>
          <Space.Compact style={{ width: '100%' }}>
            <input
              type="text"
              placeholder="输入保存名称"
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSaveFilters()
                }
              }}
              style={{ flex: 1, padding: '4px 11px', border: '1px solid #d9d9d9', borderRadius: 6 }}
              autoFocus
            />
            <Button type="primary" onClick={handleSaveFilters}>
              保存
            </Button>
            <Button onClick={() => setSaveName('')}>
              取消
            </Button>
          </Space.Compact>
        </div>
      )}

      {/* 筛选历史 */}
      {showHistory && (
        <div style={{ marginBottom: 16, padding: '12px', background: '#f5f5f5', borderRadius: 6 }}>
          <Text strong style={{ marginBottom: 8, display: 'block' }}>筛选历史</Text>
          {searchHistory.length > 0 ? (
            <div>
              {searchHistory.slice(0, 5).map(history => (
                <div
                  key={history.id}
                  style={{
                    padding: '8px 12px',
                    background: 'white',
                    border: '1px solid #e8e8e8',
                    borderRadius: 4,
                    marginBottom: 8,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                  onClick={() => handleApplyHistory(history.id)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#f0f0f0'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'white'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 'bold' }}>{history.name}</div>
                    <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                      {new Date(history.createdAt).toLocaleDateString()}
                    </div>
                  </div>
                  <Button
                    type="text"
                    size="small"
                    danger
                    onClick={(e) => {
                      e.stopPropagation()
                      removeSearchHistory(history.id)
                      message.success('历史记录已删除')
                    }}
                  >
                    删除
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <Empty description="暂无筛选历史" imageStyle={{ height: 60 }} />
          )}
        </div>
      )}

      {/* 搜索和预设筛选器 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={8}>
          <Text strong>搜索资产:</Text>
          <Search
            placeholder="输入资产名称、地址等关键词"
            allowClear
            style={{ marginTop: 8 }}
            value={searchText}
            onChange={(e) => handleSearch(e.target.value)}
            onSearch={handleSearch}
            loading={loading}
          />
        </Col>
        <Col xs={24} md={16}>
          <Text strong>快速筛选:</Text>
          <div style={{ marginTop: 8 }}>
            <Space wrap>
              {FILTER_PRESETS.map(preset => (
                <Tooltip key={preset.key} title={preset.description}>
                  <Tag
                    color={selectedPreset === preset.key ? 'blue' : 'default'}
                    style={{ cursor: 'pointer', padding: '4px 8px' }}
                    onClick={() => handlePresetSelect(preset.key)}
                  >
                    {preset.label}
                  </Tag>
                </Tooltip>
              ))}
            </Space>
          </div>
        </Col>
      </Row>

      {/* 基础筛选器 */}
      <Row gutter={[16, 16]} align="middle">
        <Col xs={24} md={6}>
          <Text strong>权属状态:</Text>
          <Select
            style={{ width: '100%', marginTop: '8px' }}
            placeholder="请选择权属状态"
            allowClear
            value={localFilters.ownership_status}
            onChange={(value) => handleFilterChange('ownership_status', value)}
            loading={loading}
          >
            <Option value="已确权">已确权</Option>
            <Option value="未确权">未确权</Option>
            <Option value="部分确权">部分确权</Option>
            <Option value="无法确认业权">无法确认业权</Option>
          </Select>
        </Col>

        <Col xs={24} md={6}>
          <Text strong>使用状态:</Text>
          <Select
            style={{ width: '100%', marginTop: '8px' }}
            placeholder="请选择使用状态"
            allowClear
            value={localFilters.usage_status}
            onChange={(value) => handleFilterChange('usage_status', value)}
            loading={loading}
          >
            <Option value="出租">出租</Option>
            <Option value="空置">空置</Option>
            <Option value="自用">自用</Option>
            <Option value="公房">公房</Option>
            <Option value="其他">其他</Option>
            <Option value="转租">转租</Option>
            <Option value="公配">公配</Option>
            <Option value="空置规划">空置规划</Option>
            <Option value="空置预留">空置预留</Option>
            <Option value="配套">配套</Option>
            <Option value="空置配套">空置配套</Option>
            <Option value="空置配">空置配</Option>
            <Option value="待处置">待处置</Option>
            <Option value="待移交">待移交</Option>
            <Option value="闲置">闲置</Option>
          </Select>
        </Col>

        <Col xs={24} md={6}>
          <Text strong>物业性质:</Text>
          <Select
            style={{ width: '100%', marginTop: '8px' }}
            placeholder="请选择物业性质"
            allowClear
            value={localFilters.property_nature}
            onChange={(value) => handleFilterChange('property_nature', value)}
            loading={loading}
          >
            <Option value="经营性">经营性</Option>
            <Option value="非经营性">非经营性</Option>
            <Option value="经营-外部">经营-外部</Option>
            <Option value="经营-内部">经营-内部</Option>
            <Option value="经营-租赁">经营-租赁</Option>
            <Option value="非经营类-公配">非经营类-公配</Option>
            <Option value="非经营类-其他">非经营类-其他</Option>
            <Option value="经营类">经营类</Option>
            <Option value="非经营类">非经营类</Option>
            <Option value="经营-配套">经营-配套</Option>
            <Option value="非经营-配套">非经营-配套</Option>
            <Option value="经营-配套镇">经营-配套镇</Option>
            <Option value="非经营-配套镇">非经营-配套镇</Option>
            <Option value="经营-处置类">经营-处置类</Option>
            <Option value="非经营-处置类">非经营-处置类</Option>
            <Option value="非经营-公配房">非经营-公配房</Option>
            <Option value="非经营类-配套">非经营类-配套</Option>
          </Select>
        </Col>

        <Col xs={24} md={6}>
          <Text strong>时间范围:</Text>
          <RangePicker
            style={{ width: '100%', marginTop: '8px' }}
            onChange={handleDateRangeChange}
            placeholder={['开始日期', '结束日期']}
            disabled={loading}
          />
        </Col>
      </Row>

      {/* 高级筛选器 */}
      {showAdvanced && (
        <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
          <Col xs={24} md={8}>
            <Text strong>面积范围 (㎡):</Text>
            <Input.Group compact style={{ marginTop: '8px' }}>
              <Input
                style={{ width: '50%' }}
                placeholder="最小面积"
                type="number"
                value={localFilters.min_area}
                onChange={(e) => handleFilterChange('min_area', e.target.value ? Number(e.target.value) : undefined)}
              />
              <Input
                style={{ width: '50%' }}
                placeholder="最大面积"
                type="number"
                value={localFilters.max_area}
                onChange={(e) => handleFilterChange('max_area', e.target.value ? Number(e.target.value) : undefined)}
              />
            </Input.Group>
          </Col>

          <Col xs={24} md={8}>
            <Text strong>租金范围 (元):</Text>
            <Input.Group compact style={{ marginTop: '8px' }}>
              <Input
                style={{ width: '50%' }}
                placeholder="最小租金"
                type="number"
                value={localFilters.min_rent}
                onChange={(e) => handleFilterChange('min_rent', e.target.value ? Number(e.target.value) : undefined)}
              />
              <Input
                style={{ width: '50%' }}
                placeholder="最大租金"
                type="number"
                value={localFilters.max_rent}
                onChange={(e) => handleFilterChange('max_rent', e.target.value ? Number(e.target.value) : undefined)}
              />
            </Input.Group>
          </Col>

          <Col xs={24} md={8}>
            <Text strong>管理状态:</Text>
            <Select
              style={{ width: '100%', marginTop: '8px' }}
              placeholder="请选择管理状态"
              allowClear
              value={localFilters.operation_status}
              onChange={(value) => handleFilterChange('operation_status', value)}
              loading={loading}
            >
              <Option value="正常运营">正常运营</Option>
              <Option value="维护中">维护中</Option>
              <Option value="整改中">整改中</Option>
              <Option value="暂停运营">暂停运营</Option>
            </Select>
          </Col>

          <Col xs={24} md={8}>
            <Text strong>业态类别:</Text>
            <Select
              style={{ width: '100%', marginTop: '8px' }}
              placeholder="请选择业态类别"
              allowClear
              value={localFilters.business_category}
              onChange={(value) => handleFilterChange('business_category', value)}
              loading={loading}
            >
              <Option value="零售">零售</Option>
              <Option value="餐饮">餐饮</Option>
              <Option value="办公">办公</Option>
              <Option value="仓储">仓储</Option>
              <Option value="工业">工业</Option>
              <Option value="其他">其他</Option>
            </Select>
          </Col>

          <Col xs={24} md={8}>
            <Text strong>租户类型:</Text>
            <Select
              style={{ width: '100%', marginTop: '8px' }}
              placeholder="请选择租户类型"
              allowClear
              value={localFilters.tenant_type}
              onChange={(value) => handleFilterChange('tenant_type', value)}
              loading={loading}
            >
              <Option value="企业">企业</Option>
              <Option value="个人">个人</Option>
              <Option value="政府">政府</Option>
              <Option value="事业单位">事业单位</Option>
              <Option value="其他">其他</Option>
            </Select>
          </Col>

          <Col xs={24} md={8}>
            <Text strong>权属主体:</Text>
            <Select
              style={{ width: '100%', marginTop: '8px' }}
              placeholder="请选择权属主体"
              allowClear
              value={localFilters.ownership_entity}
              onChange={(value) => handleFilterChange('ownership_entity', value)}
              loading={loading}
            >
              <Option value="政府">政府</Option>
              <Option value="企业">企业</Option>
              <Option value="事业单位">事业单位</Option>
              <Option value="社会组织">社会组织</Option>
              <Option value="个人">个人</Option>
              <Option value="其他">其他</Option>
            </Select>
          </Col>

        </Row>
      )}

      {/* 操作按钮 */}
      <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
        <Col xs={24} md={12}>
          <Space>
            <Button
              type="primary"
              onClick={handleApply}
              loading={loading}
            >
              应用筛选
            </Button>
            <Button
              onClick={handleReset}
              disabled={loading}
            >
              重置筛选
            </Button>
            {onToggleAdvanced && (
              <Button
                onClick={onToggleAdvanced}
                icon={showAdvanced ? '▲' : '▼'}
              >
                {showAdvanced ? '收起高级' : '高级筛选'}
              </Button>
            )}
          </Space>
        </Col>
        <Col xs={24} md={12} style={{ textAlign: 'right' }}>
          <Text type="secondary">
            当前条件: {activeFiltersCountValue} 个

          </Text>
        </Col>
      </Row>
    </Card>
  )
}

// 添加默认导出
export default AnalyticsFilters