import React, { useEffect, useMemo, useState, useCallback } from 'react';
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Switch,
  Tag,
  Popconfirm,
  Row,
  Col,
  Badge,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { SearchOutlined } from '@ant-design/icons';
import { COLORS } from '@/styles/colorMap';
import { dictionaryService } from '@/services/dictionary';
import type { EnumFieldType, EnumFieldValue } from '@/services/dictionary';
import type { SystemDictionary } from '@/types/dictionary';
import EnumValuePreview from '@/components/Dictionary/EnumValuePreview';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { useArrayListData } from '@/hooks/useArrayListData';
import {
  handleApiError as _handleError,
  withErrorHandling as _withErrorHandling_unused,
  createErrorHandler as _createErrorHandler,
} from '@/services';
import { createLogger } from '@/utils/logger';

const pageLogger = createLogger('DictionaryPage');

// Utility functions
const setDictTypes = (types: string[]) => types;

const { Option } = Select;
const { Search } = Input;

interface EnumFieldWithType {
  type: EnumFieldType;
  values: EnumFieldValue[];
}

interface EditState {
  visible: boolean;
}

interface OverviewFilters {
  keyword: string;
  category: string;
}

const DictionaryPage: React.FC = () => {
  const [overviewSourceLoading, setOverviewSourceLoading] = useState(false);
  const [_dictTypes, _setDictTypes] = useState<string[]>([]);
  const [enumTypes, setEnumTypes] = useState<EnumFieldType[]>([]);
  const [activeType, setActiveType] = useState<string | undefined>(undefined);
  const [edit, setEdit] = useState<EditState>({ visible: false });
  const [editingRecord, setEditingRecord] = useState<SystemDictionary | null>(null);
  const [form] = Form.useForm<SystemDictionary>();

  // 新增状态
  const [allEnumData, setAllEnumData] = useState<EnumFieldWithType[]>([]);
  const [detailModalVisible, setDetailModalVisible] = useState<boolean>(false);
  const [detailSource, setDetailSource] = useState<SystemDictionary[]>([]);
  const [detailSourceLoading, setDetailSourceLoading] = useState(false);

  const {
    data: overviewData,
    loading: overviewTableLoading,
    pagination: overviewPagination,
    filters: overviewFilters,
    loadList: loadOverviewList,
    applyFilters: applyOverviewFilters,
    updatePagination: updateOverviewPagination,
  } = useArrayListData<EnumFieldWithType, OverviewFilters>({
    items: allEnumData,
    initialFilters: {
      keyword: '',
      category: 'all',
    },
    initialPageSize: 10,
    filterFn: (items, filters) => {
      const trimmedKeyword = filters.keyword.trim().toLowerCase();
      return items.filter(item => {
        if (filters.category !== 'all' && item.type.category !== filters.category) {
          return false;
        }

        if (trimmedKeyword === '') {
          return true;
        }

        const typeName = item.type.name?.toLowerCase() ?? '';
        const typeCode = item.type.code?.toLowerCase() ?? '';
        const typeMatch = typeName.includes(trimmedKeyword) || typeCode.includes(trimmedKeyword);
        const valueMatch = item.values.some(value => {
          const label = value.label?.toLowerCase() ?? '';
          const code = value.code?.toLowerCase() ?? '';
          const val = value.value?.toLowerCase() ?? '';
          return (
            label.includes(trimmedKeyword) ||
            val.includes(trimmedKeyword) ||
            code.includes(trimmedKeyword)
          );
        });

        return typeMatch || valueMatch;
      });
    },
  });

  const handleDetailError = useCallback((error: unknown) => {
    pageLogger.error('获取枚举值失败:', error as Error);
    const errorMessage = error instanceof Error ? error.message : '获取枚举值失败';
    MessageManager.error(errorMessage);
  }, []);

  const {
    data: detailRows,
    loading: detailTableLoading,
    pagination: detailPagination,
    loadList: loadDetailList,
    updatePagination: updateDetailPagination,
  } = useArrayListData<SystemDictionary, Record<string, never>>({
    items: detailSource,
    initialFilters: {},
    initialPageSize: 10,
    onError: handleDetailError,
  });

  const loadDetailSource = useCallback(
    async (typeCode?: string) => {
      if (typeCode == null || typeCode === '') {
        setDetailSource([]);
        return;
      }
      setDetailSourceLoading(true);
      try {
        const list = await dictionaryService.getEnumFieldValuesByTypeCode(typeCode);
        setDetailSource(list);
      } catch (error) {
        handleDetailError(error);
      } finally {
        setDetailSourceLoading(false);
      }
    },
    [handleDetailError]
  );

  const overviewLoading = useMemo(
    () => overviewSourceLoading || overviewTableLoading,
    [overviewSourceLoading, overviewTableLoading]
  );
  const detailLoading = useMemo(
    () => detailSourceLoading || detailTableLoading,
    [detailSourceLoading, detailTableLoading]
  );

  // 获取字典类型列表
  const fetchTypes = async () => {
    try {
      const types = await dictionaryService.getTypes();
      setDictTypes(types ?? []);

      // 同时获取枚举类型详细信息
      const typesData = await dictionaryService.getEnumFieldTypes();
      setEnumTypes(typesData ?? []);
    } catch (error) {
      pageLogger.error('获取字典类型失败:', error as Error);
    }
  };

  // 获取所有枚举数据
  const fetchAllEnumData = async () => {
    setOverviewSourceLoading(true);
    try {
      const data = await dictionaryService.getEnumFieldData();
      // Got enum data
      setAllEnumData(data);
    } catch (e: unknown) {
      pageLogger.error('获取枚举数据失败:', e as Error);
      const errorMessage = e instanceof Error ? e.message : '获取枚举数据失败';
      MessageManager.error(errorMessage);
    } finally {
      setOverviewSourceLoading(false);
    }
  };

  useEffect(() => {
    fetchTypes();
    fetchAllEnumData();
  }, []);

  useEffect(() => {
    void loadOverviewList({ page: 1 });
  }, [allEnumData, loadOverviewList]);

  useEffect(() => {
    void loadDetailList({ page: 1 });
  }, [detailSource, loadDetailList]);

  useEffect(() => {
    void loadDetailSource(activeType);
  }, [activeType, loadDetailSource]);

  const handleCreate = async () => {
    if (activeType == null) {
      MessageManager.warning('请先选择字典类型');
      return;
    }

    // 获取对应的枚举类型
    const _targetType = enumTypes.find(type => type.code === activeType);
    if (!_targetType) {
      MessageManager.error('未找到对应的枚举类型');
      return;
    }

    setEditingRecord(null);
    setEdit({ visible: true });
    form.resetFields();
    const sortOrders = detailRows.map(item => item.sort_order ?? 0);
    const maxSortOrder = sortOrders.length > 0 ? Math.max(...sortOrders) : 0;
    const initialValues: Partial<SystemDictionary> = {
      dict_type: activeType,
      sort_order: sortOrders.length > 0 ? maxSortOrder + 1 : 0,
      is_active: true,
    };

    // 使用 setTimeout 确保模态框完全打开后再设置表单值
    setTimeout(() => {
      form.setFieldsValue(initialValues);
    }, 0);
  };

  const handleEdit = (record: SystemDictionary) => {
    const _targetType = enumTypes.find(type => type.code === record.dict_type);
    setEditingRecord(record);
    setEdit({ visible: true });

    // 设置表单初始值
    const formData: Partial<SystemDictionary> = {
      ...record,
      dict_type: record.dict_type,
      dict_label: record.dict_label,
      dict_value: record.dict_value,
      dict_code: record.dict_code,
      description: record.description ?? '',
      sort_order: record.sort_order ?? 0,
      is_active: record.is_active,
    };

    // 使用 setTimeout 确保模态框完全打开后再设置表单值
    setTimeout(() => {
      form.setFieldsValue(formData);
    }, 0);
  };

  const handleDelete = async (record: SystemDictionary) => {
    try {
      const result = await dictionaryService.deleteEnumValue(record.id);
      if (result.success === true) {
        MessageManager.success('删除成功');
        void loadDetailSource(record.dict_type);
        void fetchAllEnumData();
      } else {
        MessageManager.error('删除失败');
      }
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : '删除失败';
      MessageManager.error(errorMessage);
    }
  };

  const submit = async () => {
    try {
      const values = await form.validateFields();

      if (activeType == null) {
        MessageManager.error('未找到对应的枚举类型');
        return;
      }

      const targetType = enumTypes.find(type => type.code === activeType);
      if (!targetType) {
        MessageManager.error('未找到对应的枚举类型');
        return;
      }

      if (editingRecord) {
        // 更新现有枚举值
        const result = await dictionaryService.updateEnumValue(editingRecord.id, {
          label: values.dict_label,
          value: values.dict_value,
          code: values.dict_code,
          description: values.description,
          sort_order: values.sort_order,
          is_active: values.is_active,
        });

        if (result.success === true) {
          MessageManager.success('更新成功');
        } else {
          MessageManager.error('更新失败');
          return;
        }
      } else {
        // 创建新的枚举值
        const createResult = await dictionaryService.createEnumValue(targetType.id, {
          label: values.dict_label,
          value: values.dict_value,
          code: values.dict_code,
          description: values.description,
          sort_order: values.sort_order,
        });

        if (createResult.success === true) {
          MessageManager.success('创建成功');
        } else {
          MessageManager.error('创建失败');
          return;
        }
      }

      setEdit({ visible: false });
      setEditingRecord(null);
      void loadDetailSource(activeType);
      void fetchAllEnumData();
    } catch (e: unknown) {
      // Handle form validation errors
      if (typeof e === 'object' && e !== null && 'errorFields' in e) return;

      const errorMessage = e instanceof Error ? e.message : '保存失败';
      pageLogger.error('保存字典失败:', e as Error);
      MessageManager.error(errorMessage);
    }
  };

  const handleToggleActive = async (record: SystemDictionary, checked: boolean) => {
    try {
      const result = await dictionaryService.toggleEnumValueActive(record.id, checked);
      if (result.success === true) {
        MessageManager.success('状态已更新');
        void loadDetailSource(record.dict_type);
        void fetchAllEnumData();
      } else {
        MessageManager.error('更新失败');
      }
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : '更新失败';
      MessageManager.error(errorMessage);
    }
  };

  // 获取所有分类
  const categories = useMemo(() => {
    if (enumTypes.length === 0) {
      return ['all'];
    }
    const cats = enumTypes.map(type => type.category ?? '未分类');
    return ['all', ...Array.from(new Set(cats))];
  }, [enumTypes]);

  // 获取类型统计信息
  const _getTypeStats = (type: EnumFieldType) => {
    const values = allEnumData.find(item => item.type.id === type.id)?.values || [];
    const activeCount = values.filter(v => v.is_active).length;
    return {
      total: values.length,
      active: activeCount,
      inactive: values.length - activeCount,
    };
  };

  const handleActiveTypeChange = useCallback(
    (value?: string) => {
      setActiveType(value);
      void loadDetailSource(value);
    },
    [loadDetailSource]
  );

  // 查看详情处理
  const handleViewDetail = useCallback(
    (typeCode: string) => {
      setActiveType(typeCode);
      setDetailModalVisible(true);
      void loadDetailSource(typeCode);
    },
    [loadDetailSource]
  );

  // 概览视图列定义
  const overviewColumns: ColumnsType<EnumFieldWithType> = useMemo(
    () => [
      {
        title: '类型名称',
        dataIndex: ['type', 'name'],
        width: 200,
        render: (name: string, record) => (
          <div>
            <div style={{ fontWeight: 500 }}>{name}</div>
            <div style={{ fontSize: '12px', color: COLORS.textSecondary }}>
              <Tag color="blue">{record.type.code}</Tag>
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
          <Button type="link" size="small" onClick={() => handleViewDetail(record.type.code)}>
            查看详情
          </Button>
        ),
      },
    ],
    [handleViewDetail]
  );

  const columns: ColumnsType<SystemDictionary> = useMemo(
    () => [
      {
        title: '类型',
        dataIndex: 'dict_type',
        width: 160,
        render: (t: string) => {
          const typeInfo = enumTypes.find(et => et.code === t);
          return (
            <div>
              <Tag color="blue">{t}</Tag>
              {typeInfo && (
                <div style={{ fontSize: '12px', color: COLORS.textSecondary, marginTop: '2px' }}>
                  {typeInfo.name}
                </div>
              )}
            </div>
          );
        },
      },
      {
        title: '编码',
        dataIndex: 'dict_code',
        width: 160,
        render: (code: string) => code || '-',
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
          <Switch checked={v} onChange={checked => handleToggleActive(record, checked)} />
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
    ],
    [activeType, enumTypes]
  );

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
              <Button
                onClick={() => {
                  fetchTypes();
                  fetchAllEnumData();
                  void loadDetailSource(activeType);
                }}
              >
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
              value={overviewFilters.keyword}
              onChange={e =>
                applyOverviewFilters({ ...overviewFilters, keyword: e.target.value })
              }
              prefix={<SearchOutlined />}
              allowClear
            />
          </Col>
          <Col span={6}>
            <Select
              placeholder="选择分类"
              value={overviewFilters.category}
              onChange={value => applyOverviewFilters({ ...overviewFilters, category: value })}
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
              onChange={handleActiveTypeChange}
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
              <span style={{ color: COLORS.textSecondary, fontSize: '14px' }}>
                共 {overviewPagination.total} 个类型
              </span>
            </div>
          </Col>
        </Row>

        {/* 列表视图 */}
        <TableWithPagination
          rowKey={record => record.type.id}
          loading={overviewLoading}
          columns={overviewColumns}
          dataSource={overviewData}
          paginationState={overviewPagination}
          onPageChange={updateOverviewPagination}
          paginationProps={{
            showSizeChanger: false,
            showQuickJumper: false,
            showTotal: (total: number, range: [number, number]) =>
              `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
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
          form.resetFields();
          setEdit({ visible: false });
          setEditingRecord(null);
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
            <div
              style={{
                padding: '12px',
                backgroundColor: COLORS.bgTertiary,
                borderRadius: '6px',
                fontSize: '12px',
                color: COLORS.textSecondary,
              }}
            >
              <div>
                <strong>枚举类型：</strong>
                {enumTypes.find(t => t.code === activeType)?.name}
              </div>
              <div>
                <strong>类型编码：</strong>
                {activeType}
              </div>
              <div>
                <strong>分类：</strong>
                {enumTypes.find(t => t.code === activeType)?.category ?? '未分类'}
              </div>
              {enumTypes.find(t => t.code === activeType)?.description != null && (
                <div>
                  <strong>描述：</strong>
                  {enumTypes.find(t => t.code === activeType)?.description}
                </div>
              )}
            </div>
          )}
        </Form>
      </Modal>

      {/* 详情模态框 */}
      <Modal
        open={detailModalVisible}
        title={
          activeType != null
            ? `${enumTypes.find(t => t.code === activeType)?.name} (${activeType})`
            : '枚举值详情'
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
              setDetailModalVisible(false);
              handleCreate();
            }}
          >
            新增枚举值
          </Button>,
        ]}
        width={1200}
        destroyOnHidden
      >
        <TableWithPagination
          rowKey="id"
          loading={detailLoading}
          columns={columns}
          dataSource={detailRows}
          paginationState={detailPagination}
          onPageChange={updateDetailPagination}
          paginationProps={{
            showSizeChanger: false,
            showQuickJumper: false,
          }}
          scroll={{ x: 1200 }}
        />
      </Modal>
    </div>
  );
};

export default DictionaryPage;
