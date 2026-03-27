import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Input, Space, Spin, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import { CONTRACT_GROUP_ROUTES } from '@/constants/routes';
import { contractGroupService } from '@/services/contractGroupService';
import type {
  ContractGroupCreate,
  ContractGroupDetail,
  ContractGroupUpdate,
  RevenueMode,
  SettlementRule,
} from '@/types/contractGroup';

type EditableFormState = {
  revenue_mode: RevenueMode;
  operator_party_id: string;
  owner_party_id: string;
  effective_from: string;
  effective_to: string;
  settlement_version: string;
  settlement_cycle: string;
  settlement_mode: string;
  amount_rule_json: string;
  payment_rule_json: string;
  revenue_attribution_rule_json: string;
  revenue_share_rule_json: string;
  risk_tags: string;
  predecessor_group_id: string;
  asset_ids: string;
};

const EMPTY_FORM: EditableFormState = {
  revenue_mode: 'LEASE',
  operator_party_id: '',
  owner_party_id: '',
  effective_from: '',
  effective_to: '',
  settlement_version: '',
  settlement_cycle: '月付',
  settlement_mode: '',
  amount_rule_json: '',
  payment_rule_json: '',
  revenue_attribution_rule_json: '',
  revenue_share_rule_json: '',
  risk_tags: '',
  predecessor_group_id: '',
  asset_ids: '',
};

