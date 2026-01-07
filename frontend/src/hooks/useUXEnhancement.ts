import { useState, useEffect, useCallback, useRef } from 'react';
import { uxManager, recordAction, isLoading } from '@/utils/uxManager';

// 错误处理Hook
export const useErrorHandler = () => {
  const handleError = useCallback((error: Error, context?: Record<string, unknown>) => {
    uxManager.handleError(error, context);
  }, []);

  const handleAsyncError = useCallback(
    async <T>(asyncFn: () => Promise<T>, context?: unknown) => {
      try {
        return await asyncFn();
      } catch (error) {
        handleError(error as Error, context as Record<string, unknown> | undefined);
        throw error;
      }
    },
    [handleError]
  );

  return { handleError, handleAsyncError };
};

// 加载状态Hook
export const useLoadingState = (key?: string) => {
  const loadingKey =
    (key ?? null) !== null ? key : `loading_${Math.random().toString(36).substr(2, 9)}`;
  const [loading, setLoadingState] = useState(false);

  const setLoading = useCallback(
    (loading: boolean) => {
      setLoadingState(loading);
      uxManager.setLoading(loadingKey, loading);
    },
    [loadingKey]
  );

  const withLoading = useCallback(
    async <T>(asyncFn: () => Promise<T>): Promise<T> => {
      setLoading(true);
      try {
        const result = await asyncFn();
        return result;
      } finally {
        setLoading(false);
      }
    },
    [setLoading]
  );

  return { loading, setLoading, withLoading, isLoading: () => isLoading(loadingKey) };
};

// 用户操作跟踪Hook
export const useActionTracking = () => {
  const trackAction = useCallback((action: string, data?: Record<string, unknown>) => {
    recordAction(action, data);
  }, []);

  const trackClick = useCallback(
    (elementName: string, data?: Record<string, unknown>) => {
      trackAction('click', { element: elementName, ...data });
    },
    [trackAction]
  );

  const trackFormSubmit = useCallback(
    (formName: string, data?: Record<string, unknown>) => {
      trackAction('formSubmit', { form: formName, ...data });
    },
    [trackAction]
  );

  const trackPageView = useCallback(
    (pageName: string, data?: Record<string, unknown>) => {
      trackAction('pageView', { page: pageName, ...data });
    },
    [trackAction]
  );

  return { trackAction, trackClick, trackFormSubmit, trackPageView };
};

// 性能监控Hook
export const usePerformanceMonitoring = () => {
  const measureRef = useRef<Map<string, number>>(new Map());

  const startMeasure = useCallback((name: string) => {
    measureRef.current.set(name, performance.now());
    uxManager.startPerformanceMeasure(name);
  }, []);

  const endMeasure = useCallback((name: string) => {
    const startTime = measureRef.current.get(name);
    if (startTime !== null && startTime !== undefined) {
      const duration = performance.now() - startTime;
      uxManager.recordPerformanceMetric(name, duration);
      measureRef.current.delete(name);
      return duration;
    }
    uxManager.endPerformanceMeasure(name);
    return 0;
  }, []);

  const measureAsync = useCallback(
    async <T>(name: string, asyncFn: () => Promise<T>): Promise<T> => {
      startMeasure(name);
      try {
        const result = await asyncFn();
        return result;
      } finally {
        endMeasure(name);
      }
    },
    [startMeasure, endMeasure]
  );

  return { startMeasure, endMeasure, measureAsync };
};

// 用户反馈Hook
export const useUserFeedback = () => {
  const showSuccess = useCallback((message: string, description?: string) => {
    uxManager.showSuccessFeedback(message, description);
  }, []);

  const showError = useCallback((message: string, description?: string) => {
    uxManager.showErrorFeedback(message, description);
  }, []);

  const showWarning = useCallback((message: string, description?: string) => {
    uxManager.showWarningFeedback(message, description);
  }, []);

  const showInfo = useCallback((message: string, description?: string) => {
    uxManager.showInfoFeedback(message, description);
  }, []);

  const showConfirm = useCallback(
    (options: {
      title: string;
      content: string;
      onOk: () => void;
      onCancel?: () => void;
      okText?: string;
      cancelText?: string;
      danger?: boolean;
    }) => {
      uxManager.showConfirmDialog(options);
    },
    []
  );

  return { showSuccess, showError, showWarning, showInfo, showConfirm };
};

// 操作状态Hook
export const useOperationState = <T = unknown>() => {
  const [state, setState] = useState<{
    loading: boolean;
    error: Error | null;
    data: T | null;
    success: boolean;
  }>({
    loading: false,
    error: null,
    data: null,
    success: false,
  });

  const { handleError } = useErrorHandler();
  const { showSuccess, showError } = useUserFeedback();

  const execute = useCallback(
    async (
      operation: () => Promise<T>,
      options?: {
        successMessage?: string;
        errorMessage?: string;
        showFeedback?: boolean;
        trackAction?: string;
      }
    ) => {
      setState(prev => ({ ...prev, loading: true, error: null, success: false }));

      try {
        if (
          options?.trackAction !== null &&
          options?.trackAction !== undefined &&
          options?.trackAction !== ''
        ) {
          recordAction(`start_${options.trackAction}`);
        }

        const result = await operation();

        setState({
          loading: false,
          error: null,
          data: result,
          success: true,
        });

        if (
          options?.showFeedback !== false &&
          options?.successMessage !== null &&
          options?.successMessage !== undefined &&
          options?.successMessage !== ''
        ) {
          void showSuccess(options.successMessage);
        }

        if (
          options?.trackAction !== null &&
          options?.trackAction !== undefined &&
          options?.trackAction !== ''
        ) {
          recordAction(`success_${options.trackAction}`, { data: result });
        }

        return result;
      } catch (error) {
        const err = error as Error;
        setState(prev => ({
          ...prev,
          loading: false,
          error: err,
          success: false,
        }));

        void handleError(err, { operation: options?.trackAction });

        if (
          options?.showFeedback !== false &&
          options?.errorMessage !== null &&
          options?.errorMessage !== undefined &&
          options?.errorMessage !== ''
        ) {
          void showError(options.errorMessage);
        }

        if (
          options?.trackAction !== null &&
          options?.trackAction !== undefined &&
          options?.trackAction !== ''
        ) {
          recordAction(`error_${options.trackAction}`, { error: err.message });
        }

        throw error;
      }
    },
    [handleError, showSuccess, showError]
  );

  const reset = useCallback(() => {
    setState({
      loading: false,
      error: null,
      data: null,
      success: false,
    });
  }, []);

  return { ...state, execute, reset };
};

