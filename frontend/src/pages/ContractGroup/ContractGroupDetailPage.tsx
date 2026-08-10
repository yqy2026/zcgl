import React from 'react';
import { Alert, Button, Card, Descriptions, Empty, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import { CONTRACT_CENTER_ROUTES } from '@/constants/routes';
import { contractGroupService } from '@/services/contractGroupService';
import { ledgerService } from '@/services/ledgerService';
import type { ContractGroupSummaryContract } from '@/types/contractGroup';
import type { LedgerRecalculateResult, LedgerRecalculateSkippedEntry } from '@/types/ledger';

const REVENUE_MODE_META = {
  lease: {
    color: 'blue',
    label: '承租转租',
  },
  agency: {
    color: 'cyan',
    label: '代理运营',
  },
} as const;

const CONTRACT_ROLE_LABELS: Record<string, string> = {
  UPSTREAM: '上游承租合同',
  DOWNSTREAM: '下游出租合同',
  ENTRUSTED: '委托协议',
  DIRECT_LEASE: '直租合同',
};

const LEDGER_SKIP_REASON_LABELS: Record<string, string> = {
  paid_or_partial_entry_requires_manual_resolution: '已收/部分已收条目需人工对账处理',
  paid_or_partial_entry_outside_current_terms: '已收/部分已收条目不在当前合同条款账期内',
};

const AMOUNT_BASIS_LABELS: Record<string, string> = {
  fixed: '固定金额',
  area: '按面积',
  revenue: '按收入分成',
  other: '其他约定',
};

const REVENUE_ATTRIBUTION_LABELS: Record<string, string> = {
  operator: '运营方归集',
  owner: '产权方归集',
  contract: '按合同约定',
};

const contractColumns: ColumnsType<ContractGroupSummaryContract> = [
  {
    title: '合同编号',
    dataIndex: 'contract_number',
    key: 'contract_number',
  },
  {
    title: '组内角色',
    dataIndex: 'group_relation_type',
    key: 'group_relation_type',
    render: (value: string) => CONTRACT_ROLE_LABELS[value] ?? value,
  },
  {
    title: '出租/委托方',
    key: 'lessor_name_snapshot',
    render: (_value, record) => record.lessor_name_snapshot ?? record.lessor_party_id,
  },
  {
    title: '承租/受托方',
    key: 'lessee_name_snapshot',
    render: (_value, record) => record.lessee_name_snapshot ?? record.lessee_party_id,
  },
  {
    title: '生命周期',
    dataIndex: 'status',
    key: 'status',
  },
];

const skippedEntryColumns: ColumnsType<LedgerRecalculateSkippedEntry> = [
  {
    title: '账期',
    dataIndex: 'year_month',
    key: 'year_month',
  },
  {
    title: '支付状态',
    dataIndex: 'payment_status',
    key: 'payment_status',
  },
  {
    title: '跳过原因',
    dataIndex: 'reason',
    key: 'reason',
    render: (value: string) => LEDGER_SKIP_REASON_LABELS[value] ?? value,
  },
];

const emptyText = <Typography.Text type="secondary">未配置</Typography.Text>;

const readRuleValue = (rule: Record<string, unknown> | null | undefined, key: string): string => {
  const value = rule?.[key];
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value);
  }
  return '';
};

const renderAmountBasis = (rule: Record<string, unknown>) => {
  const basis = readRuleValue(rule, 'basis');
  return basis !== '' ? (AMOUNT_BASIS_LABELS[basis] ?? basis) : emptyText;
};

const renderPaymentDueDay = (rule: Record<string, unknown>) => {
  const dueDay = readRuleValue(rule, 'due_day');
  return dueDay !== '' ? `每月 ${dueDay} 日` : emptyText;
};

const renderRevenueAttribution = (rule: Record<string, unknown> | null | undefined) => {
  const scope = readRuleValue(rule, 'scope');
  return scope !== '' ? (REVENUE_ATTRIBUTION_LABELS[scope] ?? scope) : emptyText;
};

const renderOperatorRatio = (rule: Record<string, unknown> | null | undefined) => {
  const ratio = readRuleValue(rule, 'operator_ratio_percent');
  return ratio !== '' ? `${ratio}%` : emptyText;
};

const ContractGroupDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [ledgerRecalculateResult, setLedgerRecalculateResult] = React.useState<{
    contractNumber: string;
    result: LedgerRecalculateResult;
  } | null>(null);

  const { data, error, isLoading } = useQuery({
    queryKey: ['contract-group-detail', id],
    queryFn: () => contractGroupService.getContractGroup(id as string),
    enabled: id != null && id.length > 0,
  });

  const recalculateLedgerMutation = useMutation({
    mutationFn: async (contract: ContractGroupSummaryContract) => {
      const result = await ledgerService.recalculateContractLedger(contract.contract_id);
      return { contract, result };
    },
    onSuccess: ({ contract, result }) => {
      setLedgerRecalculateResult({
        contractNumber: contract.contract_number,
        result,
      });
    },
  });

  if (error != null) {
    return (
      <PageContainer title="合同关系明细" onBack={() => navigate(CONTRACT_CENTER_ROUTES.LIST)}>
        <Alert
          type="error"
          showIcon
          message="合同关系明细加载失败"
          description={error instanceof Error ? error.message : '未知错误'}
        />
      </PageContainer>
    );
  }

  if (!isLoading && data == null) {
    return (
      <PageContainer title="合同关系明细" onBack={() => navigate(CONTRACT_CENTER_ROUTES.LIST)}>
        <Empty description="未找到对应合同关系" />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={data?.group_code ?? '合同关系明细'}
      subTitle="查看项目经营关系下的主合同、终端合同、结算规则和风险状态。"
      loading={isLoading}
      onBack={() => navigate(CONTRACT_CENTER_ROUTES.LIST)}
      extra={
        data != null ? (
          <Button
            type="primary"
            onClick={() => navigate(CONTRACT_CENTER_ROUTES.EDIT(data.contract_group_id))}
          >
            编辑合同关系
          </Button>
        ) : null
      }
    >
      {data != null && (
        <Space orientation="vertical" size={16}>
          {data.revenue_mode === 'agency' ? (
            <Alert
              type="info"
              showIcon
              title="代理口径，非自营出租"
              description="该合同关系按代理模式管理，终端租金不直接计入运营方承租转租租金收入。"
            />
          ) : null}

          <Descriptions bordered column={2}>
            <Descriptions.Item label="合同关系编码">{data.group_code}</Descriptions.Item>
            <Descriptions.Item label="经营模式">
              <Tag color={REVENUE_MODE_META[data.revenue_mode].color}>
                {REVENUE_MODE_META[data.revenue_mode].label}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="生效开始日">{data.effective_from}</Descriptions.Item>
            <Descriptions.Item label="生效结束日">
              {data.effective_to ?? '未设定'}
            </Descriptions.Item>
            <Descriptions.Item label="派生状态">{data.derived_status}</Descriptions.Item>
            <Descriptions.Item label="数据状态">{data.data_status}</Descriptions.Item>
            <Descriptions.Item label="风险标签" span={2}>
              {(data.risk_tags?.length ?? 0) > 0
                ? data.risk_tags?.map(tag => <Tag key={tag}>{tag}</Tag>)
                : '未设定'}
            </Descriptions.Item>
          </Descriptions>

          <Card title="结算规则">
            {data.settlement_rule != null ? (
              <Descriptions bordered column={2}>
                <Descriptions.Item label="规则版本">
                  {data.settlement_rule.version}
                </Descriptions.Item>
                <Descriptions.Item label="结算周期">{data.settlement_rule.cycle}</Descriptions.Item>
                <Descriptions.Item label="结算模式">
                  {data.settlement_rule.settlement_mode}
                </Descriptions.Item>
                <Descriptions.Item label="计费依据">
                  {renderAmountBasis(data.settlement_rule.amount_rule)}
                </Descriptions.Item>
                <Descriptions.Item label="付款日">
                  {renderPaymentDueDay(data.settlement_rule.payment_rule)}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              emptyText
            )}
          </Card>

          <Card title="收益配置">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="收益归属口径">
                {renderRevenueAttribution(data.revenue_attribution_rule)}
              </Descriptions.Item>
              <Descriptions.Item label="运营方分成比例">
                {renderOperatorRatio(data.revenue_share_rule)}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title={`关联合同 (${data.contracts.length})`}>
            <Table<ContractGroupSummaryContract>
              rowKey="contract_id"
              columns={[
                ...contractColumns,
                {
                  title: '台账',
                  key: 'ledger_actions',
                  render: (_value, record) => (
                    <Button
                      size="small"
                      onClick={() => recalculateLedgerMutation.mutate(record)}
                      loading={
                        recalculateLedgerMutation.isPending &&
                        recalculateLedgerMutation.variables?.contract_id === record.contract_id
                      }
                    >
                      重算台账
                    </Button>
                  ),
                },
              ]}
              dataSource={data.contracts}
              pagination={false}
              locale={{ emptyText: '当前合同关系下暂无合同' }}
            />
          </Card>

          {recalculateLedgerMutation.isError ? (
            <Alert
              type="error"
              showIcon
              title="台账重算失败"
              description={
                recalculateLedgerMutation.error instanceof Error
                  ? recalculateLedgerMutation.error.message
                  : '未知错误'
              }
            />
          ) : null}

          {ledgerRecalculateResult != null ? (
            <Card title={`台账重算结果 - ${ledgerRecalculateResult.contractNumber}`}>
              <Space orientation="vertical" size={12}>
                <Typography.Text>
                  新增 {ledgerRecalculateResult.result.created} 条，更新{' '}
                  {ledgerRecalculateResult.result.updated} 条，作废{' '}
                  {ledgerRecalculateResult.result.voided} 条
                </Typography.Text>
                {(ledgerRecalculateResult.result.skipped_entries?.length ?? 0) > 0 ? (
                  <>
                    <Alert
                      type="warning"
                      showIcon
                      title="存在已收或部分已收条目未自动改写"
                      description="这些条目可能与当前合同条款不一致，请在经营台账中人工对账处理。"
                    />
                    <Table<LedgerRecalculateSkippedEntry>
                      rowKey="entry_id"
                      columns={skippedEntryColumns}
                      dataSource={ledgerRecalculateResult.result.skipped_entries}
                      pagination={false}
                    />
                  </>
                ) : (
                  <Alert type="success" showIcon title="本次重算没有跳过已收条目" />
                )}
              </Space>
            </Card>
          ) : null}
        </Space>
      )}
    </PageContainer>
  );
};

export default ContractGroupDetailPage;
