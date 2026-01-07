import React from 'react';
import { Modal, Form, DatePicker, InputNumber, Input, Row, Col } from 'antd';
import { useRentContractFormContext } from './RentContractFormContext';

const { TextArea } = Input;

/**
 * RentContractForm - Rent Term Modal
 * Modal for adding/editing rent terms
 */
const RentTermModal: React.FC = () => {
    const {
        termForm,
        showRentTermModal,
        setShowRentTermModal,
        editingTerm,
        handleSaveRentTerm
    } = useRentContractFormContext();

    return (
        <Modal
            title={editingTerm ? '编辑租金条款' : '添加租金条款'}
            open={showRentTermModal}
            onCancel={() => setShowRentTermModal(false)}
            onOk={handleSaveRentTerm}
            width={600}
        >
            <Form
                form={termForm}
                layout="vertical"
            >
                <Row gutter={16}>
                    <Col span={12}>
                        <Form.Item
                            label="开始日期"
                            name="start_date"
                            rules={[{ required: true, message: '请选择开始日期' }]}
                        >
                            <DatePicker style={{ width: '100%' }} />
                        </Form.Item>
                    </Col>
                    <Col span={12}>
                        <Form.Item
                            label="结束日期"
                            name="end_date"
                            rules={[{ required: true, message: '请选择结束日期' }]}
                        >
                            <DatePicker style={{ width: '100%' }} />
                        </Form.Item>
                    </Col>
                </Row>
                <Row gutter={16}>
                    <Col span={8}>
                        <Form.Item
                            label="月租金"
                            name="monthly_rent"
                            rules={[{ required: true, message: '请输入月租金' }]}
                        >
                            <InputNumber
                                style={{ width: '100%' }}
                                placeholder="请输入月租金"
                                min={0}
                                precision={2}
                                formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                                parser={(value: string | undefined) => value?.replace(/¥\s?|(,*)/g, '') as unknown as number}
                            />
                        </Form.Item>
                    </Col>
                    <Col span={8}>
                        <Form.Item
                            label="管理费"
                            name="management_fee"
                        >
                            <InputNumber
                                style={{ width: '100%' }}
                                placeholder="请输入管理费"
                                min={0}
                                precision={2}
                                formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                                parser={(value: string | undefined) => value?.replace(/¥\s?|(,*)/g, '') as unknown as number}
                            />
                        </Form.Item>
                    </Col>
                    <Col span={8}>
                        <Form.Item
                            label="其他费用"
                            name="other_fees"
                        >
                            <InputNumber
                                style={{ width: '100%' }}
                                placeholder="请输入其他费用"
                                min={0}
                                precision={2}
                                formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                                parser={(value: string | undefined) => value?.replace(/¥\s?|(,*)/g, '') as unknown as number}
                            />
                        </Form.Item>
                    </Col>
                </Row>
                <Form.Item
                    label="条款说明"
                    name="rent_description"
                >
                    <TextArea
                        rows={2}
                        placeholder="请输入该租金条款的说明信息"
                    />
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default RentTermModal;
