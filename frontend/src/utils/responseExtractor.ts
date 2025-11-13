/**
 * 统一API响应数据提取器
 * 智能识别和提取不同格式的API响应数据
 */

import { AxiosResponse, AxiosError } from 'axios';
import {
  StandardApiResponse,
  PaginatedApiResponse,
  DirectResponse,
  ErrorResponse,
  ExtractResult,
  SmartExtractOptions,
  ResponseDetectionConfig,
  EnhancedApiError,
  ApiErrorType,
  isStandardApiResponse,
  isPaginatedResponse,
  isErrorResponse,
  isDirectResponse
} from '../types/api-response';

// ==================== 响应检测器 ====================

/**
 * 响应格式检测器
 * 自动识别不同类型的API响应格式
 */
class ResponseDetector {
  private static readonly DEFAULT_CONFIG: ResponseDetectionConfig = {
    successField: 'success',
    dataField: 'data',
    errorFields: ['error', 'message'],
    strict: false
  };

  /**
   * 检测响应格式类型
   */
  static detectResponseType(response: any, config?: ResponseDetectionConfig): 'standard' | 'paginated' | 'direct' | 'error' {
    const finalConfig = { ...this.DEFAULT_CONFIG, ...config };

    // 优先检测错误响应
    if (this.isErrorResponse(response, finalConfig)) {
      return 'error';
    }

    // 检测分页响应
    if (this.isPaginatedResponse(response, finalConfig)) {
      return 'paginated';
    }

    // 检测标准响应
    if (this.isStandardResponse(response, finalConfig)) {
      return 'standard';
    }

    // 默认为直接响应
    return 'direct';
  }

  /**
   * 检查是否为标准响应
   */
  private static isStandardResponse(response: any, config: ResponseDetectionConfig): boolean {
    return response &&
           typeof response === 'object' &&
           config.successField && config.successField in response &&
           typeof response[config.successField] === 'boolean' &&
           config.dataField && config.dataField in response;
  }

  /**
   * 检查是否为分页响应
   */
  private static isPaginatedResponse(response: any, config: ResponseDetectionConfig): boolean {
    if (!this.isStandardResponse(response, config)) {
      return false;
    }

    const data = config.dataField && response[config.dataField];
    return data &&
           typeof data === 'object' &&
           'items' in data &&
           'pagination' in data;
  }

  /**
   * 检查是否为错误响应
   */
  private static isErrorResponse(response: any, config: ResponseDetectionConfig): boolean {
    return response &&
           typeof response === 'object' &&
           config.successField && response[config.successField] === false &&
           config.errorFields && config.errorFields.some(field => field in response);
  }
}

// ==================== 主要提取器类 ====================

/**
 * 统一响应数据提取器
 * 提供智能、类型安全的响应数据提取功能
 */
export class ResponseExtractor {
  private static readonly DEFAULT_OPTIONS: SmartExtractOptions = {
    detection: {
      successField: 'success',
      dataField: 'data',
      errorFields: ['error', 'message'],
      strict: false
    },
    enableTypeValidation: false
  };

  /**
   * 智能提取响应数据
   * 自动识别响应格式并提取数据
   */
  static smartExtract<T = any>(
    response: AxiosResponse,
    options?: SmartExtractOptions<T>
  ): ExtractResult<T> {
    const finalOptions = { ...this.DEFAULT_OPTIONS, ...options };

    try {
      // 获取响应数据
      const responseData = response.data;

      // 检测响应类型
      const responseType = ResponseDetector.detectResponseType(responseData, finalOptions.detection);

      // 根据类型提取数据
      switch (responseType) {
        case 'standard':
          return this.extractStandardResponse<T>(response, finalOptions);
        case 'paginated':
          return this.extractPaginatedResponse<T>(response, finalOptions);
        case 'direct':
          return this.extractDirectResponse<T>(response, finalOptions);
        case 'error':
          return this.extractErrorResponse<T>(response, finalOptions);
        default:
          return {
            success: false,
            error: '未知的响应格式',
            rawResponse: response
          };
      }
    } catch (error) {
      return {
        success: false,
        error: `数据提取失败: ${error instanceof Error ? error.message : '未知错误'}`,
        rawResponse: response
      };
    }
  }

