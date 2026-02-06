import React from 'react';
import { Form, Input, Row, Col, Card } from 'antd';
import { DictionarySelect } from '@/components/Dictionary';
import OwnershipSelect from '@/components/Ownership/OwnershipSelect';
import ProjectSelect from '@/components/Project/ProjectSelect';

/**
 * AssetForm - Basic Info Section
 * Fields: ownership entity, category, project, property name, address
 */
const AssetBasicInfoSection: React.FC = () => {
  return (
    <Card title="基本信息" style={{ marginBottom: '16px' }}>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="权属方"
            name="ownership_id"
            rules={[{ required: true, message: '请选择权属方' }]}
            aria-required="true"
          >
            <OwnershipSelect
              placeholder="请选择权属方"
              allowClear={false}
              showCreateButton={true}
              aria-label="权属方选择器"
              onChange={(_value, _ownership) => {
                // When ownership is selected, can auto-fill related info
              }}
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="权属类别" name="ownership_category">
            <DictionarySelect
              dictType="ownership_category"
              placeholder="请选择权属类别"
              aria-label="权属类别选择器"
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="项目名称" name="project_name">
            <ProjectSelect
              placeholder="请选择项目"
              allowClear={false}
              showCreateButton={true}
              aria-label="项目名称选择器"
              onChange={(_value, _project) => {
                // When project is selected, can auto-fill related info
              }}
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="物业名称"
            name="property_name"
            rules={[{ required: true, message: '请输入物业名称' }]}
            aria-required="true"
          >
            <Input
              placeholder="请输入物业名称"
              aria-label="物业名称输入框"
            />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="物业地址"
        name="address"
        rules={[{ required: true, message: '请输入物业地址' }]}
        aria-required="true"
      >
        <Input
          placeholder="请输入详细地址"
          aria-label="物业地址输入框"
        />
      </Form.Item>
    </Card>
  );
};

export default AssetBasicInfoSection;
