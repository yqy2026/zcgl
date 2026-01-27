import React from 'react';
import { Form, Input, Select, Row, Col, Card } from 'antd';
import { DictionarySelect } from '../../Dictionary';

const { Option } = Select;

/**
 * AssetForm - Status Info Section
 * Fields: ownership status, usage status, property nature, business category
 */
const AssetStatusSection: React.FC = () => {
  return (
    <Card title="状态信息" style={{ marginBottom: '16px' }}>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="确权状态"
            name="ownership_status"
            rules={[{ required: true, message: '请选择确权状态' }]}
          >
            <DictionarySelect dictType="ownership_status" placeholder="请选择确权状态" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="证载用途" name="certificated_usage">
            <DictionarySelect dictType="certificated_usage" placeholder="请选择证载用途" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="实际用途" name="actual_usage">
            <DictionarySelect dictType="actual_usage" placeholder="请选择实际用途" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item label="业态类别" name="business_category">
            <DictionarySelect dictType="business_category" placeholder="请选择业态类别" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="使用状态"
            name="usage_status"
            rules={[{ required: true, message: '请选择使用状态' }]}
          >
            <DictionarySelect dictType="usage_status" placeholder="请选择使用状态" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="是否涉诉" name="is_litigated">
            <Select placeholder="请选择是否涉诉">
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
          >
            <DictionarySelect dictType="property_nature" placeholder="请选择物业性质" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="是否计入出租率" name="include_in_occupancy_rate">
            <Select placeholder="请选择">
              <Option value={true}>是</Option>
              <Option value={false}>否</Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="出租率" name="occupancy_rate">
            <Input placeholder="自动计算" disabled />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );
};

export default AssetStatusSection;
