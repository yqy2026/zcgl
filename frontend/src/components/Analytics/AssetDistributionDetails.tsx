import React from 'react';
import { Row, Col, Card, Typography } from 'antd';
import styles from '../../pages/Assets/AssetAnalyticsPage.module.css';
import type { AnalyticsData } from '@/types/analytics';
import type { AnalysisDimension } from '@/hooks/useAssetAnalytics';

interface AssetDistributionDetailsProps {
  analyticsData: AnalyticsData;
  dimension: AnalysisDimension;
}

interface DistributionDetailItem {
  key: string;
  name: string;
  stats: string;
}

const AssetDistributionDetails: React.FC<AssetDistributionDetailsProps> = ({
  analyticsData,
  dimension,
}) => {
  const propertyNatureItems: DistributionDetailItem[] =
    dimension === 'count'
      ? analyticsData.property_nature_distribution.map(item => ({
          key: item.name,
          name: item.name,
          stats: `${item.count} (${item.percentage}%)`,
        }))
      : analyticsData.property_nature_area_distribution.map(item => ({
          key: item.name,
          name: item.name,
          stats: `${item.total_area.toFixed(0)}㎡ (${item.area_percentage}%)`,
        }));

  const ownershipStatusItems: DistributionDetailItem[] =
    dimension === 'count'
      ? analyticsData.ownership_status_distribution.map(item => ({
          key: item.status,
          name: item.status,
          stats: `${item.count} (${item.percentage}%)`,
        }))
      : analyticsData.ownership_status_area_distribution.map(item => ({
          key: item.status,
          name: item.status,
          stats: `${item.total_area.toFixed(0)}㎡ (${item.area_percentage}%)`,
        }));

  const usageStatusItems: DistributionDetailItem[] =
    dimension === 'count'
      ? analyticsData.usage_status_distribution.map(item => ({
          key: item.status,
          name: item.status,
          stats: `${item.count} (${item.percentage}%)`,
        }))
      : analyticsData.usage_status_area_distribution.map(item => ({
          key: item.status,
          name: item.status,
          stats: `${item.total_area.toFixed(0)}㎡ (${item.area_percentage}%)`,
        }));

  const businessCategoryItems: DistributionDetailItem[] =
    dimension === 'count'
      ? analyticsData.business_category_distribution.map(item => ({
          key: item.category,
          name: item.category,
          stats: `${item.count}个 (占比${item.percentage}%)`,
        }))
      : analyticsData.business_category_area_distribution.map(item => ({
          key: item.category,
          name: item.category,
          stats: `${item.total_area.toFixed(0)}㎡ (占比${item.area_percentage}%)`,
        }));

  const renderItems = (items: DistributionDetailItem[]) =>
    items.map(item => (
      <div key={item.key} className={styles.distributionItem}>
        <span className={styles.itemName}>{item.name}</span>
        <span className={styles.itemStats}>{item.stats}</span>
      </div>
    ));

  return (
    <Card title="分布详情">
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Typography.Title level={5}>
            物业性质分布 ({dimension === 'count' ? '数量' : '面积'})
          </Typography.Title>
          <div className={styles.distributionList}>{renderItems(propertyNatureItems)}</div>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Typography.Title level={5}>
            确权状态分布 ({dimension === 'count' ? '数量' : '面积'})
          </Typography.Title>
          <div className={styles.distributionList}>{renderItems(ownershipStatusItems)}</div>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Typography.Title level={5}>
            使用状态分布 ({dimension === 'count' ? '数量' : '面积'})
          </Typography.Title>
          <div className={styles.distributionList}>{renderItems(usageStatusItems)}</div>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Typography.Title level={5}>
            业态类别分布 ({dimension === 'count' ? '数量' : '面积'})
          </Typography.Title>
          <div className={styles.distributionList}>{renderItems(businessCategoryItems)}</div>
        </Col>
      </Row>
    </Card>
  );
};

export default AssetDistributionDetails;
