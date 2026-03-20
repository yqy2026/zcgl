import React, { useEffect, useMemo, useState, useCallback } from 'react';
import {
  Button,
  Form,
  Modal,
  Space,
  Switch,
  Tag,
  Popconfirm,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import type { EnumFieldType } from '@/services/dictionary';
import type { SystemDictionary } from '@/types/dictionary';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import PageContainer from '@/components/Common/PageContainer';
import { useArrayListData } from '@/hooks/useArrayListData';
import {
  useCreateEnumValueMutation,
  useDeleteEnumValueMutation,
  useEnumFieldDataQuery,
  useEnumFieldTypesQuery,
  useEnumFieldValuesByTypeCodeQuery,
  useToggleEnumValueActiveMutation,
  useUpdateEnumValueMutation,
} from '@/hooks/useDictionaryManagement';
import DictionaryEditor from './DictionaryEditor';
import DictionaryList, {
  type EnumFieldWithType,
  type OverviewFilters,
} from './DictionaryList';
import styles from './DictionaryPage.module.css';

interface EditState {
  visible: boolean;
}

type Tone = 'primary' | 'success' | 'warning' | 'error';

const resolveText = (value: string | null | undefined, fallback: string): string => {
  if (value == null) {
    return fallback;
  }
  const normalizedValue = value.trim();
  return normalizedValue !== '' ? normalizedValue : fallback;
};

const DictionaryPage: React.FC = () => {
  const [activeType, setActiveType] = useState<string | undefined>(undefined);
  const [edit, setEdit] = useState<EditState>({ visible: false });
  const [editingRecord, setEditingRecord] = useState<SystemDictionary | null>(null);
  const [form] = Form.useForm<SystemDictionary>();

  const [detailModalVisible, setDetailModalVisible] = useState<boolean>(false);

  const {
    data: enumTypes = [],
    error: enumTypesError,
    isLoading: isEnumTypesLoading,
    refetch: refetchEnumTypes,
  } = useEnumFieldTypesQuery();
  const {
    data: allEnumData = [],
    error: enumDataError,
    isLoading: isEnumDataLoading,
    refetch: refetchEnumData,
  } = useEnumFieldDataQuery();
  const {
    data: detailSource = [],
    error: detailSourceError,
    isLoading: isDetailSourceLoading,
    refetch: refetchDetailSource,
  } = useEnumFieldValuesByTypeCodeQuery(activeType);
  const createEnumValueMutation = useCreateEnumValueMutation();
  const updateEnumValueMutation = useUpdateEnumValueMutation();
  const deleteEnumValueMutation = useDeleteEnumValueMutation();
  const toggleEnumValueActiveMutation = useToggleEnumValueActiveMutation();

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
    filterFn: useCallback((items: EnumFieldWithType[], filters: OverviewFilters) => {
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
    }, []),
  });

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
  });

  const overviewLoading = useMemo(
    () => isEnumDataLoading || isEnumTypesLoading || overviewTableLoading,
    [isEnumDataLoading, isEnumTypesLoading, overviewTableLoading]
  );
  const detailLoading = useMemo(
    () => isDetailSourceLoading || detailTableLoading,
    [isDetailSourceLoading, detailTableLoading]
  );

  useEffect(() => {
    void loadOverviewList({ page: 1 });
  }, [allEnumData, loadOverviewList]);

  useEffect(() => {
    void loadDetailList({ page: 1 });
  }, [detailSource, loadDetailList]);

  useEffect(() => {
    if (enumTypesError != null) {
      MessageManager.error('获取字典类型失败');
    }
  }, [enumTypesError]);

  useEffect(() => {
    if (enumDataError != null) {
      MessageManager.error('获取枚举数据失败');
    }
  }, [enumDataError]);

  useEffect(() => {
    if (detailSourceError != null) {
      MessageManager.error('获取枚举值失败');
    }
  }, [detailSourceError]);

  const handleCreate = async () => {
    if (activeType == null) {
      MessageManager.warning('请先选择字典类型');
      return;
    }

    // 获取对应的枚举类型
    const targetType = enumTypes.find(type => type.code === activeType);
    if (!targetType) {
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
      const result = await deleteEnumValueMutation.mutateAsync(record.id);
      if (result.success === true) {
        MessageManager.success('删除成功');
      } else {
        MessageManager.error(result.message ?? '删除失败');
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
        const result = await updateEnumValueMutation.mutateAsync({
          valueId: editingRecord.id,
          data: {
            label: values.dict_label,
            value: values.dict_value,
            code: values.dict_code,
            description: values.description,
            sort_order: values.sort_order,
            is_active: values.is_active,
          },
        });

        if (result.success === true) {
          MessageManager.success('更新成功');
        } else {
          MessageManager.error(result.message ?? '更新失败');
          return;
        }
      } else {
        const createResult = await createEnumValueMutation.mutateAsync({
          typeId: targetType.id,
          data: {
            label: values.dict_label,
            value: values.dict_value,
            code: values.dict_code,
            description: values.description,
            sort_order: values.sort_order,
          },
        });

        if (createResult.success === true) {
          MessageManager.success('创建成功');
        } else {
          MessageManager.error(createResult.message ?? '创建失败');
          return;
        }
      }

      setEdit({ visible: false });
      setEditingRecord(null);
    } catch (e: unknown) {
      if (typeof e === 'object' && e !== null && 'errorFields' in e) return;

      const errorMessage = e instanceof Error ? e.message : '保存失败';
      MessageManager.error(errorMessage);
    }
  };

  const handleToggleActive = async (record: SystemDictionary, checked: boolean) => {
    try {
      const result = await toggleEnumValueActiveMutation.mutateAsync({
        valueId: record.id,
        isActive: checked,
      });
      if (result.success === true) {
        MessageManager.success('状态已更新');
      } else {
        MessageManager.error(result.message ?? '更新失败');
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

  const activeEnumType = useMemo(
    () => enumTypes.find(type => type.code === activeType),
    [activeType, enumTypes]
  );
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
  };

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

  const handleActiveTypeChange = useCallback((value?: string) => {
    setActiveType(value);
  }, []);

  const handleViewDetail = useCallback((typeCode: string) => {
    setActiveType(typeCode);
    setDetailModalVisible(true);
  }, []);

  const columns: ColumnsType<SystemDictionary> = useMemo(
    () => [
      {
        title: '类型',
        dataIndex: 'dict_type',
        width: 160,
        render: (t: string) => {
          const typeInfo = enumTypes.find(et => et.code === t);
          return (
            <div className={styles.typeCell}>
              <Tag className={[styles.codeTag, styles.tonePrimary].join(' ')}>{t}</Tag>
              {typeInfo && <div className={styles.typeHint}>{typeInfo.name}</div>}
            </div>
          );
        },
      },
      {
        title: '编码',
        dataIndex: 'dict_code',
        width: 160,
        render: (code: string) => resolveText(code, '-'),
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
        render: (v: boolean, record) => {
          const tone: Tone = v === true ? 'success' : 'warning';
          return (
            <Space size={6} className={styles.statusToggle}>
              <Switch
                checked={v}
                onChange={checked => handleToggleActive(record, checked)}
                aria-label={`${v ? '停用' : '启用'}字典项 ${record.dict_label}`}
              />
              <span className={[styles.statusText, toneClassMap[tone]].join(' ')}>
                {v === true ? '启用' : '停用'}
              </span>
            </Space>
          );
        },
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
          <Space size={6} className={styles.rowActions}>
            <Button
              size="small"
              type="text"
              className={styles.rowActionButton}
              onClick={() => handleEdit(record)}
              aria-label={`编辑 ${record.dict_label}`}
            >
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
              <Button
                size="small"
                type="text"
                danger
                className={[styles.rowActionButton, styles.dangerActionButton].join(' ')}
                aria-label={`删除 ${record.dict_label}`}
              >
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
    <PageContainer title="枚举值字段管理" subTitle="管理系统字典类型、枚举值与启用状态">
      <DictionaryList
        enumTypes={enumTypes}
        overviewData={overviewData}
        overviewLoading={overviewLoading}
        overviewPagination={overviewPagination}
        overviewFilters={overviewFilters}
        categories={categories}
        activeType={activeType}
        onActiveTypeChange={handleActiveTypeChange}
        onApplyOverviewFilters={applyOverviewFilters}
        onUpdateOverviewPagination={updateOverviewPagination}
        onViewDetail={handleViewDetail}
        onRefresh={() => {
          void refetchEnumTypes();
          void refetchEnumData();
          if (activeType != null && activeType !== '') {
            void refetchDetailSource();
          }
        }}
      />

      <DictionaryEditor
        open={edit.visible}
        editingRecord={editingRecord}
        form={form}
        activeType={activeType}
        activeEnumType={activeEnumType}
        onSubmit={() => {
          void submit();
        }}
        onCancel={() => {
          form.resetFields();
          setEdit({ visible: false });
          setEditingRecord(null);
        }}
      />

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
          <Button
            key="close"
            onClick={() => setDetailModalVisible(false)}
            className={styles.modalActionButton}
          >
            关闭
          </Button>,
          <Button
            key="add"
            type="primary"
            className={styles.modalActionButton}
            onClick={() => {
              setDetailModalVisible(false);
              void handleCreate();
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
    </PageContainer>
  );
};

export default DictionaryPage;
