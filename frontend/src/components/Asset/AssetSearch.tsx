import React, { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
  Button,
  Space,
  Row,
  Col,
  Collapse,
  Switch,
  Slider,
  Dropdown,
  Modal,
  List,
  Typography,
  Popconfirm,
  message,
  Tooltip,
  Tag,
} from 'antd'
import {
  SearchOutlined,
  ReloadOutlined,
  DownOutlined,
  UpOutlined,
  FilterOutlined,
  SaveOutlined,
  HistoryOutlined,
  DeleteOutlined,
  EditOutlined,
  StarOutlined,
  StarFilled,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'

import type { AssetSearchParams, OwnershipStatus, PropertyNature, UsageStatus } from '@/types/asset'
import { assetService } from '@/services/assetService'
import { useSearchHistory } from '@/hooks/useSearchHistory'
import styles from './AssetSearch.module.css'

const { Option } = Select
const { RangePicker } = DatePicker
const { Panel } = Collapse
const { Text } = Typography

interface AssetSearchProps {
  onSearch: (params: AssetSearchParams) => void
  onReset: () => void
  initialValues?: Partial<AssetSearchParams>
  loading?: boolean
  showSaveButton?: boolean
  showHistoryButton?: boolean
}

const AssetSearch: React.FC<AssetSearchProps> = ({
  onSearch,
  onReset,
  initialValues = {},
  loading = false,
  showSaveButton = true,
  showHistoryButton = true,
}) => {
  const [form] = Form.useForm()
  const [expanded, setExpanded] = useState(false)
  const [areaRange, setAreaRange] = useState<[number, number]>([0, 100000])
  const [saveModalVisible, setSaveModalVisible] = useState(false)
  const [historyModalVisible, setHistoryModalVisible] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [editingHistoryId, setEditingHistoryId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')

  // 搜索历史Hook
  const {
    searchHistory,
    addSearchHistory,
    removeSearchHistory,
    clearSearchHistory,
    updateSearchHistoryName,
  } = useSearchHistory()

  // 获取权属方列表
  const { data: ownershipEntities } = useQuery({
    queryKey: ['ownership-entities'],
    queryFn: () => assetService.getOwnershipEntities(),
    staleTime: 10 * 60 * 1000, // 10分钟缓存
  })

  // 获取管理方列表
  const { data: managementEntities } = useQuery({
    queryKey: ['management-entities'],
    queryFn: () => assetService.getManagementEntities(),
    staleTime: 10 * 60 * 1000,
  })

  // 获取业态类别列表
  const { data: businessCategories } = useQuery({
    queryKey: ['business-categories'],
    queryFn: () => assetService.getBusinessCategories(),
    staleTime: 10 * 60 * 1000,
  })

  // 设置初始值
  useEffect(() => {
    if (initialValues) {
      form.setFieldsValue(initialValues)
    }
  }, [initialValues, form])

  // 处理搜索
  const handleSearch = () => {
    const values = form.getFieldsValue()
    
    // 处理日期范围
    if (values.dateRange) {
      values.created_start = values.dateRange[0]?.format('YYYY-MM-DD')
      values.created_end = values.dateRange[1]?.format('YYYY-MM-DD')
      delete values.dateRange
    }

    // 处理面积范围
    if (values.areaRange) {
      values.area_min = values.areaRange[0]
      values.area_max = values.areaRange[1]
      delete values.areaRange
    }

    // 过滤空值
    const searchParams = Object.entries(values).reduce((acc, [key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        acc[key] = value
      }
      return acc
    }, {} as any)

    onSearch(searchParams)
  }

  // 处理重置
  const handleReset = () => {
    form.resetFields()
    setAreaRange([0, 100000])
    onReset()
  }

  // 处理保存搜索条件
  const handleSaveSearch = () => {
    const values = form.getFieldsValue()
    
    // 检查是否有搜索条件
    const hasConditions = Object.values(values).some(value => 
      value !== undefined && value !== null && value !== ''
    )
    
    if (!hasConditions) {
      message.warning('请先设置搜索条件')
      return
    }
    
    setSaveModalVisible(true)
  }

  // 确认保存搜索条件
  const handleConfirmSave = () => {
    if (!saveName.trim()) {
      message.warning('请输入搜索条件名称')
      return
    }

    const values = form.getFieldsValue()
    
    // 处理日期范围
    if (values.dateRange) {
      values.created_start = values.dateRange[0]?.format('YYYY-MM-DD')
      values.created_end = values.dateRange[1]?.format('YYYY-MM-DD')
      delete values.dateRange
    }

    // 处理面积范围
    if (values.areaRange) {
      values.area_min = values.areaRange[0]
      values.area_max = values.areaRange[1]
      delete values.areaRange
    }

    // 过滤空值
    const searchParams = Object.entries(values).reduce((acc, [key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        acc[key] = value
      }
      return acc
    }, {} as any)

    addSearchHistory(saveName.trim(), searchParams)
    message.success('搜索条件已保存')
    setSaveModalVisible(false)
    setSaveName('')
  }

  // 应用历史搜索条件
  const handleApplyHistory = (params: AssetSearchParams) => {
    // 处理日期范围
    if (params.created_start && params.created_end) {
      params.dateRange = [dayjs(params.created_start), dayjs(params.created_end)]
    }

    // 处理面积范围
    if (params.area_min !== undefined && params.area_max !== undefined) {
      setAreaRange([params.area_min, params.area_max])
    }

    form.setFieldsValue(params)
    setHistoryModalVisible(false)
    
    // 自动执行搜索
    onSearch(params)
  }

  // 开始编辑历史记录名称
  const handleStartEdit = (id: string, currentName: string) => {
    setEditingHistoryId(id)
    setEditingName(currentName)
  }

  // 确认编辑历史记录名称
  const handleConfirmEdit = (id: string) => {
    if (!editingName.trim()) {
      message.warning('名称不能为空')
      return
    }
    
    updateSearchHistoryName(id, editingName.trim())
    setEditingHistoryId(null)
    setEditingName('')
    message.success('名称已更新')
  }

  // 取消编辑
  const handleCancelEdit = () => {
    setEditingHistoryId(null)
    setEditingName('')
  }

  // 快速筛选选项
  const quickFilters = [
    { label: '经营类物业', value: { property_nature: '经营类' } },
    { label: '非经营类物业', value: { property_nature: '非经营类' } },
    { label: '已确权', value: { ownership_status: '已确权' } },
    { label: '未确权', value: { ownership_status: '未确权' } },
    { label: '出租中', value: { usage_status: '出租' } },
    { label: '闲置', value: { usage_status: '闲置' } },
    { label: '涉诉物业', value: { is_litigated: true } },
  ]

  return (
    <Card 
      className={styles.searchCard}
      title={
        <Space>
          <FilterOutlined />
          搜索筛选
          <Button
            type="text"
            size="small"
            icon={expanded ? <UpOutlined /> : <DownOutlined />}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? '收起' : '展开'}
          </Button>
        </Space>
      }
      size="small"
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSearch}
        initialValues={initialValues}
      >
        {/* 基础搜索 */}
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="search" label="关键词搜索">
              <Input
                placeholder="物业名称、地址、权属方..."
                prefix={<SearchOutlined />}
                allowClear
              />
            </Form.Item>
          </Col>
          
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="ownership_status" label="确权状态">
              <Select placeholder="请选择" allowClear>
                <Option value="已确权">已确权</Option>
                <Option value="未确权">未确权</Option>
                <Option value="部分确权">部分确权</Option>
              </Select>
            </Form.Item>
          </Col>
          
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="property_nature" label="物业性质">
              <Select placeholder="请选择" allowClear>
                <Option value="经营类">经营类</Option>
                <Option value="非经营类">非经营类</Option>
              </Select>
            </Form.Item>
          </Col>
          
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="usage_status" label="使用状态">
              <Select placeholder="请选择" allowClear>
                <Option value="出租">出租</Option>
                <Option value="闲置">闲置</Option>
                <Option value="自用">自用</Option>
                <Option value="公房">公房</Option>
                <Option value="其他">其他</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        {/* 快速筛选 */}
        <div className={styles.quickFilters}>
          <div style={{ marginBottom: 8 }}>
            <span style={{ fontSize: '14px', fontWeight: 'bold' }}>快速筛选：</span>
          </div>
          <Space wrap>
            {quickFilters.map((filter, index) => (
              <Button
                key={index}
                size="small"
                onClick={() => {
                  form.setFieldsValue(filter.value)
                  handleSearch()
                }}
              >
                {filter.label}
              </Button>
            ))}
          </Space>
        </div>

        {/* 高级搜索 */}
        <Collapse 
          activeKey={expanded ? ['advanced'] : []} 
          ghost
          onChange={(keys) => setExpanded(keys.includes('advanced'))}
        >
          <Panel header="高级搜索" key="advanced">
            <Row gutter={16}>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="ownership_entity" label="权属方">
                  <Select
                    placeholder="请选择"
                    allowClear
                    showSearch
                    filterOption={(input, option) =>
                      (option?.children as unknown as string)
                        ?.toLowerCase()
                        .includes(input.toLowerCase())
                    }
                  >
                    {ownershipEntities?.map((entity) => (
                      <Option key={entity} value={entity}>
                        {entity}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="management_entity" label="经营管理方">
                  <Select
                    placeholder="请选择"
                    allowClear
                    showSearch
                    filterOption={(input, option) =>
                      (option?.children as unknown as string)
                        ?.toLowerCase()
                        .includes(input.toLowerCase())
                    }
                  >
                    {managementEntities?.map((entity) => (
                      <Option key={entity} value={entity}>
                        {entity}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="business_category" label="业态类别">
                  <Select
                    placeholder="请选择"
                    allowClear
                    showSearch
                    filterOption={(input, option) =>
                      (option?.children as unknown as string)
                        ?.toLowerCase()
                        .includes(input.toLowerCase())
                    }
                  >
                    {businessCategories?.map((category) => (
                      <Option key={category} value={category}>
                        {category}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="certificated_usage" label="证载用途">
                  <Input placeholder="请输入" allowClear />
                </Form.Item>
              </Col>
              
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="actual_usage" label="实际用途">
                  <Input placeholder="请输入" allowClear />
                </Form.Item>
              </Col>
              
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="is_litigated" label="是否涉诉">
                  <Select placeholder="请选择" allowClear>
                    <Option value={true}>是</Option>
                    <Option value={false}>否</Option>
                  </Select>
                </Form.Item>
              </Col>
              
              <Col xs={24} sm={12} md={16} lg={12}>
                <Form.Item name="dateRange" label="创建时间范围">
                  <RangePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            {/* 面积范围滑块 */}
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label="实际面积范围 (㎡)">
                  <Slider
                    range
                    min={0}
                    max={100000}
                    step={100}
                    value={areaRange}
                    onChange={(value) => setAreaRange(value as [number, number])}
                    tooltip={{
                      formatter: (value) => `${value?.toLocaleString()} ㎡`,
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#8c8c8c' }}>
                    <span>{areaRange[0].toLocaleString()} ㎡</span>
                    <span>{areaRange[1].toLocaleString()} ㎡</span>
                  </div>
                </Form.Item>
              </Col>
              
              <Col xs={24} md={12}>
                <Row gutter={8}>
                  <Col span={12}>
                    <Form.Item name="area_min" label="最小面积">
                      <InputNumber
                        placeholder="最小面积"
                        style={{ width: '100%' }}
                        min={0}
                        formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                        parser={(value) => Number(value!.replace(/\$\s?|(,*)/g, '')) as any}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="area_max" label="最大面积">
                      <InputNumber
                        placeholder="最大面积"
                        style={{ width: '100%' }}
                        min={0}
                        formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                        parser={(value) => Number(value!.replace(/\$\s?|(,*)/g, '')) as any}
                      />
                    </Form.Item>
                  </Col>
                </Row>
              </Col>
            </Row>
          </Panel>
        </Collapse>

        {/* 操作按钮 */}
        <Row justify="space-between" style={{ marginTop: 16 }}>
          <Space>
            {showHistoryButton && (
              <Button
                icon={<HistoryOutlined />}
                onClick={() => setHistoryModalVisible(true)}
              >
                搜索历史
              </Button>
            )}
            {showSaveButton && (
              <Button
                icon={<SaveOutlined />}
                onClick={handleSaveSearch}
              >
                保存条件
              </Button>
            )}
          </Space>
          
          <Space>
            <Button onClick={handleReset} icon={<ReloadOutlined />}>
              重置
            </Button>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SearchOutlined />}
              loading={loading}
            >
              搜索
            </Button>
          </Space>
        </Row>
      </Form>

      {/* 保存搜索条件Modal */}
      <Modal
        title="保存搜索条件"
        open={saveModalVisible}
        onOk={handleConfirmSave}
        onCancel={() => {
          setSaveModalVisible(false)
          setSaveName('')
        }}
        okText="保存"
        cancelText="取消"
      >
        <Form layout="vertical">
          <Form.Item
            label="搜索条件名称"
            required
            help="为这组搜索条件起一个便于识别的名称"
          >
            <Input
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              placeholder="例如：已确权经营类物业"
              maxLength={50}
              showCount
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 搜索历史Modal */}
      <Modal
        title={
          <Space>
            <HistoryOutlined />
            搜索历史
            {searchHistory.length > 0 && (
              <Text type="secondary">({searchHistory.length}条记录)</Text>
            )}
          </Space>
        }
        open={historyModalVisible}
        onCancel={() => setHistoryModalVisible(false)}
        footer={[
          <Button key="clear" danger onClick={() => {
            Modal.confirm({
              title: '确认清空',
              content: '确定要清空所有搜索历史吗？此操作不可撤销。',
              onOk: () => {
                clearSearchHistory()
                message.success('搜索历史已清空')
              },
            })
          }}>
            清空历史
          </Button>,
          <Button key="close" onClick={() => setHistoryModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {searchHistory.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#8c8c8c' }}>
            <HistoryOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
            <div>暂无搜索历史</div>
          </div>
        ) : (
          <List
            dataSource={searchHistory}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Tooltip title="应用此搜索条件">
                    <Button
                      type="link"
                      icon={<SearchOutlined />}
                      onClick={() => handleApplyHistory(item.params)}
                    >
                      应用
                    </Button>
                  </Tooltip>,
                  <Tooltip title="编辑名称">
                    <Button
                      type="link"
                      icon={<EditOutlined />}
                      onClick={() => handleStartEdit(item.id, item.name)}
                    />
                  </Tooltip>,
                  <Popconfirm
                    title="确定要删除这条搜索历史吗？"
                    onConfirm={() => {
                      removeSearchHistory(item.id)
                      message.success('已删除')
                    }}
                  >
                    <Button
                      type="link"
                      danger
                      icon={<DeleteOutlined />}
                    />
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  title={
                    editingHistoryId === item.id ? (
                      <Space>
                        <Input
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          onPressEnter={() => handleConfirmEdit(item.id)}
                          style={{ width: 200 }}
                        />
                        <Button
                          type="link"
                          size="small"
                          onClick={() => handleConfirmEdit(item.id)}
                        >
                          确认
                        </Button>
                        <Button
                          type="link"
                          size="small"
                          onClick={handleCancelEdit}
                        >
                          取消
                        </Button>
                      </Space>
                    ) : (
                      <Space>
                        <Text strong>{item.name}</Text>
                        <Tag color="blue">使用{item.usageCount}次</Tag>
                      </Space>
                    )
                  }
                  description={
                    <div>
                      <div style={{ marginBottom: 4 }}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          创建时间: {new Date(item.createdAt).toLocaleString()}
                        </Text>
                      </div>
                      <div>
                        <Space wrap>
                          {Object.entries(item.params).map(([key, value]) => {
                            if (value === undefined || value === null || value === '') {
                              return null
                            }
                            
                            let displayValue = String(value)
                            let displayKey = key
                            
                            // 转换字段名为中文
                            const fieldNames: Record<string, string> = {
                              search: '关键词',
                              ownership_status: '确权状态',
                              property_nature: '物业性质',
                              usage_status: '使用状态',
                              ownership_entity: '权属方',
                              management_entity: '管理方',
                              business_category: '业态类别',
                              is_litigated: '涉诉',
                              area_min: '最小面积',
                              area_max: '最大面积',
                            }
                            
                            displayKey = fieldNames[key] || key
                            
                            if (key === 'is_litigated') {
                              displayValue = value ? '是' : '否'
                            }
                            
                            return (
                              <Tag key={key} style={{ fontSize: '11px' }}>
                                {displayKey}: {displayValue}
                              </Tag>
                            )
                          })}
                        </Space>
                      </div>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Modal>
    </Card>
  )
}

export default AssetSearch