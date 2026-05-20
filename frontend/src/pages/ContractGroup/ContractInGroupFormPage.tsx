import React, { useState } from 'react';
import { Alert, Button, Card, Input, Space, Spin, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import { CONTRACT_CENTER_ROUTES } from '@/constants/routes';
import { contractGroupService } from '@/services/contractGroupService';
import { partyService } from '@/services/partyService';
import { projectService } from '@/services/projectService';
import type { Asset } from '@/types/asset';
import type { Party } from '@/types/party';
import type { ContractCreate, ContractDirection, GroupRelationType } from '@/types/contractGroup';

const { Text } = Typography;

type ContractRoleConfig = {
  title: string;
  direction: ContractDirection;
  detailKind: 'lease' | 'agency';
  lessorPartyLabel: string;
  lesseePartyLabel: string;
};

type ContractFormState = {
  contract_number: string;
  lessor_party_id: string;
  lessee_party_id: string;
  effective_from: string;
  effective_to: string;
  rent_amount: string;
  payment_cycle: string;
  service_fee_ratio: string;
  asset_ids: string[];
};

const ROLE_CONFIG: Record<GroupRelationType, ContractRoleConfig> = {
  UPSTREAM: {
    title: '新增上游承租合同',
    direction: 'LESSOR',
    detailKind: 'lease',
    lessorPartyLabel: '出租方/委托方主体',
    lesseePartyLabel: '承租方/受托方主体',
  },
  DOWNSTREAM: {
    title: '新增下游出租合同',
    direction: 'LESSOR',
    detailKind: 'lease',
    lessorPartyLabel: '出租方/委托方主体',
    lesseePartyLabel: '承租方/受托方主体',
  },
  ENTRUSTED: {
    title: '新增委托协议',
    direction: 'LESSEE',
    detailKind: 'agency',
    lessorPartyLabel: '委托方主体',
    lesseePartyLabel: '受托方主体',
  },
  DIRECT_LEASE: {
    title: '新增直租合同',
    direction: 'LESSOR',
    detailKind: 'lease',
    lessorPartyLabel: '出租方/委托方主体',
    lesseePartyLabel: '承租方/受托方主体',
  },
};

const EMPTY_FORM: ContractFormState = {
  contract_number: '',
  lessor_party_id: '',
  lessee_party_id: '',
  effective_from: '',
  effective_to: '',
  rent_amount: '',
  payment_cycle: '月付',
  service_fee_ratio: '',
  asset_ids: [],
};

const isContractRole = (value: string | null): value is GroupRelationType =>
  value === 'UPSTREAM' ||
  value === 'DOWNSTREAM' ||
  value === 'ENTRUSTED' ||
  value === 'DIRECT_LEASE';

const buildPartyLabel = (party: Party): string => {
  const code = party.code.trim();
  return code !== '' ? `${party.name}（${code}）` : party.name;
};

const parsePercentToRatio = (value: string, label: string): string => {
  const normalized = value.trim();
  const parsed = Number(normalized);
  if (normalized === '' || !Number.isFinite(parsed) || parsed < 0 || parsed > 100) {
    throw new Error(`${label}必须是 0 到 100 之间的数字`);
  }
  return String(parsed / 100);
};

const LabeledInput: React.FC<{
  label: string;
  value: string;
  onChange: (value: string) => void;
}> = ({ label, value, onChange }) => (
  <label>
    <Text strong>{label}</Text>
    <Input aria-label={label} value={value} onChange={event => onChange(event.target.value)} />
  </label>
);

const LabeledSelect: React.FC<{
  label: string;
  value: string;
  options: Array<{ label: string; value: string }>;
  onChange: (value: string) => void;
}> = ({ label, value, options, onChange }) => (
  <label>
    <Text strong>{label}</Text>
    <select aria-label={label} value={value} onChange={event => onChange(event.target.value)}>
      {options.map(option => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  </label>
);

const LabeledPartySelect: React.FC<{
  label: string;
  value: string;
  parties: Party[];
  onChange: (value: string) => void;
}> = ({ label, value, parties, onChange }) => (
  <label>
    <Text strong>{label}</Text>
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

const AssetChecklist: React.FC<{
  assets: Asset[];
  value: string[];
  onChange: (value: string[]) => void;
}> = ({ assets, value, onChange }) => {
  const selectedIds = new Set(value);

  if (assets.length === 0) {
    return <Alert type="info" showIcon title="该项目暂无可选资产" />;
  }

  return (
    <fieldset aria-label="合同资产范围">
      <legend>
        <Text strong>合同资产范围</Text>
      </legend>
      <Space orientation="vertical" size={8}>
        {assets.map(asset => (
          <label key={asset.id}>
            <input
              type="checkbox"
              value={asset.id}
              checked={selectedIds.has(asset.id)}
              onChange={event => {
                const nextIds = event.target.checked
                  ? [...value, asset.id]
                  : value.filter(assetId => assetId !== asset.id);
                onChange(nextIds);
              }}
            />
            <span>{asset.asset_name}</span>
          </label>
        ))}
      </Space>
    </fieldset>
  );
};

const ContractInGroupFormPage: React.FC = () => {
  const { id } = useParams<{ id?: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const role = searchParams.get('role');
  const projectId = searchParams.get('project_id')?.trim() ?? '';
  const roleConfig = isContractRole(role) ? ROLE_CONFIG[role] : null;
  const [formState, setFormState] = useState<ContractFormState>(EMPTY_FORM);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    data: partiesData,
    isLoading: partiesLoading,
    error: partiesError,
  } = useQuery({
    queryKey: ['contract-in-group-parties'],
    queryFn: () => partyService.getParties({ limit: 500 }),
    enabled: id != null && roleConfig != null,
    staleTime: 5 * 60_000,
  });

  const {
    data: projectAssetsData,
    isLoading: projectAssetsLoading,
    error: projectAssetsError,
  } = useQuery({
    queryKey: ['contract-in-group-project-assets', projectId],
    queryFn: () => projectService.getProjectAssets(projectId),
    enabled: projectId !== '' && roleConfig != null,
    staleTime: 60_000,
  });

  const parties = partiesData?.items ?? [];
  const assets = projectAssetsData?.items ?? [];

  const updateField = <T extends keyof ContractFormState>(key: T, value: ContractFormState[T]) => {
    setFormState(current => ({
      ...current,
      [key]: value,
    }));
  };

  const buildPayload = (): ContractCreate => {
    if (
      id == null ||
      id.trim() === '' ||
      projectId === '' ||
      roleConfig == null ||
      !isContractRole(role)
    ) {
      throw new Error('缺少合同关系或合同类型上下文');
    }
    if (formState.asset_ids.length === 0) {
      throw new Error('请选择合同资产范围');
    }

    return {
      contract_group_id: id,
      contract_number: formState.contract_number.trim(),
      contract_direction: roleConfig.direction,
      group_relation_type: role,
      lessor_party_id: formState.lessor_party_id.trim(),
      lessee_party_id: formState.lessee_party_id.trim(),
      effective_from: formState.effective_from.trim(),
      ...(formState.effective_to.trim() !== ''
        ? { effective_to: formState.effective_to.trim() }
        : {}),
      asset_ids: formState.asset_ids,
      ...(roleConfig.detailKind === 'agency'
        ? {
            agency_detail: {
              service_fee_ratio: parsePercentToRatio(formState.service_fee_ratio, '服务费比例'),
              fee_calculation_base: 'actual_received',
            },
          }
        : {
            lease_detail: {
              rent_amount: formState.rent_amount.trim(),
              payment_cycle: formState.payment_cycle,
            },
          }),
    };
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    setIsSubmitting(true);

    try {
      const payload = buildPayload();
      await contractGroupService.addContractToGroup(id as string, payload);
      navigate(CONTRACT_CENTER_ROUTES.DETAIL(id as string));
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : '保存合同失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (id == null || id.trim() === '' || projectId === '' || roleConfig == null) {
    return (
      <PageContainer title="新增合同" onBack={() => navigate(CONTRACT_CENTER_ROUTES.LIST)}>
        <Alert
          type="warning"
          showIcon
          title="请先从项目合同关系卡片发起新增合同"
          description="当前页面缺少合同关系或合同类型上下文。"
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={roleConfig.title}
      subTitle="从项目合同关系进入，录入合同编号、签约主体、有效期和资产范围。"
      onBack={() => navigate(CONTRACT_CENTER_ROUTES.DETAIL(id))}
    >
      {submitError != null && <Alert type="error" showIcon title={submitError} />}
      {partiesError != null && (
        <Alert
          type="error"
          showIcon
          title="主体列表加载失败"
          description={partiesError instanceof Error ? partiesError.message : '未知错误'}
        />
      )}
      {projectAssetsError != null && (
        <Alert
          type="error"
          showIcon
          title="项目资产加载失败"
          description={
            projectAssetsError instanceof Error ? projectAssetsError.message : '未知错误'
          }
        />
      )}

      <form onSubmit={event => void handleSubmit(event)}>
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Card title="合同基础信息">
            <Space orientation="vertical" size={12}>
              <LabeledInput
                label="合同编号"
                value={formState.contract_number}
                onChange={value => updateField('contract_number', value)}
              />
              {partiesLoading ? (
                <Spin />
              ) : (
                <>
                  <LabeledPartySelect
                    label={roleConfig.lessorPartyLabel}
                    value={formState.lessor_party_id}
                    parties={parties}
                    onChange={value => updateField('lessor_party_id', value)}
                  />
                  <LabeledPartySelect
                    label={roleConfig.lesseePartyLabel}
                    value={formState.lessee_party_id}
                    parties={parties}
                    onChange={value => updateField('lessee_party_id', value)}
                  />
                </>
              )}
              <LabeledInput
                label="开始日期"
                value={formState.effective_from}
                onChange={value => updateField('effective_from', value)}
              />
              <LabeledInput
                label="结束日期"
                value={formState.effective_to}
                onChange={value => updateField('effective_to', value)}
              />
            </Space>
          </Card>

          <Card title={roleConfig.detailKind === 'agency' ? '代理约定' : '租赁约定'}>
            <Space orientation="vertical" size={12}>
              {roleConfig.detailKind === 'agency' ? (
                <LabeledInput
                  label="服务费比例（%）"
                  value={formState.service_fee_ratio}
                  onChange={value => updateField('service_fee_ratio', value)}
                />
              ) : (
                <>
                  <LabeledInput
                    label="租金总额"
                    value={formState.rent_amount}
                    onChange={value => updateField('rent_amount', value)}
                  />
                  <LabeledSelect
                    label="付款周期"
                    value={formState.payment_cycle}
                    options={[
                      { label: '月付', value: '月付' },
                      { label: '季付', value: '季付' },
                      { label: '半年付', value: '半年付' },
                      { label: '年付', value: '年付' },
                    ]}
                    onChange={value => updateField('payment_cycle', value)}
                  />
                </>
              )}
            </Space>
          </Card>

          <Card title="资产范围">
            {projectAssetsLoading ? (
              <Spin />
            ) : (
              <AssetChecklist
                assets={assets}
                value={formState.asset_ids}
                onChange={value => updateField('asset_ids', value)}
              />
            )}
          </Card>

          <Space>
            <Button htmlType="submit" type="primary" loading={isSubmitting}>
              保存合同
            </Button>
            <Button onClick={() => navigate(CONTRACT_CENTER_ROUTES.DETAIL(id))}>返回明细</Button>
          </Space>
        </Space>
      </form>
    </PageContainer>
  );
};

export default ContractInGroupFormPage;
