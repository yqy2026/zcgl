import React, { useEffect, useMemo, useState } from 'react'
import { Button, Card, Form, Input, Modal, Select, Space, Switch, Table, Tag, message, Popconfirm, Row, Col, Badge } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { SearchOutlined } from '@ant-design/icons'
import { unifiedDictionaryService } from '../../services/dictionary'
import type { EnumFieldType, EnumFieldValue } from '../../services/dictionary'
import type { SystemDictionary } from '@/types/dictionary'
import EnumValuePreview from '../../components/Dictionary/EnumValuePreview'
import { handleApiError as handleError, withErrorHandling, createErrorHandler } from '../../services'

const { Option } = Select
const { Search } = Input

interface EnumFieldWithType {
  type: EnumFieldType
  values: EnumFieldValue[]
}

interface EditState {
  visible: boolean
}

const DictionaryPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [dictTypes, setDictTypes] = useState<string[]>([])
  const [enumTypes, setEnumTypes] = useState<EnumFieldType[]>([])
  const [activeType, setActiveType] = useState<string | undefined>(undefined)
  const [data, setData] = useState<SystemDictionary[]>([])
  const [edit, setEdit] = useState<EditState>({ visible: false })
  const [editingRecord, setEditingRecord] = useState<SystemDictionary | null>(null)
  const [form] = Form.useForm<SystemDictionary>()

  // 创建上下文相关的错误处理器
  const handleDictionaryError = createErrorHandler('字典管理', {
    showDetails: false,
    duration: 3
  })

  // 新增状态
  const [searchText, setSearchText] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [allEnumData, setAllEnumData] = useState<EnumFieldWithType[]>([])
  const [detailModalVisible, setDetailModalVisible] = useState<boolean>(false)

  // 获取字典类型列表
  const fetchTypes = async () => {
    const result = await withErrorHandling(async () => {
      const types = await unifiedDictionaryService.getTypes()
      setDictTypes(types || [])

      // 同时获取枚举类型详细信息
      const typesData = await unifiedDictionaryService.getEnumFieldTypes()
      setEnumTypes(typesData || [])
    }, {
      errorMessage: '获取字典类型失败',
      successMessage: undefined
    })

    if (!result.success) {
      // 错误已由 withErrorHandling 处理
    }
  }

  // 获取所有枚举数据
  const fetchAllEnumData = async () => {
    setLoading(true)
    try {
      const data = await unifiedDictionaryService.getEnumFieldData()
      // Got enum data
      setAllEnumData(data)
    } catch (e: unknown) {
      console.error('获取枚举数据失败:', e)
      message.error(e?.message || '获取枚举数据失败')
    } finally {
      setLoading(false)
    }
  }

  // 获取指定类型的字典数据
  const fetchList = async (type?: string) => {
    if (!type) {
      setData([])
      return
    }

    setLoading(true)
    try {
      // 使用新的方法通过类型代码获取枚举值
      const list = await unifiedDictionaryService.getEnumFieldValuesByTypeCode(type)
      setData(list)
    } catch (e: unknown) {
      console.error('获取枚举值失败:', e)
      message.error(e?.message || '获取枚举值失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTypes()
    fetchAllEnumData()
  }, [])

  useEffect(() => {
    fetchList(activeType)
  }, [activeType])

  const handleCreate = async () => {
    if (!activeType) {
      message.warning('请先选择字典类型')
      return
    }

    // 获取对应的枚举类型
    const targetType = enumTypes.find(type => type.code === activeType)
    if (!targetType) {
      message.error('未找到对应的枚举类型')
      return
    }

    setEditingRecord(null)
    setEdit({ visible: true })
    form.resetFields()
    const initialValues = {
      dict_type: activeType,
      sort_order: data.length > 0 ? Math.max(...data.map(d => d.sort_order)) + 1 : 0,
      is_active: true
    }

    // 使用 setTimeout 确保模态框完全打开后再设置表单值
    setTimeout(() => {
      form.setFieldsValue(initialValues as any)
    }, 0)
  }

  const handleEdit = (record: SystemDictionary) => {
    const targetType = enumTypes.find(type => type.code === record.dict_type)
    setEditingRecord(record)
    setEdit({ visible: true })

    // 设置表单初始值
    const formData = {
      ...record,
      dict_type: record.dict_type,
      dict_label: record.dict_label,
      dict_value: record.dict_value,
      dict_code: record.dict_code,
      description: record.description || '',
      sort_order: record.sort_order || 0,
      is_active: record.is_active
    }

    // 使用 setTimeout 确保模态框完全打开后再设置表单值
    setTimeout(() => {
      form.setFieldsValue(formData as any)
    }, 0)
  }

  const handleDelete = async (record: SystemDictionary) => {
    try {
      const success = await unifiedDictionaryService.deleteEnumValue(record.id)
      if (success) {
        message.success('删除成功')
        fetchList(activeType)
        fetchAllEnumData()
        // 如果详情模态框打开，刷新详情数据
        if (detailModalVisible) {
          fetchList(activeType)
        }
      } else {
        message.error('删除失败')
      }
    } catch (e: unknown) {
      message.error(e?.message || '删除失败')
    }
  }

  const submit = async () => {
    try {
      const values = await form.validateFields()

      if (!activeType) {
        message.error('未找到对应的枚举类型')
        return
      }

      const targetType = enumTypes.find(type => type.code === activeType)
      if (!targetType) {
        message.error('未找到对应的枚举类型')
        return
      }

      if (editingRecord) {
        // 更新现有枚举值
        const success = await unifiedDictionaryService.updateEnumValue(editingRecord.id, {
          label: values.dict_label,
          value: values.dict_value,
          code: values.dict_code,
          description: values.description,
          sort_order: values.sort_order,
          is_active: values.is_active
        })

        if (success) {
          message.success('更新成功')
        } else {
          message.error('更新失败')
          return
        }
      } else {
        // 创建新的枚举值
        const success = await unifiedDictionaryService.createEnumValue(targetType.id, {
          label: values.dict_label,
          value: values.dict_value,
          code: values.dict_code,
          description: values.description,
          sort_order: values.sort_order
        })

        if (success) {
          message.success('创建成功')
        } else {
          message.error('创建失败')
          return
        }
      }

      setEdit({ visible: false })
      setEditingRecord(null)
      fetchList(activeType)
      fetchAllEnumData()
      // 如果详情模态框打开，刷新详情数据
      if (detailModalVisible) {
        fetchList(activeType)
      }
    } catch (e: unknown) {
      if (e?.errorFields) return
      message.error(e?.message || '保存失败')
    }
  }

  const handleToggleActive = async (record: SystemDictionary, checked: boolean) => {
    try {
      const success = await unifiedDictionaryService.toggleEnumValueActive(record.id, checked)
      if (success) {
        message.success('状态已更新')
        fetchList(activeType)
        fetchAllEnumData()
        // 如果详情模态框打开，刷新详情数据
        if (detailModalVisible) {
          fetchList(activeType)
        }
      } else {
        message.error('更新失败')
      }
    } catch (e: unknown) {
      message.error(e?.message || '更新失败')
    }
  }

  // 获取所有分类
  const categories = useMemo(() => {
    if (!enumTypes || enumTypes.length === 0) {
      return ['all']
    }
    const cats = enumTypes.map(type => type.category || '未分类')
    return ['all', ...Array.from(new Set(cats))]
  }, [enumTypes])

  // 过滤和搜索逻辑
  const filteredEnumData = useMemo(() => {
    return allEnumData.filter(item => {
      // 分类筛选
      if (selectedCategory !== 'all' && item.type.category !== selectedCategory) {
        return false
      }

      // 搜索筛选
      if (searchText) {
        const searchLower = searchText.toLowerCase()
        const typeMatch = item.type.name.toLowerCase().includes(searchLower) ||
                         item.type.code.toLowerCase().includes(searchLower)
        const valueMatch = item.values.some(value =>
          value.label.toLowerCase().includes(searchLower) ||
          value.value.toLowerCase().includes(searchLower) ||
          (value.code && value.code.toLowerCase().includes(searchLower))
        )
        return typeMatch || valueMatch
      }

      return true
    })
  }, [allEnumData, selectedCategory, searchText])

  // 获取类型统计信息
  const getTypeStats = (type: EnumFieldType) => {
    const values = allEnumData.find(item => item.type.id === type.id)?.values || []
    const activeCount = values.filter(v => v.is_active).length
    return {
      total: values.length,
      active: activeCount,
      inactive: values.length - activeCount
    }
  }

  // 查看详情处理
  const handleViewDetail = async (typeCode: string) => {
    setActiveType(typeCode)
    await fetchList(typeCode)
    setDetailModalVisible(true)
  }

  // 概览视图列定义
  const overviewColumns: ColumnsType<EnumFieldWithType> = useMemo(() => [
    {
      title: '类型名称',
      dataIndex: ['type', 'name'],
      width: 200,
      render: (name: string, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{name}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            <Tag color="blue" size="small">{record.type.code}</Tag>
          </div>
        </div>
      ),
    },
    {
      title: '分类',
      dataIndex: ['type', 'category'],
      width: 120,
      render: (category: string) => category || '未分类',
    },
    {
      title: '描述',
      dataIndex: ['type', 'description'],
      width: 200,
      ellipsis: true,
      render: (desc: string) => desc || '-',
    },
    {
      title: '枚举值预览',
      width: 300,
      render: (_, record) => (
        <EnumValuePreview
          values={record.values}
          maxDisplay={3}
          size="small"
          showInactiveCount={true}
        />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => handleViewDetail(record.type.code)}
        >
          查看详情
        </Button>
      ),
    },
  ], [allEnumData])

  const columns: ColumnsType<SystemDictionary> = useMemo(() => [
    {
      title: '类型',
      dataIndex: 'dict_type',
      width: 160,
      render: (t: string) => {
        const typeInfo = enumTypes.find(et => et.code === t)
        return (
          <div>
            <Tag color="blue">{t}</Tag>
            {typeInfo && (
              <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                {typeInfo.name}
              </div>
            )}
          </div>
        )
      },
    },
    {
      title: '编码',
      dataIndex: 'dict_code',
      width: 160,
      render: (code: string) => code || '-'
    },
    { title: '标签', dataIndex: 'dict_label', width: 200 },
    { title: '值', dataIndex: 'dict_value', width: 200 },
    {
      title: '排序',
      dataIndex: 'sort_order',
      width: 80,
      render: (v: number) => v ?? 0,
    },
    {
      title: '启用',
      dataIndex: 'is_active',
      width: 100,
      render: (v: boolean, record) => (
        <Switch
          checked={v}
          onChange={(checked) => handleToggleActive(record, checked)}
        />
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 180,
      render: (v: string) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button size="small" type="link" onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该枚举项？"
            description={`${record.dict_type} / ${record.dict_label}`}
            onConfirm={() => handleDelete(record)}
            okText="删除"
            okType="danger"
            cancelText="取消"
          >
            <Button size="small" type="link" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ], [activeType, enumTypes])

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={
          <Space>
            <span>枚举值字段管理</span>
            <Badge count={enumTypes.length} showZero />
          </Space>
        }
        extra={
          <Space>
            <Button onClick={() => {
              fetchTypes()
              fetchAllEnumData()
              fetchList(activeType)
            }}>
              刷新
            </Button>
          </Space>
        }
      >
        {/* 搜索和筛选区域 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Search
              placeholder="搜索枚举类型或值"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              prefix={<SearchOutlined />}
              allowClear
            />
          </Col>
          <Col span={6}>
            <Select
              placeholder="选择分类"
              value={selectedCategory}
              onChange={setSelectedCategory}
              style={{ width: '100%' }}
            >
              {categories.map(cat => (
                <Option key={cat} value={cat}>
                  {cat === 'all' ? '全部分类' : cat}
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={6}>
            <Select
              placeholder="选择字典类型"
              value={activeType}
              onChange={(v) => setActiveType(v)}
              style={{ width: '100%' }}
              allowClear
            >
              {enumTypes.map(t => (
                <Option key={t.code} value={t.code}>
                  {t.name} ({t.code})
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={4}>
            <div style={{ textAlign: 'right' }}>
              <span style={{ color: '#666', fontSize: '14px' }}>
                共 {filteredEnumData.length} 个类型
              </span>
            </div>
          </Col>
        </Row>

        {/* 列表视图 */}
        <Table
          rowKey={(record) => record.type.id}
          loading={loading}
          columns={overviewColumns}
          dataSource={filteredEnumData}
          pagination={{
            pageSize: 10,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
          }}
          scroll={{ x: 1200 }}
          size="middle"
        />
      </Card>

      <Modal
        open={edit.visible}
        title={editingRecord ? '编辑枚举值' : '新增枚举值'}
        onOk={submit}
        onCancel={() => {
          form.resetFields()
          setEdit({ visible: false })
          setEditingRecord(null)
        }}
        okText="保存"
        cancelText="取消"
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="dict_type" label="字典类型">
            <Input disabled placeholder="自动填充" />
          </Form.Item>

          <Form.Item
            name="dict_label"
            label="显示标签"
            rules={[{ required: true, message: '请输入显示标签' }]}
          >
            <Input placeholder="如：已确权、经营性等" />
          </Form.Item>

          <Form.Item
            name="dict_value"
            label="枚举值"
            rules={[{ required: true, message: '请输入枚举值' }]}
          >
            <Input placeholder="如：CONFIRMED、COMMERCIAL等" />
          </Form.Item>

          <Form.Item name="dict_code" label="编码">
            <Input placeholder="可选，如：confirmed、commercial等" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="可选描述信息" />
          </Form.Item>

          <Form.Item name="sort_order" label="排序">
            <Input type="number" placeholder="排序，数值越小越靠前" />
          </Form.Item>


          {enumTypes.find(t => t.code === activeType) && (
            <div style={{
              padding: '12px',
              backgroundColor: '#f5f5f5',
              borderRadius: '6px',
              fontSize: '12px',
              color: '#666'
            }}>
              <div><strong>枚举类型：</strong>{enumTypes.find(t => t.code === activeType)?.name}</div>
              <div><strong>类型编码：</strong>{activeType}</div>
              <div><strong>分类：</strong>{enumTypes.find(t => t.code === activeType)?.category || '未分类'}</div>
              {enumTypes.find(t => t.code === activeType)?.description && (
                <div><strong>描述：</strong>{enumTypes.find(t => t.code === activeType)?.description}</div>
              )}
            </div>
          )}
        </Form>
      </Modal>

      {/* 详情模态框 */}
      <Modal
        open={detailModalVisible}
        title={
          activeType ? `${enumTypes.find(t => t.code === activeType)?.name} (${activeType})` : '枚举值详情'
        }
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
          <Button
            key="add"
            type="primary"
            onClick={() => {
              setDetailModalVisible(false)
              handleCreate()
            }}
          >
            新增枚举值
          </Button>
        ]}
        width={1200}
        destroyOnHidden
      >
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={data}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1200 }}
        />
      </Modal>
    </div>
  )
}

export default DictionaryPage
