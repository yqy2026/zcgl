/**
 * 增强PDF导入上传组件
 * 提供更好的用户体验和进度反馈
 *
 * 重构版本 - 使用子组件架构提高可维护性
 */

import React from 'react';
import { Card, Space, Button, Tooltip, Badge } from 'antd';
import { CloudUploadOutlined, SettingOutlined, EyeOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd';

import {
  PDFImportProvider,
  usePDFImportContext,
  ProcessingStepsDisplay,
  PDFUploadArea,
  AdvancedOptionsPanel,
  SystemInfoDisplay,
  UploadStatsPanel,
  ActionButtons,
  PreviewModal,
} from './PDFImport';

interface EnhancedPDFImportUploaderProps {
  onUploadSuccess: (sessionId: string, fileInfo: UploadFile) => void;
  onUploadError: (error: string) => void;
  maxSize?: number; // MB
  className?: string;
}

/**
 * 内部组件 - 使用Context
 */
const EnhancedPDFImportUploaderInner: React.FC<{ className?: string }> = ({ className }) => {
  const {
    systemInfo,
    currentSession,
    showAdvancedOptions,
    setShowAdvancedOptions,
    setShowPreviewModal,
  } = usePDFImportContext();

  return (
    <div className={className}>
      <Card
        title={
          <Space>
            <CloudUploadOutlined />
            <span>智能PDF导入</span>
            {systemInfo !== null && systemInfo !== undefined && (
              <Badge count="AI增强" style={{ backgroundColor: '#52c41a' }} />
            )}
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="高级选项">
              <Button
                type="text"
                icon={<SettingOutlined />}
                onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
              />
            </Tooltip>
            {currentSession !== null && currentSession !== undefined && (
              <Tooltip title="预览处理结果">
                <Button
                  type="text"
                  icon={<EyeOutlined />}
                  onClick={() => setShowPreviewModal(true)}
                />
              </Tooltip>
            )}
          </Space>
        }
      >
        {/* 处理步骤显示 */}
        <ProcessingStepsDisplay />

        {/* 上传区域 */}
        <PDFUploadArea />

        {/* 高级选项 */}
        <AdvancedOptionsPanel />

        {/* 系统信息显示 */}
        <SystemInfoDisplay />

        {/* 处理统计 */}
        <UploadStatsPanel />

        {/* 操作按钮 */}
        <ActionButtons />

        {/* 预览模态框 */}
        <PreviewModal />
      </Card>
    </div>
  );
};

/**
 * 增强PDF导入上传组件
 *
 * 使用Provider包装内部组件，提供状态管理
 */
const EnhancedPDFImportUploader: React.FC<EnhancedPDFImportUploaderProps> = ({
  onUploadSuccess,
  onUploadError,
  maxSize = 50,
  className,
}) => {
  return (
    <PDFImportProvider
      maxSize={maxSize}
      onUploadSuccess={onUploadSuccess}
      onUploadError={onUploadError}
    >
      <EnhancedPDFImportUploaderInner className={className} />
    </PDFImportProvider>
  );
};

export default EnhancedPDFImportUploader;
