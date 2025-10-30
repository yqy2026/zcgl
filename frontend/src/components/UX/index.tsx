// UX智能组件集合导出文件
// 包含所有用户体验优化组件

export { SmartLoadingProvider, useSmartLoading, SmartSkeleton, SmartPreloader } from './SmartLoadingManager'
export { SmartErrorHandler, useSmartError, ErrorProvider } from './SmartErrorHandler'
export { SmartProgressProvider, useSmartProgress, ProgressTrackersList } from './SmartProgressTracker'
export { SmartFormOptimizer, SmartFormExample } from './SmartFormOptimizer'
export { SmartInteractionProvider, useSmartInteraction, SmartInteractionExample, HelpDrawer } from './SmartInteractionManager'
export { SmartResponseProvider, useSmartResponse, ResponseOptimizationDashboard } from './SmartResponseOptimizer'

// 主要UX组件包
export const UXComponents = {
  // 智能加载管理器
  Loading: 'SmartLoadingManager',

  // 智能错误处理器
  ErrorHandler: 'SmartErrorHandler',

  // 智能进度跟踪器
  ProgressTracker: 'SmartProgressTracker',

  // 智能表单优化器
  FormOptimizer: 'SmartFormOptimizer',

  // 智能交互管理器
  InteractionManager: 'SmartInteractionManager',

  // 智能响应优化器
  ResponseOptimizer: 'SmartResponseOptimizer'
}

export default UXComponents