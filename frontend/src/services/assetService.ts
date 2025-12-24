import { enhancedApiClient } from "@/api/client";
import { ResponseExtractor, ApiErrorHandler } from "../utils/responseExtractor";
import { ASSET_API, STATISTICS_API, EXCEL_API } from "../constants/api";
import type {
  Asset,
  AssetSearchParams,
  AssetListResponse,
  AssetCreateRequest,
  AssetUpdateRequest,
  AssetHistory,
  SystemDictionary,
  AssetCustomField,
  CustomFieldValue,
} from "../types/asset";
import type { StandardApiResponse, PaginatedApiResponse } from "../types/api-response";

// ==================== 接口定义 ====================

// 字段选项接口
interface FieldOption {
  label: string;
  value: unknown;
}

// 字段验证结果接口
interface FieldValidationResult {
  valid: boolean;
  error?: string;
}

// 历史比较结果接口
interface HistoryComparisonResult {
  differences: Array<{
    field: string;
    oldValue: unknown;
    newValue: unknown;
    changeType: "added" | "modified" | "deleted";
  }>;
  summary: {
    totalChanges: number;
    significantChanges: number;
  };
}

// 统计数据接口
interface AssetStats {
  totalAssets: number;
  totalArea: number;
  occupiedArea: number;
  occupancyRate: number;
  byProject: Record<
    string,
    {
      count: number;
      area: number;
      occupancyRate: number;
    }
  >;
  byOwnership: Record<
    string,
    {
      count: number;
      area: number;
    }
  >;
}

// 导出任务状态接口
export interface ExportTask {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  downloadUrl?: string;
  createdAt: string;
  completedAt?: string;
  errorMessage?: string;
}

// 导入预览结果接口
interface ImportPreviewResult {
  headers: string[];
  data: Array<Record<string, unknown>>;
  totalCount: number;
  errors: Array<{
    row: number;
    field: string;
    message: string;
  }>;
}

// 导入任务状态接口
interface ImportTask {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  processedCount: number;
  totalCount: number;
  errors: Array<{
    row: number;
    field: string;
    message: string;
  }>;
  createdAt: string;
  completedAt?: string;
}

// 出租率统计接口
interface OccupancyRateStats {
  overall: {
    totalArea: number;
    occupiedArea: number;
    occupancyRate: number;
  };
  byProject: Record<
    string,
    {
      totalArea: number;
      occupiedArea: number;
      occupancyRate: number;
    }
  >;
  byTimeRange: Array<{
    period: string;
    occupancyRate: number;
  }>;
}

// 资产分布统计接口
interface AssetDistributionStats {
  byNature: Record<string, number>;
  byStatus: Record<string, number>;
  byUsage: Record<string, number>;
  byArea: Array<{
    range: string;
    count: number;
  }>;
}

// 面积统计接口
interface AreaStatistics {
  totalLandArea: number;
  totalPropertyArea: number;
  totalRentableArea: number;
  totalRentedArea: number;
  averageOccupancyRate: number;
  breakdown: {
    byProject: Record<
      string,
      {
        landArea: number;
        propertyArea: number;
        rentableArea: number;
        rentedArea: number;
        occupancyRate: number;
      }
    >;
  };
}

// 字段历史记录接口
interface FieldHistoryRecord {
  timestamp: string;
  value: unknown;
  changedBy: string;
  changeReason?: string;
}

// 搜索过滤器接口
interface AssetSearchFilters {
  project?: string;
  ownershipEntity?: string;
  propertyNature?: string;
  usageStatus?: string;
  businessCategory?: string;
  [key: string]: unknown;
}

// 导出选项接口
interface ExportOptions {
  format?: "xlsx" | "csv";
  includeHeaders?: boolean;
  selectedFields?: string[];
}

