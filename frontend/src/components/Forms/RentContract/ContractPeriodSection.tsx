import React from 'react';
import { Form, DatePicker, InputNumber, Row, Col, Card } from 'antd';
import styles from './ContractPeriodSection.module.css';

const parseCurrency = (value: string | undefined) => {
  const normalized = value?.replace(/¥\s?|(,*)/g, '') ?? '';
  const numeric = Number(normalized);
  return normalized === '' || Number.isNaN(numeric) ? NaN : numeric;
};

/**
 * RentContractForm - Contract Period Section
 * Fields: start date, end date, deposit
 */
const ContractPeriodSection: React.FC = () => {
  return (
    <Card title="合同期限" size="small" className={styles.contractPeriodCard}>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="开始日期"
            name="start_date"
            rules={[{ required: true, message: '请选择开始日期' }]}
          >
            <DatePicker className={styles.fullWidthControl} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="结束日期"
            name="end_date"
            rules={[{ required: true, message: '请选择结束日期' }]}
          >
            <DatePicker className={styles.fullWidthControl} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="押金总额" name="total_deposit" tooltip="单位：元">
            <InputNumber
              className={styles.fullWidthControl}
              placeholder="请输入押金总额"
              min={0}
              precision={2}
              formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={parseCurrency}
            />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );
};

export default ContractPeriodSection;
