import React, { useMemo, useState } from 'react';
import { Alert, Button, Select, Space, Table, Tag } from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import { CONTRACT_CENTER_ROUTES } from '@/constants/routes';
import { contractGroupService } from '@/services/contractGroupService';
import type { ContractGroupListItem, GroupRelationType, RevenueMode } from '@/types/contractGroup';
import { MessageManager } from '@/utils/messageManager';

const PAGE_SIZE = 20;

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

const CONTRACT_ROLE_META: Record<GroupRelationType, { color: string; label: string }> = {
  UPSTREAM: {
    color: 'gold',
    label: '上游承租合同',
  },
  DOWNSTREAM: {
    color: 'blue',
    label: '下游出租合同',
  },
  ENTRUSTED: {
    color: 'cyan',
    label: '委托协议',
  },
  DIRECT_LEASE: {
    color: 'green',
    label: '直租合同',
  },
};

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
        title: '合同关系编码',
        dataIndex: 'group_code',
        key: 'group_code',
        render: (value: string, record) => (
          <Button
            type="link"
            onClick={() => navigate(CONTRACT_CENTER_ROUTES.DETAIL(record.contract_group_id))}
          >
            {value}
          </Button>
        ),
      },
      {
        title: '经营模式',
        dataIndex: 'revenue_mode',
        key: 'revenue_mode',
        render: (value: RevenueMode) => (
          <Tag color={REVENUE_MODE_META[value].color}>{REVENUE_MODE_META[value].label}</Tag>
        ),
      },
      {
        title: '所属项目',
        dataIndex: 'project_name',
        key: 'project_name',
        render: (value?: string | null) => {
          const projectName = value?.trim() ?? '';
          return projectName !== '' ? projectName : '未归属项目';
        },
      },
      {
        title: '合同角色',
        key: 'contract_role_counts',
        render: (_, record) => {
          const roleCounts = record.contract_role_counts ?? {};
          const activeRoles = (Object.keys(CONTRACT_ROLE_META) as GroupRelationType[]).filter(
            role => (roleCounts[role] ?? 0) > 0
          );

          if (activeRoles.length === 0) {
            return <Tag>暂无合同</Tag>;
          }

          return (
            <Space size={4} wrap>
              {activeRoles.map(role => (
                <Tag key={role} color={CONTRACT_ROLE_META[role].color}>
                  {CONTRACT_ROLE_META[role].label} {roleCounts[role]}
                </Tag>
              ))}
            </Space>
          );
        },
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
          <Button onClick={() => navigate(CONTRACT_CENTER_ROUTES.EDIT(record.contract_group_id))}>
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
      title="合同中心"
      subTitle="查看承租转租、代理运营等合同关系，进入明细维护关联合同、结算规则和风险状态。"
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
              { label: REVENUE_MODE_META.lease.label, value: 'lease' },
              { label: REVENUE_MODE_META.agency.label, value: 'agency' },
            ]}
          />
          <Button onClick={() => navigate(CONTRACT_CENTER_ROUTES.IMPORT)}>PDF导入</Button>
          <Button
            type="primary"
            onClick={() => MessageManager.warning('请先从项目详情发起新建合同关系')}
          >
            新建合同关系
          </Button>
        </Space>
      }
    >
      {error != null && (
        <Alert
          type="error"
          showIcon
          message="合同关系列表加载失败"
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
