import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Tag,
  Typography,
} from 'antd';
import dayjs from 'dayjs';
import { useNavigate, useParams } from 'react-router-dom';
import PageContainer from '@/components/Common/PageContainer';
import { SYSTEM_ROUTES } from '@/constants/routes';
import {
  partyService,
  type PartyReviewRejectPayload,
  type PartyReviewLog,
  type PartyUpdatePayload,
} from '@/services/partyService';
import type { Party, PartyReviewStatus, PartyType } from '@/types/party';
import { MessageManager } from '@/utils/messageManager';

const PARTY_TYPE_OPTIONS: Array<{ label: string; value: PartyType }> = [
  { label: '组织', value: 'organization' },
  { label: '法人主体', value: 'legal_entity' },
  { label: '自然人', value: 'individual' },
];

const CUSTOMER_TYPE_OPTIONS = [
  { label: '外部', value: 'external' },
  { label: '内部', value: 'internal' },
] as const;

const SUBJECT_NATURE_OPTIONS = [
  { label: '企业', value: 'enterprise' },
  { label: '个人', value: 'individual' },
] as const;

const IDENTIFIER_TYPE_OPTIONS = [
  { label: '统一社会信用代码', value: 'USCC' },
  { label: '身份证', value: 'CN_ID_CARD' },
  { label: '护照', value: 'PASSPORT' },
  { label: '其他证件', value: 'OTHER_GOV_ID' },
] as const;

const PARTY_TYPE_LABELS: Record<PartyType, string> = {
  organization: '组织',
  legal_entity: '法人主体',
  individual: '自然人',
};

const REVIEW_STATUS_META: Record<PartyReviewStatus, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  pending: { color: 'processing', label: '待审核' },
  approved: { color: 'success', label: '已审核' },
  reversed: { color: 'warning', label: '已反审核' },
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

const PartyDetailPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<Record<string, unknown>>();
  const [rejectForm] = Form.useForm<PartyReviewRejectPayload>();
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
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
  const reviewStatus = party?.review_status ?? 'draft';
  const isDraft = reviewStatus === 'draft';
  const isPending = reviewStatus === 'pending';
  const isEditable = isDraft;

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
      status: party.status,
      metadata: metadata,
      customer_type: normalizeOptionalText(metadata.customer_type),
      subject_nature: normalizeOptionalText(metadata.subject_nature),
      identifier_type: normalizeOptionalText(metadata.identifier_type),
      unified_identifier: normalizeOptionalText(metadata.unified_identifier),
      address: normalizeOptionalText(metadata.address),
      payment_term_preference: normalizeOptionalText(metadata.payment_term_preference),
      contact_name: normalizeOptionalText(metadata.contact_name),
      contact_phone: normalizeOptionalText(metadata.contact_phone),
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
      MessageManager.success('主体已驳回回草稿');
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '驳回审核失败');
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
      ...(normalizeOptionalText(values.identifier_type) != null
        ? { identifier_type: normalizeOptionalText(values.identifier_type) }
        : { identifier_type: undefined }),
      ...(normalizeOptionalText(values.unified_identifier) != null
        ? { unified_identifier: normalizeOptionalText(values.unified_identifier) }
        : { unified_identifier: undefined }),
      ...(normalizeOptionalText(values.address) != null
        ? { address: normalizeOptionalText(values.address) }
        : { address: undefined }),
      ...(normalizeOptionalText(values.payment_term_preference) != null
        ? { payment_term_preference: normalizeOptionalText(values.payment_term_preference) }
        : { payment_term_preference: undefined }),
      ...(normalizeOptionalText(values.contact_name) != null
        ? { contact_name: normalizeOptionalText(values.contact_name) }
        : { contact_name: undefined }),
      ...(normalizeOptionalText(values.contact_phone) != null
        ? { contact_phone: normalizeOptionalText(values.contact_phone) }
        : { contact_phone: undefined }),
      ...(parseRiskTags(values.risk_tags_text) != null
        ? { risk_tags: parseRiskTags(values.risk_tags_text) }
        : { risk_tags: undefined }),
    };

    updateMutation.mutate({
      party_type: normalizedPartyType,
      name: normalizeOptionalText(values.name),
      code: normalizeOptionalText(values.code),
      external_ref: normalizeOptionalText(values.external_ref) ?? null,
      status: normalizeOptionalText(values.status),
      metadata: nextMetadata,
    });
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
          {isDraft ? (
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
        </Space>

        {!hasPartyId ? <Alert type="error" title="缺少主体 ID，无法加载详情" showIcon /> : null}
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
              label="主体编码"
              name="code"
              rules={[{ required: true, message: '请输入主体编码' }]}
            >
              <Input aria-label="主体编码" />
            </Form.Item>
            <Form.Item
              label="主体类型"
              name="party_type"
              rules={[{ required: true, message: '请选择主体类型' }]}
            >
              <Select aria-label="主体类型" options={PARTY_TYPE_OPTIONS} />
            </Form.Item>
            <Form.Item label="业务状态" name="status">
              <Select
                aria-label="业务状态"
                options={[
                  { label: 'active', value: 'active' },
                  { label: 'inactive', value: 'inactive' },
                ]}
              />
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
              <Select aria-label="统一标识类型" options={IDENTIFIER_TYPE_OPTIONS as unknown as []} />
            </Form.Item>
            <Form.Item label="统一标识" name="unified_identifier">
              <Input aria-label="统一标识" />
            </Form.Item>
            <Form.Item label="联系人" name="contact_name">
              <Input aria-label="联系人" />
            </Form.Item>
            <Form.Item label="联系电话" name="contact_phone">
              <Input aria-label="联系电话" />
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
              <Typography.Text type="secondary">
                共 {reviewLogQuery.data.length} 条
              </Typography.Text>
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
