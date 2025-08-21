// 用户体验相关配置

export const UX_CONFIG = {
  // 加载状态配置
  loading: {
    // 最小显示时间（毫秒），避免闪烁
    minDisplayTime: 300,
    // 延迟显示时间（毫秒），避免短时间操作显示加载
    delayTime: 200,
    // 默认加载文本
    defaultText: '加载中...',
  },

  // 通知配置
  notification: {
    // 默认显示时间（秒）
    duration: 4.5,
    // 最大显示数量
    maxCount: 5,
    // 默认位置
    placement: 'topRight' as const,
  },

  // 消息配置
  message: {
    // 默认显示时间（秒）
    duration: 3,
    // 最大显示数量
    maxCount: 3,
  },

  // 自动保存配置
  autoSave: {
    // 自动保存间隔（毫秒）
    interval: 30000, // 30秒
    // 是否启用自动保存
    enabled: true,
    // 保存成功提示
    showSuccessMessage: true,
  },

  // 性能监控配置
  performance: {
    // 是否启用性能监控
    enabled: process.env.NODE_ENV === 'development',
    // 性能警告阈值（毫秒）
    warningThreshold: 1000,
    // API请求超时时间（毫秒）
    apiTimeout: 30000,
  },

  // 错误处理配置
  error: {
    // 是否显示详细错误信息（仅开发环境）
    showDetails: process.env.NODE_ENV === 'development',
    // 是否自动报告错误
    autoReport: true,
    // 重试配置
    retry: {
      // 最大重试次数
      maxAttempts: 3,
      // 重试延迟（毫秒）
      delay: 1000,
      // 是否使用指数退避
      exponentialBackoff: true,
    },
  },

  // 防抖和节流配置
  debounce: {
    // 搜索防抖延迟（毫秒）
    search: 300,
    // 表单输入防抖延迟（毫秒）
    input: 500,
    // 窗口大小调整防抖延迟（毫秒）
    resize: 250,
  },

  throttle: {
    // 滚动节流延迟（毫秒）
    scroll: 100,
    // 鼠标移动节流延迟（毫秒）
    mousemove: 50,
  },

  // 动画配置
  animation: {
    // 是否启用动画
    enabled: true,
    // 动画持续时间（毫秒）
    duration: 300,
    // 缓动函数
    easing: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },

  // 响应式断点
  breakpoints: {
    xs: 480,
    sm: 576,
    md: 768,
    lg: 992,
    xl: 1200,
    xxl: 1600,
  },

  // 键盘快捷键
  shortcuts: {
    // 保存：Ctrl+S
    save: { key: 's', ctrl: true },
    // 搜索：Ctrl+F
    search: { key: 'f', ctrl: true },
    // 刷新：F5
    refresh: { key: 'F5' },
    // 返回：Esc
    back: { key: 'Escape' },
    // 新建：Ctrl+N
    new: { key: 'n', ctrl: true },
    // 编辑：Ctrl+E
    edit: { key: 'e', ctrl: true },
    // 删除：Delete
    delete: { key: 'Delete' },
  },

  // 表单配置
  form: {
    // 验证触发方式
    validateTrigger: 'onChange' as const,
    // 是否保留验证状态
    preserve: false,
    // 滚动到错误字段
    scrollToFirstError: true,
  },

  // 表格配置
  table: {
    // 默认页面大小
    defaultPageSize: 20,
    // 页面大小选项
    pageSizeOptions: ['10', '20', '50', '100'],
    // 是否显示快速跳转
    showQuickJumper: true,
    // 是否显示总数
    showTotal: true,
  },

  // 上传配置
  upload: {
    // 最大文件大小（MB）
    maxSize: 10,
    // 支持的文件类型
    acceptTypes: ['.xlsx', '.xls', '.csv', '.pdf', '.jpg', '.png'],
    // 是否支持拖拽上传
    dragUpload: true,
  },

  // 缓存配置
  cache: {
    // API缓存时间（毫秒）
    apiCacheTime: 5 * 60 * 1000, // 5分钟
    // 静态资源缓存时间（毫秒）
    staticCacheTime: 24 * 60 * 60 * 1000, // 24小时
  },
}

// 获取配置值的辅助函数
export const getUXConfig = <T>(path: string, defaultValue?: T): T => {
  const keys = path.split('.')
  let value: any = UX_CONFIG

  for (const key of keys) {
    if (value && typeof value === 'object' && key in value) {
      value = value[key]
    } else {
      return defaultValue as T
    }
  }

  return value as T
}

// 更新配置的辅助函数
export const updateUXConfig = (path: string, value: any) => {
  const keys = path.split('.')
  let target: any = UX_CONFIG

  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i]
    if (!(key in target) || typeof target[key] !== 'object') {
      target[key] = {}
    }
    target = target[key]
  }

  target[keys[keys.length - 1]] = value
}

export default UX_CONFIG