// 综合统计接口
interface ComprehensiveStats extends AssetStats {
  distribution: AssetDistributionStats;
  areaStats: AreaStatistics;
  occupancyTrend: Array<{
    period: string;
    rate: number;
  }>;
  recentActivity: Array<{
    type: string;
    count: number;
    timestamp: string;
  }>;
}

// ==================== AssetService 实现 ====================

export class AssetService {
  // 获取资产列表
  async getAssets(params?: AssetSearchParams): Promise<AssetListResponse> {
    try {
      const result = await enhancedApiClient.get<AssetListResponse>(ASSET_API.LIST, {
        params: {
          ...params,
          page: params?.page || 1,
          limit: params?.limit || 20,
        },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取资产列表失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取所有资产（不分页，用于导出等场景）
  async getAllAssets(params?: Omit<AssetSearchParams, "page" | "limit">): Promise<Asset[]> {
    try {
      const result = await enhancedApiClient.get<Asset[]>(`${ASSET_API.LIST}/all`, {
        params: {
          ...params,
          // 设置较大的限制以获取所有数据
          limit: 10000,
        },
        cache: true,
        retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取所有资产失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 根据ID列表获取资产
  async getAssetsByIds(ids: string[]): Promise<Asset[]> {
    try {
      const result = await enhancedApiClient.post<Asset[]>(`${ASSET_API.LIST}/by-ids`, { ids }, {
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`根据ID列表获取资产失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取单个资产
  async getAsset(id: string): Promise<Asset> {
    try {
      const result = await enhancedApiClient.get<Asset>(ASSET_API.DETAIL(id), {
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取资产详情失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 创建资产
  async createAsset(data: AssetCreateRequest): Promise<Asset> {
    try {
      const result = await enhancedApiClient.post<Asset>(ASSET_API.CREATE, data, {
        retry: false, // 创建操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`创建资产失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 更新资产
  async updateAsset(id: string, data: AssetUpdateRequest): Promise<Asset> {
    try {
      const result = await enhancedApiClient.put<Asset>(ASSET_API.UPDATE(id), data, {
        retry: false, // 更新操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`更新资产失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 删除资产
  async deleteAsset(id: string): Promise<void> {
    try {
      const result = await enhancedApiClient.delete<void>(ASSET_API.DELETE(id), {
        retry: false, // 删除操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`删除资产失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 批量删除资产
  async deleteAssets(ids: string[]): Promise<void> {
    try {
      const result = await enhancedApiClient.post<void>(ASSET_API.BATCH_DELETE, { ids }, {
        retry: false, // 批量删除不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`批量删除资产失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取资产变更历史
  async getAssetHistory(
    assetId: string,
    page = 1,
    limit = 20,
    changeType?: string,
  ): Promise<PaginatedApiResponse<AssetHistory>> {
    try {
      const result = await enhancedApiClient.get<PaginatedApiResponse<AssetHistory>>(
        `${ASSET_API.DETAIL(assetId)}/history`,
        {
          params: { page, limit, change_type: changeType },
          cache: true,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取资产历史失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取历史记录详情
  async getHistoryDetail(historyId: string): Promise<AssetHistory> {
    try {
      const result = await enhancedApiClient.get<AssetHistory>(`/history/${historyId}`, {
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取历史详情失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 比较历史记录
  async compareHistory(historyId1: string, historyId2: string): Promise<HistoryComparisonResult> {
    try {
      const result = await enhancedApiClient.get<HistoryComparisonResult>(
        `/history/compare/${historyId1}/${historyId2}`,
        {
          cache: true,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`比较历史记录失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取字段变更历史
  async getFieldHistory(
    assetId: string,
    fieldName: string,
    limit = 10,
  ): Promise<FieldHistoryRecord[]> {
    try {
      const result = await enhancedApiClient.get<{ history: FieldHistoryRecord[] }>(
        `${ASSET_API.DETAIL(assetId)}/field-history/${fieldName}`,
        {
          params: { limit },
          cache: true,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取字段历史失败: ${result.error}`);
      }

      return result.data.history || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 搜索资产
  async searchAssets(query: string, filters?: AssetSearchFilters): Promise<AssetListResponse> {
    return this.getAssets({
      search: query,
      ...filters,
    });
  }

  // 获取资产统计信息
  async getAssetStats(filters?: AssetSearchParams): Promise<AssetStats> {
    try {
      const result = await enhancedApiClient.get<AssetStats>("/statistics/basic", {
        params: filters,
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取资产统计失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取权属方列表
  async getOwnershipEntities(): Promise<string[]> {
    try {
      const result = await enhancedApiClient.get<string[]>(ASSET_API.OWNERSHIP_ENTITIES, {
        timeout: 3000, // 3秒超时
        cache: true,
        retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取权属方列表失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取业态类别列表
  async getBusinessCategories(): Promise<string[]> {
    try {
      const result = await enhancedApiClient.get<string[]>(ASSET_API.BUSINESS_CATEGORIES, {
        timeout: 3000,
        cache: true,
        retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取业态类别失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 验证资产数据
  async validateAsset(data: AssetCreateRequest | AssetUpdateRequest): Promise<{
    valid: boolean;
    errors: string[];
  }> {
    try {
      const result = await enhancedApiClient.post<void>(`${ASSET_API.LIST}/validate`, data, {
        retry: false, // 验证操作不重试
        smartExtract: true
      });

      if (!result.success) {
        return {
          valid: false,
          errors: [result.error || '验证失败']
        };
      }

      return {
        valid: true,
        errors: [],
      };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      return {
        valid: false,
        errors: [enhancedError.message]
      };
    }
  }

  // ===== 导入导出功能 =====

  // 导出资产数据
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

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 导出选中的资产
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

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取导出状态
  async getExportStatus(taskId: string): Promise<ExportTask> {
    try {
      const result = await enhancedApiClient.get<ExportTask>(`/excel/export-status/${taskId}`, {
        cache: false, // 状态查询不缓存
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取导出状态失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取导出历史
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
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 删除导出记录
  async deleteExportRecord(id: string): Promise<void> {
    try {
      const result = await enhancedApiClient.delete<void>(`/excel/export-history/${id}`, {
        retry: false, // 删除操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`删除导出记录失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 下载导出文件
  async downloadExportFile(downloadUrl: string): Promise<void> {
    // 创建一个隐藏的链接来触发下载
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = "";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // ===== 导入功能 =====

  // 上传导入文件
  async uploadImportFile(file: File): Promise<ImportTask> {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const result = await enhancedApiClient.post<ImportTask>("/excel/import", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        retry: false, // 文件上传不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`上传导入文件失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 预览导入文件
  async previewImportFile(file: File): Promise<ImportPreviewResult> {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const result = await enhancedApiClient.post<ImportPreviewResult>("/excel/preview", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        retry: false, // 文件预览不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`预览导入文件失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 下载导入模板
  async downloadImportTemplate(): Promise<void> {
    try {
      const result = await enhancedApiClient.get<Blob>("/excel/template", {
        responseType: "blob",
        cache: true, // 模板文件可以缓存
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 }
      });

      if (!result.success) {
        throw new Error(`下载导入模板失败: ${result.error}`);
      }

      // 创建下载链接
      const blob = result.data;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "asset_import_template.xlsx";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取导入状态
  async getImportStatus(importId: string): Promise<ImportTask> {
    try {
      const result = await enhancedApiClient.get<ImportTask>(`/excel/import-status/${importId}`, {
        cache: false, // 状态查询不缓存
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取导入状态失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取导入历史
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
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 删除导入记录
  async deleteImportRecord(id: string): Promise<void> {
    try {
      const result = await enhancedApiClient.delete<void>(`/excel/import-history/${id}`, {
        retry: false, // 删除操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`删除导入记录失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ===== 统计分析功能 =====

  // 获取出租率统计数据
  async getOccupancyRateStats(filters?: AssetSearchParams): Promise<OccupancyRateStats> {
    try {
      const result = await enhancedApiClient.get<OccupancyRateStats>("/statistics/occupancy-rate", {
        params: filters,
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取出租率统计失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取资产分布统计数据
  async getAssetDistributionStats(filters?: AssetSearchParams): Promise<AssetDistributionStats> {
    try {
      const result = await enhancedApiClient.get<AssetDistributionStats>("/statistics/asset-distribution", {
        params: filters,
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取资产分布统计失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取面积统计数据
  async getAreaStatistics(filters?: AssetSearchParams): Promise<AreaStatistics> {
    try {
      const result = await enhancedApiClient.get<AreaStatistics>("/statistics/area-statistics", {
        params: filters,
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取面积统计失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取综合统计数据
  async getComprehensiveStats(filters?: AssetSearchParams): Promise<ComprehensiveStats> {
    try {
      const result = await enhancedApiClient.get<ComprehensiveStats>("/statistics/comprehensive", {
        params: filters,
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取综合统计失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ===== 系统字典管理 =====

  // 获取系统字典列表
  async getSystemDictionaries(dict_type?: string): Promise<SystemDictionary[]> {
    try {
      const result = await enhancedApiClient.get<SystemDictionary[]>("/system-dictionaries", {
        params: dict_type ? { dict_type } : undefined,
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取系统字典失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取单个系统字典
  async getSystemDictionary(id: string): Promise<SystemDictionary> {
    try {
      const result = await enhancedApiClient.get<SystemDictionary>(`/system-dictionaries/${id}`, {
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取系统字典详情失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 创建系统字典
  async createSystemDictionary(
    data: Omit<SystemDictionary, "id" | "created_at" | "updated_at">,
  ): Promise<SystemDictionary> {
    try {
      const result = await enhancedApiClient.post<SystemDictionary>("/system-dictionaries", data, {
        retry: false, // 创建操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`创建系统字典失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 更新系统字典
  async updateSystemDictionary(
    id: string,
    data: Partial<SystemDictionary>,
  ): Promise<SystemDictionary> {
    try {
      const result = await enhancedApiClient.put<SystemDictionary>(`/system-dictionaries/${id}`, data, {
        retry: false, // 更新操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`更新系统字典失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 删除系统字典
  async deleteSystemDictionary(id: string): Promise<void> {
    try {
      const result = await enhancedApiClient.delete<void>(`/system-dictionaries/${id}`, {
        retry: false, // 删除操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`删除系统字典失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 批量更新系统字典
  async batchUpdateSystemDictionaries(
    updates: Array<{ id: string; data: Partial<SystemDictionary> }>,
  ): Promise<SystemDictionary[]> {
    try {
      const result = await enhancedApiClient.post<SystemDictionary[]>("/system-dictionaries/batch-update", { updates }, {
        retry: false, // 批量操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`批量更新系统字典失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取字典类型列表
  async getDictionaryTypes(): Promise<{ types: string[] }> {
    try {
      const result = await enhancedApiClient.get<{ types: string[] }>("/system-dictionaries/types/list", {
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取字典类型列表失败: ${result.error}`);
      }

      return result.data || { types: [] };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ===== 自定义字段管理 =====

  // 获取资产自定义字段配置
  async getAssetCustomFields(assetId?: string): Promise<AssetCustomField[]> {
    try {
      const result = await enhancedApiClient.get<AssetCustomField[]>("/asset-custom-fields", {
        params: assetId ? { asset_id: assetId } : undefined,
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取资产自定义字段配置失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取单个自定义字段配置
  async getAssetCustomField(id: string): Promise<AssetCustomField> {
    try {
      const result = await enhancedApiClient.get<AssetCustomField>(`/asset-custom-fields/${id}`, {
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取自定义字段配置失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 创建自定义字段配置
  async createAssetCustomField(
    data: Omit<AssetCustomField, "id" | "created_at" | "updated_at">,
  ): Promise<AssetCustomField> {
    try {
      const result = await enhancedApiClient.post<AssetCustomField>("/asset-custom-fields", data, {
        retry: false, // 创建操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`创建自定义字段配置失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 更新自定义字段配置
  async updateAssetCustomField(
    id: string,
    data: Partial<AssetCustomField>,
  ): Promise<AssetCustomField> {
    try {
      const result = await enhancedApiClient.put<AssetCustomField>(`/asset-custom-fields/${id}`, data, {
        retry: false, // 更新操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`更新自定义字段配置失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 删除自定义字段配置
  async deleteAssetCustomField(id: string): Promise<void> {
    try {
      const result = await enhancedApiClient.delete<void>(`/asset-custom-fields/${id}`, {
        retry: false, // 删除操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`删除自定义字段配置失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取资产的自定义字段值
  async getAssetCustomFieldValues(assetId: string): Promise<CustomFieldValue[]> {
    try {
      const result = await enhancedApiClient.get<CustomFieldValue[]>(`${ASSET_API.DETAIL(assetId)}/custom-fields`, {
        cache: false, // 字段值数据不缓存
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取资产自定义字段值失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 更新资产的自定义字段值
  async updateAssetCustomFieldValues(
    assetId: string,
    values: CustomFieldValue[],
  ): Promise<CustomFieldValue[]> {
    try {
      const result = await enhancedApiClient.put<CustomFieldValue[]>(`${ASSET_API.DETAIL(assetId)}/custom-fields`, { values }, {
        retry: false, // 字段值更新不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`更新资产自定义字段值失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 批量设置自定义字段值
  async batchSetCustomFieldValues(
    updates: Array<{ assetId: string; values: CustomFieldValue[] }>,
  ): Promise<void> {
    try {
      const result = await enhancedApiClient.post<void>(`${ASSET_API.BATCH_UPDATE}/custom-fields`, { updates }, {
        retry: false, // 批量操作不重试
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`批量设置自定义字段值失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ===== 便捷方法 =====

  // 获取权属方字典
  async getOwnershipEntitiesFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries("ownership_status");
  }

  // 获取管理实体列表
  async getManagementEntities(): Promise<string[]> {
    try {
      const result = await enhancedApiClient.get<string[]>(ASSET_API.OWNERSHIP_ENTITIES, {
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取管理实体列表失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取管理方字典
  async getManagementEntitiesFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries("management_entity");
  }

  // 获取业态类别字典
  async getBusinessCategoriesFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries("business_category");
  }

  // 获取资产状态字典
  async getAssetStatusFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries("property_nature");
  }

  // 获取权属性质字典
  async getOwnershipNatureFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries("usage_status");
  }

  // 获取租赁状态字典
  async getLeaseStatusFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries("contract_status");
  }

  // ===== 数据验证和转换 =====

  // 验证自定义字段值
  async validateCustomFieldValue(fieldId: string, value: unknown): Promise<FieldValidationResult> {
    try {
      const result = await enhancedApiClient.post<void>("/asset-custom-fields/validate", {
        field_id: fieldId,
        value: value,
      }, {
        retry: false, // 验证操作不重试
        smartExtract: true
      });

      if (!result.success) {
        return {
          valid: false,
          error: result.error || "验证失败"
        };
      }

      return { valid: true };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      return {
        valid: false,
        error: enhancedError.message
      };
    }
  }

  // 获取字段选项（用于下拉框等）
  async getFieldOptions(fieldType: string, category?: string): Promise<FieldOption[]> {
    try {
      const result = await enhancedApiClient.get<FieldOption[]>("/field-options", {
        params: { field_type: fieldType, category },
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      if (!result.success) {
        throw new Error(`获取字段选项失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

// 导出服务实例
export const assetService = new AssetService();