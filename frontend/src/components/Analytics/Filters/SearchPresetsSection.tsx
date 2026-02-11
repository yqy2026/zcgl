import React from 'react';
import { Row, Col, Typography, Space, Tag, Input, Tooltip } from 'antd';
import { useAnalyticsFiltersContext, FILTER_PRESETS } from './FiltersContext';
import styles from './Filters.module.css';

const { Text } = Typography;
const { Search } = Input;

/**
 * Search input and preset filter tags
 */
const SearchPresetsSection: React.FC = () => {
  const { searchText, handleSearch, selectedPreset, handlePresetSelect, loading } =
    useAnalyticsFiltersContext();

  return (
    <Row gutter={[16, 16]} className={styles.searchPresetsRow}>
      <Col xs={24} md={8}>
        <Text strong className={styles.fieldLabel}>
          搜索资产:
        </Text>
        <Search
          placeholder="输入资产名称、地址等关键词"
          allowClear
          className={styles.fieldControl}
          value={searchText}
          onChange={e => handleSearch(e.target.value)}
          onSearch={handleSearch}
          loading={loading}
        />
      </Col>
      <Col xs={24} md={16}>
        <Text strong className={styles.fieldLabel}>
          快速筛选:
        </Text>
        <div className={styles.tagGroupContainer}>
          <Space wrap size={[8, 8]} className={styles.tagSpace}>
            {FILTER_PRESETS.map(preset => (
              <Tooltip key={preset.key} title={preset.description}>
                <Tag
                  color={selectedPreset === preset.key ? 'blue' : 'default'}
                  className={styles.presetTag}
                  onClick={() => handlePresetSelect(preset.key)}
                >
                  {preset.label}
                </Tag>
              </Tooltip>
            ))}
          </Space>
        </div>
      </Col>
    </Row>
  );
};

export default SearchPresetsSection;
