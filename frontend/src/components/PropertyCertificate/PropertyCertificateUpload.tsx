/**
 * Property Certificate Upload Component
 * 产权证上传组件
 */

import { useState } from 'react';
import { Upload, message, Card, Alert, Space } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { propertyCertificateService } from '@/services/propertyCertificateService';
import type { CertificateExtractionResult } from '@/types/propertyCertificate';

interface PropertyCertificateUploadProps {
  onSuccess: (result: CertificateExtractionResult) => void;
  loading?: boolean;
}

export const PropertyCertificateUpload: React.FC<PropertyCertificateUploadProps> = ({
  onSuccess,
  loading = false
}) => {
  const [uploading, setUploading] = useState(false);

  const uploadProps: UploadProps = {
    name: 'file',
    accept: '.pdf,.jpg,.jpeg,.png',
    beforeUpload: (file) => {
      const isValidType = ['application/pdf', 'image/jpeg', 'image/png'].includes(file.type);
      if (!isValidType) {
        message.error('只支持 PDF、JPG、PNG 格式');
      }
      const isValidSize = file.size / 1024 / 1024 < 10;
      if (!isValidSize) {
        message.error('文件大小不能超过 10MB');
      }
      return isValidType && isValidSize;
    },
    customRequest: async (options) => {
      const { file, onSuccess: uploadSuccess, onError } = options;
      setUploading(true);
      try {
        const result = await propertyCertificateService.uploadCertificate(file as File);
        if (uploadSuccess != null) {
          uploadSuccess(result);
        }
        options.onSuccess?.(result);
        message.success('文件上传并提取成功');
        onSuccess(result);
      } catch (error) {
        if (onError != null) {
          onError(error as Error);
        }
        message.error('上传失败，请重试');
      } finally {
        setUploading(false);
      }
    },
    showUploadList: false
  };

  return (
    <Card>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Alert
          message="上传产权证扫描件"
          description="支持 PDF、JPG、PNG 格式，最大 10MB。系统将自动提取产权证信息。"
          type="info"
          showIcon
        />

        <Upload.Dragger {...uploadProps} disabled={uploading || loading}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持单个文件上传。系统将使用 AI 自动识别产权证信息。
          </p>
        </Upload.Dragger>

        {(uploading || loading) && (
          <Alert
            message="正在处理..."
            description="AI 正在分析文件并提取信息，请稍候..."
            type="info"
            showIcon
          />
        )}
      </Space>
    </Card>
  );
};
