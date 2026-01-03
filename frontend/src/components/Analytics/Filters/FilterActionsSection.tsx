import React from 'react';
import { Row, Col, Button, Space, Typography } from 'antd';
import { useAnalyticsFiltersContext } from './FiltersContext';

const { Text } = Typography;

/**
 * Filter action buttons: Apply, Reset, Toggle Advanced
 */
const FilterActionsSection: React.FC = () => {
    const {
        handleApply,
        handleReset,
        loading,
        showAdvanced,
        onToggleAdvanced,
        activeFiltersCount
    } = useAnalyticsFiltersContext();

    return (
        <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
            <Col xs={24} md={12}>
                <Space>
                    <Button
                        type="primary"
                        onClick={handleApply}
                        loading={loading}
                    >
                        应用筛选
                    </Button>
                    <Button
                        onClick={handleReset}
                        disabled={loading}
                    >
                        重置筛选
                    </Button>
                    {onToggleAdvanced !== undefined && (
                        <Button
                            onClick={onToggleAdvanced}
                            icon={showAdvanced ? '▲' : '▼'}
                        >
                            {showAdvanced ? '收起高级' : '高级筛选'}
                        </Button>
                    )}
                </Space>
            </Col>
            <Col xs={24} md={12} style={{ textAlign: 'right' }}>
                <Text type="secondary">
                    当前条件: {activeFiltersCount} 个
                </Text>
            </Col>
        </Row>
    );
};

export default FilterActionsSection;
