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
  Modal,
  List,
  Typography,
  Popconfirm,
  message,
  Tag,
} from 'antd'
import {
  SearchOutlined,
  ReloadOutlined,
  DownOutlined,
  UpOutlined,
  SaveOutlined,
  HistoryOutlined,
} from '@ant-design/icons'
import { useQueries } from '@tanstack/react-query'
import dayjs from 'dayjs'

import type { AssetSearchParams } from '@/types/asset'
import { assetService } from '@/services/assetService'
import { useSearchHistory } from '@/hooks/useSearchHistory'

const { Option } = Select
const { RangePicker } = DatePicker
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

  // 使用并行查询获取所有下拉框数据，简化逻辑避免错误
  const searchQueries = useQueries({
    queries: [
      {
        queryKey: ['ownership-entities'],
        queryFn: async () => {
          try {
            // 直接从专门的API获取
            return await assetService.getOwnershipEntities()
          } catch {
            console.warn('获取权属方失败，使用默认选项:', error)
            return ['政府', '企业', '事业单位', '社会团体', '其他']
          }
        },
        staleTime: 30 * 60 * 1000,
        retry: 0, // 不重试，立即使用默认值
      },
      {
        queryKey: ['business-categories'],
        queryFn: async () => {
          try {
            // 直接从专门的API获取
            return await assetService.getBusinessCategories()
          } catch {
            console.warn('获取业态类别失败，使用默认选项:', error)
            return ['办公', '商业', '工业', '仓储', '住宅', '酒店', '餐饮', '其他']
          }
        },
        staleTime: 30 * 60 * 1000,
        retry: 0,
      },
    ],
  })

  // 提取查询结果
  const ownershipEntities = searchQueries[0].data || []
  const businessCategories = searchQueries[1].data || []

  // 检查是否所有查询都已加载完成
  const isLoadingQueries = searchQueries.some(query => query.isLoading)

  // 合并外部loading和内部查询loading
  const isComponentLoading = loading || isLoadingQueries

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

    if (!saveName.trim()) {
      message.warning('请输入保存名称')
      return
    }

    addSearchHistory({
      id: Date.now().toString(),
      name: saveName,
      conditions: values,
      createdAt: new Date().toISOString(),
    })

    setSaveName('')
    setSaveModalVisible(false)
    message.success('搜索条件已保存')
  }

  // 处理应用历史搜索条件
  const handleApplyHistory = (historyId: string) => {
    const history = searchHistory.find(h => h.id === historyId)
    if (history) {
      form.setFieldsValue(history.conditions)
      handleSearch()
      setHistoryModalVisible(false)
    }
  }

  // 处理删除历史记录
  const handleDeleteHistory = (historyId: string) => {
    removeSearchHistory(historyId)
    message.success('历史记录已删除')
  }

  // 处理编辑历史记录名称
  const handleEditHistory = (historyId: string, currentName: string) => {
    setEditingHistoryId(historyId)
    setEditingName(currentName)
  }

  // 保存编辑的名称
  const handleSaveEdit = () => {
    if (editingHistoryId && editingName.trim()) {
      updateSearchHistoryName(editingHistoryId, editingName.trim())
      setEditingHistoryId(null)
      setEditingName('')
      message.success('名称已更新')
    }
  }

  return (
    <Card
      title={
        <Space>
          <SearchOutlined />
          <span>资产搜索</span>
          {isComponentLoading && (
            <Tag color="processing">加载中...</Tag>
          )}
        </Space>
      }
      extra={
        <Space>
          {showSaveButton && (
            <Button
              type="default"
              icon={<SaveOutlined />}
              onClick={() => setSaveModalVisible(true)}
              disabled={isComponentLoading}
            >
              保存条件
            </Button>
          )}
          {showHistoryButton && (
            <Button
              type="default"
              icon={<HistoryOutlined />}
              onClick={() => setHistoryModalVisible(true)}
            >
              搜索历史
            </Button>
          )}
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleSearch}
            loading={isComponentLoading}
          >
            搜索
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleReset}
            disabled={isComponentLoading}
          >
            重置
          </Button>
          <Button
            type="text"
            icon={expanded ? <UpOutlined /> : <DownOutlined />}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? '收起' : '展开'}
          </Button>
        </Space>
      }
    >
      <Form
        form={form}
        layout="vertical"
        disabled={isComponentLoading}
      >
        <Row gutter={16}>
          {/* 基础搜索字段 */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="search" label="关键词搜索">
              <Input
                placeholder="输入物业名称、地址等关键词"
                prefix={<SearchOutlined />}
                allowClear
              />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="ownership_status" label="确权状态">
              <Select
                placeholder="选择确权状态"
                allowClear
                showSearch
                optionFilterProp="children"
              >
                <Option value="已确权">已确权</Option>
                <Option value="未确权">未确权</Option>
                <Option value="部分确权">部分确权</Option>
                <Option value="无法确认业权">无法确认业权</Option>
              </Select>
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="property_nature" label="物业性质">
              <Select
                placeholder="选择物业性质"
                allowClear
                showSearch
                optionFilterProp="children"
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
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="usage_status" label="使用状态">
              <Select
                placeholder="选择使用状态"
                allowClear
                showSearch
                optionFilterProp="children"
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
            </Form.Item>
          </Col>
        </Row>

        {/* 高级搜索条件 */}
        {expanded && (
          <>
            <Row gutter={16}>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="ownership_entity" label="权属方">
                  <Select
                    placeholder="选择权属方"
                    allowClear
                    showSearch
                    optionFilterProp="children"
                    loading={searchQueries[0].isLoading}
                  >
                    {ownershipEntities.map(entity => (
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
                    placeholder="选择业态类别"
                    allowClear
                    showSearch
                    optionFilterProp="children"
                    loading={searchQueries[1].isLoading}
                  >
                    {businessCategories.map(category => (
                      <Option key={category} value={category}>
                        {category}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>

              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="is_litigated" label="是否涉诉">
                  <Select placeholder="选择是否涉诉" allowClear>
                    <Option value="是">是</Option>
                    <Option value="否">否</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col xs={24} sm={12} md={8}>
                <Form.Item label="面积范围">
                  <Space.Compact>
                    <InputNumber
                      style={{ width: '45%' }}
                      placeholder="最小面积"
                      value={areaRange[0]}
                      onChange={(value) =>
                        setAreaRange([value || 0, areaRange[1]])
                      }
                    />
                    <Input
                      style={{ width: '10%', borderLeft: 0, borderRight: 0, pointerEvents: 'none' }}
                      placeholder="~"
                      disabled
                    />
                    <InputNumber
                      style={{ width: '45%' }}
                      placeholder="最大面积"
                      value={areaRange[1]}
                      onChange={(value) =>
                        setAreaRange([areaRange[0], value || 100000])
                      }
                    />
                  </Space.Compact>
                </Form.Item>
              </Col>

              <Col xs={24} sm={12} md={8}>
                <Form.Item name="dateRange" label="创建日期">
                  <RangePicker
                    style={{ width: '100%' }}
                    format="YYYY-MM-DD"
                  />
                </Form.Item>
              </Col>

              <Col xs={24} sm={12} md={8}>
                <Form.Item label="排序方式">
                  <Space.Compact>
                    <Form.Item name="sort_field" noStyle>
                      <Select style={{ width: '60%' }} defaultValue="created_at">
                        <Option value="created_at">创建时间</Option>
                        <Option value="property_name">物业名称</Option>
                        <Option value="total_area">建筑面积</Option>
                        <Option value="rentable_area">可租面积</Option>
                      </Select>
                    </Form.Item>
                    <Form.Item name="sort_order" noStyle>
                      <Select style={{ width: '40%' }} defaultValue="desc">
                        <Option value="asc">升序</Option>
                        <Option value="desc">降序</Option>
                      </Select>
                    </Form.Item>
                  </Space.Compact>
                </Form.Item>
              </Col>
            </Row>
          </>
        )}
      </Form>

      {/* 保存搜索条件弹窗 */}
      <Modal
        title="保存搜索条件"
        open={saveModalVisible}
        onOk={handleSaveSearch}
        onCancel={() => setSaveModalVisible(false)}
        destroyOnHidden
      >
        <Input
          placeholder="输入保存名称"
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
          onPressEnter={handleSaveSearch}
        />
      </Modal>

      {/* 搜索历史弹窗 */}
      <Modal
        title="搜索历史"
        open={historyModalVisible}
        onCancel={() => {
          setHistoryModalVisible(false)
          setEditingHistoryId(null)
          setEditingName('')
        }}
        footer={null}
        width={600}
        destroyOnHidden
      >
        <List
          dataSource={searchHistory}
          locale={{
            emptyText: '暂无搜索历史'
          }}
          renderItem={item => (
            <List.Item
              key={item.id}
              actions={[
                <Button
                  key="apply"
                  type="link"
                  size="small"
                  onClick={() => handleApplyHistory(item.id)}
                >
                  应用
                </Button>,
                <Button
                  key="edit"
                  type="link"
                  size="small"
                  onClick={() => handleEditHistory(item.id, item.name)}
                >
                  编辑
                </Button>,
                <Popconfirm
                  key="delete"
                  title="确定要删除这条历史记录吗？"
                  onConfirm={() => handleDeleteHistory(item.id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button
                    type="link"
                    size="small"
                    danger
                  >
                    删除
                  </Button>
                </Popconfirm>
              ]}
            >
              <List.Item.Meta
                title={
                  editingHistoryId === item.id ? (
                    <Input
                      size="small"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      onBlur={handleSaveEdit}
                      onPressEnter={handleSaveEdit}
                      style={{ width: 200 }}
                    />
                  ) : (
                    <Text>{item.name}</Text>
                  )
                }
                description={
                  <Space direction="vertical" size="small">
                    <Text type="secondary">
                      保存时间: {dayjs(item.createdAt).format('YYYY-MM-DD HH:mm:ss')}
                    </Text>
                    <Text type="secondary">
                      条件数: {Object.keys(item.conditions).length}
                    </Text>
                  </Space>
                }
              />
            </List.Item>
          )}
        />

        {searchHistory.length > 0 && (
          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <Popconfirm
              title="确定要清空所有搜索历史吗？"
              onConfirm={clearSearchHistory}
              okText="确定"
              cancelText="取消"
            >
              <Button danger size="small">
                清空历史
              </Button>
            </Popconfirm>
          </div>
        )}
      </Modal>
    </Card>
  )
}

export default AssetSearch
