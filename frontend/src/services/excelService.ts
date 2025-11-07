import { apiClient } from "./api";
import type { ExcelImportResponse, ExcelExportRequest, ExcelExportResponse } from "@/types/api";
import type { ImportExportHistory, TaskStatusResponse, Filters } from "@/types/common";

// API 错误接口
interface ApiError extends Error {
  response?: {
    data?: {
      message?: string;
      detail?: string;
    };
  };
  message?: string;
}

export class ExcelService {
  async importExcel(
    file: File,
    sheetName = "物业总表",
    onProgress?: (progress: number) => void,
  ): Promise<ExcelImportResponse> {
    const response = await apiClient.upload<ExcelImportResponse>(
      "/excel/import",
      file,
      onProgress,
      { sheet_name: sheetName },
    );
    return response.data!;
  }

  async exportExcel(request: ExcelExportRequest): Promise<ExcelExportResponse> {
    const response = await apiClient.post<ExcelExportResponse>("/excel/export", request);
    return response.data!;
  }

  async downloadExportFile(filename: string): Promise<void> {
    try {
      await apiClient.download(`/excel/download/${filename}`, filename);
    } catch (error) {
      console.error("操作失败:", error);
      throw new Error(error instanceof Error ? error.message : "操作失败");
    }
  }

  async downloadTemplate(templateName = "资产导入模板.xlsx"): Promise<void> {
    await apiClient.download("/excel/import/template", templateName);
  }

  async getImportHistory(page = 1, limit = 20): Promise<ImportExportHistory[]> {
    const response = await apiClient.get<{ data: ImportExportHistory[] }>("/excel/import/history", {
      params: { page, limit },
    });
    return response.data?.data || [];
  }

  async getExportHistory(page = 1, limit = 20): Promise<ImportExportHistory[]> {
    const response = await apiClient.get<{ data: ImportExportHistory[] }>("/excel/export/history", {
      params: { page, limit },
    });
    return response.data?.data || [];
  }

  async getImportStatus(taskId: string): Promise<TaskStatusResponse> {
    const response = await apiClient.get<TaskStatusResponse>(`/excel/import/status/${taskId}`);
    return response.data || response;
  }

  async getExportStatus(taskId: string): Promise<TaskStatusResponse> {
    const response = await apiClient.get<TaskStatusResponse>(`/excel/export/status/${taskId}`);
    return response.data || response;
  }

  async cancelImport(taskId: string): Promise<void> {
    await apiClient.post(`/excel/import/cancel/${taskId}`);
  }

  async cancelExport(taskId: string): Promise<void> {
    await apiClient.post(`/excel/export/cancel/${taskId}`);
  }

  async validateExcelFile(file: File): Promise<{
    valid: boolean;
    errors: string[];
    warnings: string[];
  }> {
    try {
      const response = await apiClient.upload<{
        valid: boolean;
        errors: string[];
        warnings: string[];
      }>("/excel/validate", file);
      return (
        response.data || {
          valid: true,
          errors: [],
          warnings: [],
        }
      );
    } catch (error: unknown) {
      const apiError = error as ApiError;
      return {
        valid: false,
        errors: [apiError?.response?.data?.detail || apiError?.message || "Excel文件验证失败"],
        warnings: [],
      };
    }
  }

  async getSupportedFormats(): Promise<string[]> {
    const response = await apiClient.get<string[]>("/excel/formats");
    return response.data || ["xlsx", "xls", "csv"];
  }

  async getFieldMapping(): Promise<Record<string, string>> {
    const response = await apiClient.get<Record<string, string>>("/excel/field-mapping");
    return response.data || {};
  }

  async updateFieldMapping(mapping: Record<string, string>): Promise<void> {
    await apiClient.post("/excel/field-mapping", { mapping });
  }
}

export const excelService = new ExcelService();
