import React from 'react';
import { Row, Col, Button, Space, Typography } from 'antd';
import { DownOutlined, UpOutlined } from '@ant-design/icons';
import { useAnalyticsFiltersContext } from './FiltersContext';
import styles from './Filters.module.css';

const { Text } = Typography;

/**
 * Filter action buttons: Apply, Reset, Toggle Advanced
 */
const FilterActionsSection: React.FC = () => {
  const { handleApply, handleReset, loading, showAdvanced, onToggleAdvanced, activeFiltersCount } =
    useAnalyticsFiltersContext();

  return (
    <Row gutter={[16, 16]} className={styles.actionsRow}>
      <Col xs={24} md={12}>
        <Space size={[8, 8]} wrap>
          <Button
            type="primary"
            onClick={handleApply}
            loading={loading}
            className={styles.sectionButton}
          >
            应用筛选
          </Button>
          <Button onClick={handleReset} disabled={loading} className={styles.sectionButton}>
            重置筛选
          </Button>
          {onToggleAdvanced !== undefined && (
            <Button
              onClick={onToggleAdvanced}
              icon={showAdvanced ? <UpOutlined /> : <DownOutlined />}
              className={styles.sectionButton}
            >
              {showAdvanced ? '收起高级' : '高级筛选'}
            </Button>
          )}
        </Space>
      </Col>
      <Col xs={24} md={12} className={styles.actionsSummaryCol}>
        <Text type="secondary" className={styles.actionsSummaryText}>
          当前条件: {activeFiltersCount} 个
        </Text>
      </Col>
    </Row>
  );
};

export default FilterActionsSection;
