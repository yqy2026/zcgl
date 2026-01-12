/**
 * PDF合同文件上传组件
 */

import React, { useState, useCallback } from 'react';
import {
  Upload,
  Button,
  Card,
  Progress,
  Alert,
  Space,
  Typography,
  Divider,
  Row,
  Col,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  InboxOutlined,
  UploadOutlined,
  DeleteOutlined,
  EyeOutlined,
  CloseOutlined
} from '@ant-design/icons';
import type { UploadFile, UploadProps, RcFile } from 'antd/es/upload/interface';

import { pdfImportService, type FileUploadResponse } from '../../services/pdfImportService';
import { createLogger } from '../../utils/logger';
import { COLORS } from '@/styles/colorMap';

const _pageLogger = createLogger('ContractImportUpload');

const { Title, Text, Paragraph } = Typography;

interface ContractImportUploadProps {
  onUploadSuccess: (sessionId: string, fileInfo: UploadFile) => void;
  onUploadError: (error: string) => void;
  maxFileSize?: number; // MB
}

const ContractImportUpload: React.FC<ContractImportUploadProps> = ({
  onUploadSuccess,
  onUploadError,
  maxFileSize = 50
}) => {
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [sessionId, setSessionId] = useState<string>('');
  const [uploadedFile, setUploadedFile] = useState<UploadFile | null>(null);
  /* Removed systemInfo state */
  /* const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null); */
  /* Removed showAdvanced state */
  /* const [showAdvanced, setShowAdvanced] = useState(false); */
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  /* Removed loadSystemInfo effect */

  // 文件上传前的验证
  const beforeUpload = useCallback((file: RcFile) => {
    // 验证文件类型
    if (!pdfImportService.validateFileType(file)) {
      MessageManager.error('只支持PDF文件格式！');
      return false;
    }

    // 验证文件大小
    if (!pdfImportService.validateFileSize(file, maxFileSize)) {
      MessageManager.error(`文件大小不能超过 ${maxFileSize}MB！当前文件大小：${pdfImportService.formatFileSize(file.size)}`);
      return false;
    }

    // 不在这里设置状态，让customRequest处理
    return true;
  }, [maxFileSize]);

  // 取消上传
  const handleCancelUpload = useCallback(() => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
    setUploadStatus('idle');
    setUploadProgress(0);
    MessageManager.info('已取消上传');
  }, [abortController]);

  // 自定义上传请求
  const customRequest = useCallback(async (options: Parameters<Required<UploadProps>['customRequest']>[0]) => {
    const { file, onProgress, onSuccess, onError } = options;
    const pdfFile = file as RcFile;

    // 设置上传状态
    setUploadStatus('uploading');
    setUploadProgress(0);

    // 创建新的AbortController
    const controller = new AbortController();
    setAbortController(controller);

    try {

      const response: FileUploadResponse = await pdfImportService.uploadPDFFile(
        pdfFile,
        false, // 不再使用markitdown
        controller.signal
      );

      // 清理controller
      setAbortController(null);

      if (response.success) {
        // 完成进度
        setUploadProgress(100);
        if (onProgress) {
          onProgress({ percent: 100 });
        }

        const uploadFile: UploadFile = {
          uid: response.session_id || Date.now().toString(),
          name: pdfFile.name,
          status: 'done',
          size: pdfFile.size,
          type: pdfFile.type,
          originFileObj: pdfFile
        };

        setUploadedFile(uploadFile);
        setSessionId(response.session_id || '');
        setUploadStatus('success');
        if (onSuccess) {
          onSuccess(response);
        }

        // 重要：立即调用父组件的成功回调，让父组件接管后续处理
        if (response.session_id) {
          onUploadSuccess(response.session_id, uploadFile);
          MessageManager.success('文件上传成功！正在处理中...');
        } else {
          throw new Error('未收到有效的会话ID');
        }
      } else {
        throw new Error(response.error || response.message || '上传失败');
      }
    } catch (error: unknown) {
      // 清理controller
      setAbortController(null);

      // 如果是手动取消，不显示错误消息
      const err = error as Error;
      if (err.name === 'AbortError' || err.message === 'canceled') {
        return;
      }

      setUploadStatus('error');
      setUploadProgress(0);
      if (onError) {
        onError(err);
      }
      onUploadError(err.message || '上传失败');
      MessageManager.error(err.message || '文件上传失败');
    }
  }, [onUploadSuccess, onUploadError]);

  // 移除文件
  const handleRemove = useCallback(() => {
    setUploadedFile(null);
    setSessionId('');
    setUploadStatus('idle');
    setUploadProgress(0);
  }, []);

  // 重新上传
  const handleReupload = useCallback(() => {
    handleRemove();
  }, [handleRemove]);

  // 上传区域props
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf',
    beforeUpload,
    customRequest,
    showUploadList: false,
    disabled: uploadStatus === 'uploading'
  };

  /* Removed getSystemStatusTags function */

  return (
    <div className="contract-import-upload">
      <Card
        title={
          <Space>
            <UploadOutlined />
            <span>PDF合同文件上传</span>
          </Space>
        }
      /* Removed extra actions for Advanced Options */
      >
        {/* Removed System Status section */}

        <Divider />

        {/* 上传区域 */}
        {uploadStatus === 'idle' && (
          <Upload.Dragger {...uploadProps}>
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ fontSize: 48, color: COLORS.primary }} />
            </p>
            <p className="ant-upload-text" style={{ fontSize: 16, fontWeight: 500 }}>
              点击或拖拽PDF合同文件到此区域上传
            </p>
            <p className="ant-upload-hint" style={{ color: COLORS.textSecondary }}>
              支持单个PDF文件上传，文件大小不超过 {maxFileSize}MB
            </p>
            <p className="ant-upload-hint" style={{ color: COLORS.textTertiary, fontSize: 12 }}>
              系统将自动提取合同信息，包括合同编号、承租方、地址、租金等关键字段
            </p>
          </Upload.Dragger>
        )}

        {/* 上传进度 */}
        {uploadStatus === 'uploading' && (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <Title level={4}>
              {uploadProgress < 100 ? '正在上传文件...' : '文件上传成功，正在处理中...'}
            </Title>
            <Progress
              percent={uploadProgress}
              status={uploadProgress < 100 ? "active" : "success"}
              strokeColor={{
                '0%': COLORS.primary,
                '100%': COLORS.success,
              }}
              style={{ marginBottom: 16 }}
            />
            <Text type="secondary">
              {uploadProgress < 100
                ? '正在上传文件到服务器，请稍候...'
                : '文件已上传，系统正在进行PDF转换和信息提取，请耐心等待...'}
            </Text>
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                提示：处理时间通常为30-60秒，复杂文件可能需要更长时间
              </Text>
            </div>

            {uploadProgress < 100 && (
              <div style={{ marginTop: 16 }}>
                <Button
                  danger
                  icon={<CloseOutlined />}
                  onClick={handleCancelUpload}
                >
                  取消上传
                </Button>
              </div>
            )}
          </div>
        )}

        {/* 上传成功 */}
        {uploadStatus === 'success' && uploadedFile && (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{
              width: 80,
              height: 80,
              margin: '0 auto 16px',
              borderRadius: '50%',
              backgroundColor: 'var(--color-primary-light)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <EyeOutlined style={{ fontSize: 32, color: COLORS.success }} />
            </div>

            <Title level={4} style={{ color: COLORS.success, margin: '16px 0 8px' }}>
              文件上传成功！
            </Title>

            <div style={{
              backgroundColor: COLORS.bgTertiary,
              padding: '12px 16px',
              borderRadius: '6px',
              marginBottom: 16
            }}>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Row justify="space-between">
                  <Col><Text type="secondary">文件名：</Text></Col>
                  <Col><Text strong>{uploadedFile.name}</Text></Col>
                </Row>
                <Row justify="space-between">
                  <Col><Text type="secondary">文件大小：</Text></Col>
                  <Col><Text>{pdfImportService.formatFileSize(uploadedFile.size || 0)}</Text></Col>
                </Row>
                <Row justify="space-between">
                  <Col><Text type="secondary">会话ID：</Text></Col>
                  <Col><Text code style={{ fontSize: 12 }}>{sessionId}</Text></Col>
                </Row>
              </Space>
            </div>

            <Alert
              message="文件正在处理中"
              description="系统正在自动提取PDF中的合同信息，请稍候..."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Space>
              <Button
                type="primary"
                icon={<EyeOutlined />}
                onClick={() => {
                  // 这里可以跳转到进度查看页面
                  MessageManager.info('请等待处理完成后查看结果');
                }}
              >
                查看处理进度
              </Button>
              <Button
                icon={<UploadOutlined />}
                onClick={handleReupload}
              >
                重新上传
              </Button>
            </Space>
          </div>
        )}

        {/* 上传失败 */}
        {uploadStatus === 'error' && (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{
              width: 80,
              height: 80,
              margin: '0 auto 16px',
              borderRadius: '50%',
              backgroundColor: 'var(--color-error-light)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <DeleteOutlined style={{ fontSize: 32, color: COLORS.error }} />
            </div>

            <Title level={4} style={{ color: COLORS.error, margin: '16px 0 8px' }}>
              文件上传失败
            </Title>

            <Paragraph style={{ color: COLORS.textSecondary, marginBottom: 16 }}>
              上传过程中发生错误，请检查文件格式和大小后重试。
            </Paragraph>

            <Space>
              <Button
                type="primary"
                icon={<UploadOutlined />}
                onClick={handleReupload}
              >
                重新上传
              </Button>
              {/* Removed View System Status button */}
            </Space>
          </div>
        )}

        {/* Removed Advanced Options panel */}

        {/* 使用说明 */}
        {uploadStatus === 'idle' && (
          <div style={{ marginTop: 24, padding: 16, backgroundColor: 'var(--color-primary-light)', borderRadius: 6 }}>
            <Title level={5} style={{ color: COLORS.primaryActive, marginBottom: 12 }}>
              <EyeOutlined /> 使用说明
            </Title>
            <Space direction="vertical" size="small">
              <Text>• 支持标准PDF格式的合同文件</Text>
              <Text>• 系统将自动提取58个关键字段，包括合同编号、承租方、地址、租金等</Text>
              <Text>• 提取完成后可以进行人工确认和修改</Text>
              <Text>• 支持与现有资产和权属方数据进行智能匹配</Text>
              <Text>• 处理时间通常为30-60秒，取决于文件大小和复杂度</Text>
            </Space>
          </div>
        )}
      </Card>
    </div>
  );
};

export default ContractImportUpload;
