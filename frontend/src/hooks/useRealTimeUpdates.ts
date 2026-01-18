import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';

const rtLogger = createLogger('RealTimeUpdates');

interface UseRealTimeUpdatesOptions {
  enabled?: boolean;
  interval?: number;
  onUpdate?: (data: unknown) => void;
  onError?: (error: unknown) => void;
}

/**
 * 实时更新Hook
 * 用于定期刷新数据或监听服务器推送的更新
 */
export const useRealTimeUpdates = (queryKey: string[], options: UseRealTimeUpdatesOptions = {}) => {
  const {
    enabled = false,
    interval = 30000, // 30秒
    onUpdate,
    onError,
  } = options;

  const queryClient = useQueryClient();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastUpdateRef = useRef<number>(Date.now());

  useEffect(() => {
    if (!enabled) {
      return;
    }

    // 定期检查更新
    const checkForUpdates = async () => {
      try {
        // 使用后台刷新，不显示loading状态
        await queryClient.refetchQueries({
          queryKey,
          type: 'active',
        });

        const currentTime = Date.now();
        if (currentTime - lastUpdateRef.current > interval) {
          onUpdate?.('Data updated');
          lastUpdateRef.current = currentTime;
        }
      } catch (error) {
        rtLogger.error('Real-time update error:', error as Error);
        onError?.(error);
      }
    };

    // 立即执行一次
    checkForUpdates();

    // 设置定时器
    intervalRef.current = setInterval(checkForUpdates, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [enabled, interval, queryKey, queryClient, onUpdate, onError]);

  // 手动触发更新
  const triggerUpdate = () => {
    return queryClient.refetchQueries({
      queryKey,
      type: 'active',
    });
  };

  // 停止实时更新
  const stopUpdates = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  // 重新开始实时更新
  const startUpdates = () => {
    if (!intervalRef.current && enabled) {
      intervalRef.current = setInterval(async () => {
        try {
          await queryClient.refetchQueries({
            queryKey,
            type: 'active',
          });
        } catch (error) {
          rtLogger.error('Real-time update error:', error as Error);
          onError?.(error);
        }
      }, interval);
    }
  };

  return {
    triggerUpdate,
    stopUpdates,
    startUpdates,
    isActive: !!intervalRef.current,
  };
};

/**
 * WebSocket实时更新Hook
 * 用于监听WebSocket推送的实时更新
 */
export const useWebSocketUpdates = (
  url: string,
  queryKey: string[],
  options: {
    enabled?: boolean;
    onMessage?: (data: unknown) => void;
    onError?: (error: unknown) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
  } = {}
) => {
  const { enabled = false, onMessage, onError, onConnect, onDisconnect } = options;

  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  useEffect(() => {
    if (!enabled || !url) {
      return;
    }

    const connect = () => {
      try {
        wsRef.current = new WebSocket(url);

        wsRef.current.onopen = () => {
          // WebSocket connected
          reconnectAttempts.current = 0;
          onConnect?.();
        };

        wsRef.current.onmessage = event => {
          try {
            const data = JSON.parse(event.data);

            // 处理不同类型的消息
            switch (data.type) {
              case 'asset_updated':
              case 'asset_created':
              case 'asset_deleted':
                // 刷新资产列表
                queryClient.invalidateQueries({ queryKey });
                MessageManager.info('数据已更新');
                break;
              case 'bulk_operation':
                // 批量操作完成
                queryClient.invalidateQueries({ queryKey });
                MessageManager.success(data.message ?? '批量操作完成');
                break;
              default:
              // Unknown message type
            }

            onMessage?.(data);
          } catch (error) {
            rtLogger.error('Error parsing WebSocket message:', error as Error);
          }
        };

        wsRef.current.onerror = error => {
          rtLogger.error('WebSocket error:', error as unknown as Error);
          onError?.(error);
        };

        wsRef.current.onclose = _event => {
          // WebSocket disconnected
          onDisconnect?.();

          // 自动重连
          if (reconnectAttempts.current < maxReconnectAttempts) {
            const delay = Math.pow(2, reconnectAttempts.current) * 1000; // 指数退避
            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectAttempts.current++;
              // Attempting to reconnect
              connect();
            }, delay);
          } else {
            MessageManager.error('WebSocket连接失败，请刷新页面重试');
          }
        };
      } catch (error) {
        rtLogger.error('Error creating WebSocket connection:', error as Error);
        onError?.(error);
      }
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [enabled, url, queryClient, queryKey, onMessage, onError, onConnect, onDisconnect]);

  // 发送消息
  const sendMessage = (message: unknown) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      rtLogger.warn('WebSocket is not connected');
    }
  };

  // 手动重连
  const reconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    reconnectAttempts.current = 0;
  };

  return {
    sendMessage,
    reconnect,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  };
};

/**
 * 页面可见性检测Hook
 * 当页面重新变为可见时自动刷新数据
 */
export const useVisibilityRefresh = (
  queryKey: string[],
  options: {
    enabled?: boolean;
    onRefresh?: () => void;
  } = {}
) => {
  const { enabled = true, onRefresh } = options;
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // 页面变为可见时刷新数据
        queryClient.refetchQueries({
          queryKey,
          type: 'active',
        });
        onRefresh?.();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [enabled, queryKey, queryClient, onRefresh]);
};
