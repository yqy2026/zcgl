/**
 * API客户端拦截器
 * 请求和响应拦截器的设置逻辑
 */

import {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
  AxiosError,
} from 'axios';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { ApiClientConfig } from '@/types/apiResponse';
import { API_BASE_URL, CSRF_CONFIG } from './config';
import { AuthStorage } from '@/utils/AuthStorage';
import { viewSelectionStorage } from '@/utils/viewSelectionStorage';
import {
  apiLogger,
  AUTHZ_STALE_EVENT_NAME,
  ExtendedAxiosRequestConfig,
  getCookieValue,
  setHeaderIfMissing,
  shouldDispatchAuthzStaleEvent,
  validateApiPath,
} from './clientHelpers';

// ==================== 拦截器设置 ====================

/**
 * 为 axios 实例设置请求和响应拦截器
 * @param instance axios 实例
 * @param config API 客户端配置
 * @param generateRequestId 生成请求ID的函数
 */
export function setupInterceptors(
  instance: AxiosInstance,
  config: ApiClientConfig,
  generateRequestId: () => string
): void {
  // 请求拦截器
  instance.interceptors.request.use(
    (reqConfig: InternalAxiosRequestConfig) => {
      // 规范化API路径前缀，确保走版本化路径
      if (reqConfig.url != null) {
        const normalizedBaseUrl = API_BASE_URL.startsWith('http')
          ? new URL(API_BASE_URL).pathname
          : API_BASE_URL;
        const basePath = normalizedBaseUrl.endsWith('/')
          ? normalizedBaseUrl.slice(0, -1)
          : normalizedBaseUrl;

        if (!reqConfig.url.startsWith('http://') && !reqConfig.url.startsWith('https://')) {
          let normalizedUrl = reqConfig.url;
          if (basePath !== '' && normalizedUrl.startsWith(basePath)) {
            normalizedUrl = normalizedUrl.slice(basePath.length);
          }
          if (normalizedUrl.startsWith('/')) {
            normalizedUrl = normalizedUrl.slice(1);
          }
          reqConfig.url = normalizedUrl;

          const validationUrl =
            basePath !== ''
              ? `${basePath}/${normalizedUrl}`.replace(/\/+/g, '/')
              : `/${normalizedUrl}`;
          validateApiPath(validationUrl);
        } else {
          validateApiPath(reqConfig.url);
        }
      }

      // 添加请求ID
      if (reqConfig.headers != null) {
        reqConfig.headers.set('X-Request-ID', generateRequestId());
      }

      const method = reqConfig.method?.toUpperCase() ?? 'GET';
      const isSafeMethod =
        method === 'GET' || method === 'HEAD' || method === 'OPTIONS' || method === 'TRACE';

      const currentUser = AuthStorage.getCurrentUser();
      const currentUserId =
        currentUser != null && typeof currentUser.id === 'string' ? currentUser.id : '';
      if (currentUserId.trim() !== '') {
        const currentView = viewSelectionStorage.get(currentUserId);
        if (currentView != null) {
          setHeaderIfMissing(reqConfig.headers, 'X-View-Perspective', currentView.perspective);
          setHeaderIfMissing(reqConfig.headers, 'X-View-Party-Id', currentView.partyId);
        }
      }

      if (!isSafeMethod) {
        const csrfToken = getCookieValue(CSRF_CONFIG.COOKIE_NAME);
        if (csrfToken !== null && csrfToken !== '') {
          setHeaderIfMissing(reqConfig.headers, CSRF_CONFIG.HEADER_NAME, csrfToken);
        }
      }

      // 执行自定义请求拦截器
      let finalConfig = reqConfig;
      if (config.requestInterceptors) {
        for (const interceptor of config.requestInterceptors) {
          finalConfig = interceptor(finalConfig);
        }
      }

      if (config.enableLogging === true) {
        apiLogger.debug(`🚀 API Request: ${finalConfig.method?.toUpperCase()} ${finalConfig.url}`, {
          params: finalConfig.params,
          data: finalConfig.data,
        });
      }

      return finalConfig;
    },
    error => {
      apiLogger.error('❌ Request Error:', error);
      return Promise.reject(error);
    }
  );

  // 响应拦截器
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      if (config.enableLogging === true) {
        apiLogger.debug(
          `✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`,
          {
            status: response.status,
            data: response.data,
          }
        );
      }

      // 执行自定义响应拦截器
      if (config.responseInterceptors) {
        let finalResponse = response;
        for (const interceptor of config.responseInterceptors) {
          finalResponse = interceptor(finalResponse);
        }
        return finalResponse;
      }

      return response;
    },
    async (error: unknown) => {
      const axiosError = error as AxiosError<unknown, ExtendedAxiosRequestConfig>;
      const originalRequest = axiosError.config as ExtendedAxiosRequestConfig | undefined;
      const suppressAuthRedirect = originalRequest?._suppressAuthRedirect === true;
      if (shouldDispatchAuthzStaleEvent(axiosError, originalRequest)) {
        AuthStorage.clearCapabilitiesSnapshot();
        if (typeof window !== 'undefined') {
          window.dispatchEvent(
            new CustomEvent(AUTHZ_STALE_EVENT_NAME, {
              detail: {
                headerName: 'X-Authz-Stale',
              },
            })
          );
        }
      }

      const requestUrl = originalRequest?.url ?? '';
      const isRefreshRequest =
        requestUrl.includes('/auth/refresh') || requestUrl.includes('auth/refresh');

      // 刷新接口本身返回401时，直接登出，避免递归刷新
      if (axiosError.response?.status === 401 && isRefreshRequest) {
        if (suppressAuthRedirect !== true && typeof window !== 'undefined') {
          AuthStorage.clearAuthData();
          const currentPath =
            window.location.pathname + window.location.search + window.location.hash;
          window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
        }
        return Promise.reject(error);
      }

      // 处理401错误 - 自动刷新token via cookie
      if (
        axiosError.response?.status === 401 &&
        originalRequest != null &&
        originalRequest._retry !== true &&
        originalRequest._skipAuthRefresh !== true &&
        !isRefreshRequest
      ) {
        apiLogger.warn('Token expired, attempting refresh', {
          url: originalRequest.url,
          method: originalRequest.method,
        });

        try {
          // Try to refresh using cookie-based auth
          const refreshRequestConfig: AxiosRequestConfig = {};
          if (suppressAuthRedirect === true) {
            (refreshRequestConfig as ExtendedAxiosRequestConfig)._suppressAuthRedirect = true;
          }
          await instance.post('/auth/refresh', undefined, refreshRequestConfig);

          apiLogger.info('Token refresh successful, retrying original request', {
            url: originalRequest.url,
            method: originalRequest.method,
          });

          // 标记请求已重试过，避免无限循环
          originalRequest._retry = true;

          // 重试原始请求 (cookie automatically included)
          return await instance(originalRequest);
        } catch (refreshError) {
          apiLogger.error('Token refresh failed, logging out', {
            refreshError,
            url: originalRequest.url,
            method: originalRequest.method,
          });

          if (suppressAuthRedirect === true) {
            return Promise.reject(refreshError);
          }

          // 刷新失败，跳转到登录页
          // Cookie will be cleared by backend logout endpoint
          if (typeof window !== 'undefined') {
            AuthStorage.clearAuthData();
            const currentPath =
              window.location.pathname + window.location.search + window.location.hash;
            window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
          }

          return Promise.reject(refreshError);
        }
      }

      const enhancedError = ApiErrorHandler.handleError(error);

      if (config.enableLogging === true) {
        apiLogger.error(
          `API Error: ${enhancedError.type} - ${enhancedError.message}`,
          undefined,
          {
            config: axiosError.config,
            response: axiosError.response,
          }
        );
      }

      // 执行全局错误处理器
      if (config.globalErrorHandler) {
        config.globalErrorHandler(enhancedError);
      }

      return Promise.reject(enhancedError);
    }
  );
}
