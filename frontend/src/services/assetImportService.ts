import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';

export interface AssetImportPerformanceMetrics {
  records_per_second: number;
  estimated_time_for_1000: number;
}

export interface AssetImportResult {
  success: number;
  failed: number;
  total: number;
  errors: string[];
  message: string;
  processing_time?: number;
  filename?: string;
  performance_metrics?: AssetImportPerformanceMetrics;
}

export interface AssetImportConfig {
  sheetName: string;
  skipErrors: boolean;
  useOptimized: boolean;
  timeoutSeconds: number;
}

class AssetImportService {
  async downloadTemplate(templateName = 'land_property_asset_template.xlsx'): Promise<void> {
    try {
      const result = await apiClient.get<Blob>('/excel/template', {
        responseType: 'blob',
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      });

      if (!result.success || result.data == null) {
        throw new Error(`模板下载失败: ${result.error ?? '未知错误'}`);
      }

      const downloadUrl = window.URL.createObjectURL(result.data);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = templateName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async importAssets(file: File, config: AssetImportConfig): Promise<AssetImportResult> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const endpoint = config.useOptimized ? '/excel/import/optimized' : '/excel/import';
      const result = await apiClient.post<AssetImportResult>(endpoint, formData, {
        params: {
          sheet_name: config.sheetName,
          skip_errors: config.skipErrors,
        },
        timeout: config.timeoutSeconds * 1000,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        retry: false,
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`导入失败: ${result.error ?? '未知错误'}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

export const assetImportService = new AssetImportService();
