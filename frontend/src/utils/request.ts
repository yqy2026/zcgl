/**
 * API请求工具
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { message } from 'antd';
import { createLogger } from './logger';

const logger = createLogger('Request');

// 创建axios实例
const createApiInstance = (): AxiosInstance => {
  const instance = axios.create({
    baseURL:
      process.env.VITE_API_BASE_URL !== null &&
      process.env.VITE_API_BASE_URL !== undefined &&
      process.env.VITE_API_BASE_URL !== ''
        ? process.env.VITE_API_BASE_URL
        : '/api',
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // 请求拦截器
  instance.interceptors.request.use(
    config => {
      // 可以在这里添加token等认证信息
      const token = localStorage.getItem('token');
      if (token !== null && token !== undefined && token !== '') {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    error => {
      return Promise.reject(error instanceof Error ? error : new Error(String(error)));
    }
  );

  // 响应拦截器
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      logger.debug('API响应成功', {
        url: response.config.url,
        method: response.config.method,
        status: response.status,
      });
      return response;
    },
    error => {
      const errorRecord = error as Record<string, unknown>;
      logger.debug('API响应错误', {
        url: (errorRecord.config as Record<string, unknown> | undefined)?.url,
        method: (errorRecord.config as Record<string, unknown> | undefined)?.method,
        status: (errorRecord.response as Record<string, unknown> | undefined)?.status,
        message: errorRecord.message as string | undefined,
      });

      // 统一错误处理
      if (
        errorRecord.response !== null &&
        errorRecord.response !== undefined &&
        typeof errorRecord.response === 'object'
      ) {
        const responseRecord = errorRecord.response as Record<string, unknown>;
        const status = responseRecord.status as number | undefined;
        const data = responseRecord.data as Record<string, unknown> | undefined;

        if (status === 400) {
          const detail = data?.detail as string | undefined;
          message.error(
            detail !== null && detail !== undefined && detail !== '' ? detail : '请求参数错误'
          );
        } else if (status === 401) {
          message.error('未授权，请重新登录');
          // 可以在这里处理登录跳转
        } else if (status === 403) {
          message.error('权限不足');
        } else if (status === 404) {
          const detail = data?.detail as string | undefined;
          message.error(
            detail !== null && detail !== undefined && detail !== '' ? detail : '资源不存在'
          );
        } else if (status === 422) {
          // 处理验证错误
          if (
            data?.detail !== null &&
            data?.detail !== undefined &&
            typeof data.detail === 'object' &&
            Array.isArray(data.detail)
          ) {
            const detailArray = data.detail as Array<{ msg: string }>;
            const errorMsg = detailArray.map(err => err.msg).join(', ');
            message.error(errorMsg);
          } else {
            const detail = data?.detail as string | undefined;
            message.error(
              detail !== null && detail !== undefined && detail !== '' ? detail : '数据验证失败'
            );
          }
        } else if (status === 500) {
          message.error('服务器内部错误');
        } else {
          const detail = data?.detail as string | undefined;
          message.error(
            detail !== null && detail !== undefined && detail !== '' ? detail : '请求失败'
          );
        }
      } else if (errorRecord.request !== null && errorRecord.request !== undefined) {
        message.error('网络连接失败，请检查网络');
      } else {
        message.error('请求配置错误');
      }

      return Promise.reject(error instanceof Error ? error : new Error(String(error)));
    }
  );

  return instance;
};

// 创建API实例
export const apiRequest = createApiInstance();

// 通用请求方法
export class ApiService {
  static async get<T = unknown>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    return apiRequest.get(url, config);
  }

  static async post<T = unknown>(
    url: string,
    data?: Record<string, unknown>,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    return apiRequest.post(url, data, config);
  }

  static async put<T = unknown>(
    url: string,
    data?: Record<string, unknown>,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    return apiRequest.put(url, data, config);
  }

  static async patch<T = unknown>(
    url: string,
    data?: Record<string, unknown>,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    return apiRequest.patch(url, data, config);
  }

  static async delete<T = unknown>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    return apiRequest.delete(url, config);
  }
}

// 文件上传方法
export const uploadFile = async (
  url: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<AxiosResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  return apiRequest.post(url, formData as unknown as Record<string, unknown>, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: progressEvent => {
      if (
        onProgress !== null &&
        onProgress !== undefined &&
        progressEvent.total !== null &&
        progressEvent.total !== undefined &&
        progressEvent.total > 0
      ) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });
};

// 下载文件方法
export const downloadFile = async (url: string, filename?: string): Promise<void> => {
  try {
    const response = await apiRequest.get(url, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download =
      filename !== null && filename !== undefined && filename !== '' ? filename : 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    message.error('文件下载失败');
    throw error;
  }
};

export default apiRequest;
