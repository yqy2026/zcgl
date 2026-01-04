import React from 'react';
import { Form, Select, Row, Col, Card } from 'antd';
import { useRentContractFormContext } from './RentContractFormContext';

const { Option } = Select;

/**
 * RentContractForm - Relation Info Section
 * Fields: asset, ownership
 */
const RelationInfoSection: React.FC = () => {
    const { assets, ownerships, loadingAssets, loadingOwnerships } = useRentContractFormContext();

    return (
        <Card title="关联信息" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
                <Col span={12}>
                    <Form.Item
                        label="关联资产"
                        name="asset_id"
                        rules={[{ required: true, message: '请选择关联资产' }]}
                    >
                        <Select
                            showSearch
                            placeholder="选择资产"
                            loading={loadingAssets}
                            optionFilterProp="children"
                            filterOption={(input, option) =>
                                String(option?.children || '').toLowerCase().includes(input.toLowerCase())
                            }
                        >
                            {(assets !== null && assets !== undefined) ? assets.map(asset => (
                                <Option key={asset.id} value={asset.id}>
                                    {asset.property_name} - {asset.address}
                                </Option>
                            )) : []}
                        </Select>
                    </Form.Item>
                </Col>
                <Col span={12}>
                    <Form.Item
                        label="权属方"
                        name="ownership_id"
                        rules={[{ required: true, message: '请选择权属方' }]}
                    >
                        <Select
                            showSearch
                            placeholder="选择权属方"
                            loading={loadingOwnerships}
                            optionFilterProp="children"
                            filterOption={(input, option) =>
                                String(option?.children || '').toLowerCase().includes(input.toLowerCase())
                            }
                        >
                            {(ownerships !== null && ownerships !== undefined) ? ownerships.map(ownership => (
                                <Option key={ownership.id} value={ownership.id}>
                                    {ownership.name}
                                </Option>
                            )) : []}
                        </Select>
                    </Form.Item>
                </Col>
            </Row>
        </Card>
    );
};

export default RelationInfoSection;
