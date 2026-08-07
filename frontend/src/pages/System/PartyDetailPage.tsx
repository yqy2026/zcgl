import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Descriptions,
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
import dayjs from 'dayjs';
import { useNavigate, useParams } from 'react-router-dom';
import PageContainer from '@/components/Common/PageContainer';
import { SYSTEM_ROUTES } from '@/constants/routes';
import {
  getPartyIdentifierTypeOptions,
  PARTY_IDENTIFIER_TYPE_LABELS,
  PARTY_TYPE_LABELS,
  PARTY_TYPE_OPTIONS,
} from '@/constants/party';
import {
  partyService,
  type PartyReviewRejectPayload,
  type PartyReviewLog,
  type PartyUpdatePayload,
  type RepresentingOrganizationItem,
} from '@/services/partyService';
import type {
  Party,
  PartyLifecycleOperation,
  PartyLifecyclePreviewResponse,
  PartyReviewStatus,
  PartyType,
} from '@/types/party';
import { MessageManager } from '@/utils/messageManager';

const CUSTOMER_TYPE_OPTIONS = [
  { label: '外部', value: 'external' },
  { label: '内部', value: 'internal' },
] as const;

const SUBJECT_NATURE_OPTIONS = [
  { label: '企业', value: 'enterprise' },
  { label: '个人', value: 'individual' },
] as const;

const REVIEW_STATUS_META: Record<PartyReviewStatus, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  pending: { color: 'processing', label: '待审核' },
  approved: { color: 'success', label: '已审核' },
  rejected: { color: 'warning', label: '已驳回' },
};

const renderReviewStatus = (
  reviewStatus: PartyReviewStatus | null | undefined
): React.ReactNode => {
  const resolvedStatus = reviewStatus ?? 'draft';
  const meta = REVIEW_STATUS_META[resolvedStatus];
  return <Tag color={meta.color}>{meta.label}</Tag>;
};

const formatDateTime = (value: string | null | undefined): string => {
  if (value == null || value.trim() === '') {
    return '-';
  }
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm:ss') : value;
};

const normalizeOptionalText = (value: unknown): string | undefined => {
  if (value == null) {
    return undefined;
  }
  const normalized = String(value).trim();
  return normalized !== '' ? normalized : undefined;
};

const parseRiskTags = (value: unknown): string[] | undefined => {
  const normalized = normalizeOptionalText(value);
  if (normalized == null) {
    return undefined;
  }
  const tags = normalized
    .split(/[，,]/)
    .map(tag => tag.trim())
    .filter(tag => tag !== '');
  return tags.length > 0 ? Array.from(new Set(tags)) : undefined;
};

interface PendingPartyLifecycleChange {
  operation: PartyLifecycleOperation;
  preview: PartyLifecyclePreviewResponse;
  idempotencyKey: string;
}

