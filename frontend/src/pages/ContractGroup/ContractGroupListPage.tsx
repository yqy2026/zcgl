import React, { useMemo, useState } from 'react';
import { Alert, Button, Select, Space, Table, Tag } from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import { CONTRACT_GROUP_ROUTES } from '@/constants/routes';
import { contractGroupService } from '@/services/contractGroupService';
import type { ContractGroupListItem, RevenueMode } from '@/types/contractGroup';

const PAGE_SIZE = 20;

const ContractGroupListPage: React.FC = () => {
  const navigate = useNavigate();
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [revenueMode, setRevenueMode] = useState<RevenueMode | undefined>(undefined);

  const { data, error, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['contract-groups', offset, limit, revenueMode],
    queryFn: () =>
      contractGroupService.getContractGroups({
        offset,
        limit,
        revenue_mode: revenueMode,
      }),
  });

  const columns = useMemo<ColumnsType<ContractGroupListItem>>(
    () => [
      {
        title: '合同组编码',
        dataIndex: 'group_code',
        key: 'group_code',
        render: (value: string, record) => (
          <Button
            type="link"
            onClick={() => navigate(CONTRACT_GROUP_ROUTES.DETAIL(record.contract_group_id))}
          >
            {value}
          </Button>
        ),
      },
      {
        title: '经营模式',
        dataIndex: 'revenue_mode',
        key: 'revenue_mode',
        render: (value: RevenueMode) => <Tag color={value === 'LEASE' ? 'blue' : 'purple'}>{value}</Tag>,
      },
      {
        title: '运营方主体 ID',
        dataIndex: 'operator_party_id',
        key: 'operator_party_id',
      },
      {
        title: '产权方主体 ID',
        dataIndex: 'owner_party_id',
        key: 'owner_party_id',
      },
      {
        title: '生效区间',
        key: 'effective_range',
        render: (_, record) => `${record.effective_from} ~ ${record.effective_to ?? '未设定'}`,
      },
      {
        title: '派生状态',
        dataIndex: 'derived_status',
        key: 'derived_status',
      },
      {
        title: '操作',
        key: 'actions',
        render: (_, record) => (
          <Button onClick={() => navigate(CONTRACT_GROUP_ROUTES.EDIT(record.contract_group_id))}>
            编辑
          </Button>
        ),
      },
    ],
    [navigate]
  );

  const handlePaginationChange = (pagination: TablePaginationConfig) => {
    const nextLimit = pagination.pageSize ?? PAGE_SIZE;
    const nextPage = pagination.current ?? 1;
    setLimit(nextLimit);
    setOffset((nextPage - 1) * nextLimit);
  };

  return (
    <PageContainer
      title="合同组管理"
      subTitle="新合同体系主入口，直接对接 contract_groups / contracts 后端能力。"
      extra={
        <Space>
          <Select
            aria-label="经营模式筛选"
            allowClear
            placeholder="经营模式"
            value={revenueMode}
            onChange={(value: RevenueMode | undefined) => {
              setRevenueMode(value);
              setOffset(0);
            }}
            options={[
              { label: 'LEASE', value: 'LEASE' },
              { label: 'AGENCY', value: 'AGENCY' },
            ]}
          />
          <Button onClick={() => navigate(CONTRACT_GROUP_ROUTES.IMPORT)}>PDF导入</Button>
          <Button type="primary" onClick={() => navigate(CONTRACT_GROUP_ROUTES.NEW)}>
            新建合同组
          </Button>
        </Space>
      }
    >
      {error != null && (
        <Alert
          type="error"
          showIcon
          message="合同组列表加载失败"
          description={error instanceof Error ? error.message : '未知错误'}
          action={
            <Button size="small" onClick={() => void refetch()}>
              重试
            </Button>
          }
        />
      )}

      <Table<ContractGroupListItem>
        rowKey="contract_group_id"
        columns={columns}
        dataSource={data?.items ?? []}
        loading={isLoading || isFetching}
        pagination={{
          current: Math.floor(offset / limit) + 1,
          pageSize: limit,
          total: data?.total ?? 0,
          onChange: (page, pageSize) =>
            handlePaginationChange({
              current: page,
              pageSize,
            }),
          showSizeChanger: true,
        }}
      />
    </PageContainer>
  );
};

export default ContractGroupListPage;
