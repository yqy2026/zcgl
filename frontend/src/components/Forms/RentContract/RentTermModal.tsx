import React from 'react';
import { Modal, Form, DatePicker, InputNumber, Input, Row, Col } from 'antd';
import { useRentContractFormContext } from './RentContractFormContext';
import styles from './RentTermModal.module.css';

const { TextArea } = Input;

const parseCurrency = (value: string | undefined) => {
  const normalized = value?.replace(/¥\s?|(,*)/g, '') ?? '';
  const numeric = Number(normalized);
  return normalized === '' || Number.isNaN(numeric) ? NaN : numeric;
};

/**
 * RentContractForm - Rent Term Modal
 * Modal for adding/editing rent terms
 */
const RentTermModal: React.FC = () => {
  const { termForm, showRentTermModal, setShowRentTermModal, editingTerm, handleSaveRentTerm } =
    useRentContractFormContext();

  return (
    <Modal
      title={editingTerm ? '编辑租金条款' : '添加租金条款'}
      open={showRentTermModal}
      onCancel={() => setShowRentTermModal(false)}
      onOk={handleSaveRentTerm}
      width={600}
    >
      <Form form={termForm} layout="vertical">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="开始日期"
              name="start_date"
              rules={[{ required: true, message: '请选择开始日期' }]}
            >
              <DatePicker className={styles.fullWidthControl} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="结束日期"
              name="end_date"
              rules={[{ required: true, message: '请选择结束日期' }]}
            >
              <DatePicker className={styles.fullWidthControl} />
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
                className={styles.fullWidthControl}
                placeholder="请输入月租金"
                min={0}
                precision={2}
                formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={parseCurrency}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="管理费" name="management_fee">
              <InputNumber
                className={styles.fullWidthControl}
                placeholder="请输入管理费"
                min={0}
                precision={2}
                formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={parseCurrency}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="其他费用" name="other_fees">
              <InputNumber
                className={styles.fullWidthControl}
                placeholder="请输入其他费用"
                min={0}
                precision={2}
                formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={parseCurrency}
              />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item label="条款说明" name="rent_description">
          <TextArea rows={2} placeholder="请输入该租金条款的说明信息" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default RentTermModal;
