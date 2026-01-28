import React from 'react';
import { Modal, Form, Input } from 'antd';
import { SaveOutlined } from '@ant-design/icons';

interface SaveSearchModalProps {
  visible: boolean;
  onSave: (name: string) => void;
  onCancel: () => void;
  loading?: boolean;
}

export const SaveSearchModal: React.FC<SaveSearchModalProps> = ({
  visible,
  onSave,
  onCancel,
  loading = false,
}) => {
  const [form] = Form.useForm();

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      onSave(values.name);
      form.resetFields();
    } catch {
      // Validation failed
    }
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  return (
    <Modal
      title="保存搜索条件"
      open={visible}
      onOk={handleOk}
      onCancel={handleCancel}
      confirmLoading={loading}
      okText="保存"
      cancelText="取消"
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label="搜索条件名称"
          rules={[
            { required: true, message: '请输入搜索条件名称' },
            { max: 50, message: '名称不能超过50个字符' },
            {
              pattern: /^[a-zA-Z0-9\u4e00-\u9fa5_-]+$/,
              message: '名称只能包含中文、英文、数字、下划线和连字符',
            },
          ]}
        >
          <Input
            placeholder="例如：空置商业物业"
            prefix={<SaveOutlined />}
            maxLength={50}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};
