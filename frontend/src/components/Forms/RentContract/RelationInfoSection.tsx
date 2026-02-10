import React from 'react';
import { Form, Select, Row, Col, Card } from 'antd';
import OwnershipSelect from '@/components/Ownership/OwnershipSelect';
import { useRentContractFormContext } from './RentContractFormContext';
import styles from './RelationInfoSection.module.css';

const { Option } = Select;

/**
 * RentContractForm - Relation Info Section
 * Fields: asset, ownership
 */
const RelationInfoSection: React.FC = () => {
  const { assets, loadingAssets } = useRentContractFormContext();

  return (
    <Card title="关联信息" size="small" className={styles.relationCard}>
      <Row gutter={16}>
        <Col span={12}>
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
                  {asset.property_name} - {asset.address}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="权属方"
            name="ownership_id"
            rules={[{ required: true, message: '请选择权属方' }]}
          >
            <OwnershipSelect
              placeholder="选择权属方"
              variant="compact"
              ariaLabel="租赁合同权属方选择"
            />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );
};

export default RelationInfoSection;
