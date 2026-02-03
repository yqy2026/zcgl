/**
 * 系统信息显示组件
 */

import React from 'react';
import { Alert, Space, Tag } from 'antd';
import { RocketOutlined } from '@ant-design/icons';
import { usePDFImportContext } from './PDFImportContext';

const SystemInfoDisplay: React.FC = () => {
  const { systemInfo } = usePDFImportContext();

  if (!systemInfo) {
    return null;
  }

  return (
    <Alert
      title={
        <Space>
          <RocketOutlined />
          <span>AI增强PDF处理系统已就绪</span>
        </Space>
      }
      description={
        <Space wrap>
          <Tag color="blue">多引擎处理</Tag>
          <Tag color="green">中文优化</Tag>
          <Tag color="purple">智能验证</Tag>
          <Tag color="orange">语义分析</Tag>
        </Space>
      }
      type="success"
      showIcon
      style={{ marginTop: 16 }}
    />
  );
};

export default SystemInfoDisplay;