  /**
   * 提取标准响应数据
   */
  private static extractStandardResponse<T>(
    response: AxiosResponse,
    options: SmartExtractOptions<T>
  ): ExtractResult<T> {
    const responseData = response.data;
    const dataField = options.detection?.dataField || 'data';

    if (!responseData[dataField]) {
      return {
        success: false,
        error: '标准响应中缺少数据字段',
        rawResponse: response
      };
    }

    const data = responseData[dataField];

    return {
      success: true,
      data: this.validateType<T>(data, options),
      rawResponse: response
    };
  }

  /**
   * 提取分页响应数据
   */
  private static extractPaginatedResponse<T>(
    response: AxiosResponse,
    options: SmartExtractOptions<T>
  ): ExtractResult<T> {
    const responseData = response.data;
    const dataField = options.detection?.dataField || 'data';
    const dataContainer = responseData[dataField];

    if (!dataContainer || !dataContainer.items) {
      return {
        success: false,
        error: '分页响应中缺少items字段',
        rawResponse: response
      };
    }

    return {
      success: true,
      data: this.validateType<T>(dataContainer.items, options),
      rawResponse: response
    };
  }

  /**
   * 提取直接响应数据
   */
  private static extractDirectResponse<T>(
    response: AxiosResponse,
    options: SmartExtractOptions<T>
  ): ExtractResult<T> {
    const data = response.data;

    return {
      success: true,
      data: this.validateType<T>(data, options),
      rawResponse: response
    };
  }

  /**
   * 提取错误响应
   */
  private static extractErrorResponse<T>(
    response: AxiosResponse,
    options: SmartExtractOptions<T>
  ): ExtractResult<T> {
    const responseData = response.data;

    // 尝试从常见字段提取错误信息
    const errorFields = options.detection?.errorFields || ['error', 'message'];
    let errorMessage = '未知错误';

    for (const field of errorFields) {
      if (responseData[field]) {
        if (typeof responseData[field] === 'string') {
          errorMessage = responseData[field];
        } else if (responseData[field].message) {
          errorMessage = responseData[field].message;
        }
        break;
      }
    }

    return {
      success: false,
      error: errorMessage,
      rawResponse: response
    };
  }

  /**
   * 类型验证
   */
  private static validateType<T>(data: any, options: SmartExtractOptions<T>): T {
    if (!options.enableTypeValidation || !options.expectedType) {
      return data as T;
    }

    try {
      // 如果数据已经是期望的类型，直接返回
      if (data instanceof options.expectedType) {
        return data;
      }

      // 尝试构造新实例（适用于简单对象）
      return new options.expectedType(data) as T;
    } catch (error) {
      console.warn(`类型验证失败: ${error instanceof Error ? error.message : '未知错误'}`);

      // 返回默认值或原数据
      return options.defaultValue !== undefined ? options.defaultValue : (data as T);
    }
  }

  // ==================== 便捷方法 ====================

  /**
   * 快速提取成功响应数据
   * 如果提取失败，返回默认值
   */
  static extractData<T = any>(
    response: AxiosResponse,
    defaultValue?: T
  ): T {
    const result = this.smartExtract<T>(response);

    if (!result.success) {
      console.warn(`响应数据提取失败: ${result.error}`);
      return defaultValue as T;
    }

    return result.data!;
  }

  /**
   * 提取响应消息
   */
  static extractMessage(response: AxiosResponse): string {
    try {
      const responseData = response.data;

      // 尝试从常见字段提取消息
      if (responseData.message) {
        return responseData.message;
      }

      if (responseData.data?.message) {
        return responseData.data.message;
      }

      return '操作成功';
    } catch (error) {
      return '操作完成';
    }
  }

  /**
   * 检查响应是否成功
   */
  static isSuccess(response: AxiosResponse): boolean {
    const result = this.smartExtract(response);
    return result.success;
  }

  /**
   * 批量提取响应数据
   */
  static batchExtract<T = any>(
    responses: AxiosResponse[],
    options?: SmartExtractOptions<T>
  ): ExtractResult<T>[] {
    return responses.map(response => this.smartExtract<T>(response, options));
  }

