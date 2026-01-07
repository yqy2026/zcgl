/**
 * PDF导入上传组件 - Context
 */

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import type { UploadFile } from 'antd';
import { message } from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  FileTextOutlined,
} from '@ant-design/icons';

import { pdfImportService } from '../../../services/pdfImportService';
import type { SessionProgress, SystemInfoResponse } from '../../../services/pdfImportService';
import { createLogger } from '../../../utils/logger';
import type { PDFImportContextType, ProcessingStep, ProcessingOptions, UploadStats } from './types';
import { DEFAULT_PROCESSING_OPTIONS } from './types';

const logger = createLogger('PDFImportContext');

const PDFImportContext = createContext<PDFImportContextType | null>(null);

export const usePDFImportContext = (): PDFImportContextType => {
  const context = useContext(PDFImportContext);
  if (!context) {
    throw new Error('usePDFImportContext must be used within PDFImportProvider');
  }
  return context;
};

interface PDFImportProviderProps {
  children: React.ReactNode;
  maxSize: number;
  onUploadSuccess: (sessionId: string, fileInfo: UploadFile) => void;
  onUploadError: (error: string) => void;
}

// 初始化处理步骤
const initializeProcessingSteps = (): ProcessingStep[] => [
  {
    title: '文件上传',
    description: '上传PDF文件到服务器',
    status: 'wait',
  },
  {
    title: '文档分析',
    description: '分析文档类型和质量',
    status: 'wait',
  },
  {
    title: '文本提取',
    description: '提取PDF文本内容',
    status: 'wait',
  },
  {
    title: '信息识别',
    description: '智能识别合同信息',
    status: 'wait',
  },
  {
    title: '数据验证',
    description: '验证和映射数据',
    status: 'wait',
  },
  {
    title: '处理完成',
    description: '准备人工确认',
    status: 'wait',
  },
];

