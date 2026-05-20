import React from 'react';
import { Card, Row, Col, Spin, Alert, Empty, Typography, Space, Button, Radio, Table } from 'antd';
import styles from './AssetAnalyticsPage.module.css';
import {
  ReloadOutlined,
  DownloadOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
} from '@ant-design/icons';
import {
  AnalyticsStatsGrid,
  FinancialStatsGrid,
  RevenueStatsGrid,
} from '@/components/Analytics/AnalyticsStatsCard';
import { AnalyticsLineChart, chartDataUtils } from '@/components/Analytics/AnalyticsChart';
import AnalyticsFilters from '@/components/Analytics/AnalyticsFilters';
import { createLogger } from '@/utils/logger';
import { useAssetAnalytics, AnalysisDimension } from '@/hooks/useAssetAnalytics';
import { useFullscreen } from '@/hooks/useFullscreen';
import AssetDistributionGrid from '@/components/Analytics/AssetDistributionGrid';
import AssetDistributionDetails from '@/components/Analytics/AssetDistributionDetails';
import type { ColumnsType } from 'antd/es/table';
import type { AnalyticsModeBreakdown, AnalyticsProjectBreakdown } from '@/types/analytics';
import { formatCurrency } from '@/utils/format';

const pageLogger = createLogger('AssetAnalytics');
const CHART_PRIMARY_COLOR = 'var(--color-primary)';

const { Text } = Typography;

const projectBreakdownColumns: ColumnsType<AnalyticsProjectBreakdown> = [
  {
    title: '项目',
    dataIndex: 'project_name',
    key: 'project_name',
  },
  {
    title: '合同关系',
    dataIndex: 'contract_relation_count',
    key: 'contract_relation_count',
    align: 'right',
  },
  {
    title: '承租转租',
    dataIndex: 'lease_relation_count',
    key: 'lease_relation_count',
    align: 'right',
  },
  {
    title: '代理运营',
    dataIndex: 'agency_relation_count',
    key: 'agency_relation_count',
    align: 'right',
  },
  {
    title: '经营收入',
    dataIndex: 'total_income',
    key: 'total_income',
    align: 'right',
    render: (value: number) => formatCurrency(value),
  },
  {
    title: '当期实收',
    dataIndex: 'actual_receipts',
    key: 'actual_receipts',
    align: 'right',
    render: (value: number) => formatCurrency(value),
  },
  {
    title: '客户主体',
    dataIndex: 'customer_entity_count',
    key: 'customer_entity_count',
    align: 'right',
  },
  {
    title: '客户合同',
    dataIndex: 'customer_contract_count',
    key: 'customer_contract_count',
    align: 'right',
  },
];

const getModeCardClassName = (relationKind: AnalyticsModeBreakdown['relation_kind']): string =>
  relationKind === 'agency_operation' ? styles.modeCardAgency : styles.modeCardLease;

