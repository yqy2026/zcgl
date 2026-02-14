import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Form,
  Space,
  Tag,
  Button,
  Card,
  Input,
  Select,
  Tooltip,
  Col,
  Row,
  Modal,
  Popconfirm,
  Badge,
  Statistic,
  Tabs,
  Switch,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import type { ColumnsType } from 'antd/es/table';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { dictionaryService } from '@/services/dictionary';
import type {
  EnumFieldType,
  EnumFieldValue,
  CreateEnumFieldTypeRequest,
  UpdateEnumFieldTypeRequest,
  CreateEnumFieldValueRequest,
  UpdateEnumFieldValueRequest,
} from '@/services/dictionary';
import EnumValuePreview from '@/components/Dictionary/EnumValuePreview';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { useArrayListData } from '@/hooks/useArrayListData';
import PageContainer from '@/components/Common/PageContainer';
import styles from './EnumFieldPage.module.css';

const { TextArea } = Input;
const { Option } = Select;
const { Search } = Input;

// 错误类型定义
interface ApiError {
  response?: {
    data?: {
      message?: string;
      detail?: string;
    };
  };
  message?: string;
}

// 统计信息类型
interface EnumFieldStatistics {
  total_types: number;
  active_types: number;
  total_values: number;
  active_values: number;
  usage_count: number;
  categories: string[];
}

interface EnumTypeFilters {
  keyword: string;
}

type Tone = 'primary' | 'success' | 'warning' | 'error';

const resolveText = (value: string | null | undefined, fallback: string): string => {
  if (value == null) {
    return fallback;
  }
  const normalizedValue = value.trim();
  return normalizedValue !== '' ? normalizedValue : fallback;
};

const getTypeStatusTone = (status: EnumFieldType['status']): Tone =>
  status === 'active' ? 'success' : 'warning';

const buildColorPreviewStyle = (color: string): React.CSSProperties =>
  ({ ['--preview-color' as string]: color }) as React.CSSProperties;

// Local interfaces removed, using types from services/dictionary

