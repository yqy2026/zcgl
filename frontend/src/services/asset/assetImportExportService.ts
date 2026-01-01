/**
 * Asset Import/Export Service
 * 资产导入导出相关操作
 */

import { enhancedApiClient } from "@/api/client";
import { ApiErrorHandler } from "../../utils/responseExtractor";
import type {
    AssetSearchParams,
    ExportTask,
    ExportOptions,
    ImportTask,
    ImportPreviewResult,
} from "./types";

/**
 * 资产导入导出服务类
 * 提供资产数据的导入导出功能
 */
export class AssetImportExportService {
    // ===== 导出功能 =====

    /**
     * 导出资产数据
     */
    async exportAssets(filters?: AssetSearchParams, options?: ExportOptions): Promise<Blob> {
        try {
            const result = await enhancedApiClient.post<Blob>("/excel/export", {
                filters,
                format: options?.format || "xlsx",
                include_headers: options?.includeHeaders !== false,
                selected_fields: options?.selectedFields,
            }, {
                retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
                responseType: 'blob'
            });

            if (!result.success) {
                throw new Error(`导出资产数据失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 导出选中的资产
     */
    async exportSelectedAssets(assetIds: string[], options?: ExportOptions): Promise<Blob> {
        try {
            const result = await enhancedApiClient.post<Blob>("/excel/export-selected", {
                asset_ids: assetIds,
                format: options?.format || "xlsx",
                include_headers: options?.includeHeaders !== false,
                selected_fields: options?.selectedFields,
            }, {
                retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
                responseType: 'blob'
            });

            if (!result.success) {
                throw new Error(`导出选中资产失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取导出状态
     */
    async getExportStatus(taskId: string): Promise<ExportTask> {
        try {
            const result = await enhancedApiClient.get<ExportTask>(`/excel/export-status/${taskId}`, {
                cache: false,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取导出状态失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取导出历史
     */
    async getExportHistory(): Promise<ExportTask[]> {
        try {
            const result = await enhancedApiClient.get<ExportTask[]>("/excel/export-history", {
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取导出历史失败: ${result.error}`);
            }

            return result.data || [];
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 删除导出记录
     */
    async deleteExportRecord(id: string): Promise<void> {
        try {
            const result = await enhancedApiClient.delete<void>(`/excel/export-history/${id}`, {
                retry: false,
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`删除导出记录失败: ${result.error}`);
            }
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 下载导出文件
     */
    async downloadExportFile(downloadUrl: string): Promise<void> {
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = "";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // ===== 导入功能 =====

    /**
     * 上传导入文件
     */
    async uploadImportFile(file: File): Promise<ImportTask> {
        try {
            const formData = new FormData();
            formData.append("file", file);

            const result = await enhancedApiClient.post<ImportTask>("/excel/import", formData, {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
                retry: false,
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`上传导入文件失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 预览导入文件
     */
    async previewImportFile(file: File): Promise<ImportPreviewResult> {
        try {
            const formData = new FormData();
            formData.append("file", file);

            const result = await enhancedApiClient.post<ImportPreviewResult>("/excel/preview", formData, {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
                retry: false,
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`预览导入文件失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 下载导入模板
     */
    async downloadImportTemplate(): Promise<void> {
        try {
            const result = await enhancedApiClient.get<Blob>("/excel/template", {
                responseType: "blob",
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 }
            });

            if (!result.success) {
                throw new Error(`下载导入模板失败: ${result.error}`);
            }

            const blob = result.data!;
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = "asset_import_template.xlsx";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取导入状态
     */
    async getImportStatus(importId: string): Promise<ImportTask> {
        try {
            const result = await enhancedApiClient.get<ImportTask>(`/excel/import-status/${importId}`, {
                cache: false,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取导入状态失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取导入历史
     */
    async getImportHistory(): Promise<ImportTask[]> {
        try {
            const result = await enhancedApiClient.get<ImportTask[]>("/excel/import-history", {
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取导入历史失败: ${result.error}`);
            }

            return result.data || [];
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 删除导入记录
     */
    async deleteImportRecord(id: string): Promise<void> {
        try {
            const result = await enhancedApiClient.delete<void>(`/excel/import-history/${id}`, {
                retry: false,
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`删除导入记录失败: ${result.error}`);
            }
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }
}

// 导出服务实例
export const assetImportExportService = new AssetImportExportService();