const parseJsonField = (value: string, label: string): Record<string, unknown> | undefined => {
  const normalized = value.trim();
  if (normalized === '') {
    return undefined;
  }

  try {
    const parsed = JSON.parse(normalized) as unknown;
    if (parsed == null || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error(`${label} 必须是 JSON 对象`);
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    throw new Error(
      error instanceof Error && error.message.includes('必须是 JSON 对象')
        ? error.message
        : `${label} 不是合法 JSON`
    );
  }
};

const parseRiskTags = (value: string): string[] | undefined => {
  const tags = value
    .split(',')
    .map(item => item.trim())
    .filter(item => item !== '');

  return tags.length > 0 ? tags : undefined;
};

const parseAssetIds = (value: string): string[] =>
  value
    .split(',')
    .map(item => item.trim())
    .filter(item => item !== '');

const buildSettlementRule = (state: EditableFormState): SettlementRule => ({
  version: state.settlement_version.trim(),
  cycle: state.settlement_cycle,
  settlement_mode: state.settlement_mode.trim(),
  amount_rule: parseJsonField(state.amount_rule_json, '金额规则 JSON') ?? {},
  payment_rule: parseJsonField(state.payment_rule_json, '支付规则 JSON') ?? {},
});

const mapDetailToFormState = (detail: ContractGroupDetail): EditableFormState => ({
  revenue_mode: detail.revenue_mode,
  operator_party_id: detail.operator_party_id,
  owner_party_id: detail.owner_party_id,
  effective_from: detail.effective_from,
  effective_to: detail.effective_to ?? '',
  settlement_version: detail.settlement_rule.version,
  settlement_cycle: detail.settlement_rule.cycle,
  settlement_mode: detail.settlement_rule.settlement_mode,
  amount_rule_json: JSON.stringify(detail.settlement_rule.amount_rule, null, 2),
  payment_rule_json: JSON.stringify(detail.settlement_rule.payment_rule, null, 2),
  revenue_attribution_rule_json:
    detail.revenue_attribution_rule != null
      ? JSON.stringify(detail.revenue_attribution_rule, null, 2)
      : '',
  revenue_share_rule_json:
    detail.revenue_share_rule != null ? JSON.stringify(detail.revenue_share_rule, null, 2) : '',
  risk_tags: detail.risk_tags?.join(', ') ?? '',
  predecessor_group_id: detail.predecessor_group_id ?? '',
  asset_ids: '',
});

const buildCreatePayload = (state: EditableFormState): ContractGroupCreate => {
  const revenueAttributionRule = parseJsonField(
    state.revenue_attribution_rule_json,
    '收益归属规则 JSON'
  );
  const revenueShareRule = parseJsonField(state.revenue_share_rule_json, '收益分成规则 JSON');
  const riskTags = parseRiskTags(state.risk_tags);

  return {
    revenue_mode: state.revenue_mode,
    operator_party_id: state.operator_party_id.trim(),
    owner_party_id: state.owner_party_id.trim(),
    effective_from: state.effective_from.trim(),
    ...(state.effective_to.trim() !== '' ? { effective_to: state.effective_to.trim() } : {}),
    settlement_rule: buildSettlementRule(state),
    ...(revenueAttributionRule != null ? { revenue_attribution_rule: revenueAttributionRule } : {}),
    ...(revenueShareRule != null ? { revenue_share_rule: revenueShareRule } : {}),
    ...(riskTags != null ? { risk_tags: riskTags } : {}),
    ...(state.predecessor_group_id.trim() !== ''
      ? { predecessor_group_id: state.predecessor_group_id.trim() }
      : {}),
    asset_ids: parseAssetIds(state.asset_ids),
  };
};

const buildUpdatePayload = (state: EditableFormState): ContractGroupUpdate => ({
  effective_to: state.effective_to.trim() !== '' ? state.effective_to.trim() : null,
  settlement_rule: buildSettlementRule(state),
  revenue_attribution_rule:
    parseJsonField(state.revenue_attribution_rule_json, '收益归属规则 JSON') ?? null,
  revenue_share_rule: parseJsonField(state.revenue_share_rule_json, '收益分成规则 JSON') ?? null,
  risk_tags: parseRiskTags(state.risk_tags) ?? null,
});

const LabeledInput: React.FC<{
  label: string;
  value: string;
  disabled?: boolean;
  multiline?: boolean;
  onChange: (value: string) => void;
}> = ({ label, value, disabled = false, multiline = false, onChange }) => (
  <label>
    <Typography.Text strong>{label}</Typography.Text>
    {multiline ? (
      <Input.TextArea
        aria-label={label}
        value={value}
        disabled={disabled}
        rows={4}
        onChange={event => onChange(event.target.value)}
      />
    ) : (
      <Input
        aria-label={label}
        value={value}
        disabled={disabled}
        onChange={event => onChange(event.target.value)}
      />
    )}
  </label>
);

const LabeledSelect: React.FC<{
  label: string;
  value: string;
  disabled?: boolean;
  options: Array<{ label: string; value: string }>;
  onChange: (value: string) => void;
}> = ({ label, value, disabled = false, options, onChange }) => (
  <label>
    <Typography.Text strong>{label}</Typography.Text>
    <select
      aria-label={label}
      value={value}
      disabled={disabled}
      onChange={event => onChange(event.target.value)}
    >
      {options.map(option => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  </label>
);

const ContractGroupFormPage: React.FC = () => {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const isEditMode = id != null && id.length > 0;
  const [formState, setFormState] = useState<EditableFormState>(EMPTY_FORM);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['contract-group-form-detail', id],
    queryFn: () => contractGroupService.getContractGroup(id as string),
    enabled: isEditMode,
  });

  useEffect(() => {
    if (data != null) {
      setFormState(mapDetailToFormState(data));
    }
  }, [data]);

  const submitLabel = useMemo(() => (isEditMode ? '保存修改' : '创建合同组'), [isEditMode]);

  const updateField = <T extends keyof EditableFormState>(key: T, value: EditableFormState[T]) => {
    setFormState(current => ({
      ...current,
      [key]: value,
    }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    setIsSubmitting(true);

    try {
      if (isEditMode) {
        await contractGroupService.updateContractGroup(id as string, buildUpdatePayload(formState));
        navigate(CONTRACT_GROUP_ROUTES.DETAIL(id as string));
      } else {
        const created = await contractGroupService.createContractGroup(
          buildCreatePayload(formState)
        );
        navigate(CONTRACT_GROUP_ROUTES.DETAIL(created.contract_group_id));
      }
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : '提交失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageContainer
      title={isEditMode ? '编辑合同组' : '新建合同组'}
      subTitle="当前表单直接贴合后端 schema；主体、日期和规则 JSON 都按原始字段提交。"
      onBack={() =>
        navigate(
          isEditMode ? CONTRACT_GROUP_ROUTES.DETAIL(id as string) : CONTRACT_GROUP_ROUTES.LIST
        )
      }
    >
      {error != null && (
        <Alert
          type="error"
          showIcon
          title={isEditMode ? '合同组详情加载失败' : '表单初始化失败'}
          description={error instanceof Error ? error.message : '未知错误'}
        />
      )}

      {isEditMode && isLoading ? (
        <Spin />
      ) : (
        <form onSubmit={handleSubmit}>
          <Space orientation="vertical" size={16}>
            {isEditMode && (
              <Alert
                type="info"
                showIcon
                title="编辑页当前只开放后端允许修改的字段"
                description="经营模式、主体关系、开始日期和资产关联暂不在该页修改，避免前端凭空拼装缺失字段。"
              />
            )}

            {submitError != null && <Alert type="error" showIcon title={submitError} />}

            <Card title="基础信息">
              <Space orientation="vertical" size={12}>
                <LabeledSelect
                  label="经营模式"
                  value={formState.revenue_mode}
                  disabled={isEditMode}
                  options={[
                    { label: 'LEASE', value: 'LEASE' },
                    { label: 'AGENCY', value: 'AGENCY' },
                  ]}
                  onChange={value => updateField('revenue_mode', value as RevenueMode)}
                />
                <LabeledInput
                  label="运营方主体 ID"
                  value={formState.operator_party_id}
                  disabled={isEditMode}
                  onChange={value => updateField('operator_party_id', value)}
                />
                <LabeledInput
                  label="产权方主体 ID"
                  value={formState.owner_party_id}
                  disabled={isEditMode}
                  onChange={value => updateField('owner_party_id', value)}
                />
                <LabeledInput
                  label="开始日期"
                  value={formState.effective_from}
                  disabled={isEditMode}
                  onChange={value => updateField('effective_from', value)}
                />
                <LabeledInput
                  label="结束日期"
                  value={formState.effective_to}
                  onChange={value => updateField('effective_to', value)}
                />
                {!isEditMode && (
                  <>
                    <LabeledInput
                      label="前驱合同组 ID"
                      value={formState.predecessor_group_id}
                      onChange={value => updateField('predecessor_group_id', value)}
                    />
                    <LabeledInput
                      label="关联资产 ID"
                      value={formState.asset_ids}
                      onChange={value => updateField('asset_ids', value)}
                    />
                  </>
                )}
              </Space>
            </Card>

            <Card title="结算规则">
              <Space orientation="vertical" size={12}>
                <LabeledInput
                  label="规则版本"
                  value={formState.settlement_version}
                  onChange={value => updateField('settlement_version', value)}
                />
                <LabeledSelect
                  label="结算周期"
                  value={formState.settlement_cycle}
                  options={[
                    { label: '月付', value: '月付' },
                    { label: '季付', value: '季付' },
                    { label: '半年付', value: '半年付' },
                    { label: '年付', value: '年付' },
                  ]}
                  onChange={value => updateField('settlement_cycle', value)}
                />
                <LabeledInput
                  label="结算模式"
                  value={formState.settlement_mode}
                  onChange={value => updateField('settlement_mode', value)}
                />
                <LabeledInput
                  label="金额规则 JSON"
                  value={formState.amount_rule_json}
                  multiline
                  onChange={value => updateField('amount_rule_json', value)}
                />
                <LabeledInput
                  label="支付规则 JSON"
                  value={formState.payment_rule_json}
                  multiline
                  onChange={value => updateField('payment_rule_json', value)}
                />
              </Space>
            </Card>

            <Card title="扩展配置">
              <Space orientation="vertical" size={12}>
                <LabeledInput
                  label="收益归属规则 JSON"
                  value={formState.revenue_attribution_rule_json}
                  multiline
                  onChange={value => updateField('revenue_attribution_rule_json', value)}
                />
                <LabeledInput
                  label="收益分成规则 JSON"
                  value={formState.revenue_share_rule_json}
                  multiline
                  onChange={value => updateField('revenue_share_rule_json', value)}
                />
                <LabeledInput
                  label="风险标签"
                  value={formState.risk_tags}
                  onChange={value => updateField('risk_tags', value)}
                />
                {isEditMode &&
                  data != null &&
                  data.predecessor_group_id != null &&
                  data.predecessor_group_id !== '' && (
                    <Tag>前驱合同组：{data.predecessor_group_id}</Tag>
                  )}
              </Space>
            </Card>

            <Space>
              <Button htmlType="submit" type="primary" loading={isSubmitting}>
                {submitLabel}
              </Button>
              <Button onClick={() => navigate(CONTRACT_GROUP_ROUTES.LIST)}>返回列表</Button>
            </Space>
          </Space>
        </form>
      )}
    </PageContainer>
  );
};

export default ContractGroupFormPage;
