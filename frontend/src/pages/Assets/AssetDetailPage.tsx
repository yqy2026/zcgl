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
import { useQuery } from '@tanstack/react-query';
import dayjs, { type Dayjs } from 'dayjs';
import { assetService } from '@/services/assetService';
import { useRoutePerspective } from '@/routes/perspective';
import type {
  AssetLeaseGroupRelationType,
  AssetLeaseSummaryResponse,
  ContractPartyItem,
  ContractTypeSummary,
} from '@/types/asset';
import { buildQueryScopeKey } from '@/utils/queryScope';
import { formatArea, formatCurrency } from '@/utils/format';
import AssetDetailInfo from '@/components/Asset/AssetDetailInfo';
import { PageContainer } from '@/components/Common';
import styles from './AssetDetailPage.module.css';

const { Text } = Typography;

const RELATION_TYPE_COLORS: Record<AssetLeaseGroupRelationType, string> = {
  上游: 'gold',
  下游: 'blue',
  委托: 'cyan',
  直租: 'green',
};

const AGENCY_RELATION_TYPES: AssetLeaseGroupRelationType[] = ['委托', '直租'];

const buildPeriodParams = (month: Dayjs) => ({
  period_start: month.startOf('month').format('YYYY-MM-DD'),
  period_end: month.endOf('month').format('YYYY-MM-DD'),
});

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
  const { perspective } = useRoutePerspective();
  const [selectedMonth, setSelectedMonth] = useState<Dayjs>(() => dayjs().startOf('month'));
  const hasAssetId = id != null && id !== '';
  const canQuery = hasAssetId;
  const periodParams = useMemo(() => buildPeriodParams(selectedMonth), [selectedMonth]);
  const queryScopeKey = buildQueryScopeKey(perspective);

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
              <Text strong>{item.party_name}</Text>
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
