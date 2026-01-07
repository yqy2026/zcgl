import React from 'react';
import { Card, Row, Col, Typography } from 'antd';
import {
  HomeOutlined,
  PieChartOutlined,
  RiseOutlined,
  AlertOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import styles from './QuickInsights.module.css';

const { Title, Text } = Typography;

interface QuickInsightsProps {
  data?: {
    totalAssets: number;
    totalArea: number;
    occupancyRate: number;
    totalRentedArea: number;
    totalUnrentedArea: number;
    recentActivity?: {
      newAssets: number;
      updatedAssets: number;
      maintenanceRequired: number;
    };
  };
  loading?: boolean;
}

const QuickInsights: React.FC<QuickInsightsProps> = ({ data, loading }) => {
  const insights = React.useMemo(() => {
    if (!data) {
      return [];
    }

    const items = [];

    // 出租率洞察
    if (data.occupancyRate > 95) {
      items.push({
        type: 'success',
        icon: <RiseOutlined />,
        title: '出租率表现优异',
        description: `当前出租率达到 ${data.occupancyRate.toFixed(1)}%，超过了95%的优秀水平`,
        highlight: `${data.occupancyRate.toFixed(1)}%`,
      });
    } else if (data.occupancyRate < 85) {
      items.push({
        type: 'warning',
        icon: <AlertOutlined />,
        title: '出租率有待提升',
        description: `当前出租率为 ${data.occupancyRate.toFixed(1)}%，建议关注空置资产的管理`,
        highlight: `${data.totalUnrentedArea.toFixed(0)}㎡ 空置面积`,
      });
    } else {
      items.push({
        type: 'info',
        icon: <PieChartOutlined />,
        title: '出租率正常',
        description: `当前出租率为 ${data.occupancyRate.toFixed(1)}%，处于合理区间`,
        highlight: '运营状态良好',
      });
    }

    // 资产规模洞察
    if (data.totalAssets > 500) {
      items.push({
        type: 'info',
        icon: <HomeOutlined />,
        title: '资产规模可观',
        description: `管理着 ${data.totalAssets} 个资产，总面积达 ${data.totalArea.toFixed(0)}㎡`,
        highlight: `管理 ${data.totalAssets} 个资产`,
      });
    }

    // 空置资产洞察
    if (data.totalUnrentedArea > 10000) {
      items.push({
        type: 'warning',
        icon: <AlertOutlined />,
        title: '空置面积较大',
        description: `空置面积达 ${data.totalUnrentedArea.toFixed(0)}㎡，建议制定营销策略`,
        highlight: `${data.totalUnrentedArea.toFixed(0)}㎡ 空置`,
      });
    }

    // 默认洞察
    if (items.length === 0) {
      items.push({
        type: 'info',
        icon: <CheckCircleOutlined />,
        title: '系统运行正常',
        description: '资产管理系统运行良好，数据更新及时',
        highlight: '系统状态良好',
      });
    }

    return items;
  }, [data]);

  const getTypeClass = (type: string) => {
    switch (type) {
      case 'success':
        return styles.success;
      case 'warning':
        return styles.warning;
      case 'error':
        return styles.error;
      default:
        return styles.info;
    }
  };

  return (
    <Card
      className={styles.insightsContainer}
      title={
        <div className={styles.titleContainer}>
          <Title level={4} className={styles.title}>
            智能洞察
          </Title>
          <Text type="secondary">基于当前数据的智能分析</Text>
        </div>
      }
      variant="borderless"
      loading={loading}
    >
      <Row gutter={[16, 16]}>
        {insights.map((insight, index) => (
          <Col xs={24} sm={12} lg={8} key={index}>
            <Card
              className={`${styles.insightCard} ${getTypeClass(insight.type)}`}
              variant="borderless"
              size="small"
            >
              <div className={styles.insightHeader}>
                <div className={styles.insightIcon}>{insight.icon}</div>
                <div className={styles.insightTitle}>{insight.title}</div>
              </div>
              <div className={styles.insightContent}>
                <p className={styles.insightDescription}>{insight.description}</p>
                <div className={styles.insightHighlight}>{insight.highlight}</div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  );
};

export default QuickInsights;
