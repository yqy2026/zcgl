import React from 'react';
import { Alert, Button, Card, Descriptions, Empty, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import { CONTRACT_CENTER_ROUTES } from '@/constants/routes';
import { contractGroupService } from '@/services/contractGroupService';
import type { ContractGroupSummaryContract } from '@/types/contractGroup';

const REVENUE_MODE_META = {
  LEASE: {
    color: 'blue',
    label: '承租转租',
  },
  AGENCY: {
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
    title: '生命周期',
    dataIndex: 'status',
    key: 'status',
  },
  {
    title: '审核状态',
    dataIndex: 'review_status',
    key: 'review_status',
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

  const { data, error, isLoading } = useQuery({
    queryKey: ['contract-group-detail', id],
    queryFn: () => contractGroupService.getContractGroup(id as string),
    enabled: id != null && id.length > 0,
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
          {data.revenue_mode === 'AGENCY' ? (
            <Alert
              type="info"
              showIcon
              title="代理口径，非自营出租"
              description="该合同关系按代理模式管理，终端租金不直接计入运营方自营租金收入。"
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
            <Descriptions bordered column={2}>
              <Descriptions.Item label="规则版本">{data.settlement_rule.version}</Descriptions.Item>
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
              columns={contractColumns}
              dataSource={data.contracts}
              pagination={false}
              locale={{ emptyText: '当前合同关系下暂无合同' }}
            />
          </Card>
        </Space>
      )}
    </PageContainer>
  );
};

export default ContractGroupDetailPage;
