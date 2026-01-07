import React from 'react';
import { Row, Col, Typography, Space, Tag, Input, Tooltip } from 'antd';
import { useAnalyticsFiltersContext, FILTER_PRESETS } from './FiltersContext';

const { Text } = Typography;
const { Search } = Input;

/**
 * Search input and preset filter tags
 */
const SearchPresetsSection: React.FC = () => {
  const { searchText, handleSearch, selectedPreset, handlePresetSelect, loading } =
    useAnalyticsFiltersContext();

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={24} md={8}>
        <Text strong>搜索资产:</Text>
        <Search
          placeholder="输入资产名称、地址等关键词"
          allowClear
          style={{ marginTop: 8 }}
          value={searchText}
          onChange={e => handleSearch(e.target.value)}
          onSearch={handleSearch}
          loading={loading}
        />
      </Col>
      <Col xs={24} md={16}>
        <Text strong>快速筛选:</Text>
        <div style={{ marginTop: 8 }}>
          <Space wrap>
            {FILTER_PRESETS.map(preset => (
              <Tooltip key={preset.key} title={preset.description}>
                <Tag
                  color={selectedPreset === preset.key ? 'blue' : 'default'}
                  style={{ cursor: 'pointer', padding: '4px 8px' }}
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
