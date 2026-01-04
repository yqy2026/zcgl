/**
 * API请求工具
 */

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import { message } from "antd";
import { createLogger } from "./logger";

const logger = createLogger('Request');

// 创建axios实例
const createApiInstance = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: (process.env.VITE_API_BASE_URL !== null && process.env.VITE_API_BASE_URL !== undefined && process.env.VITE_API_BASE_URL !== '') ? process.env.VITE_API_BASE_URL : "/api",
    timeout: 30000,
    headers: {
      "Content-Type": "application/json",
    },
  });

  // 请求拦截器
  instance.interceptors.request.use(
    (config) => {
      // 可以在这里添加token等认证信息
      const token = localStorage.getItem("token");
      if (token !== null && token !== undefined && token !== '') {
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
    (error: unknown) => {
      const axiosError = error as AxiosError;

      logger.debug("API响应错误", {
        url: axiosError.config?.url,
        method: axiosError.config?.method,
        status: axiosError.response?.status,
        message: axiosError.message,
      });

      // 统一错误处理
      if (axiosError.response !== null && axiosError.response !== undefined) {
        const { status, data } = axiosError.response;
        const responseData = data as { detail?: string | Array<{ msg: string }> };

        switch (status) {
          case 400:
            message.error((responseData.detail !== null && responseData.detail !== undefined && typeof responseData.detail === 'string' && responseData.detail !== '') ? responseData.detail : "请求参数错误");
            break;
          case 401:
            message.error("未授权，请重新登录");
            // 可以在这里处理登录跳转
            break;
          case 403:
            message.error("权限不足");
            break;
          case 404:
            message.error((responseData.detail !== null && responseData.detail !== undefined && typeof responseData.detail === 'string' && responseData.detail !== '') ? responseData.detail : "资源不存在");
            break;
          case 422:
            // 处理验证错误
            if ((responseData.detail !== null && responseData.detail !== undefined) && Array.isArray(responseData.detail)) {
              const errorMsg = responseData.detail.map((err: { msg: string }) => err.msg).join(", ");
              message.error(errorMsg);
            } else {
              message.error((responseData.detail !== null && responseData.detail !== undefined && typeof responseData.detail === 'string' && responseData.detail !== '') ? responseData.detail : "数据验证失败");
            }
            break;
          case 500:
            message.error("服务器内部错误");
            break;
          default:
            message.error((responseData.detail !== null && responseData.detail !== undefined && typeof responseData.detail === 'string' && responseData.detail !== '') ? responseData.detail : "请求失败");
        }
      } else if (axiosError.request !== null && axiosError.request !== undefined) {
        message.error("网络连接失败，请检查网络");
      } else {
        message.error("请求配置错误");
      }

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
      if (onProgress && (progressEvent.total !== null && progressEvent.total !== undefined && progressEvent.total !== 0)) {
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
    link.download = (filename !== null && filename !== undefined && filename !== '') ? filename : "download";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    message.error("文件下载失败");
    throw error;
  }
};

export default apiRequest;
