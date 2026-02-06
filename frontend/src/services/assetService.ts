/**
 * Asset Service - Legacy Compatibility Layer
 * 资产服务 - 向后兼容层
 *
 * 此文件现在作为聚合导出和向后兼容层。
 * 新代码应该直接从 './asset' 模块导入特定服务。
 *
 * @example
 * // 新代码推荐方式：
 * import { assetCoreService } from '@/services/asset';
 *
 * // 旧代码仍然支持：
 * import { assetService } from '@/services/assetService';
 */

// Re-export all types for backward compatibility
export * from './asset/types';

// Re-export individual services
export {
  AssetCoreService,
  assetCoreService,
  AssetHistoryService,
  assetHistoryService,
  AssetStatisticsService,
  assetStatisticsService,
  AssetImportExportService,
  assetImportExportService,
  AssetDictionaryService,
  assetDictionaryService,
  AssetFieldService,
  assetFieldService,
} from './asset';

// Import services for delegation
import { assetCoreService } from './asset/assetCoreService';
import { assetHistoryService } from './asset/assetHistoryService';
import { assetStatisticsService } from './asset/assetStatisticsService';
import { assetImportExportService } from './asset/assetImportExportService';
import { assetDictionaryService } from './asset/assetDictionaryService';
import { assetFieldService } from './asset/assetFieldService';

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
  PaginatedApiResponse,
  AssetStats,
  OccupancyRateStats,
  AssetDistributionStats,
  AreaStatistics,
  ComprehensiveStats,
  ExportTask,
  ExportOptions,
  ImportTask,
  ImportPreviewResult,
  HistoryComparisonResult,
  FieldHistoryRecord,
  AssetSearchFilters,
  FieldOption,
  FieldValidationResult,
} from './asset/types';

/**
 * 资产服务类 - Legacy Facade
 *
 * 此类现在作为向后兼容层，将方法调用委托给各个专门服务。
 * 新代码应直接使用各个服务实例，如 assetCoreService。
 *
 * @deprecated 推荐使用各个专门服务：assetCoreService, assetHistoryService 等
 */
export class AssetService {
  // ===== Core CRUD Operations =====

  async getAssets(params?: AssetSearchParams): Promise<AssetListResponse> {
    return assetCoreService.getAssets(params);
  }

  async getAllAssets(params?: Omit<AssetSearchParams, 'page' | 'page_size'>): Promise<Asset[]> {
    return assetCoreService.getAllAssets(params);
  }

  async getAssetsByIds(
    ids: string[],
    options?: { includeRelations?: boolean }
  ): Promise<Asset[]> {
    return assetCoreService.getAssetsByIds(ids, options);
  }

  async getAsset(id: string): Promise<Asset> {
    return assetCoreService.getAsset(id);
  }

  async createAsset(data: AssetCreateRequest): Promise<Asset> {
    return assetCoreService.createAsset(data);
  }

  async updateAsset(id: string, data: AssetUpdateRequest): Promise<Asset> {
    return assetCoreService.updateAsset(id, data);
  }

  async deleteAsset(id: string): Promise<void> {
    return assetCoreService.deleteAsset(id);
  }

  async restoreAsset(id: string): Promise<Asset> {
    return assetCoreService.restoreAsset(id);
  }

  async hardDeleteAsset(id: string): Promise<void> {
    return assetCoreService.hardDeleteAsset(id);
  }

  async deleteAssets(ids: string[]): Promise<void> {
    return assetCoreService.deleteAssets(ids);
  }

  async searchAssets(query: string, filters?: AssetSearchFilters): Promise<AssetListResponse> {
    return assetCoreService.searchAssets(query, filters);
  }

  async validateAsset(
    data: AssetCreateRequest | AssetUpdateRequest
  ): Promise<{ valid: boolean; errors: string[] }> {
    return assetCoreService.validateAsset(data);
  }

