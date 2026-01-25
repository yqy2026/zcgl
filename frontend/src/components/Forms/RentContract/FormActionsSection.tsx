import React from 'react';
import { Button, Space } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import { useRentContractFormContext } from './RentContractFormContext';

/**
 * RentContractForm - Form Actions
 * Submit and cancel buttons
 */
const FormActionsSection: React.FC = () => {
  const { mode, isLoading, onCancel } = useRentContractFormContext();

  return (
    <div style={{ textAlign: 'right', marginTop: 24 }}>
      <Space>
        <Button onClick={onCancel}>取消</Button>
        <Button type="primary" htmlType="submit" loading={isLoading} icon={<SaveOutlined />}>
          {mode === 'create' ? '创建合同' : '更新合同'}
        </Button>
      </Space>
    </div>
  );
};

export default FormActionsSection;
