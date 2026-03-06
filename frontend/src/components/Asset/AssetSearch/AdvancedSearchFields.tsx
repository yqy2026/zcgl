import React, { useMemo } from 'react';
import { Col, Form, Input, InputNumber, DatePicker, Row, Select, Space } from 'antd';
import styles from './AdvancedSearchFields.module.css';

const { Option } = Select;
const { RangePicker } = DatePicker;

interface AdvancedSearchFieldsProps {
  ownershipOptions: Array<{ value: string; label: string }>;
  businessCategories: string[];
  ownershipLoading?: boolean;
  businessCategoryLoading?: boolean;
  areaRange: [number, number];
  onAreaMinChange: (value: number | null) => void;
  onAreaMaxChange: (value: number | null) => void;
}

export const AdvancedSearchFields = React.memo(function AdvancedSearchFields({
  ownershipOptions,
  businessCategories,
  ownershipLoading = false,
  businessCategoryLoading = false,
  areaRange,
  onAreaMinChange,
  onAreaMaxChange,
}: AdvancedSearchFieldsProps) {
  const ownershipOptionNodes = useMemo(
    () =>
      ownershipOptions.map(option => (
        <Option key={option.value} value={option.value}>
          {option.label}
        </Option>
      )),
    [ownershipOptions]
  );

  const businessOptions = useMemo(
    () =>
      businessCategories.map(category => (
        <Option key={category} value={category}>
          {category}
        </Option>
      )),
    [businessCategories]
  );

  return (
    <>
      <Row gutter={16}>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Form.Item name="owner_party_id" label="权属方">
            <Select
              placeholder="选择权属方"
              allowClear
              showSearch
              optionFilterProp="children"
              loading={ownershipLoading}
            >
              {ownershipOptionNodes}
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
              {businessOptions}
            </Select>
          </Form.Item>
        </Col>

        <Col xs={24} sm={12} md={8} lg={6}>
          <Form.Item name="is_litigated" label="是否涉诉">
            <Select placeholder="选择是否涉诉" allowClear>
              <Option value={true}>是</Option>
              <Option value={false}>否</Option>
            </Select>
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col xs={24} sm={12} md={8}>
          <Form.Item label="面积范围">
            <Space.Compact>
              <InputNumber
                id="asset-area-min"
                name="asset-area-min"
                className={styles.areaInput}
                placeholder="最小面积"
                value={areaRange[0]}
                onChange={onAreaMinChange}
              />
              <Input
                id="asset-area-range-separator"
                name="asset-area-range-separator"
                className={styles.areaRangeSeparator}
                placeholder="~"
                disabled
              />
              <InputNumber
                id="asset-area-max"
                name="asset-area-max"
                className={styles.areaInput}
                placeholder="最大面积"
                value={areaRange[1]}
                onChange={onAreaMaxChange}
              />
            </Space.Compact>
          </Form.Item>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Form.Item name="dateRange" label="创建日期">
            <RangePicker className={styles.fullWidthControl} format="YYYY-MM-DD" />
          </Form.Item>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Form.Item label="排序方式">
            <Space.Compact>
              <Form.Item name="sort_field" noStyle>
                <Select className={styles.sortFieldSelect} defaultValue="created_at">
                  <Option value="created_at">创建时间</Option>
                  <Option value="asset_name">物业名称</Option>
                  <Option value="actual_property_area">建筑面积</Option>
                  <Option value="rentable_area">可租面积</Option>
                  <Option value="occupancy_rate">出租率</Option>
                </Select>
              </Form.Item>
              <Form.Item name="sort_order" noStyle>
                <Select className={styles.sortOrderSelect} defaultValue="desc">
                  <Option value="asc">升序</Option>
                  <Option value="desc">降序</Option>
                </Select>
              </Form.Item>
            </Space.Compact>
          </Form.Item>
        </Col>
      </Row>
    </>
  );
});
