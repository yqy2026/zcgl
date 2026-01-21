/**
 * PDF导入会话管理 Hook
 *
 * 封装所有PDF导入会话的状态管理和业务逻辑:
 * - 会话状态管理(当前会话、历史记录)
 * - API调用封装
 * - 事件处理函数
 */

import { useState, useCallback, useRef } from 'react';
import type { UploadFile } from 'antd/es/upload/interface';
import { pdfImportService } from '@/services/pdfImportService';
import type {
  CompleteResult,
  ConfirmedContractData,
  ConfirmImportResponse,
} from '@/services/pdfImportService';
import type { ProcessingSession } from '@/types/pdfImport';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';

const sessionLogger = createLogger('PDFImportSession');

interface ApiError {
  response?: {
    data?: {
      message?: string;
      detail?: string;
    };
  };
  message?: string;
}

export const usePDFImportSession = () => {
  const [currentSession, setCurrentSession] = useState<ProcessingSession | null>(null);
  const [sessionHistory, setSessionHistory] = useState<ProcessingSession[]>([]);
  const [loading, setLoading] = useState(false);

  // 使用 ref 避免闭包问题
  const currentSessionRef = useRef(currentSession);
  currentSessionRef.current = currentSession;

  /**
   * 加载会话历史记录
   */
  const loadSessionHistory = useCallback(async () => {
    try {
      const response = await pdfImportService.getActiveSessions();
      if (response.success === true) {
        // 转换为历史记录格式
        const history = response.active_sessions
          .filter(session =>
            ['ready_for_review', 'failed', 'cancelled', 'completed'].includes(session.status)
          )
          .map(session => ({
            sessionId: session.session_id,
            fileInfo: {
              uid: session.session_id,
              name: session.file_name,
              status: 'done',
              size: 0,
              type: 'application/pdf',
            } as UploadFile,
            status: ((): 'ready' | 'completed' | 'failed' | 'processing' => {
              switch (session.status) {
                case 'ready_for_review':
                  return 'ready';
                case 'completed':
                  return 'completed';
                case 'failed':
                case 'cancelled':
                  return 'failed';
                default:
                  return 'processing';
              }
            })(),
            progress: session.progress,
          }));
        setSessionHistory(history);
      }
    } catch (error) {
      sessionLogger.error('加载会话历史失败:', error as Error);
    }
  }, []);

  /**
   * 文件上传成功处理
   */
  const handleUploadSuccess = useCallback((sessionId: string, fileInfo: UploadFile) => {
    const newSession: ProcessingSession = {
      sessionId,
      fileInfo,
      status: 'processing',
      progress: 0,
    };

    setCurrentSession(newSession);

    // 强制重新渲染
    setTimeout(() => {
      setCurrentSession(prev => (prev != null ? { ...prev } : null));
    }, 100);
  }, []);

  /**
   * 文件上传失败处理
   */
  const handleUploadError = useCallback((error: unknown) => {
    const errorMsg =
      typeof error === 'string' ? error : error instanceof Error ? error.message : '上传失败';
    MessageManager.error(errorMsg);
    setCurrentSession(null);
  }, []);

  /**
   * 处理完成处理
   */
  const handleProcessingComplete = useCallback((result: CompleteResult) => {
    if (currentSessionRef.current != null) {
      setCurrentSession({
        ...currentSessionRef.current,
        status: 'ready',
        progress: 100,
        result,
      });
    }
  }, []);

  /**
   * 处理错误处理
   */
  const handleProcessingError = useCallback((error: string) => {
    if (currentSessionRef.current != null) {
      setCurrentSession({
        ...currentSessionRef.current,
        status: 'failed',
        error,
      });
    }
    MessageManager.error(error);
  }, []);

  /**
   * 确认导入处理
   */
  const handleConfirmImport = useCallback(
    async (data: ConfirmedContractData): Promise<ConfirmImportResponse> => {
      if (currentSessionRef.current == null) {
        throw new Error('No active session');
      }

      try {
        const response = await pdfImportService.confirmImport(
          currentSessionRef.current.sessionId,
          data
        );

        if (response.success === true) {
          // 更新会话状态
          setCurrentSession({
            ...currentSessionRef.current,
            status: 'completed',
          });

          // 添加到历史记录
          setSessionHistory(prev => [currentSessionRef.current!, ...prev]);

          // 显示成功通知
          MessageManager.success('合同导入成功!');
        }

        return response;
      } catch (error: unknown) {
        const errorMsg = (error as ApiError).message ?? '合同导入过程中发生错误';
        MessageManager.error(errorMsg);
        throw error;
      }
    },
    []
  );

  /**
   * 取消处理
   */
  const handleCancel = useCallback(async () => {
    if (currentSessionRef.current == null) {
      return;
    }

    try {
      const response = await pdfImportService.cancelSession(currentSessionRef.current.sessionId);
      if (response.success === true) {
        MessageManager.info('已取消导入');
        setCurrentSession(null);
      }
    } catch (error: unknown) {
      const errorMsg = (error as ApiError).message ?? '取消失败';
      MessageManager.error(errorMsg);
    }
  }, []);

  /**
   * 重新加载
   */
  const handleReload = useCallback(async () => {
    setLoading(true);
    try {
      await loadSessionHistory();
      MessageManager.success('数据已刷新');
    } catch (error) {
      const errorId = `ERR-RELOAD-${Date.now()}`;
      sessionLogger.error('刷新数据失败:', error as Error, { errorId });
      MessageManager.error(`刷新失败 [${errorId}],请稍后重试`);
    } finally {
      setLoading(false);
    }
  }, [loadSessionHistory]);

  /**
   * 返回上传页面(清除当前会话)
   */
  const handleBackToUpload = useCallback(() => {
    setCurrentSession(null);
  }, []);

  return {
    // 状态
    currentSession,
    sessionHistory,
    loading,

    // 操作方法
    loadSessionHistory,
    handleUploadSuccess,
    handleUploadError,
    handleProcessingComplete,
    handleProcessingError,
    handleConfirmImport,
    handleCancel,
    handleReload,
    handleBackToUpload,
  };
};
