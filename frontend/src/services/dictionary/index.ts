/**
 * 统一字典服务入口 - 再导出中心
 *
 * @description 整合基础功能和管理功能，提供简化的使用接口和向后兼容性。
 *              所有实现已拆分至子模块，此文件仅负责再导出以保持向后兼容。
 * @author Claude Code
 */

// ── 子模块全量再导出 ──────────────────────────────────────────
export * from './config';
export * from './base';
export * from './manager';
export * from './operations';
export * from './unified';

// ── 显式类型再导出（向后兼容，确保 named type import 可用）────
export type { DictionaryConfig, DictionaryOption } from './config';

export type { DictionaryServiceResult, DictionaryStatistics, PreloadResult } from './base';

export type {
  EnumFieldType,
  CreateEnumFieldValueRequest,
  UpdateEnumFieldValueRequest,
} from './manager';

export type { DictionaryStats, DictionaryOperationResult } from './operations';

// ── 默认导出（向后兼容）──────────────────────────────────────
export { default } from './unified';
