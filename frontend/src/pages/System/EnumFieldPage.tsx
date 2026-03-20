import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Form,
  Card,
  Input,
  Select,
  Col,
  Row,
  Modal,
  Statistic,
  Tabs,
  Switch,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import type {
  EnumFieldType,
  EnumFieldValue,
  CreateEnumFieldTypeRequest,
  UpdateEnumFieldTypeRequest,
  CreateEnumFieldValueRequest,
  UpdateEnumFieldValueRequest,
} from '@/services/dictionary';
import { useArrayListData } from '@/hooks/useArrayListData';
import PageContainer from '@/components/Common/PageContainer';
import {
  useCreateEnumFieldTypeMutation,
  useCreateEnumFieldValueMutation,
  useDeleteEnumFieldTypeMutation,
  useDeleteEnumValueMutation,
  useDictionaryStatisticsQuery,
  useEnumFieldTypesQuery,
  useEnumFieldValuesByTypeIdQuery,
  useUpdateEnumFieldTypeMutation,
  useUpdateEnumFieldValueMutation,
} from '@/hooks/useDictionaryManagement';
import EnumFieldList from './EnumFieldList';
import EnumFieldValueManager from './EnumFieldValueManager';
import styles from './EnumFieldPage.module.css';

const { TextArea } = Input;
const { Option } = Select;

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

interface EnumTypeFilters {
  keyword: string;
}

const EnumFieldPage: React.FC = () => {
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
  const {
    data: enumTypeSource = [],
    error: enumTypesError,
    isLoading: isTypeSourceLoading,
  } = useEnumFieldTypesQuery();
  const {
    data: enumValueSource = [],
    error: enumValuesError,
    isLoading: isValueSourceLoading,
  } = useEnumFieldValuesByTypeIdQuery(selectedTypeId);
  const { data: statistics = null, error: statisticsError } = useDictionaryStatisticsQuery();
  const createEnumFieldTypeMutation = useCreateEnumFieldTypeMutation();
  const updateEnumFieldTypeMutation = useUpdateEnumFieldTypeMutation();
  const deleteEnumFieldTypeMutation = useDeleteEnumFieldTypeMutation();
  const createEnumFieldValueMutation = useCreateEnumFieldValueMutation();
  const updateEnumFieldValueMutation = useUpdateEnumFieldValueMutation();
  const deleteEnumValueMutation = useDeleteEnumValueMutation();

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

  useEffect(() => {
    void loadEnumValues({ page: 1 });
  }, [enumValueSource, loadEnumValues]);

  useEffect(() => {
    void loadEnumTypes({ page: 1 });
  }, [enumTypeSource, loadEnumTypes]);

  useEffect(() => {
    if (enumTypesError != null) {
      handleTypesError(enumTypesError);
    }
  }, [enumTypesError, handleTypesError]);

  useEffect(() => {
    if (enumValuesError != null) {
      handleValuesError(enumValuesError);
    }
  }, [enumValuesError, handleValuesError]);

  useEffect(() => {
    if (statisticsError != null) {
      MessageManager.error('加载统计信息失败');
    }
  }, [statisticsError]);

  const typesLoading = useMemo(
    () => isTypeSourceLoading || typesTableLoading,
    [isTypeSourceLoading, typesTableLoading]
  );
  const valuesLoading = useMemo(
    () => isValueSourceLoading || valuesTableLoading,
    [isValueSourceLoading, valuesTableLoading]
  );

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
      const success = await deleteEnumFieldTypeMutation.mutateAsync(id);
      if (success) {
        MessageManager.success('删除成功');
        if (selectedTypeId === id) {
          setSelectedTypeId(null);
        }
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
      const result = await deleteEnumValueMutation.mutateAsync(id);
      if (result.success) {
        MessageManager.success('删除成功');
      } else {
        MessageManager.error(result.message ?? '删除失败');
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
          (await updateEnumFieldTypeMutation.mutateAsync({
            typeId: editingType.id,
            data: values as UpdateEnumFieldTypeRequest,
          })) !== null;
      } else {
        success = (await createEnumFieldTypeMutation.mutateAsync(values)) !== null;
      }

      if (success) {
        MessageManager.success(editingType ? '更新成功' : '创建成功');
        setTypeModalVisible(false);
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
          (await updateEnumFieldValueMutation.mutateAsync({
            typeId: selectedTypeId,
            valueId: editingValue.id,
            data: updateData,
          })) !== null;
      } else {
        success =
          (await createEnumFieldValueMutation.mutateAsync({
            typeId: editingValue?.enum_type_id ?? selectedTypeId!,
            data: values,
          })) !== null;
      }

      if (success) {
        MessageManager.success(editingValue ? '更新成功' : '创建成功');
        setValueModalVisible(false);
        setEditingValue(null);
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
        <EnumFieldList
          enumTypes={enumTypes}
          loading={typesLoading}
          pagination={typePagination}
          keyword={typeFilters.keyword}
          onKeywordChange={keyword => applyTypeFilters({ keyword })}
          onCreateType={handleCreateType}
          onPageChange={updateTypePagination}
          onViewValues={typeId => {
            setSelectedTypeId(typeId);
            setActiveTab('values');
          }}
          onEditType={handleEditType}
          onDeleteType={handleDeleteType}
        />
      ),
    },
    {
      key: 'values',
      label: '枚举值管理',
      children: (
        <EnumFieldValueManager
          enumTypes={enumTypeSource}
          enumValues={enumValues}
          selectedTypeId={selectedTypeId}
          loading={valuesLoading}
          pagination={valuePagination}
          onSelectType={value => {
            setSelectedTypeId(value ?? null);
          }}
          onCreateValue={handleCreateValue}
          onPageChange={updateValuePagination}
          onEditValue={handleEditValue}
          onDeleteValue={handleDeleteValue}
        />
      ),
    },
  ];

  return (
    <PageContainer
      className={styles.pageShell}
      title="枚举字段管理"
      subTitle="维护枚举类型配置、枚举值及字典可用状态"
    >
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
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          className={styles.tabs}
        />
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
