import React from 'react';
import { Form, Input, Row, Col, Card } from 'antd';
import { DictionarySelect } from '@/components/Dictionary';
import PartySelector from '@/components/Common/PartySelector';
import ProjectSelect from '@/components/Project/ProjectSelect';
import { generateFormFieldIds } from '@/utils/accessibility';
import styles from './AssetBasicInfoSection.module.css';

/**
 * AssetForm - Basic Info Section
 * Fields: ownership entity, category, project, property name, address
 */
const AssetBasicInfoSection: React.FC = () => {
  // 为必填字段生成可访问性 ID
  const ownerPartyIds = generateFormFieldIds('owner-party');
  const propertyNameIds = generateFormFieldIds('property-name');
  const addressIds = generateFormFieldIds('address');

  return (
    <Card title="基本信息" className={styles.sectionCard}>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="权属主体"
            name="owner_party_id"
            rules={[{ required: true, message: '请选择权属主体' }]}
            aria-required="true"
            htmlFor={ownerPartyIds.inputId}
          >
            <PartySelector
              filterMode="owner"
              placeholder="请选择权属主体"
              allowClear={false}
              onChange={(_value, _party) => {
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
            name="asset_name"
            rules={[{ required: true, message: '请输入物业名称' }]}
            aria-required="true"
            htmlFor={propertyNameIds.inputId}
          >
            <Input id={propertyNameIds.inputId} placeholder="请输入物业名称" aria-required="true" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="物业地址"
        name="address_detail"
        rules={[{ required: true, message: '请输入物业地址' }]}
        aria-required="true"
        htmlFor={addressIds.inputId}
      >
        <Input id={addressIds.inputId} placeholder="请输入详细地址" aria-required="true" />
      </Form.Item>
    </Card>
  );
};

export default AssetBasicInfoSection;
