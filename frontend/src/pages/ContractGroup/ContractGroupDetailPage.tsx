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
    label: '鎵跨杞',
  },
  AGENCY: {
    color: 'cyan',
    label: '浠ｇ悊杩愯惀',
  },
} as const;

const CONTRACT_ROLE_LABELS: Record<string, string> = {
  UPSTREAM: '涓婃父鎵跨鍚堝悓',
  DOWNSTREAM: '涓嬫父鍑虹鍚堝悓',
  ENTRUSTED: '濮旀墭鍗忚',
  DIRECT_LEASE: '鐩寸鍚堝悓',
};

const AMOUNT_BASIS_LABELS: Record<string, string> = {
  fixed: '鍥哄畾閲戦',
  area: '鎸夐潰绉?,
  revenue: '鎸夋敹鍏ュ垎鎴?,
  other: '鍏朵粬绾﹀畾',
};

const REVENUE_ATTRIBUTION_LABELS: Record<string, string> = {
  operator: '杩愯惀鏂瑰綊闆?,
  owner: '浜ф潈鏂瑰綊闆?,
  contract: '鎸夊悎鍚岀害瀹?,
};

const contractColumns: ColumnsType<ContractGroupSummaryContract> = [
  {
    title: '鍚堝悓缂栧彿',
    dataIndex: 'contract_number',
    key: 'contract_number',
  },
  {
    title: '缁勫唴瑙掕壊',
    dataIndex: 'group_relation_type',
    key: 'group_relation_type',
    render: (value: string) => CONTRACT_ROLE_LABELS[value] ?? value,
  },
  {
    title: '鐢熷懡鍛ㄦ湡',
    dataIndex: 'status',
    key: 'status',
  },
  {
    title: '瀹℃牳鐘舵€?,
    dataIndex: 'review_status',
    key: 'review_status',
  },
];

const emptyText = <Typography.Text type="secondary">鏈厤缃?/Typography.Text>;

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
  return dueDay !== '' ? `姣忔湀 ${dueDay} 鏃 : emptyText;
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
      <PageContainer title="鍚堝悓鍏崇郴鏄庣粏" onBack={() => navigate(CONTRACT_CENTER_ROUTES.LIST)}>
        <Alert
          type="error"
          showIcon
          message="鍚堝悓鍏崇郴鏄庣粏鍔犺浇澶辫触"
          description={error instanceof Error ? error.message : '鏈煡閿欒'}
        />
      </PageContainer>
    );
  }

  if (!isLoading && data == null) {
    return (
      <PageContainer title="鍚堝悓鍏崇郴鏄庣粏" onBack={() => navigate(CONTRACT_CENTER_ROUTES.LIST)}>
        <Empty description="鏈壘鍒板搴斿悎鍚屽叧绯? />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={data?.group_code ?? '鍚堝悓鍏崇郴鏄庣粏'}
      subTitle="鏌ョ湅椤圭洰缁忚惀鍏崇郴涓嬬殑涓诲悎鍚屻€佺粓绔悎鍚屻€佺粨绠楄鍒欏拰椋庨櫓鐘舵€併€?
      loading={isLoading}
      onBack={() => navigate(CONTRACT_CENTER_ROUTES.LIST)}
      extra={
        data != null ? (
          <Button
            type="primary"
            onClick={() => navigate(CONTRACT_CENTER_ROUTES.EDIT(data.contract_group_id))}
          >
            缂栬緫鍚堝悓鍏崇郴
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
              title="浠ｇ悊鍙ｅ緞锛岄潪鑷惀鍑虹"
              description="璇ュ悎鍚屽叧绯绘寜浠ｇ悊妯″紡绠＄悊锛岀粓绔閲戜笉鐩存帴璁″叆杩愯惀鏂硅嚜钀ョ閲戞敹鍏ャ€?
            />
          ) : null}

          <Descriptions bordered column={2}>
            <Descriptions.Item label="鍚堝悓鍏崇郴缂栫爜">{data.group_code}</Descriptions.Item>
            <Descriptions.Item label="缁忚惀妯″紡">
              <Tag color={REVENUE_MODE_META[data.revenue_mode].color}>
                {REVENUE_MODE_META[data.revenue_mode].label}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="鐢熸晥寮€濮嬫棩">{data.effective_from}</Descriptions.Item>
            <Descriptions.Item label="鐢熸晥缁撴潫鏃?>
              {data.effective_to ?? '鏈瀹?}
            </Descriptions.Item>
            <Descriptions.Item label="娲剧敓鐘舵€?>{data.derived_status}</Descriptions.Item>
            <Descriptions.Item label="鏁版嵁鐘舵€?>{data.data_status}</Descriptions.Item>
            <Descriptions.Item label="椋庨櫓鏍囩" span={2}>
              {(data.risk_tags?.length ?? 0) > 0
                ? data.risk_tags?.map(tag => <Tag key={tag}>{tag}</Tag>)
                : '鏈瀹?}
            </Descriptions.Item>
          </Descriptions>

          <Card title="缁撶畻瑙勫垯">
            {data.settlement_rule != null ? (
              <Descriptions bordered column={2}>
                <Descriptions.Item label="瑙勫垯鐗堟湰">
                  {data.settlement_rule.version}
                </Descriptions.Item>
                <Descriptions.Item label="缁撶畻鍛ㄦ湡">
                  {data.settlement_rule.cycle}
                </Descriptions.Item>
                <Descriptions.Item label="缁撶畻妯″紡">
                  {data.settlement_rule.settlement_mode}
                </Descriptions.Item>
                <Descriptions.Item label="璁¤垂渚濇嵁">
                  {renderAmountBasis(data.settlement_rule.amount_rule)}
                </Descriptions.Item>
                <Descriptions.Item label="浠樻鏃?>
                  {renderPaymentDueDay(data.settlement_rule.payment_rule)}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              emptyText
            )}
          </Card>

          <Card title="鏀剁泭閰嶇疆">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="鏀剁泭褰掑睘鍙ｅ緞">
                {renderRevenueAttribution(data.revenue_attribution_rule)}
              </Descriptions.Item>
              <Descriptions.Item label="杩愯惀鏂瑰垎鎴愭瘮渚?>
                {renderOperatorRatio(data.revenue_share_rule)}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title={`鍏宠仈鍚堝悓 (${data.contracts.length})`}>
            <Table<ContractGroupSummaryContract>
              rowKey="contract_id"
              columns={contractColumns}
              dataSource={data.contracts}
              pagination={false}
              locale={{ emptyText: '褰撳墠鍚堝悓鍏崇郴涓嬫殏鏃犲悎鍚? }}
            />
          </Card>
        </Space>
      )}
    </PageContainer>
  );
};

export default ContractGroupDetailPage;