export const PDFImportProvider: React.FC<PDFImportProviderProps> = ({
  children,
  maxSize,
  onUploadSuccess,
  onUploadError,
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [processingProgress, setProcessingProgress] = useState<SessionProgress | null>(null);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [uploadStats, setUploadStats] = useState<UploadStats | null>(null);
  const [processingSteps, setProcessingSteps] = useState<ProcessingStep[]>(
    initializeProcessingSteps()
  );
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [processingOptions, setProcessingOptions] = useState<ProcessingOptions>(
    DEFAULT_PROCESSING_OPTIONS
  );

  const abortControllerRef = useRef<AbortController | null>(null);
  const progressTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 加载系统信息
  useEffect(() => {
    const loadSystemInfo = async () => {
      try {
        const info = await pdfImportService.getEnhancedSystemInfo();
        setSystemInfo(info);
      } catch {
        // Failed to get system info
      }
    };

    void loadSystemInfo();

    return () => {
      if (progressTimerRef.current != null) {
        clearInterval(progressTimerRef.current);
      }
      if (abortControllerRef.current != null) {
        abortControllerRef.current.abort();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 更新处理步骤状态
  const updateProcessingSteps = useCallback((progress: SessionProgress) => {
    const steps = initializeProcessingSteps();

    const stepMapping: Record<string, number> = {
      uploading: 0,
      analyzing: 1,
      text_extraction: 2,
      info_extraction: 3,
      validation: 4,
      matching: 4,
      ready_for_review: 5,
      completed: 5,
      failed: -1,
    };

    const currentStepIndex = stepMapping[progress.status] || 0;

    steps.forEach((step, index) => {
      if (index < currentStepIndex) {
        step.status = 'finish';
        step.progress = 100;
      } else if (index === currentStepIndex) {
        step.status = progress.status === 'failed' ? 'error' : 'process';
        step.progress = progress.progress;
      } else {
        step.status = 'wait';
        step.progress = 0;
      }
    });

    setProcessingSteps(steps);
  }, []);

  // 开始进度轮询
  const startProgressPolling = useCallback(
    (sessionId: string) => {
      if (progressTimerRef.current != null) {
        clearInterval(progressTimerRef.current);
      }

      progressTimerRef.current = setInterval(() => {
        void (async () => {
          try {
            const result = await pdfImportService.getEnhancedProgress(sessionId);

            if (result.success && result.session_status != null) {
              setProcessingProgress(result.session_status);
              updateProcessingSteps(result.session_status);

              if (
                ['ready_for_review', 'completed', 'failed', 'cancelled'].includes(
                  result.session_status.status
                )
              ) {
                if (progressTimerRef.current) {
                  clearInterval(progressTimerRef.current);
                  progressTimerRef.current = null;
                }

                if (
                  result.session_status.status === 'ready_for_review' ||
                  result.session_status.status === 'completed'
                ) {
                  message.success('文件处理完成！');
                } else if (result.session_status.status === 'failed') {
                  message.error(`处理失败: ${result.session_status.error_message ?? '未知错误'}`);
                }
              }
            }
          } catch (error) {
            logger.error('获取进度失败:', error as Error);
          }
        })();
      }, 2000);
    },
    [updateProcessingSteps]
  );

  // 上传处理函数 (暴露给上传组件使用)
  const handleUpload = useCallback(
    async (
      file: File,
      onSuccess?: (response: unknown) => void,
      onError?: (error: Error) => void
    ) => {
      try {
        setUploading(true);
        setUploadProgress(0);

        abortControllerRef.current = new AbortController();

        const progressInterval = setInterval(() => {
          setUploadProgress(prev => {
            const newProgress = prev + Math.random() * 10;
            return Math.min(newProgress, 90);
          });
        }, 200);

        const response = await pdfImportService.uploadPDFFileEnhanced(
          file,
          processingOptions,
          abortControllerRef.current.signal
        );

        clearInterval(progressInterval);
        setUploadProgress(100);

        if (response.success) {
          setCurrentSession(response.session_id!);
          startProgressPolling(response.session_id!);

          // 使用类型安全的方式访问enhanced_status
          const enhancedStatus = (
            response as unknown as {
              enhanced_status?: {
                final_results?: { extraction_quality?: { processing_methods?: string[] } };
              };
            }
          ).enhanced_status;
          if (enhancedStatus) {
            setUploadStats({
              uploadSpeed: file.size / 1024 / (Date.now() / 1000),
              estimatedTime: 30,
              fileAnalysis: {
                type: 'mixed',
                quality: 'good',
                recommendedMethod:
                  enhancedStatus.final_results?.extraction_quality?.processing_methods?.[0] ??
                  'hybrid',
              },
            });
          }

          onSuccess?.(response);
          onUploadSuccess(response.session_id!, {
            uid: (file as unknown as { uid: string }).uid,
            name: file.name,
            status: 'done',
            size: file.size,
            type: file.type,
          });

          message.success('文件上传成功，开始智能处理...');
        } else {
          throw new Error(response.error ?? '上传失败');
        }
      } catch (error: unknown) {
        setUploading(false);
        setUploadProgress(0);

        const errorMessage = error instanceof Error ? error.message : '上传失败';
        onError?.(new Error(errorMessage));
        onUploadError(errorMessage);
        message.error(errorMessage);
      } finally {
        setTimeout(() => {
          setUploading(false);
          setUploadProgress(0);
        }, 1000);
      }
    },
    [processingOptions, startProgressPolling, onUploadSuccess, onUploadError]
  );

  // 取消上传
  const handleCancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    if (currentSession !== null && currentSession !== '') {
      void pdfImportService.cancelEnhancedSession(currentSession, '用户取消');
    }

    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }

    setUploading(false);
    setUploadProgress(0);
    setProcessingProgress(null);
    setCurrentSession(null);
    setProcessingSteps(initializeProcessingSteps());

    message.info('已取消上传');
  }, [currentSession]);

  // 重置状态
  const handleReset = useCallback(() => {
    setUploading(false);
    setUploadProgress(0);
    setProcessingProgress(null);
    setCurrentSession(null);
    setProcessingSteps(initializeProcessingSteps());
    setUploadStats(null);
  }, []);

  // 获取步骤图标
  const getStepIcon = useCallback((step: ProcessingStep): React.ReactNode => {
    switch (step.status) {
      case 'finish':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'process':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <FileTextOutlined />;
    }
  }, []);

  const contextValue: PDFImportContextType & { handleUpload: typeof handleUpload } = {
    uploading,
    uploadProgress,
    currentSession,
    processingProgress,
    showAdvancedOptions,
    systemInfo,
    uploadStats,
    processingSteps,
    showPreviewModal,
    processingOptions,
    maxSize,
    setShowAdvancedOptions,
    setShowPreviewModal,
    setProcessingOptions,
    handleCancel,
    handleReset,
    getStepIcon,
    handleUpload,
  };

  return <PDFImportContext.Provider value={contextValue}>{children}</PDFImportContext.Provider>;
};

// 扩展 context 以包含 handleUpload
export const usePDFImportUpload = () => {
  const context = useContext(PDFImportContext) as PDFImportContextType & {
    handleUpload: (
      file: File,
      onSuccess?: (response: unknown) => void,
      onError?: (error: Error) => void
    ) => Promise<void>;
  };
  if (context === null || context === undefined) {
    throw new Error('usePDFImportUpload must be used within PDFImportProvider');
  }
  return context.handleUpload;
};
