import React from 'react';
import { Form, Input, InputNumber, Row, Col, Card } from 'antd';

const { TextArea } = Input;

const parseCurrency = (value: string | undefined) => {
  const normalized = value?.replace(/¥\s?|(,*)/g, '') ?? '';
  const numeric = Number(normalized);
  return normalized === '' || Number.isNaN(numeric) ? NaN : numeric;
};

/**
 * RentContractForm - Other Info Section
 * Fields: monthly rent base, payment terms, notes
 */
const OtherInfoSection: React.FC = () => {
  return (
    <Card title="其他信息" size="small" style={{ marginBottom: 16 }}>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="基础月租金"
            name="monthly_rent_base"
            tooltip="用于快速参考，实际租金以租金条款为准"
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="请输入基础月租金"
              min={0}
              precision={2}
              formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={parseCurrency}
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="付款条款" name="payment_terms">
            <Input placeholder="例如：每月1日前支付" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={24}>
          <Form.Item label="合同备注" name="contract_notes">
            <TextArea rows={3} placeholder="请输入合同相关备注信息" />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );
};

export default OtherInfoSection;
