import React, { useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Empty,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import { EditOutlined, TeamOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import dayjs, { type Dayjs } from 'dayjs';
import { assetService } from '@/services/assetService';
import type {
  AssetReviewLog,
  AssetLeaseGroupRelationType,
  AssetLeaseSummaryResponse,
  ContractPartyItem,
  ContractTypeSummary,
} from '@/types/asset';
import { buildQueryScopeKey } from '@/utils/queryScope';
import { formatArea, formatCurrency } from '@/utils/format';
import AssetDetailInfo from '@/components/Asset/AssetDetailInfo';
import { PageContainer } from '@/components/Common';
import { CUSTOMER_ROUTES } from '@/constants/routes';
import { MessageManager } from '@/utils/messageManager';
import styles from './AssetDetailPage.module.css';

const { Text } = Typography;

const RELATION_TYPE_COLORS: Record<AssetLeaseGroupRelationType, string> = {
  上游: 'gold',
  下游: 'blue',
  委托: 'cyan',
  直租: 'green',
};

const AGENCY_RELATION_TYPES: AssetLeaseGroupRelationType[] = ['委托', '直租'];

const REVIEW_STATUS_META: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  pending: { color: 'processing', label: '待审核' },
  approved: { color: 'success', label: '已审核' },
  reversed: { color: 'warning', label: '已反审核' },
};

const buildPeriodParams = (month: Dayjs) => ({
  period_start: month.startOf('month').format('YYYY-MM-DD'),
  period_end: month.endOf('month').format('YYYY-MM-DD'),
});

const buildCustomerDetailPath = (
  partyId: string | null | undefined
): string | null => {
  if (partyId == null || partyId.trim() === '') {
    return null;
  }
  return CUSTOMER_ROUTES.DETAIL(partyId);
};

const summaryColumns: ColumnsType<ContractTypeSummary> = [
  {
    title: '合同角色',
    dataIndex: 'label',
    key: 'label',
    render: (_, record) => (
      <Space size={8}>
        <Tag color={RELATION_TYPE_COLORS[record.group_relation_type]}>
          {record.group_relation_type}
        </Tag>
        <span>{record.label}</span>
      </Space>
    ),
  },
  {
    title: '合同数',
    dataIndex: 'contract_count',
    key: 'contract_count',
    width: 120,
  },
  {
    title: '面积',
    dataIndex: 'total_area',
    key: 'total_area',
    width: 160,
    render: value => formatArea(value),
  },
  {
    title: '月度金额',
    dataIndex: 'monthly_amount',
    key: 'monthly_amount',
    width: 180,
    render: value => formatCurrency(value),
  },
];

const AssetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedMonth, setSelectedMonth] = useState<Dayjs>(() => dayjs().startOf('month'));
  const hasAssetId = id != null && id !== '';
  const canQuery = hasAssetId;
  const periodParams = useMemo(() => buildPeriodParams(selectedMonth), [selectedMonth]);
  const queryScopeKey = buildQueryScopeKey();

  const {
    data: asset,
    isLoading: isAssetLoading,
    error: assetError,
  } = useQuery({
    queryKey: ['asset', queryScopeKey, id],
    queryFn: () => assetService.getAsset(id as string),
    enabled: canQuery,
  });

  const {
    data: reviewLogs,
    isLoading: isReviewLogsLoading,
  } = useQuery<AssetReviewLog[]>({
    queryKey: ['asset-review-logs', queryScopeKey, id],
    queryFn: () => assetService.getAssetReviewLogs(id as string),
    enabled: canQuery,
  });

  const syncAssetDetail = (nextAsset: unknown) => {
    queryClient.setQueryData(['asset', queryScopeKey, id], nextAsset);
    void queryClient.invalidateQueries({ queryKey: ['asset-review-logs', queryScopeKey, id] });
  };

  const submitReviewMutation = useMutation({
    mutationFn: async () => assetService.submitAssetReview(id as string),
    onSuccess: updatedAsset => {
      syncAssetDetail(updatedAsset);
      MessageManager.success('资产已提交审核');
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '提交审核失败');
    },
  });

  const approveReviewMutation = useMutation({
    mutationFn: async () => assetService.approveAssetReview(id as string),
    onSuccess: updatedAsset => {
      syncAssetDetail(updatedAsset);
      MessageManager.success('资产审核已通过');
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '审核通过失败');
    },
  });

  const rejectReviewMutation = useMutation({
    mutationFn: async (reason: string) => assetService.rejectAssetReview(id as string, reason),
    onSuccess: updatedAsset => {
      syncAssetDetail(updatedAsset);
      MessageManager.success('资产已驳回回草稿');
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '驳回审核失败');
    },
  });

  const reverseReviewMutation = useMutation({
    mutationFn: async (reason: string) => assetService.reverseAssetReview(id as string, reason),
    onSuccess: updatedAsset => {
      syncAssetDetail(updatedAsset);
      MessageManager.success('资产已反审核');
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '反审核失败');
    },
  });

  const resubmitReviewMutation = useMutation({
    mutationFn: async () => assetService.resubmitAssetReview(id as string),
    onSuccess: updatedAsset => {
      syncAssetDetail(updatedAsset);
      MessageManager.success('资产已重新提交审核');
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '重提审核失败');
    },
  });

  const withdrawReviewMutation = useMutation({
    mutationFn: async (reason?: string) => assetService.withdrawAssetReview(id as string, reason),
    onSuccess: updatedAsset => {
      syncAssetDetail(updatedAsset);
      MessageManager.success('资产审核已撤回');
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '撤回审核失败');
    },
  });

  const {
    data: leaseSummary,
    isLoading: isLeaseSummaryLoading,
    error: leaseSummaryError,
  } = useQuery<AssetLeaseSummaryResponse>({
    queryKey: [
      'asset-lease-summary',
      queryScopeKey,
      id,
      periodParams.period_start,
      periodParams.period_end,
    ],
    queryFn: () => assetService.getAssetLeaseSummary(id as string, periodParams),
    enabled: canQuery,
  });

  if (!canQuery) {
    return (
      <PageContainer title="资产详情" loading onBack={() => navigate('/assets')}>
        <div />
      </PageContainer>
    );
  }

  if (assetError) {
    return (
      <PageContainer title="资产详情" onBack={() => navigate('/assets')}>
        <Alert
          title="数据加载失败"
          description={`错误详情: ${assetError instanceof Error ? assetError.message : '未知错误'}`}
          type="error"
          showIcon
        />
      </PageContainer>
    );
  }

  if (!isAssetLoading && !asset) {
    return (
      <PageContainer title="资产详情" onBack={() => navigate('/assets')}>
        <Alert title="资产不存在" description="未找到指定的资产信息" type="warning" showIcon />
      </PageContainer>
    );
  }

  const renderCustomerSummary = (customers: ContractPartyItem[]) => {
    if (customers.length === 0) {
      return <Empty description="暂无客户摘要" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
    }

    return (
      <div className={styles.customerList}>
        {customers.map(item => (
          <div
            key={`${item.group_relation_type}-${item.party_name}-${item.party_id ?? 'unknown'}`}
            className={styles.customerRow}
          >
            <Space size={8} wrap>
              <Tag color={RELATION_TYPE_COLORS[item.group_relation_type]}>
                {item.group_relation_type}
              </Tag>
              {buildCustomerDetailPath(item.party_id) != null ? (
                <Button
                  type="link"
                  style={{ padding: 0 }}
                  aria-label={`查看客户${item.party_name}详情`}
                  onClick={() => {
                    const nextPath = buildCustomerDetailPath(item.party_id);
                    if (nextPath != null) {
                      navigate(nextPath);
                    }
                  }}
                >
                  {item.party_name}
                </Button>
              ) : (
                <Text strong>{item.party_name}</Text>
              )}
            </Space>
            <Text type="secondary">关联 {item.contract_count} 份合同</Text>
          </div>
        ))}
      </div>
    );
  };

  const renderLeaseSummary = () => {
    if (leaseSummaryError) {
      return (
        <Alert
          title="租赁情况加载失败"
          description={leaseSummaryError instanceof Error ? leaseSummaryError.message : '未知错误'}
          type="error"
          showIcon
        />
      );
    }

    if (leaseSummary == null) {
      return <Empty description="暂无租赁汇总数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
    }

    const hasAgencyModeContracts = leaseSummary.by_type.some(
      item =>
        AGENCY_RELATION_TYPES.includes(item.group_relation_type) && item.contract_count > 0
    );

    return (
      <div className={styles.summaryContent}>
        {hasAgencyModeContracts ? (
          <Alert
            type="info"
            showIcon
            title="代理口径，非自营出租"
            description="本资产当前包含委托/直租合同，终端租金属于代理链路展示，不计入运营方自营出租收入。"
          />
        ) : null}

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={10}>
            <div className={styles.heroPanel}>
              <Text type="secondary" className={styles.heroEyebrow}>
                {selectedMonth.format('YYYY年M月')}
              </Text>
              <Statistic
                title="本月出租率"
                value={leaseSummary.occupancy_rate}
                precision={2}
                suffix="%"
                className={styles.heroStatistic}
              />
              <Text type="secondary" className={styles.heroMeta}>
                已出租/管理面积 {formatArea(leaseSummary.total_rented_area)} / 可出租面积{' '}
                {formatArea(leaseSummary.rentable_area)}
              </Text>
            </div>
          </Col>
          <Col xs={12} lg={7}>
            <Card size="small" className={styles.metricCard}>
              <Statistic title="活跃合同" value={leaseSummary.total_contracts} />
            </Card>
          </Col>
          <Col xs={12} lg={7}>
            <Card size="small" className={styles.metricCard}>
              <Statistic title="客户摘要" value={leaseSummary.customer_summary.length} />
            </Card>
          </Col>
        </Row>

        <div className={styles.sectionBlock}>
          <div className={styles.sectionHeader}>
            <Text strong>合同角色汇总</Text>
            <Text type="secondary">{selectedMonth.format('YYYY年M月')} 活跃合同口径</Text>
          </div>
          <Table
            columns={summaryColumns}
            dataSource={leaseSummary.by_type}
            rowKey={record => record.group_relation_type}
            pagination={false}
            size="small"
            className={styles.summaryTable}
          />
        </div>

        <div className={styles.sectionBlock}>
          <div className={styles.sectionHeader}>
            <Space size={8}>
              <TeamOutlined />
              <Text strong>客户摘要</Text>
            </Space>
            <Text type="secondary">仅统计下游与直租合同客户</Text>
          </div>
          {renderCustomerSummary(leaseSummary.customer_summary)}
        </div>

        <Text type="secondary" className={styles.note}>
          注：MVP 阶段合同面积统一按 0 展示，且多资产合同暂不做面积拆分。
        </Text>
      </div>
    );
  };

  const handleReasonedAction = (action: 'reject' | 'reverse' | 'withdraw') => {
    const reason = window.prompt('请输入原因');
    if (reason == null || reason.trim() === '') {
      return;
    }
    if (action === 'reject') {
      rejectReviewMutation.mutate(reason);
      return;
    }
    if (action === 'reverse') {
      reverseReviewMutation.mutate(reason);
      return;
    }
    withdrawReviewMutation.mutate(reason);
  };

  const reviewStatus = String(asset?.review_status ?? 'draft').trim().toLowerCase();
  const reviewMeta = REVIEW_STATUS_META[reviewStatus] ?? {
    color: 'default',
    label: reviewStatus || '未知',
  };

  return (
    <PageContainer
      title={asset?.asset_name ?? '资产详情'}
      loading={isAssetLoading}
      onBack={() => navigate('/assets')}
      extra={
        <Button
          type="primary"
          icon={<EditOutlined />}
          onClick={() => navigate(`/assets/${id}/edit`)}
          disabled={isAssetLoading}
        >
          编辑资产
        </Button>
      }
    >
      {asset && (
        <div className={styles.pageContent}>
          <AssetDetailInfo asset={asset} />

          <Card title="审核信息" className={styles.leaseCard}>
            <Space size={16} style={{ width: '100%', flexDirection: 'column', alignItems: 'flex-start' }}>
              <Space size={12} wrap>
                <Tag color={reviewMeta.color}>{reviewMeta.label}</Tag>
                {asset.review_reason != null && asset.review_reason.trim() !== '' ? (
                  <Text type="secondary">审核说明：{asset.review_reason}</Text>
                ) : null}
              </Space>
              <Space wrap>
                {reviewStatus === 'draft' ? (
                  <Button onClick={() => submitReviewMutation.mutate()} loading={submitReviewMutation.isPending}>
                    提交审核
                  </Button>
                ) : null}
                {reviewStatus === 'pending' ? (
                  <>
                    <Button onClick={() => approveReviewMutation.mutate()} loading={approveReviewMutation.isPending}>
                      审核通过
                    </Button>
                    <Button onClick={() => handleReasonedAction('reject')} loading={rejectReviewMutation.isPending}>
                      驳回审核
                    </Button>
                    <Button onClick={() => handleReasonedAction('withdraw')} loading={withdrawReviewMutation.isPending}>
                      撤回审核
                    </Button>
                  </>
                ) : null}
                {reviewStatus === 'approved' ? (
                  <Button onClick={() => handleReasonedAction('reverse')} loading={reverseReviewMutation.isPending}>
                    反审核
                  </Button>
                ) : null}
                {reviewStatus === 'reversed' ? (
                  <Button onClick={() => resubmitReviewMutation.mutate()} loading={resubmitReviewMutation.isPending}>
                    重提审核
                  </Button>
                ) : null}
              </Space>
              <div>
                <Text strong>审核日志</Text>
                {isReviewLogsLoading ? (
                  <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                    加载中...
                  </Text>
                ) : reviewLogs == null || reviewLogs.length === 0 ? (
                  <Empty description="暂无审核日志" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                ) : (
                  <Table
                    size="small"
                    pagination={false}
                    rowKey={record => record.id}
                    dataSource={reviewLogs}
                    columns={[
                      { title: '动作', dataIndex: 'action', key: 'action' },
                      { title: '操作人', dataIndex: 'operator', key: 'operator', render: value => value ?? '-' },
                      { title: '原因', dataIndex: 'reason', key: 'reason', render: value => value ?? '-' },
                    ]}
                  />
                )}
              </div>
            </Space>
          </Card>

          <Card
            title="租赁情况"
            className={styles.leaseCard}
            loading={isLeaseSummaryLoading && leaseSummary == null && leaseSummaryError == null}
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
            {renderLeaseSummary()}
          </Card>
        </div>
      )}
    </PageContainer>
  );
};

export default AssetDetailPage;
