import { apiClient } from "./api";
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
} from "@/types/asset";
import type { PaginatedResponse } from "@/types/api";

// API 错误接口
interface ApiError extends Error {
  response?: {
    data?: {
      details?: Array<{ msg: string }>;
      message?: string;
    };
  };
  message?: string;
}

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

export class AssetService {
  // 获取资产列表
  async getAssets(params?: AssetSearchParams): Promise<AssetListResponse> {
    try {
      const response = await apiClient.get<AssetListResponse>("/assets", {
        params: {
          ...params,
          page: params?.page || 1,
          limit: params?.limit || 20,
        },
      });

      // 处理响应数据
      if (response.data) {
        return response.data;
      }

      // 如果响应直接是数据，构造标准格式
      if (Array.isArray(response)) {
        return {
          items: response,
          total: response.length,
          page: params?.page || 1,
          limit: params?.limit || 20,
          pages: 1,
        };
      }

      return response as AssetListResponse;
    } catch (error) {
      console.error("获取资产列表失败:", error);
      // 抛出错误而不是返回空数据，让React Query能够正确处理错误状态
      throw new Error(error instanceof Error ? error.message : "获取资产列表失败");
    }
  }

  // 获取所有资产（不分页，用于导出等场景）
  async getAllAssets(params?: Omit<AssetSearchParams, "page" | "limit">): Promise<Asset[]> {
    try {
      const response = await apiClient.get<Asset[]>("/assets/all", {
        params: {
          ...params,
          // 设置较大的限制以获取所有数据
          limit: 10000,
        },
      });

      // 处理新的响应格式：{success: true, data: Asset[], message: string}
      if (response.data && Array.isArray(response.data)) {
        return response.data;
      }

      // 如果响应是包装格式，提取data字段
      if (response?.data && Array.isArray(response.data)) {
        return response.data;
      }

      // 处理统一响应格式：{success: true, data: [...], message: "..."}
      if (response?.success && Array.isArray(response?.data)) {
        return response.data;
      }

      return response as Asset[];
    } catch (error) {
      console.error("获取所有资产失败:", error);
      throw new Error(error instanceof Error ? error.message : "获取所有资产失败");
    }
  }

  // 根据ID列表获取资产
  async getAssetsByIds(ids: string[]): Promise<Asset[]> {
    try {
      const response = await apiClient.post<Asset[]>("/assets/by-ids", { ids });

      // 处理新的响应格式：{success: true, data: Asset[], message: string}
      if (response.data && Array.isArray(response.data)) {
        return response.data;
      }

      // 如果响应是包装格式，提取data字段
      if (response?.data && Array.isArray(response.data)) {
        return response.data;
      }

      // 处理统一响应格式：{success: true, data: [...], message: "..."}
      if (response?.success && Array.isArray(response?.data)) {
        return response.data;
      }

      return response as Asset[];
    } catch (error) {
      console.error("根据ID列表获取资产失败:", error);
      throw new Error(error instanceof Error ? error.message : "根据ID列表获取资产失败");
    }
  }

  // 获取单个资产
  async getAsset(id: string): Promise<Asset> {
    const response = await apiClient.get<Asset>(`/assets/${id}`);
    return response.data || (response as Asset);
  }

  // 创建资产
  async createAsset(data: AssetCreateRequest): Promise<Asset> {
    const response = await apiClient.post<Asset>("/assets", data);
    return response.data || (response as Asset);
  }

  // 更新资产
  async updateAsset(id: string, data: AssetUpdateRequest): Promise<Asset> {
    const response = await apiClient.put<Asset>(`/assets/${id}`, data);
    return response.data || (response as Asset);
  }

  // 删除资产
  async deleteAsset(id: string): Promise<void> {
    try {
      await apiClient.delete(`/assets/${id}`);
    } catch (error) {
      console.error("删除资产失败:", error);
      throw error;
    }
  }

  // 批量删除资产
  async deleteAssets(ids: string[]): Promise<void> {
    await apiClient.post("/assets/batch-delete", { ids });
  }

  // 获取资产变更历史
  async getAssetHistory(
    assetId: string,
    page = 1,
    limit = 20,
    changeType?: string,
  ): Promise<PaginatedResponse<AssetHistory>> {
    const response = await apiClient.get<PaginatedResponse<AssetHistory>>(
      `/assets/${assetId}/history`,
      {
        params: { page, limit, change_type: changeType },
      },
    );
    return response.data || (response as unknown as PaginatedResponse<AssetHistory>);
  }

  // 获取历史记录详情
  async getHistoryDetail(historyId: string): Promise<AssetHistory> {
    const response = await apiClient.get<AssetHistory>(`/history/${historyId}`);
    return response.data || (response as AssetHistory);
  }

  // 比较历史记录
  async compareHistory(historyId1: string, historyId2: string): Promise<HistoryComparisonResult> {
    const response = await apiClient.get(`/history/compare/${historyId1}/${historyId2}`);
    return response.data || response;
  }

