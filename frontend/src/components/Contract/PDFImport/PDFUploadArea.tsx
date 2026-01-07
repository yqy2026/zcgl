/**
 * PDF上传区域组件
 */

import React, { useCallback } from 'react';
import { Upload, message } from 'antd';
import { CloudUploadOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { usePDFImportContext, usePDFImportUpload } from './PDFImportContext';

const { Dragger } = Upload;

const PDFUploadArea: React.FC = () => {
  const { uploading, currentSession, maxSize } = usePDFImportContext();
  const handleUpload = usePDFImportUpload();

  // 文件上传前验证
  const beforeUpload = useCallback(
    (file: File) => {
      const isPDF = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
      if (!isPDF) {
        message.error('只能上传PDF文件！');
        return false;
      }

      const isLtMaxSize = file.size / 1024 / 1024 < maxSize;
      if (!isLtMaxSize) {
        message.error(`文件大小不能超过 ${maxSize}MB！`);
        return false;
      }

      return true;
    },
    [maxSize]
  );

  // 上传配置
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf,application/pdf',
    beforeUpload,
    showUploadList: false,
    customRequest: ({ file, onSuccess, onError }) => {
      void handleUpload(file as File, onSuccess, onError);
    },
  };

  // 如果已有会话，不显示上传区域
  if (currentSession != null) {
    return null;
  }

  return (
    <Dragger {...uploadProps} disabled={uploading}>
      <p className="ant-upload-drag-icon">
        <CloudUploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
      </p>
      <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
      <p className="ant-upload-hint">支持PDF文件，最大{maxSize}MB</p>
    </Dragger>
  );
};

export default PDFUploadArea;
