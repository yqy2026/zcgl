import React from 'react';
import { Form, Input, Select, DatePicker, Row, Col, Card } from 'antd';

const { Option } = Select;

/**
 * RentContractForm - Basic Info Section
 * Fields: contract number, sign date, status
 */
const BasicInfoSection: React.FC = () => {
  return (
    <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item label="合同编号" name="contract_number" tooltip="留空将自动生成">
            <Input placeholder="留空将自动生成" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="签订日期"
            name="sign_date"
            rules={[{ required: true, message: '请选择签订日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="合同状态"
            name="contract_status"
            rules={[{ required: true, message: '请选择合同状态' }]}
          >
            <Select>
              <Option value="有效">有效</Option>
              <Option value="到期">到期</Option>
              <Option value="终止">终止</Option>
            </Select>
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );
};

export default BasicInfoSection;