const EnumFieldPage: React.FC = () => {
  const [statistics, setStatistics] = useState<EnumFieldStatistics | null>(null);
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('types');
  const [enumTypeOptions, setEnumTypeOptions] = useState<EnumFieldType[]>([]);
  const [enumTypeSource, setEnumTypeSource] = useState<EnumFieldType[]>([]);
  const [enumValueSource, setEnumValueSource] = useState<EnumFieldValue[]>([]);
  const [isTypesLoading, setIsTypesLoading] = useState(false);
  const [isValuesLoading, setIsValuesLoading] = useState(false);

  // 模态框状态
  const [typeModalVisible, setTypeModalVisible] = useState(false);
  const [valueModalVisible, setValueModalVisible] = useState(false);
  const [editingType, setEditingType] = useState<EnumFieldType | null>(null);
  const [editingValue, setEditingValue] = useState<EnumFieldValue | null>(null);

  // 表单实例
  const [typeForm] = Form.useForm();
  const [valueForm] = Form.useForm();

  const handleTypesError = useCallback((error: unknown) => {
    const apiError = error as ApiError;
    MessageManager.error(
      apiError?.response?.data?.detail ?? apiError?.message ?? '加载枚举类型失败'
    );
  }, []);

  const handleValuesError = useCallback((error: unknown) => {
    const apiError = error as ApiError;
    MessageManager.error(apiError?.response?.data?.detail ?? apiError?.message ?? '加载枚举值失败');
  }, []);

  const {
    data: enumValues,
    loading: valuesTableLoading,
    pagination: valuePagination,
    loadList: loadEnumValues,
    updatePagination: updateValuePagination,
  } = useArrayListData<EnumFieldValue, Record<string, never>>({
    items: enumValueSource,
    initialFilters: {},
    initialPageSize: 10,
  });

  const {
    data: enumTypes,
    loading: typesTableLoading,
    pagination: typePagination,
    filters: typeFilters,
    loadList: loadEnumTypes,
    applyFilters: applyTypeFilters,
    updatePagination: updateTypePagination,
  } = useArrayListData<EnumFieldType, EnumTypeFilters>({
    items: enumTypeSource,
    initialFilters: {
      keyword: '',
    },
    initialPageSize: 10,
    filterFn: (items, nextFilters) => {
      const trimmedKeyword = nextFilters.keyword.trim();
      if (trimmedKeyword === '') {
        return items;
      }
      return items.filter(type => {
        const name = type.name ?? '';
        const code = type.code ?? '';
        const category = type.category ?? '';
        return (
          name.includes(trimmedKeyword) ||
          code.includes(trimmedKeyword) ||
          category.includes(trimmedKeyword)
        );
      });
    },
  });

  const loadStatistics = async () => {
    try {
      const [stats, enumData] = await Promise.all([
        dictionaryService.getDictionaryStats(),
        dictionaryService.getEnumFieldData(),
      ]);
      const activeValues = enumData.reduce((totalCount, item) => {
        const activeCount = item.values.filter(value => value.is_active === true).length;
        return totalCount + activeCount;
      }, 0);
      setStatistics({
        total_types: stats.totalTypes,
        active_types: stats.activeTypes,
        total_values: stats.totalValues,
        active_values: activeValues,
        usage_count: 0,
        categories: [],
      });
    } catch (error: unknown) {
      const apiError = error as ApiError;
      MessageManager.error(apiError?.message ?? '加载统计信息失败');
    }
  };

  const loadEnumTypeSource = useCallback(async () => {
    setIsTypesLoading(true);
    try {
      const data = await dictionaryService.getEnumFieldTypes();
      setEnumTypeOptions(data);
      setEnumTypeSource(data);
    } catch (error) {
      handleTypesError(error);
    } finally {
      setIsTypesLoading(false);
    }
  }, [handleTypesError]);

  const loadEnumValueSource = useCallback(
    async (typeId: string) => {
      if (typeId === '') {
        setEnumValueSource([]);
        return;
      }
      setIsValuesLoading(true);
      try {
        const data = await dictionaryService.getEnumFieldValues(typeId);
        setEnumValueSource(data);
      } catch (error) {
        handleValuesError(error);
      } finally {
        setIsValuesLoading(false);
      }
    },
    [handleValuesError]
  );

  useEffect(() => {
    void loadEnumTypeSource();
    void loadStatistics();
  }, [loadEnumTypeSource]);

  useEffect(() => {
    void loadEnumValues({ page: 1 });
  }, [enumValueSource, loadEnumValues]);

  useEffect(() => {
    void loadEnumTypes({ page: 1 });
  }, [enumTypeSource, loadEnumTypes]);

  useEffect(() => {
    const typeId = selectedTypeId ?? '';
    void loadEnumValueSource(typeId);
  }, [selectedTypeId, loadEnumValueSource]);

  const typesLoading = useMemo(
    () => isTypesLoading || typesTableLoading,
    [isTypesLoading, typesTableLoading]
  );
  const valuesLoading = useMemo(
    () => isValuesLoading || valuesTableLoading,
    [isValuesLoading, valuesTableLoading]
  );
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
  };

  // 监听模态框打开和编辑值的变化
  useEffect(() => {
    if (valueModalVisible) {
      if (editingValue) {
        // 编辑模式 - 设置表单字段值
        const formData = {
          label: String(editingValue.label ?? ''),
          value: String(editingValue.value ?? ''),
          code: String(editingValue.code ?? ''),
          description: String(editingValue.description ?? ''),
          sort_order: Number(editingValue.sort_order ?? 0),
          color: String(editingValue.color ?? ''),
          icon: String(editingValue.icon ?? ''),
          is_active: Boolean(editingValue.is_active),
          is_default: Boolean(editingValue.is_default),
          enum_type_id: String(editingValue.enum_type_id ?? selectedTypeId),
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
          enum_type_id: String(selectedTypeId ?? ''),
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
        <Space className={styles.typeNameCell}>
          <span className={styles.typeNameText}>{text}</span>
          {record.is_system && (
            <Tag className={[styles.statusTag, styles.tonePrimary].join(' ')}>系统</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '编码',
      dataIndex: 'code',
      key: 'code',
      render: text => <code className={styles.codeValue}>{text}</code>,
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      render: text => resolveText(text, '-'),
    },
    {
      title: '配置',
      key: 'config',
      render: (_, record) => (
        <Space className={styles.configTagGroup}>
          {record.is_multiple && (
            <Tag className={[styles.statusTag, styles.toneSuccess].join(' ')}>多选</Tag>
          )}
          {record.is_hierarchical && (
            <Tag className={[styles.statusTag, styles.toneWarning].join(' ')}>层级</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: status => {
        const tone = getTypeStatusTone(status);
        return (
          <Space size={6} className={styles.statusGroup}>
            <Badge status={status === 'active' ? 'success' : 'default'} />
            <span className={[styles.statusText, toneClassMap[tone]].join(' ')}>
              {status === 'active' ? '启用' : '禁用'}
            </span>
          </Space>
        );
      },
    },
    {
      title: '枚举值预览',
      key: 'enum_values_preview',
      render: (_, record) => (
        <EnumValuePreview
          values={record.enum_values ?? []}
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
        <Space className={styles.actionGroup}>
          <Tooltip title="查看枚举值">
            <Button
              type="text"
              icon={<EyeOutlined />}
              className={styles.tableActionButton}
              onClick={() => {
                setSelectedTypeId(record.id);
                setActiveTab('values');
              }}
              aria-label={`查看类型 ${record.name} 的枚举值`}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              className={styles.tableActionButton}
              onClick={() => handleEditType(record)}
              aria-label={`编辑类型 ${record.name}`}
            />
          </Tooltip>
          {!record.is_system && (
            <Popconfirm
              title="确定删除此枚举类型吗？"
              onConfirm={() => handleDeleteType(record.id)}
            >
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                className={styles.tableActionButton}
                aria-label={`删除类型 ${record.name}`}
              />
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
      render: text => <code className={styles.codeValue}>{text}</code>,
    },
    {
      title: '编码',
      dataIndex: 'code',
      key: 'code',
      render: text => (text != null ? <code className={styles.codeValue}>{text}</code> : '-'),
    },
    {
      title: '颜色',
      dataIndex: 'color',
      key: 'color',
      render: color =>
        color != null ? (
          <Space className={styles.colorCell}>
            <span
              className={styles.colorPreview}
              style={buildColorPreviewStyle(color)}
            />
            <span className={styles.colorValue}>{color}</span>
          </Space>
        ) : (
          '-'
        ),
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
        <Space className={styles.configTagGroup}>
          <Space size={6} className={styles.statusGroup}>
            <Badge status={record.is_active ? 'success' : 'default'} />
            <span
              className={[
                styles.statusText,
                record.is_active ? styles.toneSuccess : styles.toneWarning,
              ].join(' ')}
            >
              {record.is_active ? '启用' : '禁用'}
            </span>
          </Space>
          {record.is_default === true && (
            <Tag className={[styles.statusTag, styles.toneWarning].join(' ')}>默认</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space className={styles.actionGroup}>
          <Button
            type="text"
            icon={<EditOutlined />}
            className={styles.tableActionButton}
            onClick={() => handleEditValue(record)}
            aria-label={`编辑枚举值 ${record.label}`}
          />
          <Popconfirm title="确定删除此枚举值吗？" onConfirm={() => handleDeleteValue(record.id)}>
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              className={styles.tableActionButton}
              aria-label={`删除枚举值 ${record.label}`}
            />
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
      const success = await dictionaryService.deleteEnumFieldType(id);
      if (success) {
        MessageManager.success('删除成功');
        void loadEnumTypes();
        void loadStatistics();
      } else {
        MessageManager.error('删除失败');
      }
    } catch (error: unknown) {
      const apiError = error as ApiError;
      MessageManager.error(apiError?.message ?? '删除失败');
    }
  };

  const handleCreateValue = () => {
    if (selectedTypeId == null) {
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
      const result = await dictionaryService.deleteEnumValue(id);
      if (result.success) {
        MessageManager.success('删除成功');
        if (selectedTypeId != null) {
          void loadEnumValues();
        }
      } else {
        MessageManager.error('删除失败');
      }
    } catch (error: unknown) {
      const apiError = error as ApiError;
      MessageManager.error(apiError?.message ?? '删除失败');
    }
  };

  // Define form types that include all potential fields
  type EnumTypeFormValues = CreateEnumFieldTypeRequest & { is_active?: boolean };
  type EnumValueFormValues = CreateEnumFieldValueRequest & { is_active?: boolean };

  const handleTypeSubmit = async (values: EnumTypeFormValues) => {
    try {
      let success = false;
      if (editingType) {
        success =
          (await dictionaryService.updateEnumFieldType(
            editingType.id,
            values as UpdateEnumFieldTypeRequest
          )) !== null;
      } else {
        success = (await dictionaryService.createEnumFieldType(values)) !== null;
      }

      if (success) {
        MessageManager.success(editingType ? '更新成功' : '创建成功');
        setTypeModalVisible(false);
        void loadEnumTypes();
        void loadStatistics();
      } else {
        MessageManager.error('操作失败');
      }
    } catch (error: unknown) {
      const apiError = error as ApiError;
      MessageManager.error(apiError?.message ?? '操作失败');
    }
  };

  const handleValueSubmit = async (values: EnumValueFormValues) => {
    try {
      let success = false;
      if (editingValue != null && selectedTypeId != null) {
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
          is_default: values.is_default,
        };
        success =
          (await dictionaryService.updateEnumFieldValue(
            selectedTypeId,
            editingValue.id,
            updateData
          )) !== null;
      } else {
        success =
          (await dictionaryService.addEnumFieldValue(
            editingValue?.enum_type_id ?? selectedTypeId!,
            values
          )) !== null;
      }

      if (success) {
        MessageManager.success(editingValue ? '更新成功' : '创建成功');
        setValueModalVisible(false);
        setEditingValue(null);
        if (selectedTypeId != null) {
          void loadEnumValues();
        }
      } else {
        MessageManager.error('操作失败');
      }
    } catch (error: unknown) {
      const apiError = error as ApiError;
      MessageManager.error(apiError?.message ?? '操作失败');
    }
  };

  const tabItems = [
    {
      key: 'types',
      label: '枚举类型',
      children: (
        <>
          <div className={styles.toolbarSection}>
            <Space className={styles.typeToolbar} size={12} wrap>
              <Search
                placeholder="搜索类型名称、编码或类别"
                prefix={<SearchOutlined />}
                value={typeFilters.keyword}
                onChange={event => applyTypeFilters({ keyword: event.target.value })}
                allowClear
                className={styles.typeSearch}
              />
              <div className={styles.typeSummaryText}>共 {typePagination.total} 个类型</div>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                className={styles.actionButton}
                onClick={handleCreateType}
              >
                新建枚举类型
              </Button>
            </Space>
          </div>
          <TableWithPagination
            columns={typeColumns}
            dataSource={enumTypes}
            rowKey="id"
            loading={typesLoading}
            paginationState={typePagination}
            onPageChange={updateTypePagination}
            paginationProps={{
              showTotal: (total: number) => `共 ${total} 条记录`,
            }}
          />
        </>
      ),
    },
    {
      key: 'values',
      label: '枚举值管理',
      children: (
        <>
          <div className={styles.toolbarSection}>
            <Space className={styles.valueToolbar} wrap>
              <Select
                placeholder="选择枚举类型"
                className={styles.typeSelect}
                value={selectedTypeId ?? undefined}
                onChange={(value?: string) => {
                  setSelectedTypeId(value ?? null);
                }}
                allowClear
              >
                {enumTypeOptions.map(type => (
                  <Option key={type.id} value={type.id}>
                    {type.name}
                  </Option>
                ))}
              </Select>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                className={styles.actionButton}
                onClick={handleCreateValue}
                disabled={selectedTypeId == null}
              >
                新建枚举值
              </Button>
            </Space>
          </div>
          <TableWithPagination
            columns={valueColumns}
            dataSource={enumValues}
            rowKey="id"
            loading={valuesLoading}
            paginationState={valuePagination}
            onPageChange={updateValuePagination}
            paginationProps={{
              showTotal: (total: number) => `共 ${total} 条记录`,
            }}
          />
        </>
      ),
    },
  ];

  return (
    <PageContainer className={styles.pageShell} title="枚举字段管理" subTitle="维护枚举类型配置、枚举值及字典可用状态">
      <Row gutter={[16, 16]} className={styles.statsRow}>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.primaryStatsCard}`}>
            <Statistic title="枚举类型总数" value={statistics?.total_types ?? 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.activeStatsCard}`}>
            <Statistic title="启用类型" value={statistics?.active_types ?? 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.primaryStatsCard}`}>
            <Statistic title="枚举值总数" value={statistics?.total_values ?? 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.warningStatsCard}`}>
            <Statistic title="启用值数量" value={statistics?.active_values ?? 0} />
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} className={styles.tabs} />
      </Card>

      {/* 枚举类型编辑模态框 */}
      <Modal
        title={editingType ? '编辑枚举类型' : '新建枚举类型'}
        open={typeModalVisible}
        onCancel={() => setTypeModalVisible(false)}
        onOk={() => typeForm.submit()}
        okButtonProps={{ className: styles.modalActionButton }}
        cancelButtonProps={{ className: styles.modalActionButton }}
        width={600}
      >
        <Form form={typeForm} layout="vertical" onFinish={handleTypeSubmit}>
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
                  { pattern: /^[a-zA-Z0-9_]+$/, message: '编码只能包含字母、数字和下划线' },
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
        okButtonProps={{ className: styles.modalActionButton }}
        cancelButtonProps={{ className: styles.modalActionButton }}
        width={600}
      >
        <Form form={valueForm} layout="vertical" onFinish={handleValueSubmit}>
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
    </PageContainer>
  );
};

export default EnumFieldPage;
