import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Descriptions, Form, Input, Modal, Select, Space, Table, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import PartySelector, { type PartySelectorFilterMode } from '@/components/Common/PartySelector';
import { partyService } from '@/services/partyService';
import { organizationService } from '@/services/organizationService';
import type {
  Organization,
  OrganizationPartyPerspective,
  OrganizationPartyScopeBatchPreview,
  OrganizationPartyScopeBatchPreviewItem,
  OrganizationPartyScopeState,
} from '@/types/organization';
import type { Party } from '@/types/party';
import { MessageManager } from '@/utils/messageManager';

interface OrganizationPartyScopeBatchModalProps {
  open: boolean;
  organizations: Organization[];
  onClose: () => void;
  onChanged: () => void | Promise<void>;
}

interface BatchPartyScopeFormValues {
  represented_party_id?: string;
  represented_party_perspective?: OrganizationPartyPerspective;
}

const createIdempotencyKey = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `organization-party-scope-batch-${Date.now()}-${Math.random().toString(36).slice(2)}`;
};

const formatScopeValue = (scope: OrganizationPartyScopeState): string => {
  const partyId = scope.effective_party_id ?? '未配置';
  const perspective =
    scope.effective_party_perspective === 'owner'
      ? '产权方'
      : scope.effective_party_perspective === 'manager'
        ? '管理方'
        : '无视角';
  return `${partyId} / ${perspective}`;
};

/**
 * 代表法人主体选择器：只允许选择 review_status=approved 的法人主体。
 * 过滤由服务端完成（GET /api/v1/parties?review_status=approved，#82 契约对齐），
 * 客户端不再二次过滤。
 */
export const fetchEligibleRepresentedParties = async (
  query: string,
  _filterMode: PartySelectorFilterMode
): Promise<Party[]> => {
  const result = await partyService.searchParties(query, {
    party_type: 'legal_entity',
    status: 'active',
    review_status: 'approved',
    limit: 20,
  });
  return result.items;
};

