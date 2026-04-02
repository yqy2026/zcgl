import React from 'react';
import { Card, Row, Col, Typography, Button, Space, Tooltip } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  ReloadOutlined,
  DownloadOutlined,
  FullscreenOutlined,
  HomeOutlined,
  AreaChartOutlined,
  BarChartOutlined,
  PieChartOutlined,
} from '@ant-design/icons';
import { MANAGER_ROUTES, OWNER_ROUTES } from '@/constants/routes';
import { useCapabilities } from '@/hooks/useCapabilities';
import { useAnalytics } from '@/hooks/useAnalytics';
import { useRoutePerspective } from '@/routes/perspective';
import DataTrendCard from '@/components/Dashboard/DataTrendCard';
import QuickInsights from '@/components/Dashboard/QuickInsights';
import styles from './DashboardPage.module.css';

const { Title, Text } = Typography;

const DashboardPage: React.FC = () => {
  const [isFullscreen, setIsFullscreen] = React.useState(false);
  const navigate = useNavigate();
  const { isPerspectiveRoute } = useRoutePerspective();
  const { getAvailablePerspectives } = useCapabilities();
  const availablePerspectives = getAvailablePerspectives('analytics');

  // 使用统一的Analytics hook，避免重复请求
  const { data: analyticsData, isLoading, error, refetch } = useAnalytics();

  // 从综合分析数据中提取面积汇总信息
  const areaSummary = analyticsData?.data?.area_summary;

  const occupancyTrend = React.useMemo(() => {
    const trendData = analyticsData?.data?.occupancy_trend;
    if (!trendData || trendData.length < 2) return undefined;
    const current = trendData[trendData.length - 1];
    const previous = trendData[trendData.length - 2];
    const previousRate = previous.occupancy_rate ?? 0;
    if (previousRate === 0) return undefined;
    const trendValue = ((current.occupancy_rate - previousRate) / previousRate) * 100;
    return {
      value: trendValue,
      period: '较上期',
      isPositive: trendValue >= 0,
    };
  }, [analyticsData]);

  const handleRefresh = () => {
    refetch();
  };

  const handleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
    if (!isFullscreen) {
      // 进入全屏
      if (document.documentElement.requestFullscreen != null) {
        document.documentElement.requestFullscreen();
      }
    } else {
      // 退出全屏
      if (document.exitFullscreen != null) {
        document.exitFullscreen();
      }
    }
  };

  const handleExport = () => {
    // 实现导出功能
    // Exporting dashboard data
  };

  if (!isPerspectiveRoute) {
    const canOpenOwner = availablePerspectives.includes('owner');
    const canOpenManager = availablePerspectives.includes('manager');

    return (
      <div className={styles.dashboardContainer}>
        <div className={styles.errorContainer}>
          <div className={styles.errorTitle}>请选择业务视角</div>
          <div className={styles.errorDescription}>
            共享工作台不再直接请求带视角的数据分析接口。请进入业主视角或经营视角后查看对应模块。
          </div>
          <Space>
            <Button
              type="primary"
              onClick={() => navigate(OWNER_ROUTES.ASSETS)}
              disabled={!canOpenOwner}
            >
              进入业主视角
            </Button>
            <Button
              onClick={() => navigate(MANAGER_ROUTES.ASSETS)}
              disabled={!canOpenManager}
            >
              进入经营视角
            </Button>
          </Space>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.dashboardContainer}>
        <div className={styles.errorContainer}>
          <div className={styles.errorTitle}>数据加载失败</div>
          <div className={styles.errorDescription}>
            {error instanceof Error ? error.message : '未知错误，请稍后重试'}
          </div>
          <Button type="primary" onClick={handleRefresh}>
            重试
          </Button>
        </div>
      </div>
    );
  }

  const insightsData = areaSummary
    ? {
        totalAssets: areaSummary.total_assets,
        totalArea: areaSummary.total_area,
        occupancyRate: areaSummary.occupancy_rate,
        totalRentedArea: areaSummary.total_rented_area,
        totalUnrentedArea: areaSummary.total_unrented_area,
      }
    : undefined;

  return (
    <div className={`${styles.dashboardContainer} ${isFullscreen ? styles.fullscreen : ''}`}>
      {/* 页面头部 */}
      <div className={styles.dashboardHeader}>
        <div className={styles.headerContent}>
          <Title level={1} className={styles.dashboardTitle}>
            资产管理看板
          </Title>
          <Text className={styles.dashboardSubtitle}>
            实时监控资产运营状况，提供数据驱动的决策支持
          </Text>
        </div>
        <div className={styles.dashboardActions}>
          <Space>
            <Tooltip title="刷新数据">
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={isLoading}
                className={styles.actionButton}
              >
                刷新
              </Button>
            </Tooltip>
            <Tooltip title="导出数据">
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
                className={styles.actionButton}
              >
                导出
              </Button>
            </Tooltip>
            <Tooltip title={isFullscreen ? '退出全屏' : '全屏显示'}>
              <Button
                icon={<FullscreenOutlined />}
                onClick={handleFullscreen}
                className={styles.actionButton}
              >
                {isFullscreen ? '退出全屏' : '全屏'}
              </Button>
            </Tooltip>
          </Space>
        </div>
      </div>

      {/* 关键指标区域 */}
      <div className={styles.keyMetricsSection}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <DataTrendCard
              title="资产总数"
              value={areaSummary?.total_assets ?? 0}
              suffix="个"
              precision={0}
              trend={undefined}
              icon={<HomeOutlined />}
              color="primary"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <DataTrendCard
              title="管理总面积"
              value={areaSummary?.total_area ?? 0}
              suffix="㎡"
              precision={2}
              trend={undefined}
              icon={<AreaChartOutlined />}
              color="success"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <DataTrendCard
              title="可租面积"
              value={areaSummary?.total_rentable_area ?? 0}
              suffix="㎡"
              precision={2}
              trend={undefined}
              icon={<BarChartOutlined />}
              color="warning"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <DataTrendCard
              title="整体出租率"
              value={areaSummary?.occupancy_rate ?? 0}
              suffix="%"
              precision={1}
              trend={occupancyTrend}
              icon={<PieChartOutlined />}
              color={
                (areaSummary?.occupancy_rate ?? 0) >= 95
                  ? 'success'
                  : (areaSummary?.occupancy_rate ?? 0) >= 85
                    ? 'warning'
                    : 'error'
              }
              loading={isLoading}
            />
          </Col>
        </Row>
      </div>

      {/* 智能洞察区域 */}
      <div className={styles.insightsSection}>
        <QuickInsights data={insightsData} loading={isLoading} />
      </div>

      {/* 详细统计区域 */}
      <div className={styles.detailedStatsSection}>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card className={styles.statsCard} variant="borderless">
              <div className={styles.statsCardHeader}>
                <Title level={4} className={styles.statsCardTitle}>
                  面积分布统计
                </Title>
              </div>
              <div className={styles.statsCardBody}>
                <Row gutter={16}>
                  <Col span={12}>
                    <div className={styles.statItem}>
                      <div className={styles.statValue}>
                        {(areaSummary?.total_rented_area ?? 0).toFixed(2)}
                      </div>
                      <div className={styles.statLabel}>已租面积 (㎡)</div>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div className={styles.statItem}>
                      <div className={styles.statValue}>
                        {(areaSummary?.total_unrented_area ?? 0).toFixed(2)}
                      </div>
                      <div className={styles.statLabel}>空置面积 (㎡)</div>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div className={styles.statItem}>
                      <div className={styles.statValue}>
                        {(areaSummary?.total_non_commercial_area ?? 0).toFixed(2)}
                      </div>
                      <div className={styles.statLabel}>非商业面积 (㎡)</div>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div className={styles.statItem}>
                      <div className={styles.statValue}>
                        {areaSummary?.assets_with_area_data ?? 0}
                      </div>
                      <div className={styles.statLabel}>有数据资产 (个)</div>
                    </div>
                  </Col>
                </Row>
              </div>
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card className={styles.statsCard} variant="borderless">
              <div className={styles.statsCardHeader}>
                <Title level={4} className={styles.statsCardTitle}>
                  运营状况概览
                </Title>
              </div>
              <div className={styles.statsCardBody}>
                <Row gutter={16}>
                  <Col span={12}>
                    <div className={styles.statItem}>
                      <div className={styles.statValue}>{areaSummary?.total_assets ?? 0}</div>
                      <div className={styles.statLabel}>管理资产总数</div>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div className={styles.statItem}>
                      <div className={styles.statValue}>
                        {areaSummary?.total_area?.toFixed(2) ?? '0.00'}
                      </div>
                      <div className={styles.statLabel}>土地面积 (㎡)</div>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div className={styles.statItem}>
                      <div className={styles.statValue}>
                        {(areaSummary?.total_rentable_area ?? 0).toFixed(2)}
                      </div>
                      <div className={styles.statLabel}>可租面积 (㎡)</div>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div className={styles.statItem}>
                      <div className={styles.statValue}>
                        {areaSummary?.occupancy_rate?.toFixed(1) ?? '0.0'}%
                      </div>
                      <div className={styles.statLabel}>整体出租率</div>
                    </div>
                  </Col>
                </Row>
              </div>
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default DashboardPage;
