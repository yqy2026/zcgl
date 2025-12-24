/**
 * @deprecated 此文件已废弃，请使用 enhancedApiClient.ts
 *
 * 迁移指南:
 * - 旧: import { api } from '@/services/api'
 * - 新: import { enhancedApiClient } from '@/services'
 *
 * 注意: enhancedApiClient 的接口略有不同，请查看文档了解详情
 * 最后更新: 2025-12-24
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import type { ApiResponse, ErrorResponse } from "@/types/api";
import { API_CONFIG } from "@/constants/api";
import type { AppError } from "@/types/common";

// 请求重试配置
const RETRY_CONFIG = {
  retries: 3,
  retryDelay: 1000,
  retryCondition: (error: { code?: string; response?: { status: number } }) => {
    return error.code === "NETWORK_ERROR" || (error.response && error.response.status >= 500);
  },
};

// 创建axios实例
const createApiInstance = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: API_CONFIG.BASE_URL,
    timeout: 30000,
    headers: {
      "Content-Type": "application/json",
    },
  });

  // 请求拦截器
  instance.interceptors.request.use(
    (config) => {
      // 使用JWT token进行认证
      const token = localStorage.getItem("token") || localStorage.getItem("auth_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // 添加请求ID用于追踪
      config.headers["X-Request-ID"] = generateRequestId();

      // 添加时间戳防止缓存
      if (config.method === "get" && config.params) {
        config.params._t = Date.now();
      }

      return config;
    },
    (error) => {
      console.error("❌ Request Error:", error);
      return Promise.reject(error);
    },
  );

  // 响应拦截器
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      // 处理业务逻辑错误
      if (response.data && response.data.success === false) {
        // 业务错误已在错误处理器中处理
      }

      return response;
    },
    async (error) => {
      // 处理网络错误
      if (!error.response) {
        // 尝试重试网络错误
        if (error.config && !error.config.__isRetryRequest) {
          try {
            error.config.__isRetryRequest = true;
            return await retryRequest(instance, error.config);
          } catch (retryError) {
            // 重试失败，返回网络错误
          }
        }

        return Promise.reject({
          error: "Network Error",
          message: "网络连接失败，请检查网络设置",
          timestamp: new Date().toISOString(),
        } as ErrorResponse);
      }

      // 处理认证错误
      const { status } = error.response;
      handleAuthError(status);

      // 处理HTTP错误
      const { data } = error.response;
      const errorResponse: ErrorResponse = {
        error: data?.error || `HTTP ${status}`,
        message: data?.message || getDefaultErrorMessage(status),
        details: data?.details,
        timestamp: data?.timestamp || new Date().toISOString(),
      };

      return Promise.reject(errorResponse);
    },
  );

  return instance;
};

// 生成请求ID
const generateRequestId = (): string => {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

// 请求重试函数
const retryRequest = async (
  instance: AxiosInstance,
  config: AxiosRequestConfig,
  retryCount = 0,
): Promise<AxiosResponse> => {
  try {
    return await instance(config);
  } catch (error: unknown) {
    const appError = error as AppError;
    if (retryCount < RETRY_CONFIG.retries && RETRY_CONFIG.retryCondition(error)) {
      // 等待重试延迟
      await new Promise((resolve) =>
        setTimeout(resolve, RETRY_CONFIG.retryDelay * Math.pow(2, retryCount)),
      );

      return retryRequest(instance, config, retryCount + 1);
    }
    throw error;
  }
};

// 获取默认错误消息
const getDefaultErrorMessage = (status: number): string => {
  switch (status) {
    case 400:
      return "请求参数错误";
    case 401:
      return "未授权访问";
    case 403:
      return "禁止访问";
    case 404:
      return "资源不存在";
    case 409:
      return "资源冲突";
    case 422:
      return "请求参数验证失败";
    case 500:
      return "服务器内部错误";
    case 502:
      return "网关错误";
    case 503:
      return "服务不可用";
    default:
      return `请求失败 (${status})`;
  }
};

// 处理认证错误
const handleAuthError = (status: number) => {
  if (status === 401) {
    // 清除所有可能的认证信息
    localStorage.removeItem("auth_token");
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_info");
    localStorage.removeItem("user");

    console.warn("认证失败，已清除本地存储的认证信息");

    // 重定向到登录页面
    if (window.location.pathname !== "/login") {
      // 保存当前页面URL，登录后可以重定向回来
      const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/login?returnUrl=${returnUrl}`;
    }
  }
};

// 创建API实例
export const api = createApiInstance();

// API请求封装类
export class ApiClient {
  private instance: AxiosInstance;

  constructor(instance: AxiosInstance) {
    this.instance = instance;
  }

  // GET请求
  async get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.get<ApiResponse<T>>(url, config);
    // Handle both wrapped and unwrapped response formats
    return response.data || (response as unknown as ApiResponse<T>);
  }

  // POST请求
  async post<T = unknown>(
    url: string,
    data?: Record<string, unknown>,
    config?: AxiosRequestConfig,
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.post<ApiResponse<T>>(url, data, config);
    // Handle both wrapped and unwrapped response formats
    return response.data || (response as unknown as ApiResponse<T>);
  }

  // PUT请求
  async put<T = unknown>(
    url: string,
    data?: Record<string, unknown>,
    config?: AxiosRequestConfig,
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.put<ApiResponse<T>>(url, data, config);
    // Handle both wrapped and unwrapped response formats
    return response.data || (response as unknown as ApiResponse<T>);
  }

  // DELETE请求
  async delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.delete<ApiResponse<T>>(url, config);
    // Handle both wrapped and unwrapped response formats
    return response.data || (response as unknown as ApiResponse<T>);
  }

  // 文件上传
  async upload<T = unknown>(
    url: string,
    file: File,
    onProgress?: (progress: number) => void,
    additionalData?: Record<string, unknown>,
  ): Promise<ApiResponse<T>> {
    const formData = new FormData();
    formData.append("file", file);

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    const response = await this.instance.post<ApiResponse<T>>(url, formData, {
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

    return response.data;
  }

  // 文件下载
  async download(url: string, filename?: string, config?: AxiosRequestConfig): Promise<void> {
    const response = await this.instance.get(url, {
      ...config,
      responseType: "blob",
    });

    // 从响应头获取文件名
    const contentDisposition = response.headers["content-disposition"];
    let downloadFilename = filename;

    if (!downloadFilename && contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        downloadFilename = filenameMatch[1].replace(/['"]/g, "");
      }
    }

    // 创建下载链接
    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = downloadFilename || "download";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }

  // PATCH请求
  async patch<T = unknown>(
    url: string,
    data?: Record<string, unknown>,
    config?: AxiosRequestConfig,
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.patch<ApiResponse<T>>(url, data, config);
    // Handle both wrapped and unwrapped response formats
    return response.data || (response as unknown as ApiResponse<T>);
  }

  // HEAD请求
  async head(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse> {
    return await this.instance.head(url, config);
  }

  // OPTIONS请求
  async options(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse> {
    return await this.instance.options(url, config);
  }

  // 批量请求
  async batch<T = unknown>(
    requests: Array<{
      method: "get" | "post" | "put" | "delete" | "patch";
      url: string;
      data?: Record<string, unknown>;
      config?: AxiosRequestConfig;
    }>,
  ): Promise<ApiResponse<T>[]> {
    const promises = requests.map((req) => {
      switch (req.method) {
        case "get":
          return this.get(req.url, req.config);
        case "post":
          return this.post(req.url, req.data, req.config);
        case "put":
          return this.put(req.url, req.data, req.config);
        case "delete":
          return this.delete(req.url, req.config);
        case "patch":
          return this.patch(req.url, req.data, req.config);
        default:
          throw new Error(`Unsupported method: ${req.method}`);
      }
    });

    return Promise.all(promises);
  }

  // 取消请求
  createCancelToken() {
    return axios.CancelToken.source();
  }

  // 检查请求是否被取消
  isCancel(error: unknown): boolean {
    return axios.isCancel(error);
  }
}

// 导出API客户端实例
export const apiClient = new ApiClient(api);
