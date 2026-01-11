/**
 * API请求工具
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import { createLogger } from "./logger";
import { MessageManager } from "./messageManager";

const logger = createLogger('Request');

// 创建axios实例
const createApiInstance = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: process.env.VITE_API_BASE_URL || "/api",
    timeout: 30000,
    headers: {
      "Content-Type": "application/json",
    },
  });

  // 请求拦截器
  instance.interceptors.request.use(
    (config) => {
      // 兼容两种token键名：优先使用auth_token，回退到token
      const token = localStorage.getItem("auth_token") || localStorage.getItem("token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    },
  );

  // 响应拦截器
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      logger.debug("API响应成功", {
        url: response.config.url,
        method: response.config.method,
        status: response.status,
      });
      return response;
    },
    (error) => {
      // 生成唯一的错误追踪ID
      const errorId = `ERR-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      const timestamp = new Date().toISOString();

      logger.debug("API响应错误", {
        errorId,
        timestamp,
        url: error.config?.url,
        method: error.config?.method,
        status: error.response?.status,
        message: error.message,
      });

      // 统一错误处理
      if (error.response) {
        const { status, data } = error.response;

        switch (status) {
          case 400:
            MessageManager.error(`请求参数错误 [${errorId}]`);
            break;
          case 401:
            MessageManager.error(`未授权，请重新登录 [${errorId}]`);
            // 可以在这里处理登录跳转
            break;
          case 403:
            MessageManager.error(`权限不足 [${errorId}]`);
            break;
          case 404:
            MessageManager.error(`资源不存在 [${errorId}]`);
            break;
          case 422:
            // 处理验证错误
            if (data.detail && Array.isArray(data.detail)) {
              const errorMsg = data.detail.map((err: { msg: string }) => err.msg).join(", ");
              MessageManager.error(`数据验证失败: ${errorMsg} [${errorId}]`);
            } else {
              MessageManager.error(`数据验证失败 [${errorId}]`);
            }
            break;
          case 500:
            MessageManager.error(`服务器内部错误 [${errorId}]`);
            // 在开发环境，记录更详细的信息
            if (import.meta.env.DEV) {
              console.error(`[${errorId}] 服务器错误详情:`, data);
            }
            break;
          default:
            MessageManager.error(`请求失败 [${errorId}]`);
        }
      } else if (error.request) {
        MessageManager.error(`网络连接失败，请检查网络 [${errorId}]`);
      } else {
        MessageManager.error(`请求配置错误 [${errorId}]`);
      }

      // 添加错误ID到error对象，便于后续追踪
      error.errorId = errorId;
      error.timestamp = timestamp;

      return Promise.reject(error);
    },
  );

  return instance;
};

// 创建API实例
export const apiRequest = createApiInstance();

// 通用请求方法
export class ApiService {
  static async get<T = unknown>(
    url: string,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    return apiRequest.get(url, config);
  }

  static async post<T = unknown>(
    url: string,
    data?: Record<string, unknown>,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    return apiRequest.post(url, data, config);
  }

  static async put<T = unknown>(
    url: string,
    data?: Record<string, unknown>,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    return apiRequest.put(url, data, config);
  }

  static async patch<T = unknown>(
    url: string,
    data?: Record<string, unknown>,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    return apiRequest.patch(url, data, config);
  }

  static async delete<T = unknown>(
    url: string,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    return apiRequest.delete(url, config);
  }
}

// 文件上传方法
export const uploadFile = async (
  url: string,
  file: File,
  onProgress?: (progress: number) => void,
): Promise<AxiosResponse> => {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest.post(url, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
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
      responseType: "blob",
    });

    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename || "download";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    MessageManager.error("文件下载失败");
    throw error;
  }
};

export default apiRequest;
