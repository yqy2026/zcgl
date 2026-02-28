import React, { type ReactNode } from 'react';
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  TreeSelect,
} from 'antd';
import type { DataNode } from 'antd/es/tree';
import type { FormInstance } from 'antd/es/form';
import type { Organization } from '@/types/organization';
import type { OrganizationFormData, OrganizationSelectOption } from '../types';
import styles from '../../OrganizationPage.module.css';

const { Option } = Select;

interface OrganizationFormModalProps {
  open: boolean;
  editingOrganization: Organization | null;
  form: FormInstance<OrganizationFormData>;
  organizationTree: DataNode[];
  organizationTypeOptions: OrganizationSelectOption[];
  organizationStatusOptions: OrganizationSelectOption[];
  isTypeOptionsLoading: boolean;
  isStatusOptionsLoading: boolean;
  getTypeIcon: (type: string) => ReactNode;
  getStatusTag: (status: string, className?: string) => ReactNode;
  readOnlyMode: boolean;
  onCancel: () => void;
  onSubmit: (values: OrganizationFormData) => Promise<void>;
}

const OrganizationFormModal: React.FC<OrganizationFormModalProps> = ({
  open,
  editingOrganization,
  form,
  organizationTree,
  organizationTypeOptions,
  organizationStatusOptions,
  isTypeOptionsLoading,
  isStatusOptionsLoading,
  getTypeIcon,
  getStatusTag,
  readOnlyMode,
  onCancel,
  onSubmit,
}) => {
  return (
    <Modal
      title={editingOrganization != null ? '编辑组织' : '新建组织'}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={800}
    >
      <Form form={form} layout="vertical" onFinish={onSubmit} disabled={readOnlyMode}>
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              name="name"
              label="组织名称"
              rules={[{ required: true, message: '请输入组织名称' }]}
            >
              <Input placeholder="请输入组织名称" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item
              name="code"
              label="组织编码"
              rules={[
                { required: true, message: '请输入组织编码' },
                {
                  pattern: /^[A-Z0-9_-]+$/,
                  message: '编码只能包含大写字母、数字、下划线和连字符',
                },
              ]}
            >
              <Input placeholder="请输入组织编码" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} sm={12} md={8}>
            <Form.Item
              name="type"
              label="组织类型"
              rules={[{ required: true, message: '请选择组织类型' }]}
            >
              <Select placeholder="请选择组织类型" loading={isTypeOptionsLoading}>
                {organizationTypeOptions.map(type => (
                  <Option key={type.value} value={type.value}>
                    {getTypeIcon(type.value)} {type.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Form.Item
              name="status"
              label="状态"
              rules={[{ required: true, message: '请选择状态' }]}
            >
              <Select placeholder="请选择状态" loading={isStatusOptionsLoading}>
                {organizationStatusOptions.map(status => (
                  <Option key={status.value} value={status.value}>
                    {getStatusTag(status.value)}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Form.Item name="sort_order" label="排序">
              <InputNumber min={0} placeholder="排序号" className={styles.fullWidthControl} />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="parent_id" label="上级组织">
          <TreeSelect
            placeholder="请选择上级组织"
            allowClear
            treeData={organizationTree}
            treeDefaultExpandAll
          />
        </Form.Item>

        <Form.Item name="description" label="组织描述">
          <Input.TextArea rows={3} placeholder="请输入组织描述" />
        </Form.Item>

        {editingOrganization != null && (
          <Card size="small" title="系统字段" className={styles.systemFieldsCard}>
            <Row gutter={16}>
              <Col span={24}>
                <Form.Item label="组织路径" className={styles.compactFieldItem}>
                  <Input value={editingOrganization.path ?? '-'} disabled />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="创建人" className={styles.compactFieldLastItem}>
                  <Input value={editingOrganization.created_by ?? '-'} disabled />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="更新人" className={styles.compactFieldLastItem}>
                  <Input value={editingOrganization.updated_by ?? '-'} disabled />
                </Form.Item>
              </Col>
            </Row>
          </Card>
        )}

        <Form.Item className={styles.formActions}>
          <Space size={8} className={styles.formActionGroup}>
            <Button
              onClick={onCancel}
              className={`${styles.actionButton} ${styles.modalActionButton}`}
            >
              取消
            </Button>
            <Button
              type="primary"
              htmlType="submit"
              disabled={readOnlyMode}
              className={`${styles.actionButton} ${styles.modalActionButton}`}
            >
              {editingOrganization != null ? '更新' : '创建'}
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default OrganizationFormModal;
