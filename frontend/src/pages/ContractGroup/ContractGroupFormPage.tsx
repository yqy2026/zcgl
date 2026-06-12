import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Input, Space, Spin, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import { CONTRACT_CENTER_ROUTES, PROJECT_ROUTES } from '@/constants/routes';
import { contractGroupService } from '@/services/contractGroupService';
import { partyService } from '@/services/partyService';
import { projectService } from '@/services/projectService';
import type {
  ContractGroupCreate,
  ContractGroupDetail,
  ContractGroupUpdate,
  RevenueMode,
  SettlementRule,
} from '@/types/contractGroup';
import type { Asset } from '@/types/asset';
import type { Party } from '@/types/party';

type EditableFormState = {
  revenue_mode: RevenueMode;
  operator_party_id: string;
  owner_party_id: string;
  effective_from: string;
  effective_to: string;
  settlement_version: string;
  settlement_cycle: string;
  settlement_mode: string;
  amount_basis: string;
  payment_due_day: string;
  revenue_attribution_scope: string;
  revenue_share_operator_ratio: string;
  amount_rule_json: string;
  payment_rule_json: string;
  revenue_attribution_rule_json: string;
  revenue_share_rule_json: string;
  risk_tags: string;
  asset_ids: string[];
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
  amount_basis: '',
  payment_due_day: '',
  revenue_attribution_scope: '',
  revenue_share_operator_ratio: '',
  amount_rule_json: '',
  payment_rule_json: '',
  revenue_attribution_rule_json: '',
  revenue_share_rule_json: '',
  risk_tags: '',
  asset_ids: [],
};

const REVENUE_MODE_OPTIONS = [
  { label: '承租转租', value: 'LEASE' },
  { label: '代理运营', value: 'AGENCY' },
] satisfies Array<{ label: string; value: RevenueMode }>;

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

const readRuleValue = (rule: Record<string, unknown>, key: string): string => {
  const value = rule[key];
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value);
  }
  return '';
};

const parseDueDay = (value: string): number | undefined => {
  const normalized = value.trim();
  if (normalized === '') {
    return undefined;
  }

  const parsed = Number(normalized);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 31) {
    throw new Error('付款日必须是 1 到 31 之间的整数');
  }
  return parsed;
};

const parsePercent = (value: string, label: string): number | undefined => {
  const normalized = value.trim();
  if (normalized === '') {
    return undefined;
  }

  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100) {
    throw new Error(`${label}必须是 0 到 100 之间的数字`);
  }
  return parsed;
};

const buildAmountRule = (state: EditableFormState): Record<string, unknown> => {
  const amountRule = parseJsonField(state.amount_rule_json, '金额规则') ?? {};
  const basis = state.amount_basis.trim();
  if (basis !== '') {
    amountRule.basis = basis;
  }
  return amountRule;
};

const buildPaymentRule = (state: EditableFormState): Record<string, unknown> => {
  const paymentRule = parseJsonField(state.payment_rule_json, '支付规则') ?? {};
  const dueDay = parseDueDay(state.payment_due_day);
  if (dueDay != null) {
    paymentRule.due_day = dueDay;
  }
  return paymentRule;
};

const buildRevenueAttributionRule = (
  state: EditableFormState
): Record<string, unknown> | undefined => {
  const rule = parseJsonField(state.revenue_attribution_rule_json, '收益归属规则') ?? {};
  const scope = state.revenue_attribution_scope.trim();
  if (scope !== '') {
    rule.scope = scope;
  }
  return Object.keys(rule).length > 0 ? rule : undefined;
};

const buildRevenueShareRule = (state: EditableFormState): Record<string, unknown> | undefined => {
  const rule = parseJsonField(state.revenue_share_rule_json, '收益分成规则') ?? {};
  const operatorRatio = parsePercent(state.revenue_share_operator_ratio, '运营方分成比例');
  if (operatorRatio != null) {
    rule.operator_ratio_percent = operatorRatio;
  }
  return Object.keys(rule).length > 0 ? rule : undefined;
};

const hasSettlementInput = (state: EditableFormState): boolean =>
  [
    state.settlement_version,
    state.settlement_mode,
    state.amount_basis,
    state.payment_due_day,
    state.amount_rule_json,
    state.payment_rule_json,
  ].some(value => value.trim() !== '');