const createIdempotencyKey = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'party-lifecycle-' + Date.now() + '-' + Math.random().toString(36).slice(2);
};
const PartyDetailPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<Record<string, unknown>>();
  const editedPartyType = Form.useWatch('party_type', form) as PartyType | undefined;
  const [rejectForm] = Form.useForm<PartyReviewRejectPayload>();
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [pendingLifecycleChange, setPendingLifecycleChange] =
    useState<PendingPartyLifecycleChange | null>(null);
  const [lifecycleReason, setLifecycleReason] = useState('');
  const [lifecycleReasonError, setLifecycleReasonError] = useState(false);
  const params = useParams<{ id: string }>();
  const partyId = params.id?.trim() ?? '';
  const hasPartyId = partyId !== '';

  const partyDetailQuery = useQuery<Party>({
    queryKey: ['system-party-detail', partyId],
    queryFn: async () => {
      return await partyService.getPartyById(partyId);
    },
    enabled: hasPartyId,
    staleTime: 60 * 1000,
  });

  const party = partyDetailQuery.data;
  const reviewLogQuery = useQuery<PartyReviewLog[]>({
    queryKey: ['system-party-review-logs', partyId],
    queryFn: async () => {
      return await partyService.getReviewLogs(partyId);
    },
    enabled: hasPartyId,
    staleTime: 60 * 1000,
  });
  const representingOrgQuery = useQuery<RepresentingOrganizationItem[]>({
    queryKey: ['system-party-representing-organizations', partyId],
    queryFn: async () => {
      return await partyService.getRepresentingOrganizations(partyId);
    },
    enabled: hasPartyId,
    staleTime: 60 * 1000,
  });
  const representingOrganizations = representingOrgQuery.data ?? [];
  const reviewStatus = party?.review_status ?? 'draft';
  const isDraft = reviewStatus === 'draft';
  const isPending = reviewStatus === 'pending';
  const isEditable = isDraft || reviewStatus === 'rejected';

  useEffect(() => {
    if (party == null) {
      return;
    }

    const metadata = party.metadata ?? {};

    form.setFieldsValue({
      party_type: party.party_type,
      name: party.name,
      code: party.code,
      external_ref: party.external_ref ?? undefined,
      metadata: metadata,
      customer_type: normalizeOptionalText(metadata.customer_type),
      subject_nature: normalizeOptionalText(metadata.subject_nature),
      identifier_type: party.identifier_type ?? undefined,
      identifier_value: undefined,
      address: normalizeOptionalText(metadata.address),
      payment_term_preference: normalizeOptionalText(metadata.payment_term_preference),
      risk_tags_text: Array.isArray(metadata.risk_tags) ? metadata.risk_tags.join(', ') : undefined,
    });
  }, [form, party]);

  const syncPartyCaches = async (updatedParty: Party): Promise<void> => {
    queryClient.setQueryData(['system-party-detail', updatedParty.id], updatedParty);
    await queryClient.invalidateQueries({ queryKey: ['system-party-list'] });
  };

  const updateMutation = useMutation({
    mutationFn: async (payload: PartyUpdatePayload) => {
      return await partyService.updateParty(partyId, payload);
    },
    onSuccess: async updatedParty => {
      await syncPartyCaches(updatedParty);
      MessageManager.success('主体信息已更新');
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '更新主体失败');
    },
  });

  const submitReviewMutation = useMutation({
    mutationFn: async () => {
      return await partyService.submitReview(partyId);
    },
    onSuccess: async updatedParty => {
      await syncPartyCaches(updatedParty);
      MessageManager.success('主体已提交审核');
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '提交审核失败');
    },
  });

  const approveReviewMutation = useMutation({
    mutationFn: async () => {
      return await partyService.approveReview(partyId);
    },
    onSuccess: async updatedParty => {
      await syncPartyCaches(updatedParty);
      MessageManager.success('主体审核已通过');
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '审核通过失败');
    },
  });

  const rejectReviewMutation = useMutation({
    mutationFn: async (payload: PartyReviewRejectPayload) => {
      return await partyService.rejectReview(partyId, payload);
    },
    onSuccess: async updatedParty => {
      await syncPartyCaches(updatedParty);
      setRejectModalOpen(false);
      rejectForm.resetFields();
      MessageManager.success('主体已驳回');
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '驳回审核失败');
    },
  });

  const lifecyclePreviewMutation = useMutation({
    mutationFn: async (operation: PartyLifecycleOperation) => {
      return await partyService.previewLifecycle(partyId, { operation });
    },
    onSuccess: preview => {
      setPendingLifecycleChange({
        operation: preview.operation,
        preview,
        idempotencyKey: createIdempotencyKey(),
      });
      setLifecycleReason('');
      setLifecycleReasonError(false);
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '预览主体状态变更失败');
    },
  });

  const lifecycleCommitMutation = useMutation({
    mutationFn: async () => {
      if (pendingLifecycleChange == null) {
        throw new Error('主体状态变更预览不存在');
      }

      const payload = {
        preview_token: pendingLifecycleChange.preview.preview_token,
        reason: lifecycleReason.trim(),
        idempotency_key: pendingLifecycleChange.idempotencyKey,
      };
      return pendingLifecycleChange.operation === 'deactivate'
        ? await partyService.deactivate(partyId, payload)
        : await partyService.reactivate(partyId, payload);
    },
    onSuccess: async result => {
      await syncPartyCaches(result.party);
      await queryClient.invalidateQueries({ queryKey: ['system-party-review-logs', partyId] });
      setPendingLifecycleChange(null);
      setLifecycleReason('');
      setLifecycleReasonError(false);
      MessageManager.success(result.operation === 'deactivate' ? '主体已停用' : '主体已重新启用');
    },
    onError: error => {
      MessageManager.error(
        error instanceof Error ? error.message : '提交主体状态变更失败，请重新预览后再提交'
      );
    },
  });
  const overviewItems = useMemo(
    () => [
      {
        key: 'party_type',
        label: '主体类型',
        children: party != null ? PARTY_TYPE_LABELS[party.party_type] : '-',
      },
      {
        key: 'code',
        label: '主体编码',
        children: party?.code ?? '-',
      },
      {
        key: 'identifier_type',
        label: '统一标识类型',
        children:
          party?.identifier_type != null
            ? PARTY_IDENTIFIER_TYPE_LABELS[party.identifier_type]
            : '-',
      },
      {
        key: 'identifier_display',
        label: '统一标识',
        children: party?.identifier_display ?? '-',
      },
      {
        key: 'status',
        label: '业务状态',
        children: party?.status ?? '-',
      },
      {
        key: 'review_status',
        label: '审核状态',
        children: renderReviewStatus(party?.review_status),
      },
      {
        key: 'review_by',
        label: '审核人',
        children: party?.review_by ?? '-',
      },
      {
        key: 'reviewed_at',
        label: '审核时间',
        children: formatDateTime(party?.reviewed_at),
      },
      {
        key: 'review_reason',
        label: '审核说明',
        children: party?.review_reason ?? '-',
      },
      {
        key: 'updated_at',
        label: '更新时间',
        children: formatDateTime(party?.updated_at),
      },
    ],
    [party]
  );

  const handleSave = async (): Promise<void> => {
    const values = await form.validateFields();
    const normalizedPartyType =
      typeof values.party_type === 'string' ? (values.party_type as PartyType) : undefined;
    const nextMetadata = {
      ...(party?.metadata ?? {}),
      ...(normalizeOptionalText(values.customer_type) != null
        ? { customer_type: normalizeOptionalText(values.customer_type) }
        : { customer_type: undefined }),
      ...(normalizeOptionalText(values.subject_nature) != null
        ? { subject_nature: normalizeOptionalText(values.subject_nature) }
        : { subject_nature: undefined }),
      ...(normalizeOptionalText(values.address) != null
        ? { address: normalizeOptionalText(values.address) }
        : { address: undefined }),
      ...(normalizeOptionalText(values.payment_term_preference) != null
        ? { payment_term_preference: normalizeOptionalText(values.payment_term_preference) }
        : { payment_term_preference: undefined }),
      ...(parseRiskTags(values.risk_tags_text) != null
        ? { risk_tags: parseRiskTags(values.risk_tags_text) }
        : { risk_tags: undefined }),
    };

    const identifierValue = normalizeOptionalText(values.identifier_value);
    const identifierType = normalizeOptionalText(values.identifier_type);
    if (
      identifierValue == null &&
      identifierType != null &&
      identifierType !== party?.identifier_type
    ) {
      MessageManager.error('变更统一标识类型时必须填写新的统一标识值');
      return;
    }
    if (identifierValue != null && identifierType == null) {
      MessageManager.error('填写统一标识值时必须选择统一标识类型');
      return;
    }

    updateMutation.mutate({
      party_type: normalizedPartyType,
      name: normalizeOptionalText(values.name),
      ...(identifierValue != null
        ? {
            identifier_type: identifierType as PartyUpdatePayload['identifier_type'],
            identifier_value: identifierValue,
          }
        : {}),
      external_ref: normalizeOptionalText(values.external_ref) ?? null,
      metadata: nextMetadata,
    });
  };

  const handleLifecycleCommit = (): void => {
    if (pendingLifecycleChange == null) {
      return;
    }

    if (lifecycleReason.trim() === '') {
      setLifecycleReasonError(true);
      return;
    }

    lifecycleCommitMutation.mutate();
  };
  const handleReject = async (): Promise<void> => {
    const values = await rejectForm.validateFields();
    rejectReviewMutation.mutate(values);
  };

  return (
    <PageContainer title="主体详情" subTitle="查看主体审核状态，并在草稿状态下维护业务字段">
      <Space orientation="vertical" size="large" style={{ width: '100%' }}>
        <Space>
          <Button
            onClick={() => {
              navigate(SYSTEM_ROUTES.PARTIES);
            }}
          >
            返回列表
          </Button>
          {isEditable ? (
            <>
              <Button
                type="primary"
                loading={updateMutation.isPending}
                onClick={() => {
                  void handleSave();
                }}
              >
                保存变更
              </Button>
              <Button
                loading={submitReviewMutation.isPending}
                onClick={() => {
                  submitReviewMutation.mutate();
                }}
              >
                提交审核
              </Button>
            </>
          ) : null}
          {isPending ? (
            <>
              <Button
                type="primary"
                loading={approveReviewMutation.isPending}
                onClick={() => {
                  approveReviewMutation.mutate();
                }}
              >
                审核通过
              </Button>
              <Button
                danger
                onClick={() => {
                  setRejectModalOpen(true);
                }}
              >
                驳回审核
              </Button>
            </>
          ) : null}
          {reviewStatus === 'approved' && party != null ? (
            party.status === 'active' ? (
              <Button
                danger
                loading={lifecyclePreviewMutation.isPending}
                onClick={() => {
                  lifecyclePreviewMutation.mutate('deactivate');
                }}
              >
                停用主体
              </Button>
            ) : (
              <Button
                loading={lifecyclePreviewMutation.isPending}
                onClick={() => {
                  lifecyclePreviewMutation.mutate('reactivate');
                }}
              >
                重新启用主体
              </Button>
            )
          ) : null}        </Space>

        {!hasPartyId ? <Alert type="error" title="缺少主体标识，无法加载详情" showIcon /> : null}
        {partyDetailQuery.isError ? (
          <Alert type="error" title={partyDetailQuery.error.message} showIcon />
        ) : null}
        {!isEditable && party != null ? (
          <Alert
            type={isPending ? 'warning' : 'info'}
            title={isPending ? '待审核主体不可编辑业务字段' : '已审核主体不可编辑业务字段'}
            showIcon
          />
        ) : null}
        {party?.review_reason != null && party.review_reason.trim() !== '' ? (
          <Alert type="info" title={`审核说明：${party.review_reason}`} showIcon />
        ) : null}

        <Card loading={partyDetailQuery.isLoading} title={party?.name ?? '主体详情'}>
          <Descriptions column={1} bordered items={overviewItems} />
        </Card>

        <Card
          title="代表组织（只读）"
          loading={representingOrgQuery.isLoading}
          extra={
            representingOrgQuery.data != null ? (
              <Typography.Text type="secondary">
                共 {representingOrganizations.length} 个组织直接代表该主体
              </Typography.Text>
            ) : null
          }
        >
          {representingOrganizations.length === 0 ? (
            <Empty description="暂无直接代表该主体的组织" />
          ) : (
            <Table<RepresentingOrganizationItem>
              rowKey="organization_id"
              size="small"
              pagination={false}
              dataSource={representingOrganizations}
              columns={[
                {
                  title: '组织名称',
                  dataIndex: 'name',
                  key: 'name',
                },
                {
                  title: '组织编码',
                  dataIndex: 'code',
                  key: 'code',
                },
                {
                  title: '层级',
                  dataIndex: 'level',
                  key: 'level',
                  width: 80,
                },
                {
                  title: '代表视角',
                  dataIndex: 'represented_party_perspective',
                  key: 'represented_party_perspective',
                  width: 120,
                  render: (perspective: string | null) =>
                    perspective === 'owner' ? (
                      <Tag color="blue">所有者</Tag>
                    ) : perspective === 'manager' ? (
                      <Tag color="green">管理者</Tag>
                    ) : (
                      <Typography.Text type="secondary">-</Typography.Text>
                    ),
                },
                {
                  title: '状态',
                  dataIndex: 'status',
                  key: 'status',
                  width: 100,
                  render: (status: string) =>
                    status === 'active' ? (
                      <Tag color="success">启用</Tag>
                    ) : (
                      <Tag>{status}</Tag>
                    ),
                },
              ]}
            />
          )}
        </Card>

        <Card title="业务信息">
          <Form<Record<string, unknown>> form={form} layout="vertical" disabled={!isEditable}>
            <Form.Item
              label="主体名称"
              name="name"
              rules={[{ required: true, message: '请输入主体名称' }]}
            >
              <Input aria-label="主体名称" />
            </Form.Item>
            <Form.Item
              label="主体类型"
              name="party_type"
              rules={[{ required: true, message: '请选择主体类型' }]}
            >
              <Select aria-label="主体类型" options={PARTY_TYPE_OPTIONS} />
            </Form.Item>
            <Form.Item label="外部引用" name="external_ref">
              <Input aria-label="外部引用" />
            </Form.Item>
            <Form.Item label="客户类型" name="customer_type">
              <Select aria-label="客户类型" options={CUSTOMER_TYPE_OPTIONS as unknown as []} />
            </Form.Item>
            <Form.Item label="主体性质" name="subject_nature">
              <Select aria-label="主体性质" options={SUBJECT_NATURE_OPTIONS as unknown as []} />
            </Form.Item>
            <Form.Item label="统一标识类型" name="identifier_type">
              <Select
                aria-label="统一标识类型"
                allowClear
                options={getPartyIdentifierTypeOptions(editedPartyType)}
              />
            </Form.Item>
            <Form.Item
              label="新的统一标识值"
              name="identifier_value"
              extra="留空表示不变；自然人标识保存后只显示脱敏值"
            >
              <Input aria-label="新的统一标识值" />
            </Form.Item>
            <Form.Item label="地址" name="address">
              <Input.TextArea aria-label="地址" rows={3} />
            </Form.Item>
            <Form.Item label="账期偏好" name="payment_term_preference">
              <Input aria-label="账期偏好" />
            </Form.Item>
            <Form.Item label="风险标签" name="risk_tags_text">
              <Input aria-label="风险标签" placeholder="多个标签请用逗号分隔" />
            </Form.Item>
            <Form.Item label="扩展元数据" shouldUpdate>
              <Typography.Paragraph type="secondary">
                当前元数据：{party?.metadata != null ? JSON.stringify(party.metadata) : '{}'}
              </Typography.Paragraph>
            </Form.Item>
          </Form>
        </Card>

        <Card
          title="审核与变更日志"
          loading={reviewLogQuery.isLoading}
          extra={
            reviewLogQuery.data != null ? (
              <Typography.Text type="secondary">共 {reviewLogQuery.data.length} 条</Typography.Text>
            ) : null
          }
        >
          <Space orientation="vertical" style={{ width: '100%' }}>
            {(reviewLogQuery.data ?? []).map(log => (
              <Card key={log.id} size="small">
                <Descriptions
                  column={1}
                  size="small"
                  items={[
                    { key: 'action', label: '动作', children: log.action },
                    {
                      key: 'status',
                      label: '状态流转',
                      children: `${log.from_status} -> ${log.to_status}`,
                    },
                    { key: 'operator', label: '操作人', children: log.operator ?? '-' },
                    { key: 'reason', label: '说明', children: log.reason ?? '-' },
                    {
                      key: 'created_at',
                      label: '时间',
                      children: formatDateTime(log.created_at),
                    },
                  ]}
                />
              </Card>
            ))}
            {!reviewLogQuery.isLoading && (reviewLogQuery.data ?? []).length === 0 ? (
              <Typography.Text type="secondary">暂无主体日志</Typography.Text>
            ) : null}
          </Space>
        </Card>
      </Space>

      <Modal
        title={
          pendingLifecycleChange?.operation === 'deactivate'
            ? '停用主体影响预览'
            : '重新启用主体影响预览'
        }
        open={pendingLifecycleChange != null}
        onCancel={() => {
          if (!lifecycleCommitMutation.isPending) {
            setPendingLifecycleChange(null);
            setLifecycleReason('');
            setLifecycleReasonError(false);
          }
        }}
        onOk={handleLifecycleCommit}
        okText={pendingLifecycleChange?.operation === 'deactivate' ? '确认停用' : '确认启用'}
        cancelText="取消"
        confirmLoading={lifecycleCommitMutation.isPending}
        okButtonProps={{ disabled: lifecycleReason.trim() === '' }}
        destroyOnHidden
      >
        {pendingLifecycleChange != null ? (
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            <Alert
              type="warning"
              showIcon
              title="提交后会立即影响新引用资格和相关用户的有效数据范围"
            />
            <Descriptions
              column={1}
              size="small"
              bordered
              items={[
                {
                  key: 'status_transition',
                  label: '状态变更',
                  children:
                    pendingLifecycleChange.preview.before_state.status +
                    ' -> ' +
                    pendingLifecycleChange.preview.after_state.status,
                },
                {
                  key: 'organization_impact',
                  label: '组织影响',
                  children:
                    '直接代表组织 ' +
                    pendingLifecycleChange.preview.impact.represented_organization_count +
                    ' 个；潜在受影响组织 ' +
                    pendingLifecycleChange.preview.impact.potentially_affected_organization_count +
                    ' 个',
                },
                {
                  key: 'user_scope_impact',
                  label: '用户范围影响',
                  children:
                    '有效绑定 ' +
                    pendingLifecycleChange.preview.impact.current_user_binding_count +
                    ' 条；范围变化用户 ' +
                    pendingLifecycleChange.preview.impact.user_scope_change_count +
                    ' 人',
                },
                {
                  key: 'business_reference_impact',
                  label: '业务引用',
                  children:
                    '资产 ' +
                    pendingLifecycleChange.preview.impact.asset_reference_count +
                    '；项目 ' +
                    pendingLifecycleChange.preview.impact.project_reference_count +
                    '；合同组 ' +
                    pendingLifecycleChange.preview.impact.contract_group_reference_count +
                    '；合同 ' +
                    pendingLifecycleChange.preview.impact.contract_reference_count,
                },
              ]}
            />
            <Form layout="vertical">
              <Form.Item
                label={pendingLifecycleChange.operation === 'deactivate' ? '停用原因' : '重新启用原因'}
                validateStatus={lifecycleReasonError ? 'error' : undefined}
                help={lifecycleReasonError ? '请输入本次状态变更的原因' : undefined}
              >
                <Input.TextArea
                  aria-label={
                    pendingLifecycleChange.operation === 'deactivate' ? '停用原因' : '重新启用原因'
                  }
                  rows={4}
                  value={lifecycleReason}
                  onChange={event => {
                    setLifecycleReason(event.target.value);
                    setLifecycleReasonError(false);
                  }}
                />
              </Form.Item>
            </Form>
          </Space>
        ) : null}
      </Modal>
      <Modal
        title="驳回主体审核"
        open={rejectModalOpen}
        onCancel={() => {
          setRejectModalOpen(false);
          rejectForm.resetFields();
        }}
        onOk={() => {
          void handleReject();
        }}
        okText="确认驳回"
        cancelText="取消"
        confirmLoading={rejectReviewMutation.isPending}
        destroyOnHidden
      >
        <Form<PartyReviewRejectPayload> form={rejectForm} layout="vertical">
          <Form.Item
            label="驳回原因"
            name="reason"
            rules={[{ required: true, message: '请输入驳回原因' }]}
          >
            <Input.TextArea aria-label="驳回原因" rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default PartyDetailPage;
