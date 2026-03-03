import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Form, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography } from 'antd';
import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { partyService } from '@/services/partyService';
import {
  type User,
  type UserPartyBinding,
  type UserPartyRelationType,
  userService,
} from '@/services/systemService';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import styles from '../../UserManagementPage.module.css';

interface UserPartyBindingModalProps {
  open: boolean;
  user: User | null;
  onClose: () => void;
  onChanged?: () => void | Promise<void>;
}

interface BindingFormValues {
  party_id: string;
  relation_type: UserPartyRelationType;
  is_primary: boolean;
}

interface PartyOption {
  id: string;
  name: string;
}

const pageLogger = createLogger('UserPartyBindingModal');

const RELATION_TYPE_OPTIONS: Array<{ label: string; value: UserPartyRelationType }> = [
  { label: '产权方 (owner)', value: 'owner' },
  { label: '管理方 (manager)', value: 'manager' },
  { label: '总部 (headquarters)', value: 'headquarters' },
];

const getRelationTypeLabel = (relationType: UserPartyRelationType): string => {
  const matchedOption = RELATION_TYPE_OPTIONS.find(option => option.value === relationType);
  return matchedOption?.label ?? relationType;
};

const UserPartyBindingModal: React.FC<UserPartyBindingModalProps> = ({
  open,
  user,
  onClose,
  onChanged,
}) => {
  const [form] = Form.useForm<BindingFormValues>();
  const [editingBinding, setEditingBinding] = useState<UserPartyBinding | null>(null);
  const [closingBindingId, setClosingBindingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const queriesEnabled = open && user != null;

  const bindingsQuery = useQuery<UserPartyBinding[]>({
    queryKey: ['user-party-bindings', user?.id],
    queryFn: async () => {
      if (user == null) {
        return [];
      }
      return await userService.getUserPartyBindings(user.id, { active_only: true });
    },
    enabled: queriesEnabled,
    retry: 1,
  });

  const partiesQuery = useQuery<PartyOption[]>({
    queryKey: ['user-party-binding-parties'],
    queryFn: async () => {
      const partyResult = await partyService.getParties({ limit: 500 });
      return (partyResult.items ?? []).map(item => ({
        id: item.id,
        name: item.name,
      }));
    },
    enabled: queriesEnabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const bindings = bindingsQuery.data ?? [];
  const partyOptions = partiesQuery.data ?? [];

  const partyNameMap = useMemo(() => {
    return new Map(partyOptions.map(option => [option.id, option.name]));
  }, [partyOptions]);

  const resetFormToCreate = useCallback(() => {
    setEditingBinding(null);
    form.setFieldsValue({
      party_id: undefined,
      relation_type: 'owner',
      is_primary: false,
    });
  }, [form]);

  useEffect(() => {
    if (bindingsQuery.error != null) {
      pageLogger.error('加载用户主体绑定失败:', bindingsQuery.error as Error);
      MessageManager.error('加载用户主体绑定失败');
    }
  }, [bindingsQuery.error]);

  useEffect(() => {
    if (partiesQuery.error != null) {
      pageLogger.error('加载主体列表失败:', partiesQuery.error as Error);
      MessageManager.error('加载主体列表失败');
    }
  }, [partiesQuery.error]);

  useEffect(() => {
    if (open) {
      resetFormToCreate();
      return;
    }

    setEditingBinding(null);
    setClosingBindingId(null);
    form.resetFields();
  }, [form, open, resetFormToCreate, user?.id]);

  const handleEditBinding = useCallback(
    (binding: UserPartyBinding) => {
      setEditingBinding(binding);
      form.setFieldsValue({
        party_id: binding.party_id,
        relation_type: binding.relation_type,
        is_primary: binding.is_primary,
      });
    },
    [form]
  );

  const refreshBindings = useCallback(async () => {
    await bindingsQuery.refetch();
  }, [bindingsQuery]);

  const handleSubmit = useCallback(
    async (values: BindingFormValues) => {
      if (user == null) {
        return;
      }

      setSaving(true);
      try {
        if (editingBinding != null) {
          await userService.updateUserPartyBinding(user.id, editingBinding.id, values);
          MessageManager.success('主体绑定已更新');
        } else {
          await userService.createUserPartyBinding(user.id, values);
          MessageManager.success('主体绑定已创建');
        }

        await refreshBindings();
        await onChanged?.();
        resetFormToCreate();
      } catch (error) {
        pageLogger.error('保存用户主体绑定失败:', error as Error);
        MessageManager.error(editingBinding != null ? '更新主体绑定失败' : '创建主体绑定失败');
      } finally {
        setSaving(false);
      }
    },
    [editingBinding, onChanged, refreshBindings, resetFormToCreate, user]
  );

  const handleCloseBinding = useCallback(
    async (bindingId: string) => {
      if (user == null) {
        return;
      }

      setClosingBindingId(bindingId);
      try {
        await userService.closeUserPartyBinding(user.id, bindingId);
        MessageManager.success('主体绑定已关闭');
        await refreshBindings();
        await onChanged?.();
      } catch (error) {
        pageLogger.error('关闭用户主体绑定失败:', error as Error);
        MessageManager.error('关闭主体绑定失败');
      } finally {
        setClosingBindingId(null);
      }
    },
    [onChanged, refreshBindings, user]
  );

  const columns: ColumnsType<UserPartyBinding> = useMemo(
    () => [
      {
        title: '主体',
        dataIndex: 'party_id',
        key: 'party_id',
        render: (partyId: string) => partyNameMap.get(partyId) ?? partyId,
      },
      {
        title: '关系类型',
        dataIndex: 'relation_type',
        key: 'relation_type',
        render: (relationType: UserPartyRelationType) => (
          <Tag className={`${styles.semanticTag} ${styles.roleTag} ${styles.tonePrimary}`}>
            {getRelationTypeLabel(relationType)}
          </Tag>
        ),
      },
      {
        title: '主关系',
        dataIndex: 'is_primary',
        key: 'is_primary',
        render: (isPrimary: boolean) =>
          isPrimary ? (
            <Tag className={`${styles.semanticTag} ${styles.statusTag} ${styles.toneSuccess}`}>是</Tag>
          ) : (
            <Tag className={`${styles.semanticTag} ${styles.statusTag} ${styles.toneNeutral}`}>否</Tag>
          ),
      },
      {
        title: '生效区间',
        key: 'validity',
        render: (_, record) => {
          const validFrom = dayjs(record.valid_from).format('YYYY-MM-DD HH:mm');
          const validTo =
            record.valid_to != null ? dayjs(record.valid_to).format('YYYY-MM-DD HH:mm') : '长期有效';
          return `${validFrom} ~ ${validTo}`;
        },
      },
      {
        title: '操作',
        key: 'action',
        render: (_, record) => (
          <Space size={4}>
            <Button
              type="text"
              icon={<EditOutlined />}
              className={styles.tableActionButton}
              onClick={() => {
                handleEditBinding(record);
              }}
              aria-label={`编辑用户主体绑定${record.id}`}
            />
            <Popconfirm
              title="确认关闭该绑定吗？"
              okText="确认"
              cancelText="取消"
              onConfirm={() => {
                void handleCloseBinding(record.id);
              }}
            >
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                loading={closingBindingId === record.id}
                className={styles.tableActionButton}
                aria-label={`关闭用户主体绑定${record.id}`}
              />
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [closingBindingId, handleCloseBinding, handleEditBinding, partyNameMap]
  );

  const loading =
    bindingsQuery.isLoading ||
    bindingsQuery.isFetching ||
    partiesQuery.isLoading ||
    partiesQuery.isFetching;

  return (
    <Modal
      title={user != null ? `主体标签绑定 - ${user.full_name}` : '主体标签绑定'}
      open={open}
      onCancel={onClose}
      footer={null}
      width={980}
      destroyOnHidden
    >
      <Space orientation="vertical" size={16} className={styles.fullWidthControl}>
        <Typography.Text type="secondary" className={styles.bindingModalHint}>
          这里只管理当前生效的主体标签。关闭绑定后，该绑定将立即失效。
        </Typography.Text>

        <Form form={form} layout="vertical" onFinish={values => void handleSubmit(values)}>
          <Space className={styles.bindingFormRow} align="end" wrap>
            <Form.Item
              name="party_id"
              label="主体"
              rules={[{ required: true, message: '请选择主体' }]}
              className={styles.bindingFieldParty}
            >
              <Select
                showSearch
                placeholder="请选择主体"
                options={partyOptions.map(option => ({ label: option.name, value: option.id }))}
                optionFilterProp="label"
              />
            </Form.Item>

            <Form.Item
              name="relation_type"
              label="关系类型"
              rules={[{ required: true, message: '请选择关系类型' }]}
              className={styles.bindingFieldRelation}
            >
              <Select options={RELATION_TYPE_OPTIONS} placeholder="请选择关系类型" />
            </Form.Item>

            <Form.Item
              name="is_primary"
              label="主关系"
              valuePropName="checked"
              className={styles.bindingFieldPrimary}
            >
              <Switch checkedChildren="是" unCheckedChildren="否" />
            </Form.Item>

            <Form.Item className={styles.bindingFormActions}>
              <Space>
                <Button onClick={resetFormToCreate} disabled={saving}>
                  清空
                </Button>
                <Button type="primary" htmlType="submit" loading={saving}>
                  {editingBinding != null ? '更新绑定' : '新增绑定'}
                </Button>
              </Space>
            </Form.Item>
          </Space>
        </Form>

        <Table<UserPartyBinding>
          rowKey="id"
          loading={loading}
          dataSource={bindings}
          columns={columns}
          pagination={false}
          size="small"
          locale={{ emptyText: '暂无生效绑定' }}
        />
      </Space>
    </Modal>
  );
};

export default UserPartyBindingModal;
