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
  Skeleton,
  Tooltip,
} from 'antd';
import {
  EditOutlined,
  HomeOutlined,
  AreaChartOutlined,
  TeamOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import dayjs, { type Dayjs } from 'dayjs';
import { projectService } from '@/services/projectService';
import { assetService } from '@/services/assetService';
import CurrentViewBanner from '@/components/System/CurrentViewBanner';
import { useRoutePerspective } from '@/routes/perspective';
import type { ColumnsType } from 'antd/es/table';
import type { Asset, AssetLeaseSummaryResponse } from '@/types/asset';
import { useArrayListData } from '@/hooks/useArrayListData';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { PageContainer } from '@/components/Common';
import { buildQueryScopeKey } from '@/utils/queryScope';
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

const buildPeriodParams = (month: Dayjs) => ({
  period_start: month.startOf('month').format('YYYY-MM-DD'),
  period_end: month.endOf('month').format('YYYY-MM-DD'),
});

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
  AssetLeaseSummaryRowData & { onNavigate: (id: string) => void; enabled: boolean }
> = ({ queryScopeKey, assetId, assetName, periodParams, onNavigate, enabled }) => {
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
          <Tooltip title={data?.customer_summary.map(c => c.party_name).join('、')}>
            <Tag>{customerCount} 家</Tag>
          </Tooltip>
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
  const { perspective } = useRoutePerspective();
  const [selectedMonth, setSelectedMonth] = useState<Dayjs>(() => dayjs().startOf('month'));
  const periodParams = useMemo(() => buildPeriodParams(selectedMonth), [selectedMonth]);
  const queryScopeKey = buildQueryScopeKey(perspective);
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
      <PageContainer title="项目详情" loading onBack={() => navigate('/project')}>
        <div />
      </PageContainer>
    );
  }

  // 错误状态
  if (projectError) {
    return (
      <PageContainer title="项目详情" onBack={() => navigate('/project')}>
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
      <PageContainer title="项目详情" onBack={() => navigate('/project')}>
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
      onBack={() => navigate('/project')}
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
      <CurrentViewBanner />

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
                      />
                    ))}
                  </tbody>
                </table>
              </div>
              <Text
                type="secondary"
                style={{ display: 'block', marginTop: '0.5rem', fontSize: '0.75rem' }}
              >
                注：MVP 阶段面积字段以合同台账落地后口径为准；出租率目前为占位值
                0%，待台账覆盖后升级。
              </Text>
            </Card>
          )}
        </>
      )}
    </PageContainer>
  );
};

export default ProjectDetailPage;
