import React, { useCallback, useEffect, useState } from 'react';
import { Button, Form, Input, Modal, Select, Space, Typography } from 'antd';
import {
  type OrganizationOption,
  type User,
  type UserOrganizationTransferPreview,
  userService,
} from '@/services/systemService';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import styles from '../../UserManagementPage.module.css';

interface UserOrganizationTransferModalProps {
  open: boolean;
  user: User | null;
  organizations: OrganizationOption[];
  onClose: () => void;
  onChanged?: () => void | Promise<void>;
}

interface OrganizationTransferFormValues {
  organization_id: string;
}

interface PendingOrganizationTransfer {
  preview: UserOrganizationTransferPreview;
  idempotencyKey: string;
}

const pageLogger = createLogger('UserOrganizationTransferModal');

const createIdempotencyKey = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
};

const getScopeSourceLabel = (source: UserOrganizationTransferPreview['after_scope']['source']) => {
  const labels = {
    explicit: '显式主体绑定',
    organization: '组织默认范围',
    unrestricted: '不受限范围',
    none: '无有效范围',
  } as const;
  return labels[source];
};

const UserOrganizationTransferModal: React.FC<UserOrganizationTransferModalProps> = ({
  open,
  user,
  organizations,
  onClose,
  onChanged,
}) => {
  const [form] = Form.useForm<OrganizationTransferFormValues>();
  const [reason, setReason] = useState('');
  const [reasonError, setReasonError] = useState(false);
  const [pendingTransfer, setPendingTransfer] = useState<PendingOrganizationTransfer | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [committing, setCommitting] = useState(false);

  const targetOrganizationOptions = organizations.filter(
    option => option.id !== user?.organization_id
  );

  useEffect(() => {
    form.resetFields();
    setReason('');
    setReasonError(false);
    setPendingTransfer(null);
  }, [form, open, user?.id]);

  const handlePreview = useCallback(async () => {
    if (user == null) {
      return;
    }

    try {
      const values = await form.validateFields();
      setPreviewing(true);
      const preview = await userService.previewUserOrganizationTransfer(user.id, values);
      if (preview == null) {
        throw new Error('Organization transfer preview response is empty');
      }
      setReason('');
      setReasonError(false);
      setPendingTransfer({
        preview,
        idempotencyKey: createIdempotencyKey(),
      });
    } catch (error) {
      if (
        error instanceof Error &&
        error.message === 'Organization transfer preview response is empty'
      ) {
        pageLogger.error('Organization transfer preview returned no result:', error);
        MessageManager.error('组织调动预览失败');
        return;
      }

      if (typeof error === 'object' && error != null && 'errorFields' in error) {
        return;
      }

      pageLogger.error('Organization transfer preview failed:', error as Error);
      MessageManager.error('组织调动预览失败');
    } finally {
      setPreviewing(false);
    }
  }, [form, user]);

  const handleCommit = useCallback(async () => {
    if (user == null || pendingTransfer == null) {
      return;
    }

    const normalizedReason = reason.trim();
    if (normalizedReason === '') {
      setReasonError(true);
      return;
    }

    setCommitting(true);
    try {
      const result = await userService.commitUserOrganizationTransfer(user.id, {
        preview_token: pendingTransfer.preview.preview_token,
        reason: normalizedReason,
        idempotency_key: pendingTransfer.idempotencyKey,
      });
      if (result == null) {
        throw new Error('Organization transfer commit response is empty');
      }

      await onChanged?.();
      MessageManager.success('组织调动已提交');
      onClose();
    } catch (error) {
      pageLogger.error('Organization transfer commit failed:', error as Error);
      MessageManager.error('组织调动提交失败，请重新预览');
    } finally {
      setCommitting(false);
    }
  }, [onChanged, onClose, pendingTransfer, reason, user]);

  const preview = pendingTransfer?.preview;

  return (
    <Modal
      title={user != null ? `调动组织 - ${user.full_name}` : '调动组织'}
      open={open}
      forceRender
      onCancel={() => {
        if (!committing) {
          onClose();
        }
      }}
      footer={
        <Space>
          <Button onClick={onClose} disabled={committing}>
            取消
          </Button>
          {preview == null ? (
            <Button type="primary" loading={previewing} onClick={() => void handlePreview()}>
              预览调动影响
            </Button>
          ) : (
            <>
              <Button
                onClick={() => {
                  setPendingTransfer(null);
                  setReason('');
                  setReasonError(false);
                }}
                disabled={committing}
              >
                重新选择
              </Button>
              <Button type="primary" loading={committing} onClick={() => void handleCommit()}>
                确认提交
              </Button>
            </>
          )}
        </Space>
      }
      destroyOnHidden
      maskClosable={!committing}
      keyboard={!committing}
    >
      <Space orientation="vertical" size={16} className={styles.fullWidthControl}>
        <Form form={form} layout="vertical">
          <Form.Item
            name="organization_id"
            label="目标组织"
            rules={[{ required: true, message: '请选择目标组织' }]}
          >
            <Select
              showSearch
              placeholder="请选择目标组织"
              options={targetOrganizationOptions.map(option => ({
                label: option.name,
                value: option.id,
              }))}
              optionFilterProp="label"
              disabled={preview != null || previewing || committing}
            />
          </Form.Item>
        </Form>

        {preview != null && (
          <>
            <Space orientation="vertical" size={4} className={styles.fullWidthControl}>
              <Typography.Text>
                调动后范围来源：{getScopeSourceLabel(preview.after_scope.source)}
              </Typography.Text>
              <Typography.Text>
                主体范围：{preview.impact.scope_changed ? '已变化' : '不变'}
              </Typography.Text>
              <Typography.Text>
                当前显式主体绑定：{preview.impact.current_explicit_binding_count} 条
              </Typography.Text>
            </Space>

            <Input.TextArea
              value={reason}
              onChange={event => {
                setReason(event.target.value);
                if (reasonError) {
                  setReasonError(false);
                }
              }}
              placeholder="请填写本次组织调动的原因"
              rows={3}
              status={reasonError ? 'error' : undefined}
              disabled={committing}
            />
            {reasonError && <Typography.Text type="danger">请填写变更原因</Typography.Text>}
          </>
        )}
      </Space>
    </Modal>
  );
};

export default UserOrganizationTransferModal;
