import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import type { AnalyticsData } from '@/services/analyticsService';
import { formatArea, formatPercentage } from '@/utils/format';

interface AssetAreaSummaryProps {
  analyticsData?: AnalyticsData;
  loading?: boolean;
}

const AssetAreaSummary: React.FC<AssetAreaSummaryProps> = ({ analyticsData, loading = false }) => {
  // 使用分析数据（基于搜索条件的所有资产），不提供fallback到当前页数据
  // 因为我们需要显示的是所有筛选条件下数据的汇总，而不是当前页的汇总
  const hasAnalyticsData =
    analyticsData?.area_summary && analyticsData.area_summary.total_assets >= 0;

  const summary =
    hasAnalyticsData === true && analyticsData?.area_summary !== undefined
      ? {
          totalLandArea: analyticsData.area_summary.total_area ?? 0,
          totalActualArea: analyticsData.area_summary.total_area ?? 0,
          totalRentableArea: analyticsData.area_summary.total_rentable_area,
          totalRentedArea: analyticsData.area_summary.total_rented_area,
          totalUnrentedArea: analyticsData.area_summary.total_unrented_area,
          averageOccupancyRate: analyticsData.area_summary.occupancy_rate,
        }
      : null;

  return (
    <Card title="面积统计汇总" size="small" loading={loading} style={{ marginBottom: 16 }}>
      {summary ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="土地面积"
              value={summary.totalLandArea}
              formatter={value => formatArea(value)}
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="实际物业面积"
              value={summary.totalActualArea}
              formatter={value => formatArea(value)}
              valueStyle={{ color: '#1677ff' }}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="可出租面积"
              value={summary.totalRentableArea}
              formatter={value => formatArea(value)}
              valueStyle={{ color: '#722ed1' }}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="已出租面积"
              value={summary.totalRentedArea}
              formatter={value => formatArea(value)}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="未出租面积"
              value={summary.totalUnrentedArea}
              formatter={value => formatArea(value)}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="平均出租率"
              value={summary.averageOccupancyRate}
              formatter={value => formatPercentage(value)}
              valueStyle={{
                color:
                  summary.averageOccupancyRate >= 80
                    ? '#52c41a'
                    : summary.averageOccupancyRate >= 60
                      ? '#faad14'
                      : '#ff4d4f',
              }}
              precision={2}
            />
          </Col>
        </Row>
      ) : (
        <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
          {loading ? '正在加载统计数据...' : '暂无统计数据'}
        </div>
      )}
    </Card>
  );
};

export default AssetAreaSummary;
