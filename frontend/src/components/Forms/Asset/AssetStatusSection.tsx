import React from 'react';
import { Form, Input, Select, Row, Col, Card } from 'antd';
import { DictionarySelect } from '@/components/Dictionary';
import { generateFormFieldIds } from '@/utils/accessibility';

const { Option } = Select;

/**
 * AssetForm - Status Info Section
 * Fields: ownership status, usage status, property nature, business category
 */
const AssetStatusSection: React.FC = () => {
  // 为必填字段生成可访问性 ID
  const ownershipStatusIds = generateFormFieldIds('ownership-status');
  const usageStatusIds = generateFormFieldIds('usage-status');
  const propertyNatureIds = generateFormFieldIds('property-nature');

  // 为可选字段生成 ID
  const certificatedUsageIds = generateFormFieldIds('certificated-usage');
  const actualUsageIds = generateFormFieldIds('actual-usage');
  const businessCategoryIds = generateFormFieldIds('business-category');
  const isLitigatedIds = generateFormFieldIds('is-litigated');
  const includeInOccupancyIds = generateFormFieldIds('include-in-occupancy');
  const occupancyRateIds = generateFormFieldIds('occupancy-rate');

  return (
    <Card title="状态信息" style={{ marginBottom: '16px' }}>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="确权状态"
            name="ownership_status"
            rules={[{ required: true, message: '请选择确权状态' }]}
            htmlFor={ownershipStatusIds.inputId}
            aria-required="true"
          >
            <DictionarySelect
              dictType="ownership_status"
              placeholder="请选择确权状态"
              id={ownershipStatusIds.inputId}
              aria-label={ownershipStatusIds.labelId}
              aria-required="true"
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="证载用途"
            name="certificated_usage"
            htmlFor={certificatedUsageIds.inputId}
          >
            <DictionarySelect
              dictType="certificated_usage"
              placeholder="请选择证载用途"
              id={certificatedUsageIds.inputId}
              aria-label={certificatedUsageIds.labelId}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="实际用途"
            name="actual_usage"
            htmlFor={actualUsageIds.inputId}
          >
            <DictionarySelect
              dictType="actual_usage"
              placeholder="请选择实际用途"
              id={actualUsageIds.inputId}
              aria-label={actualUsageIds.labelId}
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="业态类别"
            name="business_category"
            htmlFor={businessCategoryIds.inputId}
          >
            <DictionarySelect
              dictType="business_category"
              placeholder="请选择业态类别"
              id={businessCategoryIds.inputId}
              aria-label={businessCategoryIds.labelId}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="使用状态"
            name="usage_status"
            rules={[{ required: true, message: '请选择使用状态' }]}
            htmlFor={usageStatusIds.inputId}
            aria-required="true"
          >
            <DictionarySelect
              dictType="usage_status"
              placeholder="请选择使用状态"
              id={usageStatusIds.inputId}
              aria-label={usageStatusIds.labelId}
              aria-required="true"
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="是否涉诉"
            name="is_litigated"
            htmlFor={isLitigatedIds.inputId}
          >
            <Select
              placeholder="请选择是否涉诉"
              id={isLitigatedIds.inputId}
              aria-label={isLitigatedIds.labelId}
            >
              <Option value={false}>否</Option>
              <Option value={true}>是</Option>
            </Select>
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="物业性质"
            name="property_nature"
            rules={[{ required: true, message: '请选择物业性质' }]}
            htmlFor={propertyNatureIds.inputId}
            aria-required="true"
          >
            <DictionarySelect
              dictType="property_nature"
              placeholder="请选择物业性质"
              id={propertyNatureIds.inputId}
              aria-label={propertyNatureIds.labelId}
              aria-required="true"
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="是否计入出租率"
            name="include_in_occupancy_rate"
            htmlFor={includeInOccupancyIds.inputId}
          >
            <Select
              placeholder="请选择"
              id={includeInOccupancyIds.inputId}
              aria-label={includeInOccupancyIds.labelId}
            >
              <Option value={true}>是</Option>
              <Option value={false}>否</Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="出租率"
            name="occupancy_rate"
            htmlFor={occupancyRateIds.inputId}
          >
            <Input
              placeholder="自动计算"
              disabled
              id={occupancyRateIds.inputId}
              aria-label={occupancyRateIds.labelId}
              aria-readonly="true"
            />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );
};

export default AssetStatusSection;