const buildSettlementRule = (state: EditableFormState): SettlementRule | undefined => {
  if (!hasSettlementInput(state)) {
    return undefined;
  }

  return {
    version: state.settlement_version.trim(),
    cycle: state.settlement_cycle,
    settlement_mode: state.settlement_mode.trim(),
    amount_rule: buildAmountRule(state),
    payment_rule: buildPaymentRule(state),
  };
};

const mapDetailToFormState = (detail: ContractGroupDetail): EditableFormState => ({
  revenue_mode: detail.revenue_mode,
  operator_party_id: detail.operator_party_id,
  owner_party_id: detail.owner_party_id,
  effective_from: detail.effective_from,
  effective_to: detail.effective_to ?? '',
  settlement_version: detail.settlement_rule?.version ?? '',
  settlement_cycle: detail.settlement_rule?.cycle ?? EMPTY_FORM.settlement_cycle,
  settlement_mode: detail.settlement_rule?.settlement_mode ?? '',
  amount_basis: readRuleValue(detail.settlement_rule?.amount_rule ?? {}, 'basis'),
  payment_due_day: readRuleValue(detail.settlement_rule?.payment_rule ?? {}, 'due_day'),
  revenue_attribution_scope:
    detail.revenue_attribution_rule != null
      ? readRuleValue(detail.revenue_attribution_rule, 'scope')
      : '',
  revenue_share_operator_ratio:
    detail.revenue_share_rule != null
      ? readRuleValue(detail.revenue_share_rule, 'operator_ratio_percent')
      : '',
  amount_rule_json:
    detail.settlement_rule != null ? JSON.stringify(detail.settlement_rule.amount_rule, null, 2) : '',
  payment_rule_json:
    detail.settlement_rule != null
      ? JSON.stringify(detail.settlement_rule.payment_rule, null, 2)
      : '',
  revenue_attribution_rule_json:
    detail.revenue_attribution_rule != null
      ? JSON.stringify(detail.revenue_attribution_rule, null, 2)
      : '',
  revenue_share_rule_json:
    detail.revenue_share_rule != null ? JSON.stringify(detail.revenue_share_rule, null, 2) : '',
  risk_tags: detail.risk_tags?.join(', ') ?? '',
  asset_ids: [],
});

const buildCreatePayload = (state: EditableFormState, projectId: string): ContractGroupCreate => {
  const revenueAttributionRule = buildRevenueAttributionRule(state);
  const revenueShareRule = buildRevenueShareRule(state);
  const riskTags = parseRiskTags(state.risk_tags);
  const settlementRule = buildSettlementRule(state);

  return {
    project_id: projectId,
    revenue_mode: state.revenue_mode,
    operator_party_id: state.operator_party_id.trim(),
    owner_party_id: state.owner_party_id.trim(),
    effective_from: state.effective_from.trim(),
    ...(state.effective_to.trim() !== '' ? { effective_to: state.effective_to.trim() } : {}),
    ...(settlementRule != null ? { settlement_rule: settlementRule } : {}),
    ...(revenueAttributionRule != null ? { revenue_attribution_rule: revenueAttributionRule } : {}),
    ...(revenueShareRule != null ? { revenue_share_rule: revenueShareRule } : {}),
    ...(riskTags != null ? { risk_tags: riskTags } : {}),
    asset_ids: state.asset_ids,
  };
};

const buildUpdatePayload = (state: EditableFormState): ContractGroupUpdate => {
  const settlementRule = buildSettlementRule(state);

  return {
    effective_to: state.effective_to.trim() !== '' ? state.effective_to.trim() : null,
    settlement_rule: settlementRule ?? null,
    revenue_attribution_rule: buildRevenueAttributionRule(state) ?? null,
    revenue_share_rule: buildRevenueShareRule(state) ?? null,
    risk_tags: parseRiskTags(state.risk_tags) ?? null,
  };
};

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

