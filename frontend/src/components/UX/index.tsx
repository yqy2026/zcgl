// UX智能组件集合导出文件
// 包含所有用户体验优化组件

export {
  useSmartLoading,
  SmartLoadingManager,
  SmartSkeleton,
  SmartPreloader,
} from './SmartLoadingManager';
export { SmartErrorHandler, useSmartError } from './SmartErrorHandler';
export { SmartProgressProvider, useSmartProgress } from './SmartProgressTracker';
export { default as SmartFormOptimizer } from './SmartFormOptimizer';
export { useSmartInteraction, SmartInteractionExample } from './SmartInteractionManager';
export { default as SmartInteractionProvider } from './SmartInteractionManager';
export { useSmartResponse } from './SmartResponseOptimizer';
export { default as SmartResponseProvider } from './SmartResponseOptimizer';

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
  ResponseOptimizer: 'SmartResponseOptimizer',
};

export default UXComponents;
