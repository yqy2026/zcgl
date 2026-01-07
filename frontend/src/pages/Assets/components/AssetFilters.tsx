import React from 'react';
import { Form, Select, DatePicker, Button, Space, Row, Col, Slider } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

// 资产筛选条件接口
export interface AssetFilterConditions {
  keyword?: string;
  ownership_status?: string;
  property_nature?: string;
  usage_status?: string;
  business_category?: string;
  area_range?: [number, number];
  rent_range?: [number, number];
  date_range?: [dayjs.Dayjs, dayjs.Dayjs];
  tenant_type?: string;
  [key: string]: unknown;
}

interface AssetFiltersProps {
  filters: AssetFilterConditions;
  onChange: (filters: AssetFilterConditions) => void;
  onReset: () => void;
}

const AssetFilters: React.FC<AssetFiltersProps> = ({ filters, onChange, onReset }) => {
  const [form] = Form.useForm();

  const handleValuesChange = (
    changedValues: AssetFilterConditions,
    allValues: AssetFilterConditions
  ) => {
    onChange(allValues);
  };

  const handleReset = () => {
    form.resetFields();
    onReset();
  };

  return (
    <Form form={form} layout="vertical" initialValues={filters} onValuesChange={handleValuesChange}>
      <Row gutter={16}>
        <Col span={6}>
          <Form.Item label="物业性质" name="propertyNature">
            <Select placeholder="请选择物业性质" allowClear>
              <Option value="经营类">经营类</Option>
              <Option value="非经营类">非经营类</Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item label="使用状态" name="usageStatus">
            <Select placeholder="请选择使用状态" allowClear>
              <Option value="出租">出租</Option>
              <Option value="闲置">闲置</Option>
              <Option value="自用">自用</Option>
              <Option value="公房">公房</Option>
              <Option value="其他">其他</Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item label="确权状态" name="ownershipStatus">
            <Select placeholder="请选择确权状态" allowClear>
              <Option value="已确权">已确权</Option>
              <Option value="未确权">未确权</Option>
              <Option value="部分确权">部分确权</Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item label="权属方" name="ownershipEntity">
            <Select placeholder="请选择权属方" allowClear>
              <Option value="华润集团">华润集团</Option>
              <Option value="万科集团">万科集团</Option>
              <Option value="中信集团">中信集团</Option>
              <Option value="绿地集团">绿地集团</Option>
            </Select>
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item label="出租率范围" name="occupancyRateRange">
            <Slider
              range
              min={0}
              max={100}
              marks={{
                0: '0%',
                50: '50%',
                100: '100%',
              }}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="创建时间" name="dateRange">
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label=" " style={{ marginTop: '30px' }}>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重置筛选
              </Button>
            </Space>
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );
};

export default AssetFilters;
