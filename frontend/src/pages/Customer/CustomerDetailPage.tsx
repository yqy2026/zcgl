import React from 'react';
import { Alert, Button, Card, Descriptions, Space, Table, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import PageContainer from '@/components/Common/PageContainer';
import { ASSET_ROUTES } from '@/constants/routes';
import { partyService } from '@/services/partyService';
import type { CustomerContractSummary, CustomerProfile } from '@/types/party';
import { buildQueryScopeKey } from '@/utils/queryScope';

const CUSTOMER_TYPE_LABELS: Record<string, string> = {
  internal: '内部',
  external: '外部',
};

const SUBJECT_NATURE_LABELS: Record<string, string> = {
  enterprise: '企业',
  individual: '个人',
};

const CONTRACT_ROLE_LABELS: Record<string, string> = {
  upstream_lease: '上游承租',
  downstream_sublease: '下游转租',
  entrusted_operation: '委托运营',
};

const RISK_TAG_SOURCE_COLORS: Record<string, string> = {
  manual: 'blue',
  rule: 'orange',
};

const contractColumns = [
  {
    title: '合同编号',
    dataIndex: 'contract_number',
    key: 'contract_number',
  },
  {
    title: '合同组',
    dataIndex: 'group_code',
    key: 'group_code',
  },
  {
    title: '经营模式',
    dataIndex: 'revenue_mode',
    key: 'revenue_mode',
  },
  {
    title: '合同角色',
    dataIndex: 'group_relation_type',
    key: 'group_relation_type',
  },
  {
    title: '生命周期',
    dataIndex: 'status',
    key: 'status',
  },
];

const CustomerDetailPage: React.FC = () => {
  const navigate = useNavigate();
  const params = useParams<{ id: string }>();
  const customerId = params.id?.trim() ?? '';
  const hasCustomerId = customerId !== '';
  const queryScopeKey = buildQueryScopeKey();

  const customerProfileQuery = useQuery<CustomerProfile>({
    queryKey: ['customer-profile', queryScopeKey, customerId],
    queryFn: async () => {
      return await partyService.getCustomerProfile(customerId);
    },
    enabled: hasCustomerId,
    staleTime: 60 * 1000,
  });

  const customerProfile = customerProfileQuery.data;

  return (
    <PageContainer
      title={customerProfile?.customer_name ?? '客户详情'}
      subTitle="客户档案基于当前视角聚合 Party 主档、联系人与合同历史。"
    >
      <Space orientation="vertical" size="large" style={{ width: '100%' }}>
        <Button
          onClick={() => {
            navigate(ASSET_ROUTES.LIST);
          }}
        >
          返回列表
        </Button>

        {!hasCustomerId ? <Alert type="error" title="缺少客户 ID，无法加载详情" showIcon /> : null}
        {customerProfileQuery.isError ? (
          <Alert
            type="error"
            title={customerProfileQuery.error instanceof Error ? customerProfileQuery.error.message : '客户档案加载失败'}
            showIcon
          />
        ) : null}

        <Card loading={customerProfileQuery.isLoading} title="客户概览">
          {customerProfile != null ? (
            <Descriptions
              bordered
              column={2}
              items={[
                {
                  key: 'customer_type',
                  label: '客户类型',
                  children: CUSTOMER_TYPE_LABELS[customerProfile.customer_type] ?? customerProfile.customer_type,
                },
                {
                  key: 'subject_nature',
                  label: '主体性质',
                  children:
                    SUBJECT_NATURE_LABELS[customerProfile.subject_nature] ??
                    customerProfile.subject_nature,
                },
                {
                  key: 'contract_role',
                  label: '当前合同角色',
                  children:
                    CONTRACT_ROLE_LABELS[customerProfile.contract_role] ??
                    customerProfile.contract_role,
                },
                {
                  key: 'historical_contract_count',
                  label: '历史签约数',
                  children: customerProfile.historical_contract_count,
                },
                {
                  key: 'contact_name',
                  label: '联系人',
                  children: customerProfile.contact_name ?? '-',
                },
                {
                  key: 'contact_phone',
                  label: '联系电话',
                  children: customerProfile.contact_phone ?? '-',
                },
                {
                  key: 'unified_identifier',
                  label: '统一标识',
                  children: customerProfile.unified_identifier ?? '-',
                },
                {
                  key: 'payment_term_preference',
                  label: '账期偏好',
                  children: customerProfile.payment_term_preference ?? '-',
                },
                {
                  key: 'address',
                  label: '地址',
                  children: customerProfile.address ?? '-',
                  span: 2,
                },
              ]}
            />
          ) : null}
        </Card>

        <Card title="风险标签" loading={customerProfileQuery.isLoading}>
          <Space wrap>
            {(customerProfile?.risk_tag_items ?? []).map(item => (
              <Tag key={`${item.source}-${item.tag}`} color={RISK_TAG_SOURCE_COLORS[item.source]}>
                {item.tag}
                <Typography.Text style={{ marginLeft: 6, color: 'inherit' }}>
                  {item.source === 'manual' ? '手工' : '规则'}
                </Typography.Text>
              </Tag>
            ))}
            {(customerProfile?.risk_tag_items ?? []).length === 0 ? (
              <Typography.Text type="secondary">暂无风险标签</Typography.Text>
            ) : null}
          </Space>
        </Card>

        <Card title="历史签约记录" loading={customerProfileQuery.isLoading}>
          <Table<CustomerContractSummary>
            rowKey="contract_id"
            columns={contractColumns}
            dataSource={customerProfile?.contracts ?? []}
            pagination={false}
            locale={{ emptyText: '暂无历史合同' }}
          />
        </Card>
      </Space>
    </PageContainer>
  );
};

export default CustomerDetailPage;
