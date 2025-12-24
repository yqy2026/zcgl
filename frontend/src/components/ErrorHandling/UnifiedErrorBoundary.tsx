/**
 * @deprecated 此组件已废弃，请使用 ErrorBoundary.tsx
 *
 * 迁移指南:
 * - 旧: import { UnifiedErrorBoundary } from '@/components/ErrorHandling/UnifiedErrorBoundary'
 * - 新: import { ErrorBoundary } from '@/components/ErrorHandling/ErrorBoundary'
 *
 * UnifiedErrorBoundary 依赖的 unifiedErrorHandler 已废弃
 * 请使用 ErrorBoundary 配合 services/errorHandler.ts 进行错误处理
 * 最后更新: 2025-12-24
 */

// 重新导出 ErrorBoundary 以保持向后兼容
export { ErrorBoundary as UnifiedErrorBoundary } from './ErrorBoundary';
export type { Props as UnifiedErrorBoundaryProps } from './ErrorBoundary';
