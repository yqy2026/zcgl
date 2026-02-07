import React from 'react';
import { Button, Space, Typography, Progress, Alert } from 'antd';
import { CheckCircleOutlined, DownloadOutlined, LoadingOutlined } from '@ant-design/icons';

import { COLORS } from '@/styles/colorMap';
import type { ExportTaskWithApiFields } from './assetExportConfig';
import { formatFileSize } from './assetExportUtils';

const { Title, Text } = Typography;

interface AssetExportProgressProps {
  exportTask: ExportTaskWithApiFields;
  onDownload: (task: ExportTaskWithApiFields) => void;
}

const AssetExportProgress: React.FC<AssetExportProgressProps> = ({ exportTask, onDownload }) => {
  return (
    <div style={{ marginTop: 24, padding: 16, background: '#fafafa', borderRadius: 8 }}>
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Title level={5} style={{ margin: 0 }}>
            {exportTask.status === 'completed'
              ? '导出完成'
              : exportTask.status === 'failed'
                ? '导出失败'
                : '正在导出...'}
          </Title>
          {(exportTask.status === 'running' || exportTask.status === 'processing') && (
            <LoadingOutlined />
          )}
          {exportTask.status === 'completed' && (
            <CheckCircleOutlined style={{ color: COLORS.success }} />
          )}
        </Space>
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <Text>文件名: {exportTask.filename}</Text>
          <Text>记录数: {exportTask.total_records ?? 0}</Text>
        </div>

        {(exportTask.status === 'running' || exportTask.status === 'processing') && (
          <Progress
            percent={exportTask.progress}
            status="active"
            format={percent => `${percent}%`}
          />
        )}

        {exportTask.status === 'completed' && (
          <div>
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary">文件大小: {formatFileSize(exportTask.file_size)}</Text>
            </div>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={() => onDownload(exportTask)}
            >
              下载文件
            </Button>
          </div>
        )}

        {exportTask.status === 'failed' && (
          <Alert title="导出失败" description={exportTask.errorMessage} type="error" showIcon />
        )}
      </div>
    </div>
  );
};

export default React.memo(AssetExportProgress);
