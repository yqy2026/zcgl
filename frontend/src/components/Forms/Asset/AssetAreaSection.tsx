import React from 'react';
import { Form, InputNumber, Row, Col, Card } from 'antd';
import { generateFormFieldIds } from '@/utils/accessibility';

/**
 * AssetForm - Area Info Section
 * Fields: land area, property area, rental areas
 */
const AssetAreaSection: React.FC = () => {
  // 为字段生成可访问性 ID
  const landAreaIds = generateFormFieldIds('land-area');
  const actualPropertyAreaIds = generateFormFieldIds('actual-property-area');
  const nonCommercialAreaIds = generateFormFieldIds('non-commercial-area');
  const rentableAreaIds = generateFormFieldIds('rentable-area');
  const rentedAreaIds = generateFormFieldIds('rented-area');
  const unrentedAreaIds = generateFormFieldIds('unrented-area');

  return (
    <Card title="面积信息" style={{ marginBottom: '16px' }}>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="土地面积(㎡)"
            name="land_area"
            htmlFor={landAreaIds.inputId}
          >
            <InputNumber
              id={landAreaIds.inputId}
              placeholder="请输入土地面积"
              style={{ width: '100%' }}
              min={0}
              aria-label={landAreaIds.labelId}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="实际房产面积(㎡)"
            name="actual_property_area"
            htmlFor={actualPropertyAreaIds.inputId}
          >
            <InputNumber
              id={actualPropertyAreaIds.inputId}
              placeholder="请输入实际房产面积"
              style={{ width: '100%' }}
              min={0}
              aria-label={actualPropertyAreaIds.labelId}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="非经营物业面积(㎡)"
            name="non_commercial_area"
            htmlFor={nonCommercialAreaIds.inputId}
          >
            <InputNumber
              id={nonCommercialAreaIds.inputId}
              placeholder="请输入非经营物业面积"
              style={{ width: '100%' }}
              min={0}
              aria-label={nonCommercialAreaIds.labelId}
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="可出租面积(㎡)"
            name="rentable_area"
            htmlFor={rentableAreaIds.inputId}
          >
            <InputNumber
              id={rentableAreaIds.inputId}
              placeholder="请输入可出租面积"
              style={{ width: '100%' }}
              min={0}
              aria-label={rentableAreaIds.labelId}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="已出租面积(㎡)"
            name="rented_area"
            htmlFor={rentedAreaIds.inputId}
          >
            <InputNumber
              id={rentedAreaIds.inputId}
              placeholder="请输入已出租面积"
              style={{ width: '100%' }}
              min={0}
              aria-label={rentedAreaIds.labelId}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="未出租面积(㎡)"
            name="unrented_area"
            htmlFor={unrentedAreaIds.inputId}
          >
            <InputNumber
              id={unrentedAreaIds.inputId}
              placeholder="自动计算"
              style={{ width: '100%' }}
              disabled
              aria-label={unrentedAreaIds.labelId}
              aria-readonly="true"
            />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );
};

export default AssetAreaSection;
