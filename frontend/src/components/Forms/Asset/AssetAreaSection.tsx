import React from 'react';
import { Form, InputNumber, Row, Col, Card } from 'antd';

/**
 * AssetForm - Area Info Section
 * Fields: land area, property area, rental areas
 */
const AssetAreaSection: React.FC = () => {
    return (
        <Card title="面积信息" style={{ marginBottom: '16px' }}>
            <Row gutter={16}>
                <Col span={8}>
                    <Form.Item label="土地面积(㎡)" name="land_area">
                        <InputNumber placeholder="请输入土地面积" style={{ width: '100%' }} min={0} />
                    </Form.Item>
                </Col>
                <Col span={8}>
                    <Form.Item label="实际房产面积(㎡)" name="actual_property_area">
                        <InputNumber placeholder="请输入实际房产面积" style={{ width: '100%' }} min={0} />
                    </Form.Item>
                </Col>
                <Col span={8}>
                    <Form.Item label="非经营物业面积(㎡)" name="non_commercial_area">
                        <InputNumber placeholder="请输入非经营物业面积" style={{ width: '100%' }} min={0} />
                    </Form.Item>
                </Col>
            </Row>

            <Row gutter={16}>
                <Col span={8}>
                    <Form.Item label="可出租面积(㎡)" name="rentable_area">
                        <InputNumber placeholder="请输入可出租面积" style={{ width: '100%' }} min={0} />
                    </Form.Item>
                </Col>
                <Col span={8}>
                    <Form.Item label="已出租面积(㎡)" name="rented_area">
                        <InputNumber placeholder="请输入已出租面积" style={{ width: '100%' }} min={0} />
                    </Form.Item>
                </Col>
                <Col span={8}>
                    <Form.Item label="未出租面积(㎡)" name="unrented_area">
                        <InputNumber placeholder="自动计算" style={{ width: '100%' }} disabled />
                    </Form.Item>
                </Col>
            </Row>
        </Card>
    );
};

export default AssetAreaSection;
