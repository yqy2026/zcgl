import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Form, Input, Modal, Select, Space, Typography } from 'antd';
import type { Organization, OrganizationMovePreview, OrganizationTree } from '@/types/organization';
import { organizationService } from '@/services/organizationService';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import styles from '../../OrganizationPage.module.css';

interface OrganizationMoveModalProps {
  open: boolean;
  organization: Organization | null;
  organizationTree: OrganizationTree[];
  onClose: () => void;
  onChanged?: () => void | Promise<void>;
}

interface OrganizationMoveFormValues {
  target_parent_id: string;
}

interface PendingOrganizationMove {
  preview: OrganizationMovePreview;
  idempotencyKey: string;
}

const ROOT_ORGANIZATION_VALUE = '__organization_move_root__';
const pageLogger = createLogger('OrganizationMoveModal');

const createIdempotencyKey = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
};

const collectSubtreeIds = (nodes: OrganizationTree[], organizationId: string): Set<string> => {
  const excludedIds = new Set<string>();

  const collectNode = (node: OrganizationTree): void => {
    excludedIds.add(node.id);
    node.children.forEach(collectNode);
  };

  const visit = (node: OrganizationTree): void => {
    if (node.id === organizationId) {
      collectNode(node);
      return;
    }
    node.children.forEach(visit);
  };

  nodes.forEach(visit);
  return excludedIds;
};

const flattenOrganizationTree = (nodes: OrganizationTree[]): OrganizationTree[] => {
  return nodes.flatMap(node => [node, ...flattenOrganizationTree(node.children)]);
};

const OrganizationMoveModal: React.FC<OrganizationMoveModalProps> = ({
  open,
  organization,
  organizationTree,
  onClose,
  onChanged,
}) => {
  const [form] = Form.useForm<OrganizationMoveFormValues>();
  const [reason, setReason] = useState('');
  const [reasonError, setReasonError] = useState(false);
  const [pendingMove, setPendingMove] = useState<PendingOrganizationMove | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [committing, setCommitting] = useState(false);

  const targetOptions = useMemo(() => {
    if (organization == null) {
      return [];
    }

    const excludedIds = collectSubtreeIds(organizationTree, organization.id);
    const options = flattenOrganizationTree(organizationTree)
      .filter(item => !excludedIds.has(item.id))
      .map(item => ({
        label: item.name,
        value: item.id,
        disabled: item.status !== 'active',
      }));

    if (organization.parent_id != null) {
      options.unshift({ label: '设为根组织', value: ROOT_ORGANIZATION_VALUE, disabled: false });
    }
    return options;
  }, [organization, organizationTree]);

  useEffect(() => {
    // destroyOnHidden 关闭即卸载表单，重开按 initialValues 重建，无需 resetFields
    setReason('');
    setReasonError(false);
    setPendingMove(null);
  }, [open, organization?.id]);

  const handlePreview = useCallback(async () => {
    if (organization == null) {
      return;
    }

    try {
      const values = await form.validateFields();
      setPreviewing(true);
      const preview = await organizationService.previewOrganizationMove(organization.id, {
        target_parent_id:
          values.target_parent_id === ROOT_ORGANIZATION_VALUE ? null : values.target_parent_id,
      });
      setReason('');
      setReasonError(false);
      setPendingMove({ preview, idempotencyKey: createIdempotencyKey() });
    } catch (error) {
      if (typeof error === 'object' && error != null && 'errorFields' in error) {
        return;
      }
      pageLogger.error('Organization move preview failed:', error as Error);
      MessageManager.error('组织迁移预览失败');
    } finally {
      setPreviewing(false);
    }
  }, [form, organization]);

  const handleCommit = useCallback(async () => {
    if (organization == null || pendingMove == null) {
      return;
    }

    const normalizedReason = reason.trim();
    if (normalizedReason === '') {
      setReasonError(true);
      return;
    }

    setCommitting(true);
    try {
      await organizationService.commitOrganizationMove(organization.id, {
        preview_token: pendingMove.preview.preview_token,
        reason: normalizedReason,
        idempotency_key: pendingMove.idempotencyKey,
      });
      await onChanged?.();
      MessageManager.success('组织迁移已提交');
      onClose();
    } catch (error) {
      pageLogger.error('Organization move commit failed:', error as Error);
      MessageManager.error('组织迁移提交失败，请重新预览');
    } finally {
      setCommitting(false);
    }
  }, [onChanged, onClose, organization, pendingMove, reason]);

  const preview = pendingMove?.preview;

  return (
    <Modal
      title={organization != null ? `迁移组织 - ${organization.name}` : '迁移组织'}
      open={open}
      onCancel={() => {
        if (!committing) {
          onClose();
        }
      }}
      destroyOnHidden
      maskClosable={!committing}
      keyboard={!committing}
      footer={
        <Space>
          <Button onClick={onClose} disabled={committing}>
            取消
          </Button>
          {preview == null ? (
            <Button type="primary" loading={previewing} onClick={() => void handlePreview()}>
              预览迁移影响
            </Button>
          ) : (
            <>
              <Button
                onClick={() => {
                  setPendingMove(null);
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
    >
      <Space orientation="vertical" size={16} className={styles.fullWidthControl}>
        <Form form={form} layout="vertical">
          <Form.Item
            name="target_parent_id"
            label="目标上级组织"
            rules={[{ required: true, message: '请选择目标上级组织' }]}
          >
            <Select
              showSearch
              placeholder="请选择目标上级组织"
              options={targetOptions}
              optionFilterProp="label"
              disabled={preview != null || previewing || committing}
            />
          </Form.Item>
        </Form>

        {preview != null && (
          <>
            <Space orientation="vertical" size={4} className={styles.fullWidthControl}>
              <Typography.Text>受影响组织：{preview.impact.organization_count} 个</Typography.Text>
              <Typography.Text>
                主体范围变化组织：{preview.impact.organization_scope_change_count} 个
              </Typography.Text>
              <Typography.Text>受影响人员：{preview.impact.user_count} 个</Typography.Text>
              <Typography.Text>
                人员主体范围变化：{preview.impact.user_scope_change_count} 个
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
              placeholder="请填写本次组织迁移的原因"
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

export default OrganizationMoveModal;
