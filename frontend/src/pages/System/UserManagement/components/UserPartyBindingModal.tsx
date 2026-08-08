import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Form, Input, Modal, Select, Space, Table, Tag, Typography } from 'antd';
import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { partyService } from '@/services/partyService';
import {
  type User,
  type UserPartyBinding,
  type UserPartyRelationType,
  type UserPartyScopePreview,
  type UserPartyScopeProposal,
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
}

interface PartyOption {
  id: string;
  name: string;
}

interface PendingScopeChange {
  preview: UserPartyScopePreview;
  idempotencyKey: string;
  successMessage: string;
}

const pageLogger = createLogger('UserPartyBindingModal');

const RELATION_TYPE_OPTIONS: Array<{ label: string; value: UserPartyRelationType }> = [
  { label: '产权方 (owner)', value: 'owner' },
  { label: '管理方 (manager)', value: 'manager' },
];

const getRelationTypeLabel = (relationType: UserPartyRelationType): string => {
  const matchedOption = RELATION_TYPE_OPTIONS.find(option => option.value === relationType);
  return matchedOption?.label ?? relationType;
};

const getScopeSourceLabel = (source: UserPartyScopePreview['after_scope']['source']): string => {
  const labels = {
    explicit: '显式用户绑定',
    organization: '组织默认范围',
    unrestricted: '不受限范围',
    none: '无有效范围',
  } as const;
  return labels[source];
};

const createIdempotencyKey = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
};