const LabeledAssetChecklist: React.FC<{
  assets: Asset[];
  value: string[];
  disabled?: boolean;
  onChange: (value: string[]) => void;
}> = ({ assets, value, disabled = false, onChange }) => {
  const selectedIds = new Set(value);

  if (assets.length === 0) {
    return (
      <div>
        <Typography.Text strong>关联资产</Typography.Text>
        <Alert type="info" showIcon title="该项目暂无可选资产" />
      </div>
    );
  }

  return (
    <fieldset aria-label="关联资产" disabled={disabled}>
      <legend>
        <Typography.Text strong>关联资产</Typography.Text>
      </legend>
      <Space orientation="vertical" size={8}>
        {assets.map(asset => {
          const isChecked = selectedIds.has(asset.id);
          const address = asset.address_detail?.trim() || asset.address?.trim();
          return (
            <label key={asset.id}>
              <input
                type="checkbox"
                value={asset.id}
                checked={isChecked}
                onChange={event => {
                  const nextIds = event.target.checked
                    ? [...value, asset.id]
                    : value.filter(assetId => assetId !== asset.id);
                  onChange(nextIds);
                }}
              />
              <span>{asset.asset_name}</span>
              {address != null && address !== '' && (
                <Typography.Text type="secondary"> {address}</Typography.Text>
              )}
            </label>
          );
        })}
      </Space>
    </fieldset>
  );
};

const buildPartyLabel = (party: Party): string => {
  const code = party.code.trim();
  return code !== '' ? `${party.name}（${code}）` : party.name;
};

const LabeledPartySelect: React.FC<{
  label: string;
  value: string;
  parties: Party[];
  onChange: (value: string) => void;
}> = ({ label, value, parties, onChange }) => (
  <label>
    <Typography.Text strong>{label}</Typography.Text>
    <select aria-label={label} value={value} onChange={event => onChange(event.target.value)}>
      <option value="">请选择主体</option>
      {parties.map(party => (
        <option key={party.id} value={party.id}>
          {buildPartyLabel(party)}
        </option>
      ))}
    </select>
  </label>
);