  async getOwnershipEntities(): Promise<Array<{ value: string; label: string }>> {
    return assetCoreService.getOwnershipEntities();
  }

  async getBusinessCategories(): Promise<string[]> {
    return assetCoreService.getBusinessCategories();
  }

  async getManagementEntities(): Promise<string[]> {
    return assetCoreService.getManagementEntities();
  }

  // ===== History Operations =====

  async getAssetHistory(
    assetId: string,
    page?: number,
    page_size?: number,
    changeType?: string
  ): Promise<PaginatedApiResponse<AssetHistory>> {
    return assetHistoryService.getAssetHistory(assetId, page, page_size, changeType);
  }

  async getHistoryDetail(historyId: string): Promise<AssetHistory> {
    return assetHistoryService.getHistoryDetail(historyId);
  }

  async compareHistory(historyId1: string, historyId2: string): Promise<HistoryComparisonResult> {
    return assetHistoryService.compareHistory(historyId1, historyId2);
  }

  async getFieldHistory(
    assetId: string,
    fieldName: string,
    page_size?: number
  ): Promise<FieldHistoryRecord[]> {
    return assetHistoryService.getFieldHistory(assetId, fieldName, page_size);
  }

  // ===== Statistics Operations =====

  async getAssetStats(filters?: AssetSearchParams): Promise<AssetStats> {
    return assetStatisticsService.getAssetStats(filters);
  }

  async getOccupancyRateStats(filters?: AssetSearchParams): Promise<OccupancyRateStats> {
    return assetStatisticsService.getOccupancyRateStats(filters);
  }

  async getAssetDistributionStats(filters?: AssetSearchParams): Promise<AssetDistributionStats> {
    return assetStatisticsService.getAssetDistributionStats(filters);
  }

  async getAreaStatistics(filters?: AssetSearchParams): Promise<AreaStatistics> {
    return assetStatisticsService.getAreaStatistics(filters);
  }

  async getComprehensiveStats(filters?: AssetSearchParams): Promise<ComprehensiveStats> {
    return assetStatisticsService.getComprehensiveStats(filters);
  }

  // ===== Import/Export Operations =====

  async exportAssets(filters?: AssetSearchParams, options?: ExportOptions): Promise<Blob> {
    return assetImportExportService.exportAssets(filters, options);
  }

  async exportSelectedAssets(assetIds: string[], options?: ExportOptions): Promise<Blob> {
    return assetImportExportService.exportSelectedAssets(assetIds, options);
  }

  async getExportStatus(taskId: string): Promise<ExportTask> {
    return assetImportExportService.getExportStatus(taskId);
  }

  async getExportHistory(): Promise<ExportTask[]> {
    return assetImportExportService.getExportHistory();
  }

  async deleteExportRecord(id: string): Promise<void> {
    return assetImportExportService.deleteExportRecord(id);
  }

  async downloadExportFile(downloadUrl: string): Promise<void> {
    return assetImportExportService.downloadExportFile(downloadUrl);
  }

  async uploadImportFile(file: File): Promise<ImportTask> {
    return assetImportExportService.uploadImportFile(file);
  }

  async previewImportFile(file: File): Promise<ImportPreviewResult> {
    return assetImportExportService.previewImportFile(file);
  }

  async downloadImportTemplate(): Promise<void> {
    return assetImportExportService.downloadImportTemplate();
  }

  async getImportStatus(importId: string): Promise<ImportTask> {
    return assetImportExportService.getImportStatus(importId);
  }

  async getImportHistory(): Promise<ImportTask[]> {
    return assetImportExportService.getImportHistory();
  }

  async deleteImportRecord(id: string): Promise<void> {
    return assetImportExportService.deleteImportRecord(id);
  }

  // ===== Dictionary Operations =====

  async getSystemDictionaries(dict_type?: string): Promise<SystemDictionary[]> {
    return assetDictionaryService.getSystemDictionaries(dict_type);
  }