const UserPartyBindingModal: React.FC<UserPartyBindingModalProps> = ({
  open,
  user,
  onClose,
  onChanged,
}) => {
  const [form] = Form.useForm<BindingFormValues>();
  const [reason, setReason] = useState('');
  const [reasonError, setReasonError] = useState(false);
  const [editingBinding, setEditingBinding] = useState<UserPartyBinding | null>(null);
  const [pendingScopeChange, setPendingScopeChange] = useState<PendingScopeChange | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [committing, setCommitting] = useState(false);

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
      const partyResult = await partyService.getParties({ limit: 500, status: 'active' });
      return (partyResult.items ?? [])
        .filter(item => item.review_status === 'approved')
        .map(item => ({
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
      setReason('');
      setReasonError(false);
      return;
    }

    setEditingBinding(null);
    setPendingScopeChange(null);
    setReason('');
    setReasonError(false);
  }, [open, resetFormToCreate, user?.id]);

  const handleEditBinding = useCallback(
    (binding: UserPartyBinding) => {
      setEditingBinding(binding);
      form.setFieldsValue({
        party_id: binding.party_id,
        relation_type: binding.relation_type,
      });
    },
    [form]
  );

  const refreshBindings = useCallback(async () => {
    await bindingsQuery.refetch();
  }, [bindingsQuery]);

  const requestScopePreview = useCallback(
    async (proposal: UserPartyScopeProposal, successMessage: string) => {
      if (user == null) {
        return;
      }

      setPreviewing(true);
      try {
        const preview = await userService.previewUserPartyScope(user.id, proposal);
        if (preview == null) {
          throw new Error('用户主体范围预览响应为空');
        }
        setReason('');
        setReasonError(false);
        setPendingScopeChange({
          preview,
          idempotencyKey: createIdempotencyKey(),
          successMessage,
        });
      } catch (error) {
        pageLogger.error('预览用户主体范围变更失败:', error as Error);
        MessageManager.error('预览用户数据范围变更失败');
      } finally {
        setPreviewing(false);
      }
    },
    [user]
  );

  const handleSubmit = useCallback(
    async (values: BindingFormValues) => {
      if (user == null) {
        return;
      }

      const proposal: UserPartyScopeProposal =
        editingBinding != null
          ? {
              operation: 'update',
              binding_id: editingBinding.id,
              party_id: values.party_id,
              relation_type: values.relation_type,
            }
          : {
              operation: 'create',
              party_id: values.party_id,
              relation_type: values.relation_type,
            };
      await requestScopePreview(
        proposal,
        editingBinding != null ? '用户数据范围已更新' : '用户数据范围已创建'
      );
    },
    [editingBinding, requestScopePreview, user]
  );

  const handleCloseBinding = useCallback(
    async (bindingId: string) => {
      await requestScopePreview(
        {
          operation: 'close',
          binding_id: bindingId,
        },
        '用户数据范围已关闭'
      );
    },
    [requestScopePreview]
  );

  const handleCommitScopeChange = useCallback(async () => {
    if (user == null || pendingScopeChange == null) {
      return;
    }

    const normalizedReason = reason.trim();
    if (normalizedReason === '') {
      setReasonError(true);
      return;
    }

    setCommitting(true);
    try {
      const result = await userService.commitUserPartyScope(user.id, {
        preview_token: pendingScopeChange.preview.preview_token,
        reason: normalizedReason,
        idempotency_key: pendingScopeChange.idempotencyKey,
      });
      if (result == null) {
        throw new Error('用户主体范围提交响应为空');
      }

      await refreshBindings();
      await onChanged?.();
      MessageManager.success(pendingScopeChange.successMessage);
      setPendingScopeChange(null);
      setReason('');
      setReasonError(false);
      resetFormToCreate();
    } catch (error) {
      pageLogger.error('提交用户主体范围变更失败:', error as Error);
      MessageManager.error('提交用户数据范围变更失败，请重新预览');
    } finally {
      setCommitting(false);
    }
  }, [onChanged, pendingScopeChange, reason, refreshBindings, resetFormToCreate, user]);

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
        title: '生效区间',
        key: 'validity',
        render: (_, record) => {
          const validFrom = dayjs(record.valid_from).format('YYYY-MM-DD HH:mm');
          const validTo =
            record.valid_to != null
              ? dayjs(record.valid_to).format('YYYY-MM-DD HH:mm')
              : '长期有效';
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
              disabled={previewing || committing}
              onClick={() => {
                handleEditBinding(record);
              }}
              aria-label={`编辑用户主体绑定${record.id}`}
            />
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              loading={previewing}
              disabled={committing}
              className={styles.tableActionButton}
              onClick={() => {
                void handleCloseBinding(record.id);
              }}
              aria-label={`关闭用户主体绑定${record.id}`}
            />
          </Space>
        ),
      },
    ],
    [committing, handleCloseBinding, handleEditBinding, partyNameMap, previewing]
  );

  const loading =
    bindingsQuery.isLoading ||
    bindingsQuery.isFetching ||
    partiesQuery.isLoading ||
    partiesQuery.isFetching;

  return (
    <Modal
      title={user != null ? `用户数据范围 - ${user.full_name}` : '用户数据范围'}
      open={open}
      onCancel={onClose}
      footer={null}
      forceRender
      width={980}
      destroyOnHidden
    >
      <Space orientation="vertical" size={16} className={styles.fullWidthControl}>
        <Typography.Text type="secondary" className={styles.bindingModalHint}>
          当前有效绑定是该用户完整的数据范围来源；关闭全部绑定后，系统才会回退到组织默认范围。
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

            <Form.Item className={styles.bindingFormActions}>
              <Space>
                <Button onClick={resetFormToCreate} disabled={previewing || committing}>
                  清空
                </Button>
                <Button type="primary" htmlType="submit" loading={previewing} disabled={committing}>
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

        {pendingScopeChange != null ? (
          <Modal
            title="确认用户数据范围变更"
            open
            onCancel={() => {
              if (!committing) {
                setPendingScopeChange(null);
                setReason('');
                setReasonError(false);
              }
            }}
            onOk={() => {
              void handleCommitScopeChange();
            }}
            okText="确认提交"
            cancelText="取消"
            confirmLoading={committing}
            maskClosable={!committing}
            keyboard={!committing}
            destroyOnHidden
          >
            <Space orientation="vertical" size={12} className={styles.fullWidthControl}>
              <Typography.Text>
                变更后范围来源：{getScopeSourceLabel(pendingScopeChange.preview.after_scope.source)}
              </Typography.Text>
              <Typography.Text type="secondary">
                当前有效绑定：{pendingScopeChange.preview.impact.before_current_binding_count} 个
                {' -> '}
                {pendingScopeChange.preview.impact.after_current_binding_count} 个
              </Typography.Text>
              {pendingScopeChange.preview.impact.uses_organization_default_after ? (
                <Typography.Text type="secondary">提交后将回退到组织默认范围。</Typography.Text>
              ) : null}
              <Form layout="vertical">
                <Form.Item
                  label="变更原因"
                  validateStatus={reasonError ? 'error' : undefined}
                  help={reasonError ? '请填写变更原因' : undefined}
                >
                  <Input.TextArea
                    autoFocus
                    maxLength={500}
                    rows={3}
                    value={reason}
                    onChange={event => {
                      setReason(event.target.value);
                      if (reasonError) {
                        setReasonError(false);
                      }
                    }}
                    placeholder="请填写本次范围调整的原因"
                  />
                </Form.Item>
              </Form>
            </Space>
          </Modal>
        ) : null}
      </Space>
    </Modal>
  );
};

export default UserPartyBindingModal;
