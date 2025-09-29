import React, { useState, useCallback, useEffect } from 'react'
import { Card, Row, Col, Typography, Select, DatePicker, Button, Space, Tag, Input, Switch, Checkbox, Tooltip } from 'antd'
import { debounce } from 'lodash'
import type { AssetSearchParams } from '../../types/asset'
import { UsageStatus, PropertyNature, OwnershipStatus } from '../../types/asset'
import type { FilterPreset } from '../../types/analytics'

const { Text } = Typography
const { RangePicker } = DatePicker
const { Option } = Select
const { Search } = Input
const { Group: CheckboxGroup } = Checkbox

interface AnalyticsFiltersProps {
  filters: AssetSearchParams
  onFiltersChange: (filters: AssetSearchParams) => void
  onApplyFilters: () => void
  onResetFilters: () => void
  onPresetSelect?: (presetKey: string) => void
  loading?: boolean
  showAdvanced?: boolean
  onToggleAdvanced?: () => void
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
  {
    key: 'high_value',
    label: '高价值资产',
    filters: { min_value: 1000000 },
    description: '价值超过100万的资产'
  },
  {
    key: 'high_occupancy',
    label: '高出租率资产',
    filters: { min_occupancy_rate: 80 },
    description: '出租率超过80%的资产'
  },
]

