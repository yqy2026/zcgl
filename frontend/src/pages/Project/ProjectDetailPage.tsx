/**
 * 项目详情页面 - V2
 *
 * @description 展示项目的完整信息，包括基本信息、关联资产列表和统计数据
 * @module pages/Project
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
  Typography,
  Button,
  Space,
  Row,
  Col,
  Alert,
  Card,
  Descriptions,
  Tag,
  Statistic,
  Badge,
  DatePicker,
  Empty,
  Skeleton,
  Tooltip,
} from 'antd';
import {
  EditOutlined,
  HomeOutlined,
  AreaChartOutlined,
  TeamOutlined,
  InfoCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import dayjs, { type Dayjs } from 'dayjs';
import { projectService } from '@/services/projectService';
import { assetService } from '@/services/assetService';
import type { ColumnsType } from 'antd/es/table';
import type { Asset, AssetLeaseSummaryResponse } from '@/types/asset';
import type {
  ProjectAnalysisModeSummary,
  ProjectContractRelation,
  ProjectRiskItem,
} from '@/types/project';
import type { GroupRelationType } from '@/types/contractGroup';
import { useArrayListData } from '@/hooks/useArrayListData';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { PageContainer } from '@/components/Common';
import { buildQueryScopeKey } from '@/utils/queryScope';
import {
  CONTRACT_CENTER_ROUTES,
  CUSTOMER_ROUTES,
  OPERATIONS_ROUTES,
  PROJECT_ROUTES,
} from '@/constants/routes';
import styles from './ProjectDetailPage.module.css';

const { Text } = Typography;
const PROJECT_STATUS_MAP: Record<string, { text: string; color: string; active: boolean }> = {
  planning: { text: '规划中', color: 'default', active: false },
  active: { text: '进行中', color: 'green', active: true },
  paused: { text: '已暂停', color: 'orange', active: false },
  completed: { text: '已完成', color: 'blue', active: false },
  terminated: { text: '已终止', color: 'red', active: false },
};

const RELATION_TYPE_LABELS: Record<string, string> = {
  上游: '上游承租',
  下游: '下游转租',
  委托: '委托协议',
  直租: '直租合同',
};

const RELATION_TYPE_COLORS: Record<string, string> = {
  上游: 'gold',
  下游: 'blue',
  委托: 'cyan',
  直租: 'green',
};

const PROJECT_RELATION_KIND_META: Record<
  ProjectContractRelation['relation_kind'],
  {
    label: string;
    color: string;
    primaryLabel: string;
    terminalLabel: string;
  }
> = {
  lease_sublease: {
    label: '承租转租',
    color: 'gold',
    primaryLabel: '上游合同',
    terminalLabel: '下游合同',
  },
  agency_operation: {
    label: '代理运营',
    color: 'cyan',
    primaryLabel: '委托协议',
    terminalLabel: '直租合同',
  },
};

const PROJECT_RELATION_CONTRACT_ACTIONS: Record<
  ProjectContractRelation['relation_kind'],
  Array<{ label: string; role: GroupRelationType }>
> = {
  lease_sublease: [
    { label: '新增上游承租合同', role: 'UPSTREAM' },
    { label: '新增下游出租合同', role: 'DOWNSTREAM' },
  ],
  agency_operation: [
    { label: '新增委托协议', role: 'ENTRUSTED' },
    { label: '新增直租合同', role: 'DIRECT_LEASE' },
  ],
};

const PROJECT_RISK_SEVERITY_COLORS: Record<string, string> = {
  critical: 'red',
  error: 'red',
  warning: 'orange',
  info: 'blue',
};

const buildPeriodParams = (month: Dayjs) => ({
  period_start: month.startOf('month').format('YYYY-MM-DD'),
  period_end: month.endOf('month').format('YYYY-MM-DD'),
});

const formatCurrency = (value: string | number | null | undefined): string => {
  const amount = Number(value ?? 0);
  if (!Number.isFinite(amount)) {
    return '¥0.00';
  }
  return `¥${amount.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

const buildCustomerDetailPath = (partyId: string | null | undefined): string | null => {
  if (partyId == null || partyId.trim() === '') {
    return null;
  }
  return CUSTOMER_ROUTES.DETAIL(partyId);
};

const buildNewContractPath = ({
  relationId,
  projectId,
  role,
}: {
  relationId: string;
  projectId: string;
  role: GroupRelationType;
}) =>
  `${CONTRACT_CENTER_ROUTES.NEW_CONTRACT(relationId)}?project_id=${encodeURIComponent(
    projectId
  )}&role=${role}`;

const getProjectRiskTagColor = (risk: ProjectRiskItem): string =>
  PROJECT_RISK_SEVERITY_COLORS[risk.severity] ?? 'orange';

const getAnalysisModeColor = (mode: ProjectAnalysisModeSummary): string =>
  PROJECT_RELATION_KIND_META[mode.relation_kind]?.color ?? 'blue';

const formatSuppressedMetric = (value: number | null | undefined): string =>
  value == null ? '需选视图' : String(value);

const formatTrendDelta = (current: string | number, previous: string | number): string => {
  const currentValue = Number(current);
  const previousValue = Number(previous);
  if (!Number.isFinite(currentValue) || !Number.isFinite(previousValue)) {
    return '0.0%';
  }
  if (previousValue === 0) {
    return currentValue === 0 ? '0.0%' : '+100.0%';
  }
  const delta = ((currentValue - previousValue) / Math.abs(previousValue)) * 100;
  const prefix = delta > 0 ? '+' : '';
  return `${prefix}${delta.toFixed(1)}%`;
};

// 子组件：逐资产获取租赁汇总，避免在 map 中调用 hook
interface AssetLeaseSummaryRowData {
  queryScopeKey: string;
  assetId: string;
  assetName: string;
  periodParams: { period_start: string; period_end: string };
}

const useAssetLeaseSummary = (
  queryScopeKey: string,
  assetId: string,
  periodParams: { period_start: string; period_end: string },
  enabled: boolean
) =>
  useQuery<AssetLeaseSummaryResponse>({
    queryKey: [
      'asset-lease-summary',
      queryScopeKey,
      assetId,
      periodParams.period_start,
      periodParams.period_end,
    ],
    queryFn: () => assetService.getAssetLeaseSummary(assetId, periodParams),
    staleTime: 60_000,
    enabled,
  });

const AssetLeaseSummaryRow: React.FC<
  AssetLeaseSummaryRowData & {
    onNavigate: (id: string) => void;
    onNavigateCustomer: (id: string) => void;
    enabled: boolean;
  }
> = ({
  queryScopeKey,
  assetId,
  assetName,
  periodParams,
  onNavigate,
  onNavigateCustomer,
  enabled,
}) => {
  const { data, isLoading } = useAssetLeaseSummary(queryScopeKey, assetId, periodParams, enabled);

  if (isLoading) {
    return (
      <tr>
        <td colSpan={7}>
          <Skeleton active paragraph={{ rows: 1 }} title={false} />
        </td>
      </tr>
    );
  }

  const byType = data?.by_type ?? [];
  const typeMap = Object.fromEntries(byType.map(t => [t.group_relation_type, t.contract_count]));
  const totalContracts = data?.total_contracts ?? 0;
  const occupancyRate = data?.occupancy_rate ?? 0;
  const customerCount = data?.customer_summary.length ?? 0;

  return (
    <tr>
      <td>
        <Button type="link" style={{ padding: 0 }} onClick={() => onNavigate(assetId)}>
          {assetName}
        </Button>
      </td>
      {['上游', '下游', '委托', '直租'].map(rt => (
        <td key={rt} style={{ textAlign: 'center' }}>
          {(typeMap[rt] ?? 0) > 0 ? (
            <Tag color={RELATION_TYPE_COLORS[rt]}>{typeMap[rt]}</Tag>
          ) : (
            <Text type="secondary">—</Text>
          )}
        </td>
      ))}
      <td style={{ textAlign: 'right' }}>
        <Text strong={occupancyRate > 0}>
          {occupancyRate > 0 ? `${occupancyRate.toFixed(1)}%` : '—'}
        </Text>
      </td>
      <td style={{ textAlign: 'center' }}>
        {customerCount > 0 ? (
          <Space size={8} wrap>
            <Tooltip title={data?.customer_summary.map(c => c.party_name).join('、')}>
              <Tag>{customerCount} 家</Tag>
            </Tooltip>
            {(data?.customer_summary ?? [])
              .filter(customer => buildCustomerDetailPath(customer.party_id) != null)
              .slice(0, 2)
              .map(customer => (
                <Button
                  key={`${customer.party_id}-${customer.party_name}`}
                  type="link"
                  style={{ padding: 0 }}
                  aria-label={`查看客户${customer.party_name}详情`}
                  onClick={() => {
                    if (customer.party_id != null) {
                      onNavigateCustomer(customer.party_id);
                    }
                  }}
                >
                  {customer.party_name}
                </Button>
              ))}
          </Space>
        ) : (
          <Text type="secondary">—</Text>
        )}
      </td>
      <td style={{ textAlign: 'right' }}>
        <Text type="secondary" style={{ fontSize: '0.75rem' }}>
          {totalContracts} 份合同
        </Text>
      </td>
    </tr>
  );
};

/**
 * ProjectDetailPage - 项目详情页面组件
 *
 * 功能：
 * - 根据URL参数获取项目ID
 * - 展示项目基本信息
 * - 展示关联资产列表
 * - 展示统计卡片（资产数量、总面积、出租率）
 * - 展示各资产租赁情况汇总（合同口径，按 group_relation_type 分类）
 */
const ProjectDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [selectedMonth, setSelectedMonth] = useState<Dayjs>(() => dayjs().startOf('month'));
  const periodParams = useMemo(() => buildPeriodParams(selectedMonth), [selectedMonth]);
  const queryScopeKey = buildQueryScopeKey();
  const hasProjectId = id != null && id.length > 0;
  const canQuery = hasProjectId;

  // 获取项目详情
  const {
    data: project,
    isLoading: projectLoading,
    error: projectError,
  } = useQuery({
    queryKey: ['project', queryScopeKey, id],
    queryFn: () => projectService.getProject(id as string),
    enabled: canQuery,
  });

  // 获取项目关联资产
  const { data: assetsData, isLoading: assetsLoading } = useQuery({
    queryKey: ['project-assets', queryScopeKey, id],
    queryFn: () => projectService.getProjectAssets(id as string),
    enabled: canQuery,
  });

  const { data: contractRelationsData, isLoading: contractRelationsLoading } = useQuery({
    queryKey: ['project-contract-relations', queryScopeKey, id],
    queryFn: () => projectService.getProjectContractRelations(id as string),
    enabled: canQuery,
    staleTime: 60_000,
  });

  const { data: ledgerSummaryData, isLoading: ledgerSummaryLoading } = useQuery({
    queryKey: ['project-ledger-summary', queryScopeKey, id],
    queryFn: () => projectService.getProjectLedgerSummary(id as string),
    enabled: canQuery,
    staleTime: 60_000,
  });

  const { data: projectRisksData, isLoading: projectRisksLoading } = useQuery({
    queryKey: ['project-risks', queryScopeKey, id],
    queryFn: () => projectService.getProjectRisks(id as string),
    enabled: canQuery,
    staleTime: 60_000,
  });

  const { data: projectTenantsData, isLoading: projectTenantsLoading } = useQuery({
    queryKey: ['project-tenants', queryScopeKey, id],
    queryFn: () => projectService.getProjectTenants(id as string),
    enabled: canQuery,
    staleTime: 60_000,
  });

  const { data: projectAnalyticsData, isLoading: projectAnalyticsLoading } = useQuery({
    queryKey: ['project-analytics', queryScopeKey, id],
    queryFn: () => projectService.getProjectAnalytics(id as string),
    enabled: canQuery,
    staleTime: 60_000,
  });

  // 资产表格列定义
  const assetColumns: ColumnsType<Asset> = [
    {
      title: '物业名称',
      dataIndex: 'asset_name',
      key: 'asset_name',
      render: (text: string, record: Asset) => (
        <Button
          type="link"
          className={styles.assetLinkButton}
          onClick={() => navigate(`/assets/${record.id}`)}
        >
          {text}
        </Button>
      ),
    },
    {
      title: '使用状态',
      dataIndex: 'usage_status',
      key: 'usage_status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          已出租: 'green',
          空置: 'orange',
          自用: 'blue',
          维修中: 'red',
        };
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: '可出租面积 (㎡)',
      dataIndex: 'rentable_area',
      key: 'rentable_area',
      align: 'right',
      render: (val?: number | null) => (val != null ? val.toLocaleString() : '-'),
    },
    {
      title: '已出租面积 (㎡)',
      dataIndex: 'rented_area',
      key: 'rented_area',
      align: 'right',
      render: (val?: number | null) => (val != null ? val.toLocaleString() : '-'),
    },
    {
      title: '租户',
      dataIndex: 'tenant_name',
      key: 'tenant_name',
      render: (text: string) => text || '-',
    },
  ];

  // 计算统计数据
  const assets = useMemo(() => assetsData?.items ?? [], [assetsData?.items]);
  const contractRelations = contractRelationsData?.items ?? [];
  const leaseSubleaseCount = contractRelations.filter(
    relation => relation.relation_kind === 'lease_sublease'
  ).length;
  const agencyOperationCount = contractRelations.filter(
    relation => relation.relation_kind === 'agency_operation'
  ).length;
  const projectRisks = projectRisksData?.items ?? [];
  const projectTenants = projectTenantsData?.items ?? [];
  const projectTenantContractCount = projectTenants.reduce(
    (total, item) => total + item.contract_count,
    0
  );
  const ledgerSummary = ledgerSummaryData ?? {
    receivable_amount: '0.00',
    payable_amount: '0.00',
    received_amount: '0.00',
    paid_amount: '0.00',
    overdue_amount: '0.00',
    service_fee_receivable: '0.00',
    service_fee_received: '0.00',
    terminal_collection: {
      amount_due: '0.00',
      paid_amount: '0.00',
      outstanding_amount: '0.00',
      overdue_amount: '0.00',
    },
    operator_income: {
      amount_due: '0.00',
      paid_amount: '0.00',
      outstanding_amount: '0.00',
      overdue_amount: '0.00',
    },
    operator_cost: {
      amount_due: '0.00',
      paid_amount: '0.00',
      outstanding_amount: '0.00',
      overdue_amount: '0.00',
    },
    service_fee_settlement: {
      amount_due: '0.00',
      paid_amount: '0.00',
      outstanding_amount: '0.00',
      overdue_amount: '0.00',
    },
    operating_result: {
      accrual_net_amount: '0.00',
      cash_net_amount: '0.00',
    },
  };
  const ledgerSummaryItems = [
    {
      label: '终端租户收缴',
      value: ledgerSummary.terminal_collection.paid_amount,
      detail: `应收 ${formatCurrency(ledgerSummary.terminal_collection.amount_due)} / 未收 ${formatCurrency(ledgerSummary.terminal_collection.outstanding_amount)}`,
      ledgerView: 'terminal_collection',
    },
    {
      label: '运营方收入',
      value: ledgerSummary.operator_income.paid_amount,
      detail: `应收 ${formatCurrency(ledgerSummary.operator_income.amount_due)} / 未收 ${formatCurrency(ledgerSummary.operator_income.outstanding_amount)}`,
      ledgerView: 'operator_income',
    },
    {
      label: '运营方成本',
      value: ledgerSummary.operator_cost.paid_amount,
      detail: `应付 ${formatCurrency(ledgerSummary.operator_cost.amount_due)} / 未付 ${formatCurrency(ledgerSummary.operator_cost.outstanding_amount)}`,
      ledgerView: 'operator_cost',
    },
    {
      label: '服务费结算',
      value: ledgerSummary.service_fee_settlement.paid_amount,
      detail: `应收 ${formatCurrency(ledgerSummary.service_fee_settlement.amount_due)} / 未收 ${formatCurrency(ledgerSummary.service_fee_settlement.outstanding_amount)}`,
      ledgerView: 'service_fee_settlement',
    },
    {
      label: '经营净流入',
      value: ledgerSummary.operating_result.cash_net_amount,
      detail: `账面差额 ${formatCurrency(ledgerSummary.operating_result.accrual_net_amount)}`,
      ledgerView: 'operator_income',
    },
  ];
  const buildProjectLedgerPath = (ledgerView: string): string =>
    `${OPERATIONS_ROUTES.LEDGER}?project_id=${encodeURIComponent(
      id as string
    )}&ledger_view=${ledgerView}`;
  const summary = assetsData?.summary ?? {
    total_assets: 0,
    total_rentable_area: 0,
    total_rented_area: 0,
    occupancy_rate: 0,
  };
  const totalAssets = summary.total_assets;
  const totalRentableArea = summary.total_rentable_area;
  const totalRentedArea = summary.total_rented_area;
  const occupancyRate = summary.occupancy_rate;
  const occupancyToneClass =
    occupancyRate >= 80
      ? styles.occupancySuccess
      : occupancyRate >= 50
        ? styles.occupancyWarning
        : styles.occupancyError;
  const monthlyTrends = projectAnalyticsData?.monthly_trends ?? [];
  const latestTrend = monthlyTrends.at(-1);
  const previousTrend = monthlyTrends.at(-2);
  const receivableTrendText =
    latestTrend != null && previousTrend != null
      ? formatTrendDelta(latestTrend.receivable_amount, previousTrend.receivable_amount)
      : null;

  const {
    data: assetRows,
    loading: assetTableLoading,
    pagination: assetPagination,
    loadList: loadAssetList,
    updatePagination: updateAssetPagination,
  } = useArrayListData<Asset, Record<string, never>>({
    items: assets,
    initialFilters: {},
    initialPageSize: 10,
  });

  useEffect(() => {
    void loadAssetList({ page: 1 });
  }, [assets, loadAssetList]);

  if (!canQuery) {
    return (
      <PageContainer title="项目详情" loading onBack={() => navigate(PROJECT_ROUTES.LIST)}>
        <div />
      </PageContainer>
    );
  }

  // 错误状态
  if (projectError) {
    return (
      <PageContainer title="项目详情" onBack={() => navigate(PROJECT_ROUTES.LIST)}>
        <Alert
          title="数据加载失败"
          description={`错误详情: ${projectError instanceof Error ? projectError.message : '未知错误'}`}
          type="error"
          showIcon
        />
      </PageContainer>
    );
  }

  // 数据不存在状态
  if (!projectLoading && !project) {
    return (
      <PageContainer title="项目详情" onBack={() => navigate(PROJECT_ROUTES.LIST)}>
        <Alert title="项目不存在" description="未找到指定的项目信息" type="warning" showIcon />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={
        <span className={styles.projectTitle}>
          <span>{project?.project_name}</span>
          {project && (
            <Badge
              status={(PROJECT_STATUS_MAP[project.status]?.active ?? false) ? 'success' : 'default'}
              text={PROJECT_STATUS_MAP[project.status]?.text ?? project.status}
              className={styles.projectStatus}
            />
          )}
        </span>
      }
      loading={projectLoading}
      onBack={() => navigate(PROJECT_ROUTES.LIST)}
      extra={
        <Button
          type="primary"
          icon={<EditOutlined />}
          className={styles.editButton}
          onClick={() => navigate(`/project/${id}/edit`)}
        >
          编辑项目
        </Button>
      }
    >
      <Row gutter={[16, 16]} className={styles.metricsRow}>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.metricCard}>
            <Statistic
              title="关联资产"
              value={totalAssets}
              prefix={<HomeOutlined />}
              suffix="个"
              className={styles.metricPrimary}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.metricCard}>
            <Statistic
              title="可出租总面积"
              value={totalRentableArea}
              precision={2}
              prefix={<AreaChartOutlined />}
              suffix="㎡"
              className={styles.metricSuccess}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.metricCard}>
            <Statistic
              title="已出租面积"
              value={totalRentedArea}
              precision={2}
              prefix={<TeamOutlined />}
              suffix="㎡"
              className={styles.metricWarning}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.metricCard}>
            <Statistic
              title="出租率"
              value={occupancyRate}
              precision={1}
              suffix="%"
              className={occupancyToneClass}
            />
          </Card>
        </Col>
      </Row>

      {/* 项目基本信息 */}
      {project && (
        <>
          <Card title="项目信息" className={styles.infoCard}>
            <Descriptions column={2}>
              <Descriptions.Item label="项目编码">
                <Text code>{project.project_code}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="业务状态">
                <Tag color={PROJECT_STATUS_MAP[project.status]?.color ?? 'default'}>
                  {PROJECT_STATUS_MAP[project.status]?.text ?? project.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="项目状态">
                <Tag
                  color={project.data_status === '正常' ? 'green' : 'default'}
                  className={styles.projectDataStatusTag}
                >
                  {project.data_status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {project.created_at ? new Date(project.created_at).toLocaleString('zh-CN') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {project.updated_at ? new Date(project.updated_at).toLocaleString('zh-CN') : '-'}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card
            className={styles.contractRelationCard}
            title={
              <div className={styles.contractRelationHeader}>
                <Space className={styles.assetTableTitle}>
                  <span>合同关系</span>
                  <Badge
                    count={contractRelationsData?.total ?? 0}
                    className={styles.assetCountBadge}
                  />
                </Space>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  aria-label="新建合同关系"
                  onClick={() =>
                    navigate(
                      `${CONTRACT_CENTER_ROUTES.NEW}?project_id=${encodeURIComponent(id as string)}`
                    )
                  }
                >
                  新建合同关系
                </Button>
              </div>
            }
          >
            <div className={styles.relationSummaryStrip}>
              <div className={styles.relationSummaryItem}>
                <Text type="secondary">承租转租</Text>
                <Text strong>{leaseSubleaseCount}</Text>
              </div>
              <div className={styles.relationSummaryItem}>
                <Text type="secondary">代理运营</Text>
                <Text strong>{agencyOperationCount}</Text>
              </div>
              <div className={styles.relationSummaryItem}>
                <Text type="secondary">覆盖资产</Text>
                <Text strong>
                  {new Set(contractRelations.flatMap(relation => relation.asset_ids ?? [])).size}
                </Text>
              </div>
            </div>

            {contractRelationsLoading ? (
              <Skeleton active paragraph={{ rows: 3 }} />
            ) : contractRelations.length === 0 ? (
              <Empty description="暂无合同关系" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <div className={styles.relationGrid}>
                {contractRelations.map(relation => {
                  const meta = PROJECT_RELATION_KIND_META[relation.relation_kind];
                  const riskTags = relation.risk_tags ?? [];
                  return (
                    <div key={relation.contract_relation_id} className={styles.relationItem}>
                      <div className={styles.relationItemHeader}>
                        <Space size={8} wrap>
                          <Tag color={meta.color}>{meta.label}</Tag>
                          <Text strong>{relation.display_name}</Text>
                        </Space>
                        <Button
                          type="link"
                          className={styles.relationDetailButton}
                          onClick={() =>
                            navigate(CONTRACT_CENTER_ROUTES.DETAIL(relation.contract_relation_id))
                          }
                        >
                          查看明细
                        </Button>
                      </div>
                      <div className={styles.relationFacts}>
                        <div>
                          <Text type="secondary">{meta.primaryLabel}</Text>
                          <Text strong>{relation.primary_contract_ids.length}</Text>
                        </div>
                        <div>
                          <Text type="secondary">{meta.terminalLabel}</Text>
                          <Text strong>{relation.terminal_contract_ids.length}</Text>
                        </div>
                        <div>
                          <Text type="secondary">关联资产</Text>
                          <Text strong>{relation.asset_ids.length}</Text>
                        </div>
                        <div>
                          <Text type="secondary">状态</Text>
                          <Tag className={styles.relationStatusTag}>{relation.derived_status}</Tag>
                        </div>
                      </div>
                      {riskTags.length > 0 && (
                        <div className={styles.relationRiskTags}>
                          {riskTags.map(tag => (
                            <Tag key={`${relation.contract_relation_id}-${tag}`} color="orange">
                              {tag}
                            </Tag>
                          ))}
                        </div>
                      )}
                      <div className={styles.relationActions}>
                        {PROJECT_RELATION_CONTRACT_ACTIONS[relation.relation_kind].map(action => (
                          <Button
                            key={`${relation.contract_relation_id}-${action.role}`}
                            size="small"
                            onClick={() =>
                              navigate(
                                buildNewContractPath({
                                  relationId: relation.contract_relation_id,
                                  projectId: id as string,
                                  role: action.role,
                                })
                              )
                            }
                          >
                            {action.label}
                          </Button>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          <Card className={styles.assetTableCard} title="收付款摘要">
            {ledgerSummaryLoading ? (
              <Skeleton active paragraph={{ rows: 2 }} />
            ) : (
              <>
                <div className={styles.relationSummaryStrip}>
                  {ledgerSummaryItems.map(item => (
                    <button
                      key={item.label}
                      type="button"
                      className={styles.relationSummaryButton}
                      onClick={() => navigate(buildProjectLedgerPath(item.ledgerView))}
                    >
                      <Text type="secondary">{item.label}</Text>
                      <Text strong>{formatCurrency(item.value)}</Text>
                      <Text type="secondary">{item.detail}</Text>
                    </button>
                  ))}
                </div>
              </>
            )}
          </Card>

          <Card className={styles.assetTableCard} title="风险提示">
            {projectRisksLoading ? (
              <Skeleton active paragraph={{ rows: 2 }} />
            ) : projectRisks.length > 0 ? (
              <div className={styles.projectRiskList}>
                {projectRisks.map(risk => (
                  <div key={risk.risk_id} className={styles.projectRiskItem}>
                    <Tag color={getProjectRiskTagColor(risk)}>{risk.message}</Tag>
                    {risk.display_name != null && risk.display_name.trim() !== '' && (
                      <Text type="secondary">{risk.display_name}</Text>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <Empty description="暂无风险提示" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>

          <Card className={styles.assetTableCard} title="租户/客户">
            {projectTenantsLoading ? (
              <Skeleton active paragraph={{ rows: 2 }} />
            ) : projectTenants.length > 0 ? (
              <>
                <div className={styles.relationSummaryStrip}>
                  <div className={styles.relationSummaryItem}>
                    <Text type="secondary">客户主体</Text>
                    <Text strong>{projectTenants.length}</Text>
                  </div>
                  <div className={styles.relationSummaryItem}>
                    <Text type="secondary">客户合同</Text>
                    <Text strong>{projectTenantContractCount} 份合同</Text>
                  </div>
                  <div className={styles.relationSummaryItem}>
                    <Text type="secondary">直租客户</Text>
                    <Text strong>
                      {projectTenants.filter(item => item.group_relation_type === '直租').length}
                    </Text>
                  </div>
                </div>
                <div className={styles.projectTenantList}>
                  {projectTenants.slice(0, 6).map(item => {
                    const detailPath = buildCustomerDetailPath(item.party_id);
                    return (
                      <div
                        key={`${item.party_id}-${item.group_relation_type}`}
                        className={styles.projectTenantItem}
                      >
                        <Space size={8} wrap>
                          <Tag>{item.group_relation_type}</Tag>
                          {detailPath != null ? (
                            <Button
                              type="link"
                              className={styles.tenantLinkButton}
                              aria-label={`查看客户${item.party_name}详情`}
                              onClick={() => navigate(detailPath)}
                            >
                              {item.party_name}
                            </Button>
                          ) : (
                            <Text strong>{item.party_name}</Text>
                          )}
                        </Space>
                        <Text type="secondary">{item.contract_count} 份合同</Text>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <Empty description="暂无租户/客户" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>

          <Card className={styles.assetTableCard} title="项目分析">
            {projectAnalyticsLoading ? (
              <Skeleton active paragraph={{ rows: 2 }} />
            ) : projectAnalyticsData != null ? (
              <>
                <div className={styles.analysisSummaryStrip}>
                  <div className={styles.relationSummaryItem}>
                    <Text type="secondary">合同关系</Text>
                    <Text strong>{projectAnalyticsData.contract_relation_count}</Text>
                  </div>
                  <div className={styles.relationSummaryItem}>
                    <Text type="secondary">客户主体</Text>
                    <Text strong>{formatSuppressedMetric(projectAnalyticsData.tenant_count)}</Text>
                  </div>
                  <div className={styles.relationSummaryItem}>
                    <Text type="secondary">经营风险</Text>
                    <Text strong>{projectAnalyticsData.risk_count}</Text>
                  </div>
                  <div className={styles.relationSummaryItem}>
                    <Text type="secondary">应收</Text>
                    <Text strong>{formatCurrency(projectAnalyticsData.receivable_amount)}</Text>
                  </div>
                </div>
                {projectAnalyticsData.customer_metrics_suppression_reason != null && (
                  <Tag color="gold">客户指标需选产权方或运营方视图</Tag>
                )}
                <div className={styles.analysisModeGrid}>
                  {projectAnalyticsData.mode_summaries.map(mode => (
                    <div key={mode.relation_kind} className={styles.analysisModeItem}>
                      <div className={styles.analysisModeHeader}>
                        <Tag color={getAnalysisModeColor(mode)}>{mode.label}</Tag>
                        <Text type="secondary">{mode.risk_count} 个风险</Text>
                      </div>
                      <div className={styles.analysisModeFacts}>
                        <span>
                          <Text type="secondary">关系</Text>
                          <Text strong>{mode.contract_relation_count}</Text>
                        </span>
                        <span>
                          <Text type="secondary">资产</Text>
                          <Text strong>{mode.asset_count}</Text>
                        </span>
                        <span>
                          <Text type="secondary">客户</Text>
                          <Text strong>{formatSuppressedMetric(mode.customer_count)}</Text>
                        </span>
                        <span>
                          <Text type="secondary">应收</Text>
                          <Text strong>{formatCurrency(mode.receivable_amount)}</Text>
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
                {monthlyTrends.length > 0 && (
                  <div className={styles.analysisTrendPanel}>
                    <div className={styles.analysisModeHeader}>
                      <Text strong>项目分析趋势</Text>
                      {receivableTrendText != null && (
                        <Tag color={receivableTrendText.startsWith('-') ? 'orange' : 'green'}>
                          应收环比 {receivableTrendText}
                        </Tag>
                      )}
                    </div>
                    <div className={styles.analysisTrendList}>
                      {monthlyTrends.slice(-6).map(item => (
                        <div key={item.period} className={styles.analysisTrendItem}>
                          <Text type="secondary">{item.period}</Text>
                          <Text strong>应收 {formatCurrency(item.receivable_amount)}</Text>
                          <Text type="secondary">实收 {formatCurrency(item.received_amount)}</Text>
                          <Text type="secondary">逾期 {formatCurrency(item.overdue_amount)}</Text>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <Empty description="暂无项目分析" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>

          {/* 关联资产列表 */}
          <Card
            className={styles.assetTableCard}
            title={
              <Space className={styles.assetTableTitle}>
                <span>关联资产</span>
                <Badge count={totalAssets} className={styles.assetCountBadge} />
              </Space>
            }
          >
            <TableWithPagination
              columns={assetColumns}
              dataSource={assetRows}
              rowKey="id"
              loading={assetsLoading || assetTableLoading}
              paginationState={assetPagination}
              onPageChange={updateAssetPagination}
              paginationProps={{
                showSizeChanger: true,
                showTotal: (total: number) => `共 ${total} 条`,
              }}
              locale={{ emptyText: '暂无关联资产' }}
            />
          </Card>

          {/* 租赁情况（合同口径） */}
          {assets.length > 0 && (
            <Card
              className={styles.assetTableCard}
              title={
                <Space>
                  <span>租赁情况（合同口径）</span>
                  <Tooltip title="数据来源：各资产活跃合同，不含草稿/待审/已终止/已到期">
                    <InfoCircleOutlined style={{ color: 'var(--color-text-secondary)' }} />
                  </Tooltip>
                </Space>
              }
              extra={
                <DatePicker
                  picker="month"
                  allowClear={false}
                  value={selectedMonth}
                  onChange={value => setSelectedMonth((value ?? dayjs()).startOf('month'))}
                  inputReadOnly
                />
              }
            >
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                  <thead>
                    <tr
                      style={{ borderBottom: 'var(--border-width-thin) solid var(--color-border)' }}
                    >
                      <th style={{ textAlign: 'left', padding: '0.5rem 0.75rem', fontWeight: 600 }}>
                        资产
                      </th>
                      {['上游', '下游', '委托', '直租'].map(rt => (
                        <th
                          key={rt}
                          style={{
                            textAlign: 'center',
                            padding: '0.5rem 0.75rem',
                            fontWeight: 600,
                          }}
                        >
                          <Tag color={RELATION_TYPE_COLORS[rt]} style={{ margin: 0 }}>
                            {RELATION_TYPE_LABELS[rt]}
                          </Tag>
                        </th>
                      ))}
                      <th
                        style={{ textAlign: 'right', padding: '0.5rem 0.75rem', fontWeight: 600 }}
                      >
                        出租率
                      </th>
                      <th
                        style={{ textAlign: 'center', padding: '0.5rem 0.75rem', fontWeight: 600 }}
                      >
                        客户摘要
                      </th>
                      <th
                        style={{ textAlign: 'right', padding: '0.5rem 0.75rem', fontWeight: 600 }}
                      >
                        合同数
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {assets.map(asset => (
                      <AssetLeaseSummaryRow
                        key={asset.id}
                        queryScopeKey={queryScopeKey}
                        assetId={asset.id}
                        assetName={asset.asset_name}
                        periodParams={periodParams}
                        enabled={canQuery}
                        onNavigate={assetId => navigate(`/assets/${assetId}`)}
                        onNavigateCustomer={customerId => {
                          const nextPath = buildCustomerDetailPath(customerId);
                          if (nextPath != null) {
                            navigate(nextPath);
                          }
                        }}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
              <Text
                type="secondary"
                style={{ display: 'block', marginTop: '0.5rem', fontSize: '0.75rem' }}
              >
                注：MVP 阶段出租率目前为占位值 0%，后续将按有效合同面积口径升级。
              </Text>
            </Card>
          )}
        </>
      )}
    </PageContainer>
  );
};

export default ProjectDetailPage;
