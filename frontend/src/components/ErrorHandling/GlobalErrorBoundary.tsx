/**
 * @deprecated 此组件已废弃，请使用 ErrorBoundary.tsx
 *
 * 迁移指南:
 * - 旧: import { GlobalErrorBoundary } from '@/components/ErrorHandling/GlobalErrorBoundary'
 * - 新: import { ErrorBoundary } from '@/components/ErrorHandling/ErrorBoundary'
 *
 * GlobalErrorBoundary 的错误追踪和报告功能已集成到 ErrorBoundary 中
 * 最后更新: 2025-12-24
 */

// 重新导出 ErrorBoundary 以保持向后兼容
export { ErrorBoundary as GlobalErrorBoundary } from './ErrorBoundary';
export type { Props as GlobalErrorBoundaryProps } from './ErrorBoundary';