export const AnalyticsFilters: React.FC<AnalyticsFiltersProps> = ({
  filters,
  onFiltersChange,
  onApplyFilters,
  onResetFilters,
  onPresetSelect,
  loading = false,
  showAdvanced = false,
  onToggleAdvanced
}) => {
  const [localFilters, setLocalFilters] = useState<AssetSearchParams>(filters)
  const [selectedPreset, setSelectedPreset] = useState<string>('all')
  const [searchText, setSearchText] = useState<string>('')

  // 初始化时应用默认筛选值
  useEffect(() => {
    if (Object.keys(filters).length === 0) {
      // 如果父组件没有提供筛选值，应用默认预设
      const defaultPreset = FILTER_PRESETS.find(preset => preset.key === 'all')
      if (defaultPreset) {
        setLocalFilters(defaultPreset.filters)
        onFiltersChange(defaultPreset.filters)
      }
    }
  }, [filters, onFiltersChange])

  // 防抖处理筛选器变化
  const debouncedFilterChange = useCallback(
    debounce((newFilters: AssetSearchParams) => {
      onFiltersChange(newFilters)
    }, 300),
    [onFiltersChange]
  )

  const handleFilterChange = (field: string, value: any) => {
    const newFilters = { ...localFilters, [field]: value }
    setLocalFilters(newFilters)
    debouncedFilterChange(newFilters)
  }

  const handleDateRangeChange = (dates: any, dateStrings: [string, string]) => {
    const newFilters = {
      ...localFilters,
      start_date: dateStrings[0] || undefined,
      end_date: dateStrings[1] || undefined
    }
    setLocalFilters(newFilters)
    debouncedFilterChange(newFilters)
  }

  const handleSearch = (value: string) => {
    setSearchText(value)
    const newFilters = { ...localFilters, search_keyword: value || undefined }
    setLocalFilters(newFilters)
    debouncedFilterChange(newFilters)
  }

  const handleAreaRangeChange = (values: [number, number] | null) => {
    const newFilters = {
      ...localFilters,
      min_area: values?.[0] || undefined,
      max_area: values?.[1] || undefined
    }
    setLocalFilters(newFilters)
    debouncedFilterChange(newFilters)
  }

  const handleValueRangeChange = (values: [number, number] | null) => {
    const newFilters = {
      ...localFilters,
      min_value: values?.[0] || undefined,
      max_value: values?.[1] || undefined
    }
    setLocalFilters(newFilters)
    debouncedFilterChange(newFilters)
  }

  const handleOccupancyRangeChange = (values: [number, number] | null) => {
    const newFilters = {
      ...localFilters,
      min_occupancy_rate: values?.[0] || undefined,
      max_occupancy_rate: values?.[1] || undefined
    }
    setLocalFilters(newFilters)
    debouncedFilterChange(newFilters)
  }

  const handleReset = () => {
    const resetFilters = {}
    setLocalFilters(resetFilters)
    setSelectedPreset('all')
    setSearchText('')
    onResetFilters()
  }

  const handleApply = () => {
    onApplyFilters()
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

  return (
    <Card style={{ marginBottom: '24px' }}>
      {/* 搜索和预设筛选器 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '16px' }}>
        <Col xs={24} md={8}>
          <Text strong style={{ marginRight: '12px' }}>搜索资产:</Text>
          <Search
            placeholder="输入资产名称、地址等关键词"
            allowClear
            enterButton
            value={searchText}
            onChange={(e) => handleSearch(e.target.value)}
            onSearch={handleSearch}
            loading={loading}
          />
        </Col>
        <Col xs={24} md={16}>
          <Text strong style={{ marginRight: '12px' }}>快速筛选:</Text>
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
            <Text strong>价值范围 (万元):</Text>
            <Input.Group compact style={{ marginTop: '8px' }}>
              <Input
                style={{ width: '50%' }}
                placeholder="最小价值"
                type="number"
                value={localFilters.min_value}
                onChange={(e) => handleFilterChange('min_value', e.target.value ? Number(e.target.value) : undefined)}
              />
              <Input
                style={{ width: '50%' }}
                placeholder="最大价值"
                type="number"
                value={localFilters.max_value}
                onChange={(e) => handleFilterChange('max_value', e.target.value ? Number(e.target.value) : undefined)}
              />
            </Input.Group>
          </Col>

          <Col xs={24} md={8}>
            <Text strong>出租率范围 (%):</Text>
            <Input.Group compact style={{ marginTop: '8px' }}>
              <Input
                style={{ width: '50%' }}
                placeholder="最小出租率"
                type="number"
                min={0}
                max={100}
                value={localFilters.min_occupancy_rate}
                onChange={(e) => handleFilterChange('min_occupancy_rate', e.target.value ? Number(e.target.value) : undefined)}
              />
              <Input
                style={{ width: '50%' }}
                placeholder="最大出租率"
                type="number"
                min={0}
                max={100}
                value={localFilters.max_occupancy_rate}
                onChange={(e) => handleFilterChange('max_occupancy_rate', e.target.value ? Number(e.target.value) : undefined)}
              />
            </Input.Group>
          </Col>

          <Col xs={24} md={6}>
            <Text strong>业态类别:</Text>
            <Select
              style={{ width: '100%', marginTop: '8px' }}
              placeholder="请选择业态类别"
              allowClear
              value={localFilters.business_category}
              onChange={(value) => handleFilterChange('business_category', value)}
              loading={loading}
              mode="multiple"
            >
              <Option value="零售">零售</Option>
              <Option value="餐饮">餐饮</Option>
              <Option value="办公">办公</Option>
              <Option value="仓储">仓储</Option>
              <Option value="工业">工业</Option>
              <Option value="其他">其他</Option>
            </Select>
          </Col>

          <Col xs={24} md={6}>
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

          <Col xs={24} md={6}>
            <Text strong>数据状态:</Text>
            <Select
              style={{ width: '100%', marginTop: '8px' }}
              placeholder="请选择数据状态"
              allowClear
              value={localFilters.data_status}
              onChange={(value) => handleFilterChange('data_status', value)}
              loading={loading}
            >
              <Option value="active">正常</Option>
              <Option value="inactive">停用</Option>
              <Option value="archived">归档</Option>
            </Select>
          </Col>

          <Col xs={24} md={6}>
            <Text strong>权属主体:</Text>
            <Select
              style={{ width: '100%', marginTop: '8px' }}
              placeholder="请选择权属主体"
              allowClear
              value={localFilters.ownership_entity}
              onChange={(value) => handleFilterChange('ownership_entity', value)}
              loading={loading}
              mode="multiple"
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
            当前条件: {Object.keys(localFilters).filter(key => localFilters[key] !== undefined && localFilters[key] !== '').length} 个
          </Text>
        </Col>
      </Row>
    </Card>
  )
}