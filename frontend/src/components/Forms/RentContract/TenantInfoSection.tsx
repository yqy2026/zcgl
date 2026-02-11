import React from 'react';
import { Form, Input, Row, Col, Card } from 'antd';

/**
 * RentContractForm - Lessee Info Section
 * Fields: tenant name, contact, phone, address
 */
const TenantInfoSection: React.FC = () => {
  return (
    <Card title="承租方信息" size="small" style={{ marginBottom: 16 }}>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="承租方名称"
            name="tenant_name"
            rules={[{ required: true, message: '请输入承租方名称' }]}
          >
            <Input placeholder="请输入承租方名称" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="联系人" name="tenant_contact">
            <Input placeholder="请输入联系人姓名" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="联系电话" name="tenant_phone">
            <Input placeholder="请输入联系电话" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="联系地址" name="tenant_address">
            <Input placeholder="请输入联系地址" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={24}>
          <Form.Item label="经营用途" name="tenant_usage" tooltip="例如：餐饮、办公、仓储等">
            <Input.TextArea id="tenant_usage" rows={2} placeholder="请输入经营用途说明" />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );
};

export default TenantInfoSection;
