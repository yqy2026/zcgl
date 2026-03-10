import React from 'react';
import { Alert, Button, Card, Descriptions, Empty, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import { CONTRACT_GROUP_ROUTES } from '@/constants/routes';
import { contractGroupService } from '@/services/contractGroupService';
import type { ContractGroupSummaryContract } from '@/types/contractGroup';

const jsonBlockStyle: React.CSSProperties = {
  margin: 0,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
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

const renderJson = (value: unknown) => {
  if (value == null) {
    return <Typography.Text type="secondary">未配置</Typography.Text>;
  }

  return <pre style={jsonBlockStyle}>{JSON.stringify(value, null, 2)}</pre>;
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
      <PageContainer title="合同组详情" onBack={() => navigate(CONTRACT_GROUP_ROUTES.LIST)}>
        <Alert
          type="error"
          showIcon
          message="合同组详情加载失败"
          description={error instanceof Error ? error.message : '未知错误'}
        />
      </PageContainer>
    );
  }

  if (!isLoading && data == null) {
    return (
      <PageContainer title="合同组详情" onBack={() => navigate(CONTRACT_GROUP_ROUTES.LIST)}>
        <Empty description="未找到对应合同组" />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={data?.group_code ?? '合同组详情'}
      subTitle="当前页面直接展示后端返回的主体 ID 与规则 JSON，不做额外兼容包装。"
      loading={isLoading}
      onBack={() => navigate(CONTRACT_GROUP_ROUTES.LIST)}
      extra={
        data != null ? (
          <Button type="primary" onClick={() => navigate(CONTRACT_GROUP_ROUTES.EDIT(data.contract_group_id))}>
            编辑合同组
          </Button>
        ) : null
      }
    >
      {data != null && (
        <Space orientation="vertical" size={16}>
          <Descriptions bordered column={2}>
            <Descriptions.Item label="合同组编码">{data.group_code}</Descriptions.Item>
            <Descriptions.Item label="经营模式">
              <Tag color={data.revenue_mode === 'LEASE' ? 'blue' : 'purple'}>{data.revenue_mode}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="运营方主体 ID">{data.operator_party_id}</Descriptions.Item>
            <Descriptions.Item label="产权方主体 ID">{data.owner_party_id}</Descriptions.Item>
            <Descriptions.Item label="生效开始日">{data.effective_from}</Descriptions.Item>
            <Descriptions.Item label="生效结束日">{data.effective_to ?? '未设定'}</Descriptions.Item>
            <Descriptions.Item label="派生状态">{data.derived_status}</Descriptions.Item>
            <Descriptions.Item label="数据状态">{data.data_status}</Descriptions.Item>
            <Descriptions.Item label="风险标签" span={2}>
              {(data.risk_tags?.length ?? 0) > 0
                ? data.risk_tags?.map(tag => <Tag key={tag}>{tag}</Tag>)
                : '未设定'}
            </Descriptions.Item>
          </Descriptions>

          <Card title="结算规则 JSON">{renderJson(data.settlement_rule)}</Card>
          <Card title="收益归属规则 JSON">{renderJson(data.revenue_attribution_rule)}</Card>
          <Card title="收益分成规则 JSON">{renderJson(data.revenue_share_rule)}</Card>

          <Card title={`组内合同 (${data.contracts.length})`}>
            <Table<ContractGroupSummaryContract>
              rowKey="contract_id"
              columns={contractColumns}
              dataSource={data.contracts}
              pagination={false}
              locale={{ emptyText: '当前合同组下暂无合同' }}
            />
          </Card>
        </Space>
      )}
    </PageContainer>
  );
};

export default ContractGroupDetailPage;
