import React, { useState, useEffect } from 'react'
import {
  Form, Space, Tag, Button, Card, Input,
  Select, Tooltip, Col, Row, Table, Modal, Popconfirm,
  Badge, Statistic, Tabs, Switch
} from 'antd'
import { MessageManager } from '@/utils/messageManager'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  EyeOutlined
} from '@ant-design/icons'
import { unifiedDictionaryService } from '../../services/dictionary'
import type {
  EnumFieldType,
  EnumFieldValue,
  CreateEnumFieldTypeRequest,
  UpdateEnumFieldTypeRequest,
  CreateEnumFieldValueRequest,
  UpdateEnumFieldValueRequest
} from '../../services/dictionary'
import EnumValuePreview from '../../components/Dictionary/EnumValuePreview'
import { COLORS } from '@/styles/colorMap'

const { TabPane } = Tabs
const { TextArea } = Input
const { Option } = Select

// 错误类型定义
interface ApiError {
  response?: {
    data?: {
      message?: string
      detail?: string
    }
  }
  message?: string
}

// 统计信息类型
interface EnumFieldStatistics {
  total_types: number
  active_types: number
  total_values: number
  active_values: number
  usage_count: number
  categories: string[]
}

// Local interfaces removed, using types from services/dictionary

const EnumFieldPage: React.FC = () => {
  const [enumTypes, setEnumTypes] = useState<EnumFieldType[]>([]);
  const [enumValues, setEnumValues] = useState<EnumFieldValue[]>([]);
  const [statistics, setStatistics] = useState<EnumFieldStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('types');

  // 模态框状态
  const [typeModalVisible, setTypeModalVisible] = useState(false);
  const [valueModalVisible, setValueModalVisible] = useState(false);
  const [editingType, setEditingType] = useState<EnumFieldType | null>(null);
  const [editingValue, setEditingValue] = useState<EnumFieldValue | null>(null);

  // 表单实例
  const [typeForm] = Form.useForm();
  const [valueForm] = Form.useForm();

  // 加载数据
  const loadEnumTypes = async () => {
    setLoading(true);
    try {
      const data = await unifiedDictionaryService.getEnumFieldTypes()
      setEnumTypes(data);
    } catch (error: unknown) {
      const apiError = error as ApiError
      MessageManager.error(apiError?.response?.data?.detail ?? apiError?.message ?? '加载枚举类型失败');
    } finally {
      setLoading(false);
    }
  };

  const loadEnumValues = async (typeId: string) => {
    try {
      const data = await unifiedDictionaryService.getEnumFieldValues(typeId)
      setEnumValues(data);
    } catch (error: unknown) {
      const apiError = error as ApiError
      MessageManager.error(apiError?.response?.data?.detail ?? apiError?.message ?? '加载枚举值失败');
    }
  };

  const loadStatistics = async () => {
    try {
      const stats = await unifiedDictionaryService.getDictionaryStats()
      setStatistics({
        total_types: stats.totalTypes,
        active_types: stats.activeTypes,
        total_values: stats.totalValues,
        active_values: stats.activeTypes,
        usage_count: 0,
        categories: []
      });
    } catch (error: unknown) {
      const apiError = error as ApiError
      MessageManager.error(apiError?.message ?? '加载统计信息失败');
    }
  };

  useEffect(() => {
    loadEnumTypes();
    loadStatistics();
  }, []);

  useEffect(() => {
    if (selectedTypeId) {
      loadEnumValues(selectedTypeId);
    }
  }, [selectedTypeId]);

  // 监听模态框打开和编辑值的变化
  useEffect(() => {
    if (valueModalVisible) {
      if (editingValue) {
        // 编辑模式 - 设置表单字段值
        const formData = {
          label: String(editingValue.label || ''),
          value: String(editingValue.value || ''),
          code: String(editingValue.code || ''),
          description: String(editingValue.description || ''),
          sort_order: Number(editingValue.sort_order || 0),
          color: String(editingValue.color || ''),
          icon: String(editingValue.icon || ''),
          is_active: Boolean(editingValue.is_active),
          is_default: Boolean(editingValue.is_default),
          enum_type_id: String(editingValue.enum_type_id || selectedTypeId)
        };

        // 使用 setTimeout 确保 modal 完全打开后再设置表单值
        setTimeout(() => {
          valueForm.setFieldsValue(formData);
        }, 0);
      } else {
        // 新建模式 - 重置表单为默认值
        const formData = {
          label: '',
          value: '',
          code: '',
          description: '',
          sort_order: 0,
          color: '',
          icon: '',
          is_active: true,
          is_default: false,
          enum_type_id: String(selectedTypeId || '')
        };

        // 使用 setTimeout 确保 modal 完全打开后再设置表单值
        setTimeout(() => {
          valueForm.setFieldsValue(formData);
        }, 0);
      }
    }
  }, [valueModalVisible, editingValue, selectedTypeId, valueForm]);

  // 枚举类型表格列定义
  const typeColumns: ColumnsType<EnumFieldType> = [
    {
      title: '类型名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <span>{text}</span>
          {record.is_system && <Tag color="blue">系统</Tag>}
        </Space>
      ),
    },
    {
      title: '编码',
      dataIndex: 'code',
      key: 'code',
      render: (text) => <code>{text}</code>,
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      render: (text) => text || '-',
    },
    {
      title: '配置',
      key: 'config',
      render: (_, record) => (
        <Space>
          {record.is_multiple && <Tag color="green">多选</Tag>}
          {record.is_hierarchical && <Tag color="orange">层级</Tag>}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Badge
          status={status === 'active' ? 'success' : 'default'}
          text={status === 'active' ? '启用' : '禁用'}
        />
      ),
    },
    {
      title: '枚举值预览',
      key: 'enum_values_preview',
      render: (_, record) => (
        <EnumValuePreview
          values={record.enum_values || []}
          maxDisplay={5}
          size="small"
          showInactiveCount={false}
        />
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Tooltip title="查看枚举值">
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedTypeId(record.id);
                setActiveTab('values');
              }}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => handleEditType(record)}
            />
          </Tooltip>
          {!record.is_system && (
            <Popconfirm
              title="确定删除此枚举类型吗？"
              onConfirm={() => handleDeleteType(record.id)}
            >
              <Button type="link" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // 枚举值表格列定义
  const valueColumns: ColumnsType<EnumFieldValue> = [
    {
      title: '标签',
      dataIndex: 'label',
      key: 'label',
    },
    {
      title: '值',
      dataIndex: 'value',
      key: 'value',
      render: (text) => <code>{text}</code>,
    },
    {
      title: '编码',
      dataIndex: 'code',
      key: 'code',
      render: (text) => text ? <code>{text}</code> : '-',
    },
    {
      title: '颜色',
      dataIndex: 'color',
      key: 'color',
      render: (color) => color ? (
        <Space>
          <div
            style={{
              width: 16,
              height: 16,
              backgroundColor: color,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 2,
            }}
          />
          <span>{color}</span>
        </Space>
      ) : '-',
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
    },
    {
      title: '状态',
      key: 'status',
      render: (_, record) => (
        <Space>
          <Badge
            status={record.is_active ? 'success' : 'default'}
            text={record.is_active ? '启用' : '禁用'}
          />
          {record.is_default && <Tag color="gold">默认</Tag>}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditValue(record)}
          />
          <Popconfirm
            title="确定删除此枚举值吗？"
            onConfirm={() => handleDeleteValue(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 处理函数
  const handleCreateType = () => {
    setEditingType(null);
    typeForm.resetFields();
    setTypeModalVisible(true);
  };

  const handleEditType = (type: EnumFieldType) => {
    setEditingType(type);
    typeForm.setFieldsValue(type);
    setTypeModalVisible(true);
  };

  const handleDeleteType = async (id: string) => {
    try {
      const success = await unifiedDictionaryService.deleteEnumFieldType(id)
      if (success) {
        MessageManager.success('删除成功');
        loadEnumTypes();
        loadStatistics();
      } else {
        MessageManager.error('删除失败');
      }
    } catch (error: unknown) {
      const apiError = error as ApiError
      MessageManager.error(apiError?.message || '删除失败');
    }
  };

  const handleCreateValue = () => {
    if (!selectedTypeId) {
      MessageManager.warning('请先选择枚举类型');
      return;
    }

    setEditingValue(null);
    valueForm.resetFields();
    setValueModalVisible(true);
  };

  const handleEditValue = (value: EnumFieldValue) => {
    setEditingValue(value);
    setValueModalVisible(true);
  };

  const handleDeleteValue = async (id: string) => {
    try {
      const success = await unifiedDictionaryService.deleteEnumValue(id)
      if (success) {
        MessageManager.success('删除成功');
        if (selectedTypeId) {
          loadEnumValues(selectedTypeId);
        }
      } else {
        MessageManager.error('删除失败');
      }
    } catch (error: unknown) {
      const apiError = error as ApiError
      MessageManager.error(apiError?.message || '删除失败');
    }
  };

  // Define form types that include all potential fields
  type EnumTypeFormValues = CreateEnumFieldTypeRequest & { is_active?: boolean }
  type EnumValueFormValues = CreateEnumFieldValueRequest & { is_active?: boolean }

  const handleTypeSubmit = async (values: EnumTypeFormValues) => {
    try {
      let success = false
      if (editingType) {
        success = await unifiedDictionaryService.updateEnumFieldType(editingType.id, values as UpdateEnumFieldTypeRequest) !== null
      } else {
        success = await unifiedDictionaryService.createEnumFieldType(values) !== null
      }

      if (success) {
        MessageManager.success(editingType ? '更新成功' : '创建成功');
        setTypeModalVisible(false);
        loadEnumTypes();
        loadStatistics();
      } else {
        MessageManager.error('操作失败');
      }
    } catch (error: unknown) {
      const apiError = error as ApiError
      MessageManager.error(apiError?.message ?? '操作失败');
    }
  };

  const handleValueSubmit = async (values: EnumValueFormValues) => {
    try {
      let success = false
      if (editingValue && selectedTypeId) {
        // For update, we need to cast values to UpdateEnumFieldValueRequest as it might contain extra fields or we just pick what we need
        // But UpdateEnumFieldValueRequest is subset/compatible mostly.
        const updateData: UpdateEnumFieldValueRequest = {
          label: values.label,
          value: values.value,
          code: values.code,
          description: values.description,
          sort_order: values.sort_order,
          color: values.color,
          icon: values.icon,
          is_active: values.is_active,
          is_default: values.is_default
        }
        success = await unifiedDictionaryService.updateEnumFieldValue(selectedTypeId, editingValue.id, updateData) !== null
      } else {
        success = await unifiedDictionaryService.addEnumFieldValue(editingValue?.enum_type_id || selectedTypeId!, values) !== null
      }

      if (success) {
        MessageManager.success(editingValue ? '更新成功' : '创建成功');
        setValueModalVisible(false);
        setEditingValue(null);
        if (selectedTypeId) {
          loadEnumValues(selectedTypeId);
        }
      } else {
        MessageManager.error('操作失败');
      }
    } catch (error: unknown) {
      const apiError = error as ApiError
      MessageManager.error(apiError?.message ?? '操作失败');
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="枚举类型总数"
              value={statistics?.total_types || 0}
              valueStyle={{ color: COLORS.primary }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="启用类型"
              value={statistics?.active_types || 0}
              valueStyle={{ color: COLORS.success }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="枚举值总数"
              value={statistics?.total_values || 0}
              valueStyle={{ color: COLORS.primary }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="使用次数"
              value={statistics?.usage_count || 0}
              valueStyle={{ color: COLORS.warning }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="枚举类型" key="types">
            <div style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreateType}
              >
                新建枚举类型
              </Button>
            </div>
            <Table
              columns={typeColumns}
              dataSource={enumTypes}
              rowKey="id"
              loading={loading}
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }}
            />
          </TabPane>

          <TabPane tab="枚举值管理" key="values">
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Select
                  placeholder="选择枚举类型"
                  style={{ width: 200 }}
                  value={selectedTypeId}
                  onChange={setSelectedTypeId}
                  allowClear
                >
                  {enumTypes.map((type) => (
                    <Option key={type.id} value={type.id}>
                      {type.name}
                    </Option>
                  ))}
                </Select>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreateValue}
                  disabled={!selectedTypeId}
                >
                  新建枚举值
                </Button>
              </Space>
            </div>
            <Table
              columns={valueColumns}
              dataSource={enumValues}
              rowKey="id"
              loading={loading}
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 枚举类型编辑模态框 */}
      <Modal
        title={editingType ? '编辑枚举类型' : '新建枚举类型'}
        open={typeModalVisible}
        onCancel={() => setTypeModalVisible(false)}
        onOk={() => typeForm.submit()}
        width={600}
      >
        <Form
          form={typeForm}
          layout="vertical"
          onFinish={handleTypeSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="类型名称"
                rules={[{ required: true, message: '请输入类型名称' }]}
              >
                <Input placeholder="请输入类型名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="code"
                label="类型编码"
                rules={[
                  { required: true, message: '请输入类型编码' },
                  { pattern: /^[a-zA-Z0-9_]+$/, message: '编码只能包含字母、数字和下划线' }
                ]}
              >
                <Input placeholder="请输入类型编码" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="类别">
                <Input placeholder="请输入类别" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="status" label="状态" initialValue="active">
                <Select>
                  <Option value="active">启用</Option>
                  <Option value="inactive">禁用</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="is_multiple" label="支持多选" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="is_hierarchical" label="层级结构" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="default_value" label="默认值">
                <Input placeholder="默认值" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* 枚举值编辑模态框 */}
      <Modal
        key={editingValue ? `edit-${editingValue.id}` : 'create'}
        title={editingValue ? '编辑枚举值' : '新建枚举值'}
        open={valueModalVisible}
        onCancel={() => {
          valueForm.resetFields();
          setValueModalVisible(false);
        }}
        onOk={() => {
          valueForm.submit();
        }}
        width={600}
      >
        <Form
          form={valueForm}
          layout="vertical"
          onFinish={handleValueSubmit}
        >
          <Form.Item name="enum_type_id" hidden>
            <Input />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="label"
                label="显示标签"
                rules={[{ required: true, message: '请输入显示标签' }]}
              >
                <Input placeholder="请输入显示标签" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="value"
                label="枚举值"
                rules={[{ required: true, message: '请输入枚举值' }]}
              >
                <Input placeholder="请输入枚举值" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="code" label="编码">
                <Input placeholder="请输入编码" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="sort_order" label="排序">
                <Input type="number" placeholder="排序" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="color" label="颜色">
                <Input placeholder="#FFFFFF" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="icon" label="图标">
                <Input placeholder="图标名称" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="is_active" label="启用" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="is_default" label="默认值" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default EnumFieldPage;
