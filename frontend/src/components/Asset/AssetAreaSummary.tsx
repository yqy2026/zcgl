import React, { useMemo } from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import type { AnalyticsData } from '@/services/analyticsService';
import { formatArea, formatPercentage } from '@/utils/format';
import { getOccupancyRateColor, COLORS } from '@/styles/colorMap';
import styles from './AssetAreaSummary.module.css';

interface AssetAreaSummaryProps {
  analyticsData?: AnalyticsData;
  loading?: boolean;
}

const AssetAreaSummary: React.FC<AssetAreaSummaryProps> = ({ analyticsData, loading = false }) => {
  // 使用分析数据（基于搜索条件的所有资产），不提供fallback到当前页数据
  // 因为我们需要显示的是所有筛选条件下数据的汇总，而不是当前页的汇总
  const areaSummary = analyticsData?.area_summary;
  const summary = useMemo(() => {
    const hasAnalyticsData = areaSummary != null && areaSummary.total_assets >= 0;

    if (!hasAnalyticsData) {
      return null;
    }

    return {
      totalLandArea: areaSummary.total_area ?? 0,
      totalActualArea: areaSummary.total_area ?? 0,
      totalRentableArea: areaSummary.total_rentable_area,
      totalRentedArea: areaSummary.total_rented_area,
      totalUnrentedArea: areaSummary.total_unrented_area,
      averageOccupancyRate: areaSummary.occupancy_rate,
    };
  }, [areaSummary]);

  return (
    <Card title="面积统计汇总" size="small" loading={loading} className="asset-area-summary-card">
      {summary ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="土地面积"
              value={summary.totalLandArea}
              formatter={value => formatArea(value)}
              styles={{ content: { color: COLORS.success } }}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="实际物业面积"
              value={summary.totalActualArea}
              formatter={value => formatArea(value)}
              styles={{ content: { color: COLORS.primary } }}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="可出租面积"
              value={summary.totalRentableArea}
              formatter={value => formatArea(value)}
              styles={{ content: { color: COLORS.primary } }}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="已出租面积"
              value={summary.totalRentedArea}
              formatter={value => formatArea(value)}
              styles={{ content: { color: COLORS.success } }}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="未出租面积"
              value={summary.totalUnrentedArea}
              formatter={value => formatArea(value)}
              styles={{ content: { color: COLORS.error } }}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="平均出租率"
              value={summary.averageOccupancyRate}
              formatter={value => formatPercentage(value)}
              styles={{
                content: { color: getOccupancyRateColor(summary.averageOccupancyRate ?? 0) },
              }}
              precision={2}
            />
          </Col>
        </Row>
      ) : (
        <div className={styles.emptyState}>
          {loading ? '正在加载统计数据...' : '暂无统计数据'}
        </div>
      )}
    </Card>
  );
};

export default React.memo(AssetAreaSummary);
