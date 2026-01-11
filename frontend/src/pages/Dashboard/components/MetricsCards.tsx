import React from 'react';
import { Row, Col, Card, Statistic } from 'antd';
import {
  BuildOutlined,
  AreaChartOutlined,
  PercentageOutlined,
  DollarOutlined,
  HomeOutlined,
  ShopOutlined,
} from '@ant-design/icons';
import { COLORS } from '@/styles/colorMap';

interface MetricsCardsProps {
  metrics?: {
    totalAssets: number;
    totalArea: number;
    occupancyRate: number;
    monthlyRevenue: number;
    rentedAssets: number;
    vacantAssets: number;
  };
  loading?: boolean;
}

const MetricsCards: React.FC<MetricsCardsProps> = ({ metrics, loading }) => {
  return (
    <Row gutter={16}>
      <Col xs={24} sm={12} lg={8} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="资产总数"
            value={metrics?.totalAssets ?? 0}
            suffix="个"
            prefix={<BuildOutlined />}
            valueStyle={{ color: COLORS.primary }}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={8} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="总面积"
            value={metrics?.totalArea ?? 0}
            suffix="㎡"
            prefix={<AreaChartOutlined />}
            valueStyle={{ color: COLORS.success }}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={8} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="平均出租率"
            value={metrics?.occupancyRate ?? 0}
            suffix="%"
            prefix={<PercentageOutlined />}
            precision={1}
            valueStyle={{ color: COLORS.warning }}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={8} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="月度收入"
            value={metrics?.monthlyRevenue ?? 0}
            prefix={<DollarOutlined />}
            valueStyle={{ color: COLORS.info }}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={8} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="出租中"
            value={metrics?.rentedAssets ?? 0}
            suffix="个"
            prefix={<HomeOutlined />}
            valueStyle={{ color: COLORS.success }}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={8} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="空置"
            value={metrics?.vacantAssets ?? 0}
            suffix="个"
            prefix={<ShopOutlined />}
            valueStyle={{ color: COLORS.error }}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default MetricsCards;
