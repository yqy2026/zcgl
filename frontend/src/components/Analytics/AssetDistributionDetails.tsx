import React from 'react';
import { Row, Col, Card, Typography } from 'antd';
import styles from '../../pages/Assets/AssetAnalyticsPage.module.css';
import type {
  AnalyticsData,
  BusinessCategoryAreaDistribution,
} from '@/types/analytics';
import type { AnalysisDimension } from '@/hooks/useAssetAnalytics';

interface AssetDistributionDetailsProps {
  analyticsData: AnalyticsData;
  dimension: AnalysisDimension;
}

const AssetDistributionDetails: React.FC<AssetDistributionDetailsProps> = ({
  analyticsData,
  dimension,
}) => {
  return (
    <Card title="分布详情">
      <Row gutter={[16, 16]}>
        {/* 物业性质分布 */}
        <Col xs={24} sm={12} lg={6}>
          <Typography.Title level={5}>
            物业性质分布 ({dimension === 'count' ? '数量' : '面积'})
          </Typography.Title>
          <div className={styles.distributionList}>
            {(dimension === 'count'
              ? (analyticsData.property_nature_distribution ?? [])
              : (analyticsData.property_nature_area_distribution ?? [])
            ).map(item => (
              <div key={item.name} className={styles.distributionItem}>
                <span className={styles.itemName}>
                  {item.name}
                </span>
                <span className={styles.itemStats}>
                  {dimension === 'count'
                    ? `${(item as { count: number; percentage: number }).count} (${(item as { percentage: number }).percentage}%)`
                    : `${(item as { total_area?: number }).total_area?.toFixed(0)}㎡ (${(item as { area_percentage?: number }).area_percentage ?? 0}%)`}
                </span>
              </div>
            ))}
          </div>
        </Col>

        {/* 确权状态分布 */}
        <Col xs={24} sm={12} lg={6}>
          <Typography.Title level={5}>
            确权状态分布 ({dimension === 'count' ? '数量' : '面积'})
          </Typography.Title>
          <div className={styles.distributionList}>
            {(dimension === 'count'
              ? (analyticsData.ownership_status_distribution ?? [])
              : (analyticsData.ownership_status_area_distribution ?? [])
            ).map(item => (
              <div key={(item as { status: string }).status} className={styles.distributionItem}>
                <span className={styles.itemName}>
                  {(item as { status: string }).status}
                </span>
                <span className={styles.itemStats}>
                  {dimension === 'count'
                    ? `${(item as { count: number; percentage: number }).count} (${(item as { percentage: number }).percentage}%)`
                    : `${(item as { total_area?: number }).total_area?.toFixed(0)}㎡ (${(item as { area_percentage?: number; percentage?: number }).area_percentage ?? (item as { area_percentage?: number; percentage?: number }).percentage}%)`}
                </span>
              </div>
            ))}
          </div>
        </Col>

        {/* 使用状态分布 */}
        <Col xs={24} sm={12} lg={6}>
          <Typography.Title level={5}>
            使用状态分布 ({dimension === 'count' ? '数量' : '面积'})
          </Typography.Title>
          <div className={styles.distributionList}>
            {(dimension === 'count'
              ? (analyticsData.usage_status_distribution ?? [])
              : (analyticsData.usage_status_area_distribution ?? [])
            ).map(item => (
              <div key={(item as { status: string }).status} className={styles.distributionItem}>
                <span className={styles.itemName}>
                  {(item as { status: string }).status}
                </span>
                <span className={styles.itemStats}>
                  {dimension === 'count'
                    ? `${(item as { count: number; percentage: number }).count} (${(item as { percentage: number }).percentage}%)`
                    : `${(item as { total_area?: number }).total_area?.toFixed(0)}㎡ (${(item as { area_percentage?: number }).area_percentage}%)`}
                </span>
              </div>
            ))}
          </div>
        </Col>

        {/* 业态类别分布 */}
        <Col xs={24} sm={12} lg={6}>
          <Typography.Title level={5}>
            业态类别分布 ({dimension === 'count' ? '数量' : '面积'})
          </Typography.Title>
          <div className={styles.distributionList}>
            {(dimension === 'count'
              ? (analyticsData.business_category_distribution ?? [])
              : (analyticsData.business_category_area_distribution ?? [])
            ).map(item => {
              const isCount = dimension === 'count';
              const countItem = isCount ? item : null;
              const areaItem = isCount
                ? null
                : (item as BusinessCategoryAreaDistribution);
              const itemKey =
                isCount && countItem
                  ? countItem.category
                  : (areaItem?.category ?? '');

              return (
                <div key={itemKey} className={styles.distributionItem}>
                  <span className={styles.itemName}>
                    {isCount && countItem
                      ? countItem.category
                      : (areaItem?.category ?? '')}
                  </span>
                  <span className={styles.itemStats}>
                    {isCount && countItem
                      ? `${countItem.count}个 (占比${((countItem.count / (analyticsData.business_category_distribution?.reduce((sum, i) => sum + i.count, 0) ?? 1)) * 100).toFixed(1)}%)`
                      : areaItem
                        ? `${areaItem.total_area?.toFixed(0) ?? 0}㎡ (占比${areaItem.area_percentage ?? 0}%)`
                        : ''}
                    {isCount &&
                      countItem &&
                      countItem.occupancy_rate != null &&
                      countItem.occupancy_rate > 0 && (
                        <span className={styles.occupancyRate}>
                          ，出租率{countItem.occupancy_rate.toFixed(2)}%
                        </span>
                      )}
                    {!isCount &&
                      areaItem &&
                      areaItem.occupancy_rate != null &&
                      areaItem.occupancy_rate > 0 && (
                        <span className={styles.occupancyRate}>
                          ，出租率{areaItem.occupancy_rate.toFixed(2)}%
                        </span>
                      )}
                  </span>
                </div>
              );
            })}
          </div>
        </Col>
      </Row>
    </Card>
  );
};

export default AssetDistributionDetails;
