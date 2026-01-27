import React from 'react';
import { Card, Row, Col, Spin, Alert, Empty, Typography, Space, Button, Radio } from 'antd';
import styles from './AssetAnalyticsPage.module.css';
import {
  ReloadOutlined,
  DownloadOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
} from '@ant-design/icons';
import { AnalyticsStatsGrid, FinancialStatsGrid } from '@/components/Analytics/AnalyticsStatsCard';
import { AnalyticsLineChart, chartDataUtils } from '@/components/Analytics/AnalyticsChart';
import AnalyticsFilters from '@/components/Analytics/AnalyticsFilters';
import { createLogger } from '@/utils/logger';
import { COLORS } from '@/styles/colorMap';
import { useAssetAnalytics, AnalysisDimension } from '@/hooks/useAssetAnalytics';
import { useFullscreen } from '@/hooks/useFullscreen';
import AssetDistributionGrid from '@/components/Analytics/AssetDistributionGrid';
import AssetDistributionDetails from '@/components/Analytics/AssetDistributionDetails';

const pageLogger = createLogger('AssetAnalytics');

const { Text } = Typography;

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
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>加载分析数据中...</div>
      </div>
    );
  }

  if (error) {
    pageLogger.error('Analytics Error:', error as Error);
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="数据加载失败"
          description={`错误详情: ${error instanceof Error ? error.message : '未知错误'}`}
          type="error"
          showIcon
        />
      </div>
    );
  }

  return (
    <div className={styles.analyticsContainer}>
      {/* 页面标题和操作栏 */}
      <Card style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col xs={24} sm={12}>
            <Typography.Title level={3} style={{ margin: 0 }}>
              资产分析
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
      <Card style={{ marginBottom: '24px' }}>
        <Space align="center">
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
        <Card>
          <Empty description="暂无数据" style={{ padding: '60px 0' }}>
            <p>数据库中还没有资产数据，请先录入资产信息</p>
          </Empty>
        </Card>
      ) : (
        <>
          {/* 概览统计卡片 */}
          <Card title="概览统计" style={{ marginBottom: '24px' }}>
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
          <Card title="财务指标" style={{ marginBottom: '24px' }}>
            <FinancialStatsGrid data={analyticsData.financial_summary} loading={loading} />
          </Card>

          {/* 出租率趋势 */}
          {analyticsData.occupancy_trend != null && analyticsData.occupancy_trend.length > 0 && (
            <Card title="出租率趋势" style={{ marginBottom: '24px' }}>
              <AnalyticsLineChart
                title="出租率趋势"
                data={chartDataUtils.toTrendData(analyticsData.occupancy_trend)}
                lines={[
                  {
                    key: 'occupancy_rate',
                    name: '出租率 (%)',
                    color: COLORS.primary,
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
