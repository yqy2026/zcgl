import React from 'react';
import { Row, Col } from 'antd';
import {
  AnalyticsPieChart,
  AnalyticsBarChart,
  chartDataUtils,
} from '@/components/Analytics/AnalyticsChart';
import type {
  AnalyticsData,
  OwnershipStatusAreaDistribution,
  UsageStatusAreaDistribution,
} from '@/types/analytics';
import type { AnalysisDimension } from '@/hooks/useAssetAnalytics';

interface AssetDistributionGridProps {
  analyticsData: AnalyticsData;
  dimension: AnalysisDimension;
  loading: boolean;
}

const AssetDistributionGrid: React.FC<AssetDistributionGridProps> = ({
  analyticsData,
  dimension,
  loading,
}) => {
  return (
    <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
      {/* 物业性质分布饼图 */}
      <Col xs={24} sm={12} xl={6}>
        <AnalyticsPieChart
          title={`物业性质分布 (${dimension === 'count' ? '数量' : '面积'})`}
          data={
            dimension === 'count'
              ? chartDataUtils.toPieData(analyticsData.property_nature_distribution ?? [])
              : chartDataUtils.toAreaData(analyticsData.property_nature_area_distribution ?? [])
          }
          loading={loading}
          height={280}
        />
      </Col>

      {/* 确权状态分布饼图 */}
      <Col xs={24} sm={12} xl={6}>
        <AnalyticsPieChart
          title={`确权状态分布 (${dimension === 'count' ? '数量' : '面积'})`}
          data={
            dimension === 'count'
              ? chartDataUtils.toPieData(
                  (analyticsData.ownership_status_distribution ?? []).map(item => ({
                    name: item.status,
                    count: item.count,
                    percentage: item.percentage,
                  }))
                )
              : chartDataUtils.toAreaData(
                  (
                    analyticsData.ownership_status_area_distribution as
                      | OwnershipStatusAreaDistribution[]
                      | undefined
                  )?.map(item => ({
                    name: item.status,
                    total_area: item.total_area,
                    area_percentage: item.area_percentage ?? item.percentage ?? 0,
                    average_area: item.average_area,
                  })) ?? []
                )
          }
          loading={loading}
          height={280}
        />
      </Col>

      {/* 使用状态分布柱状图 */}
      <Col xs={24} sm={12} xl={6}>
        <AnalyticsBarChart
          title={`使用状态分布 (${dimension === 'count' ? '数量' : '面积'})`}
          data={
            dimension === 'count'
              ? (analyticsData.usage_status_distribution ?? []).map(item => ({
                  name: item.status,
                  value: item.count,
                }))
              : chartDataUtils.toAreaBarData(
                  (
                    analyticsData.usage_status_area_distribution as
                      | UsageStatusAreaDistribution[]
                      | undefined
                  )?.map(item => ({
                    name: item.status,
                    total_area: item.total_area,
                    count: item.count,
                    average_area: item.average_area,
                  })) ?? []
                )
          }
          xAxisKey="name"
          barKey="value"
          loading={loading}
          height={280}
        />
      </Col>

      {/* 业态类别分布柱状图 */}
      <Col xs={24} sm={12} xl={6}>
        <AnalyticsBarChart
          title={`业态类别分布 (${dimension === 'count' ? '数量' : '面积'})`}
          data={
            dimension === 'count'
              ? chartDataUtils.toBusinessCategoryData(
                  analyticsData.business_category_distribution ?? []
                )
              : chartDataUtils.toBusinessCategoryAreaData(
                  analyticsData.business_category_area_distribution ?? []
                )
          }
          xAxisKey="name"
          barKey="value"
          loading={loading}
          height={280}
        />
      </Col>
    </Row>
  );
};

export default AssetDistributionGrid;
