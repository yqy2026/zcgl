import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import type {
  Organization,
  OrganizationPartyPerspective,
  OrganizationPartyScopePreview,
  OrganizationPartyScopeState,
} from '@/types/organization';
import type { Party } from '@/types/party';
import { type User, userService } from '@/services/systemService';
import { organizationService } from '@/services/organizationService';
import { partyService } from '@/services/partyService';
import PartySelector, { type PartySelectorFilterMode } from '@/components/Common/PartySelector';
import UserPartyBindingModal from '@/pages/System/UserManagement/components/UserPartyBindingModal';
import { MessageManager } from '@/utils/messageManager';

interface OrganizationBindingDrawerProps {
  open: boolean;
  organization: Organization | null;
  onClose: () => void;
}

interface RepresentedPartyFormValues {
  represented_party_id?: string;
  represented_party_perspective: OrganizationPartyPerspective;
}

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

const createIdempotencyKey = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `organization-party-scope-${Date.now()}-${Math.random().toString(36).slice(2)}`;
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

const OrganizationBindingDrawer: React.FC<OrganizationBindingDrawerProps> = ({
  open,
  organization,
  onClose,
}) => {
  const [bindingUser, setBindingUser] = useState<User | null>(null);
  const [bindingModalVisible, setBindingModalVisible] = useState(false);
  const [savingRepresentedParty, setSavingRepresentedParty] = useState(false);
  const [committingRepresentedParty, setCommittingRepresentedParty] = useState(false);
  const [scopePreview, setScopePreview] = useState<OrganizationPartyScopePreview | null>(null);
  const [scopeReason, setScopeReason] = useState('');
  const [representedPartyForm] = Form.useForm<RepresentedPartyFormValues>();

  useEffect(() => {
    if (!open || organization == null) {
      return;
    }
    representedPartyForm.setFieldsValue({
      represented_party_id: organization.represented_party_id ?? undefined,
      represented_party_perspective: organization.represented_party_perspective ?? 'owner',
    });
  }, [open, organization, representedPartyForm]);

  const handleSaveRepresentedParty = useCallback(
    async (values: RepresentedPartyFormValues) => {
      if (organization == null) {
        return;
      }
      const representedPartyId = values.represented_party_id?.trim() ?? '';
      setSavingRepresentedParty(true);
      try {
        const preview = await organizationService.previewOrganizationPartyScope(organization.id, {
          represented_party_id: representedPartyId !== '' ? representedPartyId : null,
          represented_party_perspective:
            representedPartyId !== '' ? values.represented_party_perspective : null,
        });
        setScopePreview(preview);
        setScopeReason('');
      } catch (error) {
        MessageManager.error(error instanceof Error ? error.message : '生成组织主体范围预览失败');
      } finally {
        setSavingRepresentedParty(false);
      }
    },
    [organization]
  );

  const handleCommitRepresentedParty = useCallback(async () => {
    if (organization == null || scopePreview == null) {
      return;
    }
    const reason = scopeReason.trim();
    if (reason === '') {
      MessageManager.error('请输入变更原因');
      return;
    }

    setCommittingRepresentedParty(true);
    try {
      const result = await organizationService.commitOrganizationPartyScope(organization.id, {
        preview_token: scopePreview.preview_token,
        reason,
        idempotency_key: createIdempotencyKey(),
      });
      representedPartyForm.setFieldsValue({
        represented_party_id: result.organization.represented_party_id ?? undefined,
        represented_party_perspective: result.organization.represented_party_perspective ?? 'owner',
      });
      setScopePreview(null);
      setScopeReason('');
      MessageManager.success(result.idempotent ? '组织代表主体变更已确认' : '组织代表主体已更新');
    } catch (error) {
      MessageManager.error(error instanceof Error ? error.message : '提交组织代表主体变更失败');
    } finally {
      setCommittingRepresentedParty(false);
    }
  }, [organization, representedPartyForm, scopePreview, scopeReason]);

  const usersQuery = useQuery({
    queryKey: ['organization-binding-users', organization?.id],
    queryFn: async () => {
      if (organization == null) {
        return [];
      }
      const result = await userService.getUsers({
        organization_id: organization.id,
        page_size: 100,
      });
      return result.items ?? [];
    },
    enabled: open && organization != null,
  });

  const columns = useMemo<ColumnsType<User>>(
    () => [
      {
        title: '用户',
        key: 'user',
        render: (_, record) => (
          <div>
            <Typography.Text strong>{record.full_name}</Typography.Text>
            <div>{record.username}</div>
          </div>
        ),
      },
      {
        title: '角色',
        key: 'roles',
        render: (_, record) => {
          const roleLabels = record.roles ?? [];
          if (roleLabels.length === 0) {
            return <Tag>未分配</Tag>;
          }
          return (
            <Space size={[4, 4]} wrap>
              {roleLabels.map(roleLabel => (
                <Tag key={roleLabel}>{roleLabel}</Tag>
              ))}
            </Space>
          );
        },
      },
      {
        title: '操作',
        key: 'actions',
        render: (_, record) => (
          <Button
            type="link"
            onClick={() => {
              setBindingUser(record);
              setBindingModalVisible(true);
            }}
            aria-label={`管理 ${record.full_name} 用户数据范围`}
          >
            管理用户数据范围
          </Button>
        ),
      },
    ],
    []
  );

  const users = usersQuery.data ?? [];

  return (
    <>
      <Drawer
        title={organization != null ? `${organization.name} · 数据范围配置` : '数据范围配置'}
        placement="right"
        size="large"
        open={open}
        onClose={onClose}
      >
        <Typography.Title level={5}>组织代表主体</Typography.Title>
        <Typography.Paragraph type="secondary">
          直接配置仅允许已审核且启用的法人主体；未配置时由系统解析最近的有效上级配置。
        </Typography.Paragraph>
        <Form<RepresentedPartyFormValues>
          form={representedPartyForm}
          layout="vertical"
          onFinish={values => void handleSaveRepresentedParty(values)}
        >
          <Form.Item name="represented_party_id" label="代表法人主体">
            <PartySelector
              allowClear
              placeholder="未配置时继承上级组织"
              fetcher={fetchEligibleRepresentedParties}
            />
          </Form.Item>
          <Form.Item
            name="represented_party_perspective"
            label="默认视角"
            rules={[{ required: true, message: '请选择默认视角' }]}
          >
            <Select
              aria-label="默认视角"
              options={[
                { label: '产权方', value: 'owner' },
                { label: '管理方', value: 'manager' },
              ]}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={savingRepresentedParty}>
              保存代表主体
            </Button>
          </Form.Item>
        </Form>

        <Typography.Title level={5}>组织用户数据范围</Typography.Title>
        {users.length === 0 && !usersQuery.isLoading ? (
          <Empty description="该组织下暂无用户" />
        ) : (
          <Table<User>
            rowKey="id"
            loading={usersQuery.isLoading}
            columns={columns}
            dataSource={users}
            pagination={false}
          />
        )}
      </Drawer>

      <Modal
        title="确认组织代表主体变更"
        open={scopePreview != null}
        onCancel={() => {
          if (committingRepresentedParty) {
            return;
          }
          setScopePreview(null);
          setScopeReason('');
        }}
        onOk={() => void handleCommitRepresentedParty()}
        okText="提交变更"
        cancelText="返回修改"
        confirmLoading={committingRepresentedParty}
        okButtonProps={{ disabled: scopeReason.trim() === '' }}
      >
        {scopePreview != null ? (
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="变更前有效范围">
                {formatScopeValue(scopePreview.before_scope)}
              </Descriptions.Item>
              <Descriptions.Item label="变更后有效范围">
                {formatScopeValue(scopePreview.after_scope)}
              </Descriptions.Item>
              <Descriptions.Item label="受影响组织">
                {scopePreview.impact.organization_scope_change_count} /{' '}
                {scopePreview.impact.organization_count}
              </Descriptions.Item>
              <Descriptions.Item label="受影响用户">
                {scopePreview.impact.user_scope_change_count} / {scopePreview.impact.user_count}
              </Descriptions.Item>
            </Descriptions>
            <Input.TextArea
              aria-label="变更原因"
              value={scopeReason}
              onChange={event => setScopeReason(event.target.value)}
              placeholder="请输入变更原因"
              maxLength={500}
              showCount
              rows={3}
            />
          </Space>
        ) : null}
      </Modal>

      <UserPartyBindingModal
        open={bindingModalVisible}
        user={bindingUser}
        onClose={() => {
          setBindingModalVisible(false);
          setBindingUser(null);
        }}
        onChanged={async () => {
          await usersQuery.refetch();
        }}
      />
    </>
  );
};

export default OrganizationBindingDrawer;