// 表单增强Hook
export const useFormEnhancement = () => {
  const [isDirty, setIsDirty] = useState(false);
  const [hasErrors, setHasErrors] = useState(false);
  const { showWarning, showConfirm } = useUserFeedback();
  const { trackAction } = useActionTracking();

  const markDirty = useCallback(() => {
    if (!isDirty) {
      setIsDirty(true);
      trackAction('formDirty');
    }
  }, [isDirty, trackAction]);

  const markClean = useCallback(() => {
    setIsDirty(false);
    trackAction('formClean');
  }, [trackAction]);

  const setErrors = useCallback(
    (hasErrors: boolean) => {
      setHasErrors(hasErrors);
      if (hasErrors) {
        trackAction('formValidationError');
      }
    },
    [trackAction]
  );

  const confirmLeave = useCallback(
    (callback: () => void) => {
      if (isDirty) {
        showConfirm({
          title: '确认离开',
          content: '您有未保存的更改，确定要离开吗？',
          onOk: () => {
            markClean();
            callback();
          },
          danger: true,
        });
      } else {
        callback();
      }
    },
    [isDirty, showConfirm, markClean]
  );

  const warnUnsaved = useCallback(() => {
    if (isDirty) {
      showWarning('数据未保存', '您有未保存的更改，请及时保存');
    }
  }, [isDirty, showWarning]);

  // 监听页面刷新/关闭
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty === true) {
        e.preventDefault();
        const message = '您有未保存的更改，确定要离开吗？';
        e.returnValue = message;
        return message;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  return {
    isDirty,
    hasErrors,
    markDirty,
    markClean,
    setErrors,
    confirmLeave,
    warnUnsaved,
  } as {
    isDirty: boolean;
    hasErrors: boolean;
    markDirty: () => void;
    markClean: () => void;
    setErrors: (errors: Record<string, boolean>) => void;
    confirmLeave: () => Promise<boolean>;
    warnUnsaved: () => void;
  };
};

// 网络状态Hook
export const useNetworkStatus = (enabled = true) => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [connectionType, setConnectionType] = useState<string>('unknown');
  const { showWarning, showInfo } = useUserFeedback();

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const handleOnline = () => {
      setIsOnline(true);
      showInfo('网络已连接', '网络连接已恢复');
      recordAction('networkOnline');
    };

    const handleOffline = () => {
      setIsOnline(false);
      showWarning('网络已断开', '请检查您的网络连接');
      recordAction('networkOffline');
    };

    const handleConnectionChange = () => {
      const connection = (
        navigator as unknown as {
          connection?: { effectiveType?: string };
        }
      ).connection;
      if (connection !== null && connection !== undefined) {
        setConnectionType(
          (connection.effectiveType ?? null) !== null ? connection.effectiveType : 'unknown'
        );
        recordAction('connectionChange', { type: connection.effectiveType });
      }
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // 监听连接类型变化
    const connection = (
      navigator as unknown as {
        connection?: {
          effectiveType?: string;
          addEventListener?: (type: string, handler: () => void) => void;
          removeEventListener?: (type: string, handler: () => void) => void;
        };
      }
    ).connection;
    if (connection !== null && connection !== undefined) {
      connection.addEventListener?.('change', handleConnectionChange);
      setConnectionType(
        (connection.effectiveType ?? null) !== null ? connection.effectiveType : 'unknown'
      );
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      if (connection !== null && connection !== undefined) {
        connection.removeEventListener?.('change', handleConnectionChange);
      }
    };
  }, [showWarning, showInfo, enabled]);

  return { isOnline, connectionType };
};

// 综合UX增强Hook
export const useUXEnhancement = (options?: {
  trackPageView?: string;
  enableErrorHandling?: boolean;
  enablePerformanceMonitoring?: boolean;
  enableNetworkMonitoring?: boolean;
}) => {
  const errorHandler = useErrorHandler();
  const actionTracking = useActionTracking();
  const performanceMonitoring = usePerformanceMonitoring();
  const userFeedback = useUserFeedback();
  const networkStatus = useNetworkStatus(options?.enableNetworkMonitoring);

  // 页面加载时跟踪页面访问
  useEffect(() => {
    if (
      options?.trackPageView !== null &&
      options?.trackPageView !== undefined &&
      options?.trackPageView !== ''
    ) {
      actionTracking.trackPageView(options.trackPageView);
    }
  }, [options?.trackPageView, actionTracking]);

  return {
    // 错误处理
    ...(options?.enableErrorHandling !== false ? errorHandler : {}),

    // 用户操作跟踪
    ...actionTracking,

    // 性能监控
    ...(options?.enablePerformanceMonitoring !== false ? performanceMonitoring : {}),

    // 用户反馈
    ...userFeedback,

    // 网络状态
    ...(options?.enableNetworkMonitoring === true ? networkStatus : {}),
  };
};

export default useUXEnhancement;
