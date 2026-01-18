import React from 'react';
import { Row, Col, Typography, Select, DatePicker } from 'antd';
import { useAnalyticsFiltersContext } from './FiltersContext';

const { Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

/**
 * Basic filter controls: ownership status, usage status, property nature, date range
 */
const BasicFiltersSection: React.FC = () => {
  const { localFilters, handleFilterChange, handleDateRangeChange, loading } =
    useAnalyticsFiltersContext();

  return (
    <Row gutter={[16, 16]} align="middle">
      <Col xs={24} md={6}>
        <Text strong>权属状态:</Text>
        <Select
          style={{ width: '100%', marginTop: '8px' }}
          placeholder="请选择权属状态"
          allowClear
          value={localFilters.ownership_status}
          onChange={value => handleFilterChange('ownership_status', value)}
          loading={loading}
        >
          <Option value="已确权">已确权</Option>
          <Option value="未确权">未确权</Option>
          <Option value="部分确权">部分确权</Option>
          <Option value="无法确认业权">无法确认业权</Option>
        </Select>
      </Col>

      <Col xs={24} md={6}>
        <Text strong>使用状态:</Text>
        <Select
          style={{ width: '100%', marginTop: '8px' }}
          placeholder="请选择使用状态"
          allowClear
          value={localFilters.usage_status}
          onChange={value => handleFilterChange('usage_status', value)}
          loading={loading}
        >
          <Option value="出租">出租</Option>
          <Option value="空置">空置</Option>
          <Option value="自用">自用</Option>
          <Option value="公房">公房</Option>
          <Option value="其他">其他</Option>
          <Option value="转租">转租</Option>
          <Option value="公配">公配</Option>
          <Option value="空置规划">空置规划</Option>
          <Option value="空置预留">空置预留</Option>
          <Option value="配套">配套</Option>
          <Option value="空置配套">空置配套</Option>
          <Option value="待处置">待处置</Option>
          <Option value="待移交">待移交</Option>
          <Option value="闲置">闲置</Option>
        </Select>
      </Col>

      <Col xs={24} md={6}>
        <Text strong>物业性质:</Text>
        <Select
          style={{ width: '100%', marginTop: '8px' }}
          placeholder="请选择物业性质"
          allowClear
          value={localFilters.property_nature}
          onChange={value => handleFilterChange('property_nature', value)}
          loading={loading}
        >
          <Option value="经营性">经营性</Option>
          <Option value="非经营性">非经营性</Option>
          <Option value="经营-外部">经营-外部</Option>
          <Option value="经营-内部">经营-内部</Option>
          <Option value="经营-租赁">经营-租赁</Option>
          <Option value="非经营类-公配">非经营类-公配</Option>
          <Option value="非经营类-其他">非经营类-其他</Option>
          <Option value="经营类">经营类</Option>
          <Option value="非经营类">非经营类</Option>
          <Option value="经营-配套">经营-配套</Option>
          <Option value="非经营-配套">非经营-配套</Option>
          <Option value="经营-处置类">经营-处置类</Option>
          <Option value="非经营-处置类">非经营-处置类</Option>
          <Option value="非经营-公配房">非经营-公配房</Option>
          <Option value="非经营类-配套">非经营类-配套</Option>
        </Select>
      </Col>

      <Col xs={24} md={6}>
        <Text strong>时间范围:</Text>
        <RangePicker
          style={{ width: '100%', marginTop: '8px' }}
          onChange={handleDateRangeChange}
          placeholder={['开始日期', '结束日期']}
          disabled={loading}
        />
      </Col>
    </Row>
  );
};

export default BasicFiltersSection;
