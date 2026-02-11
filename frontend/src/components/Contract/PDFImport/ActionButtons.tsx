/**
 * 操作按钮组件
 */

import React from 'react';
import { Space, Button } from 'antd';
import { usePDFImportContext } from './PDFImportContext';
import styles from './ActionButtons.module.css';

const ActionButtons: React.FC = () => {
  const { uploading, currentSession, handleCancel, handleReset } = usePDFImportContext();

  if (
    (uploading === undefined || uploading === null || uploading === false) &&
    (currentSession === undefined || currentSession === null)
  ) {
    return null;
  }

  return (
    <div className={styles.actionContainer}>
      <Space className={styles.actionSpace}>
        <Button onClick={handleCancel} danger>
          取消处理
        </Button>
        <Button onClick={handleReset}>重新开始</Button>
      </Space>
    </div>
  );
};

export default ActionButtons;
