import React from 'react';
import { Modal, List, Button, Tooltip, Tag, Space, Typography, Progress } from 'antd';
import { DeleteOutlined, DownloadOutlined } from '@ant-design/icons';

import type { ExportTaskWithApiFields } from './assetExportConfig';
import { formatFileSize, getStatusColor, getStatusText } from './assetExportUtils';
import styles from './AssetExportHistoryModal.module.css';

const { Text } = Typography;

interface AssetExportHistoryModalProps {
  open: boolean;
  exportHistory?: ExportTaskWithApiFields[];
  onClose: () => void;
  onDownload: (task: ExportTaskWithApiFields) => void;
  onDelete: (id: string) => void;
}

const AssetExportHistoryModal: React.FC<AssetExportHistoryModalProps> = ({
  open,
  exportHistory,
  onClose,
  onDownload,
  onDelete,
}) => {
  return (
    <Modal
      title="导出历史"
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={800}
    >
      <List
        dataSource={exportHistory}
        renderItem={(item: ExportTaskWithApiFields) => (
          <List.Item
            actions={[
              item.status === 'completed' &&
                item.download_url !== undefined && (
                  <Tooltip key="download" title="下载文件">
                    <Button
                      type="text"
                      icon={<DownloadOutlined />}
                      onClick={() => onDownload(item)}
                    />
                  </Tooltip>
                ),
              <Tooltip key="delete" title="删除记录">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => {
                    Modal.confirm({
                      title: '确认删除',
                      content: '确定要删除这条导出记录吗？',
                      onOk: () => onDelete(item.id),
                    });
                  }}
                />
              </Tooltip>,
            ].filter(Boolean)}
          >
            <List.Item.Meta
              title={
                <Space>
                  <Text strong>{item.filename}</Text>
                  <Tag color={getStatusColor(item.status)}>{getStatusText(item.status)}</Tag>
                </Space>
              }
              description={
                <div>
                  <div>创建时间: {new Date(item.created_at).toLocaleString()}</div>
                  <div>
                    记录数: {item.total_records ?? 0} | 文件大小: {formatFileSize(item.file_size)}
                  </div>
                  {(item.status === 'running' || item.status === 'processing') && (
                    <Progress percent={item.progress} size="small" className={styles.progressBar} />
                  )}
                </div>
              }
            />
          </List.Item>
        )}
      />
    </Modal>
  );
};

export default React.memo(AssetExportHistoryModal);
