/**
 * Asset Module Index
 * 资产服务模块入口 - 导出所有服务和类型
 */

// 导出类型定义
export * from './types';

// 导出服务类和实例
export { AssetCoreService, assetCoreService } from './assetCoreService';
export { AssetHistoryService, assetHistoryService } from './assetHistoryService';
export { AssetStatisticsService, assetStatisticsService } from './assetStatisticsService';
export { AssetImportExportService, assetImportExportService } from './assetImportExportService';
export { AssetDictionaryService, assetDictionaryService } from './assetDictionaryService';
export { AssetFieldService, assetFieldService } from './assetFieldService';