  async getSystemDictionary(id: string): Promise<SystemDictionary> {
    return assetDictionaryService.getSystemDictionary(id);
  }

  async createSystemDictionary(
    data: Omit<SystemDictionary, 'id' | 'created_at' | 'updated_at'>
  ): Promise<SystemDictionary> {
    return assetDictionaryService.createSystemDictionary(data);
  }

  async updateSystemDictionary(
    id: string,
    data: Partial<SystemDictionary>
  ): Promise<SystemDictionary> {
    return assetDictionaryService.updateSystemDictionary(id, data);
  }

  async deleteSystemDictionary(id: string): Promise<void> {
    return assetDictionaryService.deleteSystemDictionary(id);
  }

  async batchUpdateSystemDictionaries(
    updates: Array<{ id: string; data: Partial<SystemDictionary> }>
  ): Promise<SystemDictionary[]> {
    return assetDictionaryService.batchUpdateSystemDictionaries(updates);
  }

  async getDictionaryTypes(): Promise<{ types: string[] }> {
    return assetDictionaryService.getDictionaryTypes();
  }

  async getOwnershipEntitiesFromDict(): Promise<SystemDictionary[]> {
    return assetDictionaryService.getOwnershipEntitiesFromDict();
  }

  async getManagementEntitiesFromDict(): Promise<SystemDictionary[]> {
    return assetDictionaryService.getManagementEntitiesFromDict();
  }

  async getBusinessCategoriesFromDict(): Promise<SystemDictionary[]> {
    return assetDictionaryService.getBusinessCategoriesFromDict();
  }

  async getAssetStatusFromDict(): Promise<SystemDictionary[]> {
    return assetDictionaryService.getAssetStatusFromDict();
  }

  async getOwnershipNatureFromDict(): Promise<SystemDictionary[]> {
    return assetDictionaryService.getOwnershipNatureFromDict();
  }

  async getLeaseStatusFromDict(): Promise<SystemDictionary[]> {
    return assetDictionaryService.getLeaseStatusFromDict();
  }

  // ===== Custom Field Operations =====

  async getAssetCustomFields(assetId?: string): Promise<AssetCustomField[]> {
    return assetFieldService.getAssetCustomFields(assetId);
  }

  async getAssetCustomField(id: string): Promise<AssetCustomField> {
    return assetFieldService.getAssetCustomField(id);
  }

  async createAssetCustomField(
    data: Omit<AssetCustomField, 'id' | 'created_at' | 'updated_at'>
  ): Promise<AssetCustomField> {
    return assetFieldService.createAssetCustomField(data);
  }

  async updateAssetCustomField(
    id: string,
    data: Partial<AssetCustomField>
  ): Promise<AssetCustomField> {
    return assetFieldService.updateAssetCustomField(id, data);
  }

  async deleteAssetCustomField(id: string): Promise<void> {
    return assetFieldService.deleteAssetCustomField(id);
  }

  async getAssetCustomFieldValues(assetId: string): Promise<CustomFieldValue[]> {
    return assetFieldService.getAssetCustomFieldValues(assetId);
  }

  async updateAssetCustomFieldValues(
    assetId: string,
    values: CustomFieldValue[]
  ): Promise<CustomFieldValue[]> {
    return assetFieldService.updateAssetCustomFieldValues(assetId, values);
  }

  async batchSetCustomFieldValues(
    updates: Array<{ assetId: string; values: CustomFieldValue[] }>
  ): Promise<void> {
    return assetFieldService.batchSetCustomFieldValues(updates);
  }

  async validateCustomFieldValue(fieldId: string, value: unknown): Promise<FieldValidationResult> {
    return assetFieldService.validateCustomFieldValue(fieldId, value);
  }

  async getFieldOptions(fieldType: string, category?: string): Promise<FieldOption[]> {
    return assetFieldService.getFieldOptions(fieldType, category);
  }
}

// 导出服务实例 - 向后兼容
export const assetService = new AssetService();
