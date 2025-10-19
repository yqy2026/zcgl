/**
 * 租金合同Excel导入导出服务
 */

import { apiClient } from './api';
import axios from 'axios';
import { RentContract, RentTerm, RentLedger } from '../types/rentContract';

export interface ExcelImportResult {
  success: boolean;
  message: string;
  imported_contracts: number;
  imported_terms: number;
  imported_ledgers: number;
  errors: string[];
  warnings: string[];
}

export interface ExcelExportResult {
  success: boolean;
  message: string;
  file_path: string;
  file_name: string;
  file_size: number;
  stats: {
    total_contracts: number;
    total_terms: number;
    total_ledgers: number;
  };
}

export interface ExcelTemplateResult {
  success: boolean;
  message: string;
  file_path: string;
  file_name: string;
  file_size: number;
}

class RentContractExcelService {
  private baseUrl = '/rent_contract';

  /**
   * 下载Excel导入模板
   */
  async downloadTemplate(): Promise<Blob> {
    try {
      const apiBase = import.meta.env.DEV ? '/api/v1' : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1');
      const response = await axios.get(`${apiBase}${this.baseUrl}/excel/template`, {
        responseType: 'blob',
      });

      return response.data;
    } catch (error) {
      console.error('下载模板失败:', error);
      throw new Error('下载模板失败');
    }
  }

  /**
   * 导入Excel文件
   */
  async importFromFile(
    file: File,
    options: {
      import_terms?: boolean;
      import_ledger?: boolean;
      overwrite_existing?: boolean;
    } = {}
  ): Promise<ExcelImportResult> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('import_terms', String(options.import_terms ?? true));
      formData.append('import_ledger', String(options.import_ledger ?? false));
      formData.append('overwrite_existing', String(options.overwrite_existing ?? false));

      const response = await apiClient.post<ExcelImportResult>(
        `${this.baseUrl}/excel/import`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      return response.data;
    } catch (error) {
      console.error('导入Excel失败:', error);
      throw new Error('导入Excel失败');
    }
  }

  /**
   * 导出Excel文件
   */
  async exportToFile(
    options: {
      contract_ids?: string[];
      include_terms?: boolean;
      include_ledger?: boolean;
      start_date?: string;
      end_date?: string;
    } = {}
  ): Promise<Blob> {
    try {
      const params = new URLSearchParams();
      if (options.contract_ids?.length) {
        options.contract_ids.forEach(id => params.append('contract_ids', id));
      }
      if (options.include_terms !== undefined) {
        params.append('include_terms', String(options.include_terms));
      }
      if (options.include_ledger !== undefined) {
        params.append('include_ledger', String(options.include_ledger));
      }
      if (options.start_date) {
        params.append('start_date', options.start_date);
      }
      if (options.end_date) {
        params.append('end_date', options.end_date);
      }

      const apiBase = import.meta.env.DEV ? '/api/v1' : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1');
      const response = await axios.get(`${apiBase}${this.baseUrl}/excel/export`, {
        params,
        responseType: 'blob',
      });

      return response.data;
    } catch (error) {
      console.error('导出Excel失败:', error);
      throw new Error('导出Excel失败');
    }
  }

  /**
   * 下载模板文件
   */
  async downloadTemplateFile(): Promise<void> {
    try {
      const blob = await this.downloadTemplate();

      // 确保blob是有效的
      if (!(blob instanceof Blob)) {
        throw new Error('无效的文件数据');
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = '租金合同导入模板.xlsx';
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();

      // 延迟清理以确保下载开始
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
    } catch (error) {
      console.error('下载模板文件失败:', error);
      throw error;
    }
  }

  /**
   * 导出并下载文件
   */
  async exportAndDownload(
    options: {
      contract_ids?: string[];
      include_terms?: boolean;
      include_ledger?: boolean;
      start_date?: string;
      end_date?: string;
      filename?: string;
    } = {}
  ): Promise<void> {
    try {
      const blob = await this.exportToFile(options);

      // 确保blob是有效的
      if (!(blob instanceof Blob)) {
        throw new Error('无效的文件数据');
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      // 生成文件名
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const filename = options.filename || `租金合同导出_${timestamp}.xlsx`;
      link.download = filename;
      link.style.display = 'none';

      document.body.appendChild(link);
      link.click();

      // 延迟清理以确保下载开始
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
    } catch (error) {
      console.error('导出并下载文件失败:', error);
      throw error;
    }
  }

  /**
   * 处理文件上传和导入
   */
  async handleFileUpload(
    file: File,
    options: {
      import_terms?: boolean;
      import_ledger?: boolean;
      overwrite_existing?: boolean;
      onSuccess?: (result: ExcelImportResult) => void;
      onError?: (error: Error) => void;
    } = {}
  ): Promise<ExcelImportResult> {
    try {
      // 验证文件类型
      if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        throw new Error('请选择Excel文件（.xlsx或.xls格式）');
      }

      // 验证文件大小（限制为10MB）
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (file.size > maxSize) {
        throw new Error('文件大小不能超过10MB');
      }

      const result = await this.importFromFile(file, options);

      if (options.onSuccess) {
        options.onSuccess(result);
      }

      return result;
    } catch (error) {
      if (options.onError) {
        options.onError(error as Error);
      }
      throw error;
    }
  }

  /**
   * 获取导入错误摘要
   */
  getImportErrorSummary(result: ExcelImportResult): string {
    if (result.errors.length === 0) {
      return '';
    }

    const errorCount = result.errors.length;
    const warningCount = result.warnings.length;

    let summary = `导入完成，但发现 ${errorCount} 个错误`;
    if (warningCount > 0) {
      summary += `和 ${warningCount} 个警告`;
    }
    summary += '。';

    // 显示前几个错误
    const maxErrors = 3;
    if (result.errors.length > 0) {
      summary += '\n\n错误详情：';
      result.errors.slice(0, maxErrors).forEach((error, index) => {
        summary += `\n${index + 1}. ${error}`;
      });

      if (result.errors.length > maxErrors) {
        summary += `\n... 还有 ${result.errors.length - maxErrors} 个错误`;
      }
    }

    return summary;
  }

  /**
   * 获取导入成功摘要
   */
  getImportSuccessSummary(result: ExcelImportResult): string {
    const parts = [];

    if (result.imported_contracts > 0) {
      parts.push(`${result.imported_contracts} 个合同`);
    }

    if (result.imported_terms > 0) {
      parts.push(`${result.imported_terms} 个租金条款`);
    }

    if (result.imported_ledgers > 0) {
      parts.push(`${result.imported_ledgers} 个台账记录`);
    }

    if (parts.length === 0) {
      return '没有导入任何数据';
    }

    return `成功导入 ${parts.join('、')}`;
  }

  /**
   * 格式化文件大小
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';

    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * 验证Excel文件
   */
  validateExcelFile(file: File): { isValid: boolean; error?: string } {
    // 检查文件扩展名
    const validExtensions = ['.xlsx', '.xls'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!validExtensions.includes(fileExtension)) {
      return {
        isValid: false,
        error: '请选择Excel文件（.xlsx或.xls格式）'
      };
    }

    // 检查文件大小（限制为10MB）
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      return {
        isValid: false,
        error: '文件大小不能超过10MB'
      };
    }

    // 检查文件类型
    if (file.type && !file.type.includes('sheet') && !file.type.includes('excel')) {
      return {
        isValid: false,
        error: '请选择有效的Excel文件'
      };
    }

    return { isValid: true };
  }
}

// 导出单例实例
export const rentContractExcelService = new RentContractExcelService();