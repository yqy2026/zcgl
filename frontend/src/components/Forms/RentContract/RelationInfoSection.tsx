import React from 'react';
import { Form, Select, Row, Col, Card } from 'antd';
import PartySelector from '@/components/Common/PartySelector';
import { useRentContractFormContext } from './RentContractFormContext';
import styles from './RelationInfoSection.module.css';

const { Option } = Select;

/**
 * RentContractForm - Relation Info Section
 * Fields: asset, owner party, manager party, tenant party
 */
const RelationInfoSection: React.FC = () => {
  const { assets, loadingAssets } = useRentContractFormContext();

  return (
    <Card title="关联信息" size="small" className={styles.relationCard}>
      <Row gutter={16}>
        <Col span={24}>
          <Form.Item
            label="关联资产"
            name="asset_ids"
            rules={[{ required: true, message: '请选择关联资产' }]}
          >
            <Select
              mode="multiple"
              showSearch
              placeholder="选择资产（可多选）"
              loading={loadingAssets}
              optionFilterProp="children"
              filterOption={(input, option) =>
                String(option?.children || '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            >
              {(assets.length > 0 ? assets : []).map(asset => (
                <Option key={asset.id} value={asset.id}>
                  {asset.asset_name} - {asset.address}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col xs={24} md={8}>
          <Form.Item
            label="产权方主体"
            name="owner_party_id"
            rules={[{ required: true, message: '请选择产权方主体' }]}
          >
            <PartySelector
              filterMode="owner"
              placeholder="请选择产权方主体"
              allowClear={false}
              allowQuickCreate
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={8}>
          <Form.Item
            label="经营管理方主体"
            name="manager_party_id"
            rules={[{ required: true, message: '请选择经营管理方主体' }]}
          >
            <PartySelector
              filterMode="manager"
              placeholder="请选择经营管理方主体"
              allowClear={false}
              allowQuickCreate
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={8}>
          <Form.Item label="承租方主体" name="tenant_party_id">
            <PartySelector
              filterMode="tenant"
              placeholder="请选择承租方主体（可选）"
              allowQuickCreate
            />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );
};

export default RelationInfoSection;
