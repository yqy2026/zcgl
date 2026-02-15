import React from 'react';
import { Button, Col, Form, Input, Modal, Row, Select, Space } from 'antd';
import type { FormInstance } from 'antd/es/form';
import type { Role } from '@/services/systemService';
import styles from '../../RoleManagementPage.module.css';

const { Option } = Select;
const { TextArea } = Input;

interface RoleFormValues {
  name: string;
  code: string;
  description: string;
  status: 'active' | 'inactive';
}

interface RoleFormModalProps {
  open: boolean;
  editingRole: Role | null;
  form: FormInstance;
  statusOptions: Array<{ value: 'active' | 'inactive'; label: string }>;
  onCancel: () => void;
  onSubmit: (values: RoleFormValues) => void | Promise<void>;
}

const RoleFormModal: React.FC<RoleFormModalProps> = ({
  open,
  editingRole,
  form,
  statusOptions,
  onCancel,
  onSubmit,
}) => {
  return (
    <Modal
      title={editingRole != null ? '编辑角色' : '新建角色'}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={600}
    >
      <Form form={form} layout="vertical" onFinish={onSubmit}>
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              name="name"
              label="角色名称"
              rules={[{ required: true, message: '请输入角色名称' }]}
            >
              <Input placeholder="请输入角色名称" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item
              name="code"
              label="角色编码"
              rules={[
                { required: true, message: '请输入角色编码' },
                {
                  pattern: /^[a-z_][a-z0-9_]*$/,
                  message: '编码只能包含小写字母、数字和下划线，且不能以数字开头',
                },
              ]}
            >
              <Input placeholder="请输入角色编码" disabled={editingRole != null} />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="description"
          label="角色描述"
          rules={[{ required: true, message: '请输入角色描述' }]}
        >
          <TextArea rows={3} placeholder="请输入角色描述" />
        </Form.Item>

        <Form.Item name="status" label="状态" rules={[{ required: true, message: '请选择状态' }]}>
          <Select placeholder="请选择状态">
            {statusOptions.map(status => (
              <Option key={status.value} value={status.value}>
                {status.label}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item className={styles.modalFooter}>
          <Space size={8} className={styles.modalFooterActions}>
            <Button className={styles.modalActionButton} onClick={onCancel}>
              取消
            </Button>
            <Button type="primary" htmlType="submit" className={styles.modalActionButton}>
              {editingRole != null ? '更新' : '创建'}
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default RoleFormModal;
