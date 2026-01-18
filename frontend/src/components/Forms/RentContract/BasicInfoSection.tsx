import React from 'react';
import { Form, Input, Select, DatePicker, Row, Col, Card, InputNumber } from 'antd';

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
          <Form.Item
            label="合同类型"
            name="contract_type"
            rules={[{ required: true, message: '请选择合同类型' }]}
            initialValue="lease_downstream"
          >
            <Select>
              <Option value="lease_downstream">租赁合同（下游）</Option>
              <Option value="lease_upstream">承租合同（上游）</Option>
              <Option value="entrusted">委托运营协议</Option>
            </Select>
          </Form.Item>
        </Col>
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
      </Row>
      <Row gutter={16}>
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
        <Col span={8}>
          <Form.Item
            label="付款周期"
            name="payment_cycle"
            rules={[{ required: true, message: '请选择付款周期' }]}
            initialValue="monthly"
          >
            <Select>
              <Option value="monthly">月付</Option>
              <Option value="quarterly">季付</Option>
              <Option value="semi_annual">半年付</Option>
              <Option value="annual">年付</Option>
            </Select>
          </Form.Item>
        </Col>
        <Form.Item
          noStyle
          shouldUpdate={(prevValues, currentValues) =>
            prevValues.contract_type !== currentValues.contract_type
          }
        >
          {({ getFieldValue }) => {
            return getFieldValue('contract_type') === 'entrusted' ? (
              <Col span={8}>
                <Form.Item
                  label="服务费率"
                  name="service_fee_rate"
                  rules={[{ required: true, message: '请输入服务费率' }]}
                  tooltip="例如：0.05 表示 5%"
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    max={1}
                    step={0.01}
                    placeholder="如 0.05"
                  />
                </Form.Item>
              </Col>
            ) : null;
          }}
        </Form.Item>
      </Row>
    </Card>
  );
};

export default BasicInfoSection;