const AssetAnalyticsPage: React.FC = () => {
  const {
    analyticsData,
    loading,
    error,
    refetch,
    filters,
    dimension,
    hasData,
    handleFilterChange,
    handleFilterReset,
    handleDimensionChange,
    handleExport,
  } = useAssetAnalytics();

  const { isFullscreen, toggleFullscreen } = useFullscreen();

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <Spin size="large" />
        <div className={styles.loadingText}>加载分析数据中...</div>
      </div>
    );
  }

  if (error) {
    pageLogger.error('Analytics Error:', error);
    return (
      <div className={styles.errorContainer}>
        <Alert
          title="数据加载失败"
          description={`错误详情: ${error instanceof Error ? error.message : '未知错误'}`}
          type="error"
          showIcon
          className={styles.errorAlert}
        />
      </div>
    );
  }

  return (
    <div className={styles.analyticsContainer}>
      {/* 页面标题和操作栏 */}
      <Card className={styles.sectionCard}>
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col xs={24} sm={12}>
            <Typography.Title level={3} className={styles.pageTitle}>
              经营分析
            </Typography.Title>
          </Col>
          <Col xs={24} sm={12}>
            <Space wrap className={styles.headerActions}>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => refetch()}
                loading={loading}
                size="small"
                className="no-print"
              >
                <span className={styles.btnText}>刷新</span>
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
                disabled={hasData === false}
                size="small"
                className="no-print"
              >
                <span className={styles.btnText}>导出</span>
              </Button>
              <Button
                icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                onClick={toggleFullscreen}
                size="small"
                className="no-print"
              >
                <span className={styles.btnText}>{isFullscreen ? '退出全屏' : '全屏'}</span>
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 筛选条件 */}
      <AnalyticsFilters
        filters={filters}
        onFiltersChange={handleFilterChange}
        onResetFilters={handleFilterReset}
        loading={loading}
      />

      {/* 维度切换 */}
      <Card className={styles.sectionCard}>
        <Space align="center" wrap>
          <Text strong>分析维度：</Text>
          <Radio.Group
            value={dimension}
            onChange={e => handleDimensionChange(e.target.value as AnalysisDimension)}
            buttonStyle="solid"
          >
            <Radio.Button value="count">数量维度</Radio.Button>
            <Radio.Button value="area">面积维度</Radio.Button>
          </Radio.Group>
          <Text type="secondary">
            {dimension === 'count' ? '基于资产个数进行分析' : '基于资产面积进行分析'}
          </Text>
        </Space>
      </Card>

      {hasData === false || analyticsData == null ? (
        <Card className={styles.emptyCard}>
          <Empty description="暂无数据" className={styles.emptyState}>
            <p className={styles.emptyHintText}>数据库中还没有资产数据，请先录入资产信息</p>
          </Empty>
        </Card>
      ) : (
        <>
          {/* 概览统计卡片 */}
          <Card title="概览统计" className={styles.sectionCard}>
            <AnalyticsStatsGrid
              data={{
                total_assets: analyticsData.area_summary.total_assets,
                total_area: analyticsData.area_summary.total_area,
                total_rentable_area: analyticsData.area_summary.total_rentable_area,
                occupancy_rate: analyticsData.area_summary.occupancy_rate,
                total_annual_income: analyticsData.financial_summary.total_annual_income,
                total_net_income: analyticsData.financial_summary.total_net_income,
                total_monthly_rent: analyticsData.financial_summary.total_monthly_rent,
              }}
              loading={loading}
            />
          </Card>

          {/* 分布图表网格 */}
          <AssetDistributionGrid
            analyticsData={analyticsData}
            dimension={dimension}
            loading={loading}
          />

          {/* 财务指标 */}
          <Card title="财务指标" className={styles.sectionCard}>
            <FinancialStatsGrid data={analyticsData.financial_summary} loading={loading} />
          </Card>

          {/* 经营口径（ANA-001） */}
          <Card title="经营口径" className={styles.sectionCard}>
            <RevenueStatsGrid
              data={{
                total_income: analyticsData.total_income ?? 0,
                self_operated_rent_income: analyticsData.self_operated_rent_income ?? 0,
                agency_service_income: analyticsData.agency_service_income ?? 0,
                actual_receipts: analyticsData.actual_receipts ?? 0,
                collection_rate: analyticsData.collection_rate ?? null,
                customer_entity_count: analyticsData.customer_entity_count ?? 0,
                customer_contract_count: analyticsData.customer_contract_count ?? 0,
                customer_entity_breakdown: analyticsData.customer_entity_breakdown,
                customer_contract_breakdown: analyticsData.customer_contract_breakdown,
                metrics_version: analyticsData.metrics_version,
              }}
              loading={loading}
            />
          </Card>

          {/* 项目与模式分区 */}
          <Card title="项目与模式分区" className={styles.sectionCard}>
            <div className={styles.modeBreakdownGrid}>
              {(analyticsData.mode_breakdown ?? []).map(mode => (
                <div
                  className={`${styles.modeBreakdownCard} ${getModeCardClassName(
                    mode.relation_kind
                  )}`}
                  key={mode.relation_kind}
                >
                  <div>
                    <Text strong>{mode.label}</Text>
                    <div className={styles.modeSubtitle}>
                      {mode.contract_relation_count} 个关系 / {mode.contract_count} 份合同
                    </div>
                  </div>
                  <div className={styles.modeMetricGrid}>
                    <div>
                      <span>经营收入</span>
                      <strong>{formatCurrency(mode.total_income)}</strong>
                    </div>
                    <div>
                      <span>当期实收</span>
                      <strong>{formatCurrency(mode.actual_receipts)}</strong>
                    </div>
                    <div>
                      <span>客户主体</span>
                      <strong>{mode.customer_entity_count} 个</strong>
                    </div>
                    <div>
                      <span>客户合同</span>
                      <strong>{mode.customer_contract_count} 份</strong>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <Table<AnalyticsProjectBreakdown>
              className={styles.projectBreakdownTable}
              rowKey="project_id"
              size="small"
              columns={projectBreakdownColumns}
              dataSource={analyticsData.project_breakdown ?? []}
              pagination={false}
              scroll={{ x: 920 }}
              locale={{ emptyText: '暂无项目分区数据' }}
            />
          </Card>

          {/* 出租率趋势 */}
          {analyticsData.occupancy_trend != null && analyticsData.occupancy_trend.length > 0 && (
            <Card title="出租率趋势" className={styles.sectionCard}>
              <AnalyticsLineChart
                title="出租率趋势"
                data={chartDataUtils.toTrendData(analyticsData.occupancy_trend)}
                lines={[
                  {
                    key: 'occupancy_rate',
                    name: '出租率 (%)',
                    color: CHART_PRIMARY_COLOR,
                  },
                ]}
                xAxisKey="date"
                loading={loading}
                height={400}
              />
            </Card>
          )}

          {/* 详细数据表格 */}
          <Row gutter={[16, 16]}>
            <Col xs={24}>
              <AssetDistributionDetails analyticsData={analyticsData} dimension={dimension} />
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default AssetAnalyticsPage;
