import React from 'react';
import { Row, Col, Progress, Typography, Space } from 'antd';
import styles from './AssetChart.module.css';

const { Text, Title } = Typography;

interface ChartData {
  propertyTypes?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  occupancyTrend?: Array<{
    month: string;
    rate: number;
  }>;
}

interface AssetChartProps {
  data?: ChartData;
  loading?: boolean;
}

const AssetChart: React.FC<AssetChartProps> = ({ data, loading }) => {
  if (loading === true) {
    return (
      <div className={styles.loadingState} role="status" aria-live="polite">
        加载中...
      </div>
    );
  }

  const propertyTypes = data?.propertyTypes ?? [];
  const occupancyTrend = data?.occupancyTrend ?? [];
  const total = propertyTypes.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className={styles.assetChart}>
      {/* 物业类型分布 */}
      <Title level={5} className={styles.sectionTitle}>
        物业类型分布
      </Title>

      <div className={styles.sectionBody}>
        {propertyTypes.map(item => {
          const percentage = total > 0 ? (item.value / total) * 100 : 0;
          return (
            <div key={item.name} className={styles.propertyItem}>
              <Row justify="space-between" align="middle" className={styles.propertyHeaderRow}>
                <Col>
                  <Space className={styles.propertyLabelGroup}>
                    <span
                      className={styles.propertyColorDot}
                      style={{ ['--legend-color' as string]: item.color } as React.CSSProperties}
                      aria-hidden
                    />
                    <Text className={styles.propertyName}>{item.name}</Text>
                  </Space>
                </Col>
                <Col>
                  <Text strong className={styles.propertyValue}>
                    {item.value}个
                  </Text>
                </Col>
              </Row>
              <Progress
                className={styles.propertyProgress}
                percent={percentage}
                strokeColor={item.color}
                showInfo={false}
                size="small"
              />
            </div>
          );
        })}
      </div>

      {/* 出租率趋势 */}
      <Title level={5} className={styles.sectionTitle}>
        出租率趋势
      </Title>

      <div className={styles.trendList}>
        {occupancyTrend.map(item => (
          <div key={item.month} className={styles.trendItem}>
            <Row justify="space-between" align="middle">
              <Col>
                <Text className={styles.trendMonth}>{item.month}</Text>
              </Col>
              <Col>
                <Text strong className={styles.trendValue}>
                  {item.rate}%
                </Text>
              </Col>
            </Row>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AssetChart;
