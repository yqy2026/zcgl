import React from 'react';
import { Form, DatePicker, InputNumber, Row, Col, Card } from 'antd';

/**
 * RentContractForm - Contract Period Section
 * Fields: start date, end date, deposit
 */
const ContractPeriodSection: React.FC = () => {
    return (
        <Card title="合同期限" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
                <Col span={8}>
                    <Form.Item
                        label="开始日期"
                        name="start_date"
                        rules={[{ required: true, message: '请选择开始日期' }]}
                    >
                        <DatePicker style={{ width: '100%' }} />
                    </Form.Item>
                </Col>
                <Col span={8}>
                    <Form.Item
                        label="结束日期"
                        name="end_date"
                        rules={[{ required: true, message: '请选择结束日期' }]}
                    >
                        <DatePicker style={{ width: '100%' }} />
                    </Form.Item>
                </Col>
                <Col span={8}>
                    <Form.Item
                        label="押金总额"
                        name="total_deposit"
                        tooltip="单位：元"
                    >
                        <InputNumber
                            style={{ width: '100%' }}
                            placeholder="请输入押金总额"
                            min={0}
                            precision={2}
                            formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                            parser={(value: string | undefined) => value?.replace(/¥\s?|(,*)/g, '') as unknown as number}
                        />
                    </Form.Item>
                </Col>
            </Row>
        </Card>
    );
};

export default ContractPeriodSection;
