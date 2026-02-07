import React from 'react';
import { Row, Col, Card, Statistic } from 'antd';
import { FileTextOutlined, DollarOutlined } from '@ant-design/icons';
import { COLORS } from '@/styles/colorMap';
import type { RentStatisticsOverview } from '@/types/rentContract';

interface ContractStatsCardsProps {
  statistics: RentStatisticsOverview | null;
}

const ContractStatsCards: React.FC<ContractStatsCardsProps> = ({ statistics }) => {
  if (!statistics) return null;

  return (
    <Row gutter={16} style={{ marginBottom: '24px' }}>
      <Col span={6}>
        <Card>
          <Statistic
            title="总合同数"
            value={statistics.total_records}
            prefix={<FileTextOutlined />}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="应收总额"
            value={statistics.total_due}
            precision={2}
            prefix={<DollarOutlined />}
            suffix="元"
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="已收总额"
            value={statistics.total_paid}
            precision={2}
            prefix={<DollarOutlined />}
            suffix="元"
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="收缴率"
            value={statistics.payment_rate}
            precision={2}
            suffix="%"
            styles={{
              content: {
                color: statistics.payment_rate > 80 ? COLORS.success : COLORS.error,
              },
            }}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default ContractStatsCards;