const OrganizationPartyScopeBatchModal: React.FC<OrganizationPartyScopeBatchModalProps> = ({
  open,
  organizations,
  onClose,
  onChanged,
}) => {
  const [form] = Form.useForm<BatchPartyScopeFormValues>();
  const [preview, setPreview] = useState<OrganizationPartyScopeBatchPreview | null>(null);
  const [reason, setReason] = useState('');
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const organizationIds = useMemo(
    () => organizations.map(organization => organization.id).join(','),
    [organizations]
  );

  useEffect(() => {
    if (!open) {
      // destroyOnHidden 关闭即卸载表单，重开按 initialValues 重建，无需 resetFields
      setPreview(null);
      setReason('');
    }
  }, [open, organizationIds]);

  const previewColumns = useMemo<ColumnsType<OrganizationPartyScopeBatchPreviewItem>>(
    () => [
      {
        title: '组织',
        key: 'organization',
        render: (_, item) => item.organization.name,
      },
      {
        title: '变更前有效范围',
        key: 'before_scope',
        render: (_, item) => formatScopeValue(item.before_scope),
      },
      {
        title: '变更后有效范围',
        key: 'after_scope',
        render: (_, item) => formatScopeValue(item.after_scope),
      },
      {
        title: '受影响组织',
        key: 'organizations',
        render: (_, item) =>
          `${item.impact.organization_scope_change_count} / ${item.impact.organization_count}`,
      },
      {
        title: '受影响用户',
        key: 'users',
        render: (_, item) => `${item.impact.user_scope_change_count} / ${item.impact.user_count}`,
      },
    ],
    []
  );

  const handlePreview = useCallback(
    async (values: BatchPartyScopeFormValues) => {
      if (organizations.length < 2) {
        MessageManager.error('请至少选择两个启用组织');
        return;
      }
      const representedPartyId = values.represented_party_id?.trim() ?? '';
      if (representedPartyId !== '' && values.represented_party_perspective == null) {
        MessageManager.error('请选择默认视角');
        return;
      }

      setIsPreviewing(true);
      try {
        const result = await organizationService.previewOrganizationPartyScopeBatch({
          items: organizations.map(organization => ({
            organization_id: organization.id,
            represented_party_id: representedPartyId !== '' ? representedPartyId : null,
            represented_party_perspective:
              representedPartyId !== '' ? (values.represented_party_perspective ?? null) : null,
          })),
        });
        setPreview(result);
        setReason('');
      } catch (error) {
        MessageManager.error(
          error instanceof Error ? error.message : '生成批量组织主体范围预览失败'
        );
      } finally {
        setIsPreviewing(false);
      }
    },
    [organizations]
  );

  const handleCommit = useCallback(async () => {
    if (preview == null) {
      return;
    }
    const normalizedReason = reason.trim();
    if (normalizedReason === '') {
      MessageManager.error('请输入变更原因');
      return;
    }

    setIsCommitting(true);
    try {
      const result = await organizationService.commitOrganizationPartyScopeBatch({
        preview_token: preview.preview_token,
        reason: normalizedReason,
        idempotency_key: createIdempotencyKey(),
      });
      MessageManager.success(
        result.idempotent ? '批量组织代表主体变更已确认' : '批量组织代表主体已更新'
      );
      await onChanged();
      onClose();
    } catch (error) {
      MessageManager.error(error instanceof Error ? error.message : '提交批量组织代表主体变更失败');
    } finally {
      setIsCommitting(false);
    }
  }, [onChanged, onClose, preview, reason]);

  const handleClose = useCallback(() => {
    if (!isCommitting) {
      onClose();
    }
  }, [isCommitting, onClose]);

  return (
    <Modal
      title="批量设置组织代表主体"
      open={open}
      onCancel={handleClose}
      footer={null}
      width={960}
      destroyOnHidden
    >
      {preview == null ? (
        <Form<BatchPartyScopeFormValues>
          form={form}
          layout="vertical"
          onFinish={values => void handlePreview(values)}
        >
          <Typography.Paragraph type="secondary">
            已选择 {organizations.length} 个启用组织。
          </Typography.Paragraph>
          <Form.Item name="represented_party_id" label="代表法人主体">
            <PartySelector
              allowClear
              placeholder="清空直接配置并继承上级组织"
              fetcher={fetchEligibleRepresentedParties}
            />
          </Form.Item>
          <Form.Item name="represented_party_perspective" label="默认视角">
            <Select
              aria-label="批量默认视角"
              options={[
                { label: '产权方', value: 'owner' },
                { label: '管理方', value: 'manager' },
              ]}
            />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button onClick={handleClose} disabled={isPreviewing}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={isPreviewing}>
                生成预览
              </Button>
            </Space>
          </Form.Item>
        </Form>
      ) : (
        <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          <Table<OrganizationPartyScopeBatchPreviewItem>
            rowKey={item => item.organization.id}
            columns={previewColumns}
            dataSource={preview.items}
            pagination={false}
            size="small"
            scroll={{ x: 800 }}
          />
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="受影响组织">
              {preview.impact.organization_scope_change_count} / {preview.impact.organization_count}
            </Descriptions.Item>
            <Descriptions.Item label="受影响用户">
              {preview.impact.user_scope_change_count} / {preview.impact.user_count}
            </Descriptions.Item>
          </Descriptions>
          <Input.TextArea
            aria-label="批量变更原因"
            value={reason}
            onChange={event => setReason(event.target.value)}
            placeholder="请输入变更原因"
            maxLength={500}
            showCount
            rows={3}
          />
          <Space>
            <Button
              onClick={() => {
                if (!isCommitting) {
                  setPreview(null);
                  setReason('');
                }
              }}
              disabled={isCommitting}
            >
              返回修改
            </Button>
            <Button type="primary" onClick={() => void handleCommit()} loading={isCommitting}>
              提交变更
            </Button>
          </Space>
        </Space>
      )}
    </Modal>
  );
};

export default OrganizationPartyScopeBatchModal;
