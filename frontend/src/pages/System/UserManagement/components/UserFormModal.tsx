import React from 'react';
import { Button, Col, Form, Input, Modal, Row, Select, Space } from 'antd';
import type { FormInstance } from 'antd/es/form';
import type {
  CreateUserData,
  OrganizationOption,
  RoleOption,
  UpdateUserData,
  User,
} from '@/services/systemService';
import styles from '../../UserManagementPage.module.css';

const { Option } = Select;

interface UserFormModalProps {
  open: boolean;
  editingUser: User | null;
  form: FormInstance;
  organizations: OrganizationOption[];
  roles: RoleOption[];
  statusOptions: Array<{ value: 'active' | 'inactive'; label: string }>;
  onCancel: () => void;
  onSubmit: (values: CreateUserData | UpdateUserData) => void | Promise<void>;
  onFullNameChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const UserFormModal: React.FC<UserFormModalProps> = ({
  open,
  editingUser,
  form,
  organizations,
  roles,
  statusOptions,
  onCancel,
  onSubmit,
  onFullNameChange,
}) => {
  return (
    <Modal
      title={editingUser != null ? '编辑用户' : '新建用户'}
      open={open}
      onCancel={onCancel}
      footer={null}
      forceRender
      width={600}
    >
      <Form form={form} layout="vertical" onFinish={onSubmit}>
        <Row gutter={16}>
          <Col span={24}>
            <Form.Item
              name="default_organization_id"
              label="所属组织"
              rules={[{ required: true, message: '请选择所属组织' }]}
            >
              <Select placeholder="请选择所属组织">
                {organizations.map(org => (
                  <Option key={org.id} value={org.id}>
                    {org.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="full_name"
              label="姓名"
              rules={[{ required: true, message: '请输入姓名' }]}
            >
              <Input placeholder="请输入姓名" onChange={onFullNameChange} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="phone"
              label="手机号"
              rules={[
                { required: true, message: '请输入手机号' },
                { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号格式' },
              ]}
            >
              <Input placeholder="请输入手机号" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="username"
              label="用户名"
              rules={[
                { required: true, message: '请输入用户名' },
                { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' },
              ]}
            >
              <Input placeholder="请输入用户名（输入姓名后自动生成拼音）" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="email"
              label="邮箱"
              rules={[{ type: 'email', message: '请输入正确的邮箱格式' }]}
            >
              <Input placeholder="请输入邮箱（选填）" />
            </Form.Item>
          </Col>
        </Row>

        {editingUser == null && (
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="password"
                label="密码"
                rules={[
                  { required: true, message: '请输入密码' },
                  { min: 8, message: '密码至少8位' },
                  {
                    pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$/,
                    message: '密码需包含大小写字母、数字和特殊字符',
                  },
                ]}
              >
                <Input.Password placeholder="请输入密码（至少8位，需包含大小写字母、数字和特殊字符）" />
              </Form.Item>
            </Col>
          </Row>
        )}

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="status" label="状态">
              <Select placeholder="请选择状态（默认活跃）">
                {statusOptions.map(status => (
                  <Option key={status.value} value={status.value}>
                    {status.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="role_id" label="角色">
              <Select placeholder="请选择角色（选填）">
                {roles.map(role => (
                  <Option key={role.id} value={role.id}>
                    {role.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item className={styles.formActions}>
          <Space>
            <Button onClick={onCancel} className={styles.actionButton}>
              取消
            </Button>
            <Button type="primary" htmlType="submit" className={styles.actionButton}>
              {editingUser != null ? '更新' : '创建'}
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default UserFormModal;
