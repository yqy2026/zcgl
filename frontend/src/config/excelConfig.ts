/**
 * Excel导入导出配置常量
 */

// 统一的工作簿名称
export const STANDARD_SHEET_NAME = '土地物业资产数据';

// Excel文件相关配置
export const EXCEL_CONFIG = {
  sheetName: STANDARD_SHEET_NAME,
  maxFileSize: 10 * 1024 * 1024, // 10MB
  allowedExtensions: ['.xlsx', '.xls'],
  contentTypes: [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
  ],
};

// 导入配置
export const IMPORT_CONFIG = {
  batchSize: 100,
  skipErrors: false,
  timeout: 300000, // 5分钟超时
};

// 导出配置
export const EXPORT_CONFIG = {
  maxRecords: 1000,
  includeHeaders: true,
  dateFormat: 'YYYY-MM-DD HH:mm:ss',
};

// 导入说明
export const IMPORT_INSTRUCTIONS = [
  '请先下载Excel模板，按照模板格式填写数据',
  '支持的文件格式：.xlsx, .xls',
  '文件大小限制：10MB以内',
  '请确保数据格式正确，避免导入失败',
  `工作表名称必须为："${STANDARD_SHEET_NAME}"`,
  '必填字段：权属方、物业名称、地址、确权状态、物业性质、使用状态',
];
