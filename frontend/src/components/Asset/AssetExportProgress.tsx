import React from 'react';
import { Button, Space, Typography, Progress, Alert } from 'antd';
import { CheckCircleOutlined, DownloadOutlined, LoadingOutlined } from '@ant-design/icons';

import type { ExportTaskWithApiFields } from './assetExportConfig';
import { formatFileSize } from './assetExportUtils';
import styles from './AssetExportProgress.module.css';

const { Title, Text } = Typography;

interface AssetExportProgressProps {
  exportTask: ExportTaskWithApiFields;
  onDownload: (task: ExportTaskWithApiFields) => void;
}

const AssetExportProgress: React.FC<AssetExportProgressProps> = ({ exportTask, onDownload }) => {
  return (
    <div className={styles.progressContainer}>
      <div className={styles.headerBlock}>
        <Space>
          <Title level={5} className={styles.title}>
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
            <CheckCircleOutlined className={styles.successIcon} />
          )}
        </Space>
      </div>

      <div className={styles.contentBlock}>
        <div className={styles.infoRow}>
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
            <div className={styles.fileSizeBlock}>
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
          <Alert
            title="导出失败"
            description={exportTask.error_message ?? '导出任务失败，请稍后重试'}
            type="error"
            showIcon
          />
        )}
      </div>
    </div>
  );
};

export default React.memo(AssetExportProgress);