  // 获取字段变更历史
  async getFieldHistory(
    assetId: string,
    fieldName: string,
    limit = 10,
  ): Promise<FieldHistoryRecord[]> {
    const response = await apiClient.get(`/assets/${assetId}/field-history/${fieldName}`, {
      params: { limit },
    });
    return response.data?.history || [];
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
    const response = await apiClient.get("/statistics/basic", {
      params: filters,
    });
    return response.data || response;
  }

  // 获取权属方列表
  async getOwnershipEntities(): Promise<string[]> {
    try {
      const response = await apiClient.get("/assets/ownership-entities", {
        timeout: 3000, // 3秒超时
      });
      return response.data || [];
    } catch (error) {
      throw error; // 重新抛出错误，让上层处理
    }
  }

  // 获取业态类别列表
  async getBusinessCategories(): Promise<string[]> {
    try {
      const response = await apiClient.get("/assets/business-categories", {
        timeout: 3000,
      });
      return response.data || [];
    } catch (error) {
      throw error;
    }
  }

  // 验证资产数据
  async validateAsset(data: AssetCreateRequest | AssetUpdateRequest): Promise<{
    valid: boolean;
    errors: string[];
  }> {
    try {
      await apiClient.post("/assets/validate", data);
      return {
        valid: true,
        errors: [],
      };
    } catch (error: unknown) {
      const apiError = error as ApiError;
      return {
        valid: false,
        errors: apiError.response?.data?.details?.map((d) => d.msg) || [apiError.message],
      };
    }
  }

  // 导出资产数据
  async exportAssets(filters?: AssetSearchParams, options?: ExportOptions): Promise<Blob> {
    const response = await apiClient.post("/excel/export", {
      filters,
      format: options?.format || "xlsx",
      include_headers: options?.includeHeaders !== false,
      selected_fields: options?.selectedFields,
    });
    return response.data || response;
  }

  // 导出选中的资产
  async exportSelectedAssets(assetIds: string[], options?: ExportOptions): Promise<Blob> {
    const response = await apiClient.post("/excel/export-selected", {
      asset_ids: assetIds,
      format: options?.format || "xlsx",
      include_headers: options?.includeHeaders !== false,
      selected_fields: options?.selectedFields,
    });
    return response.data || response;
  }

  // 获取导出状态
  async getExportStatus(taskId: string): Promise<ExportTask> {
    const response = await apiClient.get(`/excel/export-status/${taskId}`);
    return response.data || response;
  }

  // 获取导出历史
  async getExportHistory(): Promise<ExportTask[]> {
    const response = await apiClient.get("/excel/export-history");
    return response.data || [];
  }