const ContractGroupFormPage: React.FC = () => {
  const { id } = useParams<{ id?: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const isEditMode = id != null && id.length > 0;
  const projectId = searchParams.get('project_id')?.trim() ?? '';
  const [formState, setFormState] = useState<EditableFormState>(EMPTY_FORM);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['contract-group-form-detail', id],
    queryFn: () => contractGroupService.getContractGroup(id as string),
    enabled: isEditMode,
  });

  const {
    data: projectAssetsData,
    isLoading: projectAssetsLoading,
    error: projectAssetsError,
  } = useQuery({
    queryKey: ['contract-group-form-project-assets', projectId],
    queryFn: () => projectService.getProjectAssets(projectId),
    enabled: !isEditMode && projectId !== '',
    staleTime: 60_000,
  });

  const {
    data: partiesData,
    isLoading: partiesLoading,
    error: partiesError,
  } = useQuery({
    queryKey: ['contract-group-form-parties'],
    queryFn: () => partyService.getParties({ limit: 500 }),
    enabled: !isEditMode && projectId !== '',
    staleTime: 5 * 60_000,
  });

  const projectAssets = projectAssetsData?.items ?? [];
  const parties = partiesData?.items ?? [];

  useEffect(() => {
    if (data != null) {
      setFormState(mapDetailToFormState(data));
    }
  }, [data]);

  const submitLabel = useMemo(() => (isEditMode ? '保存修改' : '创建合同关系'), [isEditMode]);

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
        navigate(CONTRACT_CENTER_ROUTES.DETAIL(id as string));
      } else {
        const created = await contractGroupService.createContractGroup(
          buildCreatePayload(formState, projectId)
        );
        navigate(CONTRACT_CENTER_ROUTES.DETAIL(created.contract_group_id));
      }
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : '提交失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isEditMode && projectId === '') {
    return (
      <PageContainer
        title="新建合同关系"
        subTitle="合同关系必须归属到具体项目。"
        onBack={() => navigate(CONTRACT_CENTER_ROUTES.LIST)}
      >
        <Alert
          type="warning"
          showIcon
          title="请先从项目详情发起新建合同关系"
          description="当前页面缺少项目上下文，无法提交到后端。请进入项目详情后再新建合同关系。"
          action={
            <Button size="small" type="primary" onClick={() => navigate(PROJECT_ROUTES.LIST)}>
              选择项目
            </Button>
          }
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={isEditMode ? '编辑合同关系' : '新建合同关系'}
      subTitle="创建或维护承租转租、代理运营的合同关系，填写主体、日期、结算规则和关联资产。"
      onBack={() =>
        navigate(
          isEditMode ? CONTRACT_CENTER_ROUTES.DETAIL(id as string) : CONTRACT_CENTER_ROUTES.LIST
        )
      }
    >
      {error != null && (
        <Alert
          type="error"
          showIcon
          title={isEditMode ? '合同关系明细加载失败' : '表单初始化失败'}
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
                  options={REVENUE_MODE_OPTIONS}
                  onChange={value => updateField('revenue_mode', value as RevenueMode)}
                />
                {!isEditMode && (
                  <LabeledInput
                    label="所属项目 ID"
                    value={projectId}
                    disabled
                    onChange={() => undefined}
                  />
                )}
                {!isEditMode && partiesError != null ? (
                  <Alert
                    type="error"
                    showIcon
                    title="主体列表加载失败"
                    description={partiesError instanceof Error ? partiesError.message : '未知错误'}
                  />
                ) : null}
                {!isEditMode && partiesLoading ? <Spin /> : null}
                {!isEditMode && !partiesLoading && parties.length === 0 ? (
                  <Alert type="info" showIcon title="暂无可选主体" />
                ) : null}
                {!isEditMode && !partiesLoading && parties.length > 0 ? (
                  <>
                    <LabeledPartySelect
                      label="运营方主体"
                      value={formState.operator_party_id}
                      parties={parties}
                      onChange={value => updateField('operator_party_id', value)}
                    />
                    <LabeledPartySelect
                      label="产权方主体"
                      value={formState.owner_party_id}
                      parties={parties}
                      onChange={value => updateField('owner_party_id', value)}
                    />
                  </>
                ) : null}
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
                    {projectAssetsError != null && (
                      <Alert
                        type="error"
                        showIcon
                        title="项目资产加载失败"
                        description={
                          projectAssetsError instanceof Error
                            ? projectAssetsError.message
                            : '未知错误'
                        }
                      />
                    )}
                    {projectAssetsLoading ? (
                      <Spin />
                    ) : (
                      <LabeledAssetChecklist
                        assets={projectAssets}
                        value={formState.asset_ids}
                        onChange={value => updateField('asset_ids', value)}
                      />
                    )}
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
                <LabeledSelect
                  label="计费依据"
                  value={formState.amount_basis}
                  options={[
                    { label: '请选择计费依据', value: '' },
                    { label: '固定金额', value: 'fixed' },
                    { label: '按面积', value: 'area' },
                    { label: '按收入分成', value: 'revenue' },
                    { label: '其他约定', value: 'other' },
                  ]}
                  onChange={value => updateField('amount_basis', value)}
                />
                <LabeledInput
                  label="付款日"
                  value={formState.payment_due_day}
                  onChange={value => updateField('payment_due_day', value)}
                />
              </Space>
            </Card>

            <Card title="收益配置">
              <Space orientation="vertical" size={12}>
                <LabeledSelect
                  label="收益归属口径"
                  value={formState.revenue_attribution_scope}
                  options={[
                    { label: '不单独配置', value: '' },
                    { label: '运营方归集', value: 'operator' },
                    { label: '产权方归集', value: 'owner' },
                    { label: '按合同约定', value: 'contract' },
                  ]}
                  onChange={value => updateField('revenue_attribution_scope', value)}
                />
                <LabeledInput
                  label="运营方分成比例（%）"
                  value={formState.revenue_share_operator_ratio}
                  onChange={value => updateField('revenue_share_operator_ratio', value)}
                />
                <LabeledInput
                  label="风险标签"
                  value={formState.risk_tags}
                  onChange={value => updateField('risk_tags', value)}
                />
              </Space>
            </Card>

            <Space>
              <Button htmlType="submit" type="primary" loading={isSubmitting}>
                {submitLabel}
              </Button>
              <Button onClick={() => navigate(CONTRACT_CENTER_ROUTES.LIST)}>返回列表</Button>
            </Space>
          </Space>
        </form>
      )}
    </PageContainer>
  );
};

export default ContractGroupFormPage;
