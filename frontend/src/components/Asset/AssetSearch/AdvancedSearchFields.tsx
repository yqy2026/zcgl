import React from 'react';
import { Col, Form, InputNumber, DatePicker, Row, Select, Space } from 'antd';
import type { Dayjs } from 'dayjs';

const { Option } = Select;
const { RangePicker } = DatePicker;

interface AdvancedSearchFieldsProps {
  ownershipEntities: string[];
  businessCategories: string[];
  ownershipEntityLoading?: boolean;
  businessCategoryLoading?: boolean;
}

export const AdvancedSearchFields: React.FC<AdvancedSearchFieldsProps> = ({
  ownershipEntities,
  businessCategories,
  ownershipEntityLoading = false,
  businessCategoryLoading = false,
}) => {
  return (
    <>
      <Row gutter={16}>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Form.Item name="ownership_entity" label="权属方">
            <Select
              placeholder="选择权属方"
              allowClear
              showSearch
              optionFilterProp="children"
              loading={ownershipEntityLoading}
            >
              {ownershipEntities.map(entity => (
                <Option key={entity} value={entity}>
                  {entity}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>

        <Col xs={24} sm={12} md={8} lg={6}>
          <Form.Item name="business_category" label="业态类别">
            <Select
              placeholder="选择业态类别"
              allowClear
              showSearch
              optionFilterProp="children"
              loading={businessCategoryLoading}
            >
              {businessCategories.map(category => (
                <Option key={category} value={category}>
                  {category}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>

        <Col xs={24} sm={12} md={8} lg={6}>
          <Form.Item label="建筑面积范围(㎡)">
            <Space.Compact style={{ width: '100%' }}>
              <Form.Item name="area_min" noStyle>
                <InputNumber
                  placeholder="最小"
                  min={0}
                  max={100000}
                  style={{ width: '50%' }}
                />
              </Form.Item>
              <Form.Item name="area_max" noStyle>
                <InputNumber
                  placeholder="最大"
                  min={0}
                  max={100000}
                  style={{ width: '50%' }}
                />
              </Form.Item>
            </Space.Compact>
          </Form.Item>
        </Col>

        <Col xs={24} sm={12} md={8} lg={6}>
          <Form.Item
            name="created_date_range"
            label="创建时间"
            getValueFromEvent={(values: [Dayjs, Dayjs]) => {
              if (values && values.length === 2) {
                return {
                  created_start: values[0].format('YYYY-MM-DD'),
                  created_end: values[1].format('YYYY-MM-DD'),
                };
              }
              return undefined;
            }}
          >
            <RangePicker
              style={{ width: '100%' }}
              placeholder={['开始日期', '结束日期']}
            />
          </Form.Item>
        </Col>
      </Row>
    </>
  );
};