  /**
   * 提取并转换数据格式
   */
  static extractAndTransform<T, R>(
    response: AxiosResponse,
    transformer: (data: T) => R,
    options?: SmartExtractOptions<T>
  ): ExtractResult<R> {
    const originalResult = this.smartExtract<T>(response, options);

    if (!originalResult.success) {
      return {
        success: false,
        error: originalResult.error,
        rawResponse: originalResult.rawResponse
      };
    }

    try {
      const transformedData = transformer(originalResult.data!);

      return {
        success: true,
        data: transformedData,
        rawResponse: originalResult.rawResponse
      };
    } catch (error) {
      return {
        success: false,
        error: `数据转换失败: ${error instanceof Error ? error.message : '未知错误'}`,
        rawResponse: originalResult.rawResponse
      };
    }
  }
}

// ==================== 错误处理工具 ====================

/**
 * API错误处理器
 */
export class ApiErrorHandler {
  /**
   * 将axios错误转换为增强API错误
   */
  static handleError(error: any): EnhancedApiError {
    if (error instanceof AxiosError) {
      return this.handleAxiosError(error);
    }

    // 检查是否已经是增强型错误对象
    if (error && typeof error === 'object' && 'type' in error && 'code' in error && 'message' in error) {
      return error as EnhancedApiError;
    }

    // 未知错误
    return {
      type: ApiErrorType.UNKNOWN_ERROR,
      code: 'UNKNOWN_ERROR',
      message: error.message || '未知错误',
      timestamp: new Date().toISOString(),
      originalError: error
    };
  }

  /**
   * 处理axios错误
   */
  private static handleAxiosError(error: AxiosError): EnhancedApiError {
    const statusCode = error.response?.status;
    const responseData = error.response?.data;

    // 网络错误
    if (!error.response) {
      return {
        type: ApiErrorType.NETWORK_ERROR,
        code: 'NETWORK_ERROR',
        message: '网络连接失败，请检查网络设置',
        statusCode,
        timestamp: new Date().toISOString(),
        originalError: error
      };
    }

    // 4xx 客户端错误
    if (statusCode && statusCode >= 400 && statusCode < 500) {
      return {
        type: this.getClientErrorType(statusCode),
        code: (responseData as any)?.code || `HTTP_${statusCode}`,
        message: (responseData as any)?.message || (responseData as any)?.error || this.getDefaultErrorMessage(statusCode),
        details: (responseData as any)?.details,
        statusCode,
        timestamp: new Date().toISOString(),
        requestId: (responseData as any)?.requestId,
        originalError: error
      };
    }

    // 5xx 服务器错误
    if (statusCode && statusCode >= 500) {
      return {
        type: ApiErrorType.SERVER_ERROR,
        code: (responseData as any)?.code || `HTTP_${statusCode}`,
        message: (responseData as any)?.message || '服务器内部错误',
        details: (responseData as any)?.details,
        statusCode,
        timestamp: new Date().toISOString(),
        requestId: (responseData as any)?.requestId,
        originalError: error
      };
    }

    // 其他错误
    return {
      type: ApiErrorType.UNKNOWN_ERROR,
      code: 'UNKNOWN_ERROR',
      message: (responseData as any)?.message || (error as Error)?.message || '未知错误',
      statusCode,
      timestamp: new Date().toISOString(),
      originalError: error
    };
  }

  /**
   * 获取客户端错误类型
   */
  private static getClientErrorType(statusCode: number): ApiErrorType {
    switch (statusCode) {
      case 401:
        return ApiErrorType.AUTH_ERROR;
      case 422:
        return ApiErrorType.VALIDATION_ERROR;
      default:
        return ApiErrorType.CLIENT_ERROR;
    }
  }

  /**
   * 获取默认错误消息
   */
  private static getDefaultErrorMessage(statusCode: number): string {
    const messages: Record<number, string> = {
      400: '请求参数错误',
      401: '未授权访问',
      403: '访问被拒绝',
      404: '请求的资源不存在',
      422: '请求数据验证失败',
      429: '请求过于频繁，请稍后重试',
      500: '服务器内部错误',
      502: '网关错误',
      503: '服务暂时不可用',
      504: '网关超时'
    };

    return messages[statusCode] || `HTTP ${statusCode} 错误`;
  }
}

export default ResponseExtractor;