  // 删除导出记录
  async deleteExportRecord(id: string): Promise<void> {
    await apiClient.delete(`/excel/export-history/${id}`);
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

  // 上传导入文件
  async uploadImportFile(file: File): Promise<ImportTask> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await apiClient.post("/excel/import", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data || response;
  }

  // 预览导入文件
  async previewImportFile(file: File): Promise<ImportPreviewResult> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await apiClient.post("/excel/preview", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data || [];
  }

  // 下载导入模板
  async downloadImportTemplate(): Promise<void> {
    const response = await apiClient.get("/excel/template", {
      responseType: "blob",
    });

    // 创建下载链接
    const blob = new Blob([response.data], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "asset_import_template.xlsx";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  // 获取导入状态
  async getImportStatus(importId: string): Promise<ImportTask> {
    const response = await apiClient.get(`/excel/import-status/${importId}`);
    return response.data || response;
  }

  // 获取导入历史
  async getImportHistory(): Promise<ImportTask[]> {
    const response = await apiClient.get("/excel/import-history");
    return response.data || [];
  }

  // 删除导入记录
  async deleteImportRecord(id: string): Promise<void> {
    await apiClient.delete(`/excel/import-history/${id}`);
  }

  // 获取出租率统计数据
  async getOccupancyRateStats(filters?: AssetSearchParams): Promise<OccupancyRateStats> {
    const response = await apiClient.get("/statistics/occupancy-rate", {
      params: filters,
    });
    return response.data || response;
  }

  // 获取资产分布统计数据
  async getAssetDistributionStats(filters?: AssetSearchParams): Promise<AssetDistributionStats> {
    const response = await apiClient.get("/statistics/asset-distribution", {
      params: filters,
    });
    return response.data || response;
  }

  // 获取面积统计数据
  async getAreaStatistics(filters?: AssetSearchParams): Promise<AreaStatistics> {
    const response = await apiClient.get("/statistics/area-statistics", {
      params: filters,
    });
    return response.data || response;
  }

  // 获取综合统计数据
  async getComprehensiveStats(filters?: AssetSearchParams): Promise<ComprehensiveStats> {
    const response = await apiClient.get("/statistics/comprehensive", {
      params: filters,
    });
    return response.data || response;
  }

  // ===== 系统字典管理 =====

  // 获取系统字典列表
  async getSystemDictionaries(dict_type?: string): Promise<SystemDictionary[]> {
    const response = await apiClient.get("/system-dictionaries", {
      params: dict_type ? { dict_type } : undefined,
    });
    return response.data || [];
  }

  // 获取单个系统字典
  async getSystemDictionary(id: string): Promise<SystemDictionary> {
    const response = await apiClient.get(`/system-dictionaries/${id}`);
    return response.data;
  }

  // 创建系统字典
  async createSystemDictionary(
    data: Omit<SystemDictionary, "id" | "created_at" | "updated_at">,
  ): Promise<SystemDictionary> {
    const response = await apiClient.post("/system-dictionaries", data);
    return response.data;
  }

  // 更新系统字典
  async updateSystemDictionary(
    id: string,
    data: Partial<SystemDictionary>,
  ): Promise<SystemDictionary> {
    const response = await apiClient.put(`/system-dictionaries/${id}`, data);
    return response.data;
  }

  // 删除系统字典
  async deleteSystemDictionary(id: string): Promise<void> {
    await apiClient.delete(`/system-dictionaries/${id}`);
  }

  // 批量更新系统字典
  async batchUpdateSystemDictionaries(
    updates: Array<{ id: string; data: Partial<SystemDictionary> }>,
  ): Promise<SystemDictionary[]> {
    const response = await apiClient.post("/system-dictionaries/batch-update", { updates });
    return response.data || [];
  }

  // 获取字典类型列表
  async getDictionaryTypes(): Promise<{ types: string[] }> {
    const response = await apiClient.get("/system-dictionaries/types/list");
    return response.data || { types: [] };
  }

  // ===== 自定义字段管理 =====

  // 获取资产自定义字段配置
  async getAssetCustomFields(assetId?: string): Promise<AssetCustomField[]> {
    const response = await apiClient.get("/asset-custom-fields", {
      params: assetId ? { asset_id: assetId } : undefined,
    });
    return response.data || [];
  }

  // 获取单个自定义字段配置
  async getAssetCustomField(id: string): Promise<AssetCustomField> {
    const response = await apiClient.get(`/asset-custom-fields/${id}`);
    return response.data;
  }

  // 创建自定义字段配置
  async createAssetCustomField(
    data: Omit<AssetCustomField, "id" | "created_at" | "updated_at">,
  ): Promise<AssetCustomField> {
    const response = await apiClient.post("/asset-custom-fields", data);
    return response.data;
  }

  // 更新自定义字段配置
  async updateAssetCustomField(
    id: string,
    data: Partial<AssetCustomField>,
  ): Promise<AssetCustomField> {
    const response = await apiClient.put(`/asset-custom-fields/${id}`, data);
    return response.data;
  }

  // 删除自定义字段配置
  async deleteAssetCustomField(id: string): Promise<void> {
    await apiClient.delete(`/asset-custom-fields/${id}`);
  }

  // 获取资产的自定义字段值
  async getAssetCustomFieldValues(assetId: string): Promise<CustomFieldValue[]> {
    const response = await apiClient.get(`/assets/${assetId}/custom-fields`);
    return response.data || [];
  }

  // 更新资产的自定义字段值
  async updateAssetCustomFieldValues(
    assetId: string,
    values: CustomFieldValue[],
  ): Promise<CustomFieldValue[]> {
    const response = await apiClient.put(`/assets/${assetId}/custom-fields`, { values });
    return response.data || [];
  }

  // 批量设置自定义字段值
  async batchSetCustomFieldValues(
    updates: Array<{ assetId: string; values: CustomFieldValue[] }>,
  ): Promise<void> {
    await apiClient.post("/assets/batch-custom-fields", { updates });
  }

  // ===== 数据字典相关的便捷方法 =====

  // 获取权属方字典
  async getOwnershipEntitiesFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries("ownership_status");
  }

  // 获取管理实体列表
  async getManagementEntities(): Promise<string[]> {
    try {
      const response = await apiClient.get<string[]>("/assets/management-entities");
      return response.data || (response as string[]);
    } catch (error) {
      console.error("获取管理实体列表失败:", error);
      return [];
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
      await apiClient.post("/asset-custom-fields/validate", {
        field_id: fieldId,
        value: value,
      });
      return { valid: true };
    } catch (error: unknown) {
      const apiError = error as ApiError;
      return {
        valid: false,
        error: error.message || "验证失败",
      };
    }
  }

  // 获取字段选项（用于下拉框等）
  async getFieldOptions(fieldType: string, category?: string): Promise<FieldOption[]> {
    const response = await apiClient.get("/field-options", {
      params: { field_type: fieldType, category },
    });
    return response.data || [];
  }
}

// 导出服务实例
export const assetService = new AssetService();
