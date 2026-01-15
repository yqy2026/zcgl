/**
 * PDF导入状态展示组件
 *
 * 展示导入成功或失败的状态页面
 */

import React from 'react';
import { Button, Space, Typography } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { COLORS } from '@/styles/colorMap';

const { Title, Paragraph } = Typography;

interface ImportStatusStatesProps {
  status: 'completed' | 'failed';
  fileName?: string;
  error?: string;
  onUploadNew: () => void;
  onViewHistory: () => void;
}

export const ImportStatusStates: React.FC<ImportStatusStatesProps> = ({
  status,
  fileName,
  error,
  onUploadNew,
  onViewHistory
}) => {
  if (status === 'completed') {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <CheckCircleOutlined style={{ fontSize: 64, color: COLORS.success, marginBottom: 16 }} />
        <Title level={4} style={{ color: COLORS.success }}>
          导入成功！
        </Title>
        <Paragraph>
          合同已成功导入到系统中。
        </Paragraph>
        <Space>
          <Button type="primary" onClick={onUploadNew}>
            导入新合同
          </Button>
          <Button onClick={onViewHistory}>
            查看历史记录
          </Button>
        </Space>
      </div>
    );
  }

  // status === 'failed'
  return (
    <div style={{ textAlign: 'center', padding: '40px' }}>
      <CloseCircleOutlined style={{ fontSize: 64, color: COLORS.error, marginBottom: 16 }} />
      <Title level={4} style={{ color: COLORS.error }}>
        处理失败
      </Title>
      <Paragraph>
        {error ?? '处理过程中发生错误'}
      </Paragraph>
      <Space>
        <Button onClick={onUploadNew}>
          重新上传
        </Button>
        <Button onClick={onViewHistory}>
          查看历史记录
        </Button>
      </Space>
    </div>
  );
};
