import { message, notification, Modal } from 'antd'
import { createLogger } from './logger'

const uxLogger = createLogger('UX')

// 用户操作记录接口
export interface UserAction {
  action: string
  timestamp: number
  data?: Record<string, unknown>
}

// 错误上下文接口
export interface ErrorContext {
  component?: string
  action?: string
  url?: string
  userAgent?: string
  userId?: string
  [key: string]: unknown
}

export interface UXConfig {
  // 全局设置
  enableErrorReporting?: boolean
  enablePerformanceMonitoring?: boolean
  enableUserFeedback?: boolean

  // 错误处理设置
  errorReportingEndpoint?: string
  maxErrorReports?: number
  errorReportingInterval?: number

  // 通知设置
  notificationPlacement?: 'topLeft' | 'topRight' | 'bottomLeft' | 'bottomRight'
  notificationDuration?: number
  maxNotifications?: number

  // 消息设置
  messageDuration?: number
  maxMessages?: number

  // 性能监控设置
  performanceThreshold?: number
  memoryThreshold?: number
}

class UXManager {
  private config: UXConfig
  private errorQueue: Error[] = []
  private performanceMetrics: Map<string, number> = new Map()
  private userActions: UserAction[] = []

  constructor(config: UXConfig = {}) {
    this.config = {
      enableErrorReporting: true,
      enablePerformanceMonitoring: true,
      enableUserFeedback: true,
      maxErrorReports: 10,
      errorReportingInterval: 5000,
      notificationPlacement: 'topRight',
      notificationDuration: 4.5,
      maxNotifications: 5,
      messageDuration: 3,
      maxMessages: 3,
      performanceThreshold: 1000,
      memoryThreshold: 100 * 1024 * 1024, // 100MB
      ...config,
    }

    this.init()
  }

  private init() {
    // 配置 Ant Design 组件
    notification.config({
      placement: this.config.notificationPlacement!,
      duration: this.config.notificationDuration!,
      maxCount: this.config.maxNotifications!,
    })

    message.config({
      duration: this.config.messageDuration!,
      maxCount: this.config.maxMessages!,
    })

    // 监听全局错误
    if (this.config.enableErrorReporting) {
      this.setupErrorHandling()
    }

    // 监听性能指标
    if (this.config.enablePerformanceMonitoring) {
      this.setupPerformanceMonitoring()
    }

    // 监听用户交互
    if (this.config.enableUserFeedback) {
      this.setupUserInteractionTracking()
    }
  }

  private setupErrorHandling() {
    // 监听未捕获的错误
    window.addEventListener('error', (event) => {
      this.handleError(new Error(event.message), {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      })
    })

    // 监听未处理的 Promise 拒绝
    window.addEventListener('unhandledrejection', (event) => {
      this.handleError(new Error(event.reason), {
        type: 'unhandledrejection',
      })
    })
  }

  private setupPerformanceMonitoring() {
    // 监听页面性能
    if ('performance' in window) {
      // 监听导航性能
      window.addEventListener('load', () => {
        setTimeout(() => {
          const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
          if (navigation !== null && navigation !== undefined) {
            this.recordPerformanceMetric('pageLoad', navigation.loadEventEnd - navigation.loadEventStart)
            this.recordPerformanceMetric('domContentLoaded', navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart)
          }
        }, 0)
      })

      // 监听资源加载性能
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.duration > this.config.performanceThreshold!) {
            this.recordPerformanceMetric(`slow_${entry.entryType}`, entry.duration)
          }
        }
      })

      observer.observe({ entryTypes: ['measure', 'navigation', 'resource'] })
    }

    // 监听内存使用
    if ('memory' in performance) {
      setInterval(() => {
        const memory = (performance as Performance & { memory?: { usedJSHeapSize: number } }).memory
        if (memory && memory.usedJSHeapSize > this.config.memoryThreshold!) {
          this.recordPerformanceMetric('highMemoryUsage', memory.usedJSHeapSize)
        }
      }, 10000) // 每10秒检查一次
    }
  }

  private setupUserInteractionTracking() {
    // 记录用户点击
    document.addEventListener('click', (event) => {
      const target = event.target as HTMLElement
      this.recordUserAction('click', {
        element: target.tagName,
        className: target.className,
        id: target.id,
        text: target.textContent?.slice(0, 50),
      })
    })

    // 记录表单提交
    document.addEventListener('submit', (event) => {
      const target = event.target as HTMLFormElement
      this.recordUserAction('formSubmit', {
        formId: target.id,
        formClass: target.className,
      })
    })
  }

  // 错误处理
  public handleError(error: Error, context?: ErrorContext) {
    uxLogger.error('UXManager caught error:', error, context)

    // 添加到错误队列
    this.errorQueue.push(error)
    if (this.errorQueue.length > this.config.maxErrorReports!) {
      this.errorQueue.shift()
    }

    // 显示用户友好的错误消息
    this.showErrorFeedbackInternal(error, context)

    // 发送错误报告
    if (this.config.errorReportingEndpoint) {
      this.sendErrorReport(error, context)
    }
  }

  private showErrorFeedbackInternal(error: Error, _context?: ErrorContext) {
    // 根据错误类型显示不同的反馈
    // Error context
    if (error.message.includes('Network')) {
      notification.error({
        message: '网络错误',
        description: '网络连接失败，请检查网络设置后重试',
      })
    } else if (error.message.includes('timeout')) {
      notification.error({
        message: '请求超时',
        description: '服务器响应时间过长，请稍后重试',
      })
    } else if (error.message.includes('permission')) {
      notification.warning({
        message: '权限不足',
        description: '您没有执行此操作的权限，请联系管理员',
      })
    } else {
      notification.error({
        message: '系统错误',
        description: '系统发生错误，请稍后重试',
      })
    }
  }

  private async sendErrorReport(error: Error, context?: ErrorContext) {
    try {
      const report = {
        message: error.message,
        stack: error.stack,
        context,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
        userId: this.getUserId(),
        sessionId: this.getSessionId(),
        performanceMetrics: Object.fromEntries(this.performanceMetrics),
        recentActions: this.userActions.slice(-10),
      }

      await fetch(this.config.errorReportingEndpoint!, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(report),
      })
    } catch (reportError) {
      uxLogger.error('Failed to send error report:', reportError as Error)
    }
  }

  // 性能监控
  public recordPerformanceMetric(name: string, value: number) {
    this.performanceMetrics.set(name, value)

    // 如果性能指标超过阈值，显示警告
    if (value > this.config.performanceThreshold!) {
      uxLogger.warn(`Performance warning: ${name} took ${value}ms`)
    }
  }

  public startPerformanceMeasure(name: string) {
    performance.mark(`${name}-start`)
  }

  public endPerformanceMeasure(name: string) {
    performance.mark(`${name}-end`)
    performance.measure(name, `${name}-start`, `${name}-end`)

    const measure = performance.getEntriesByName(name, 'measure')[0]
    if (measure !== null && measure !== undefined) {
      this.recordPerformanceMetric(name, measure.duration)
    }
  }

  // 用户行为跟踪
  public recordUserAction(action: string, data?: Record<string, unknown>) {
    this.userActions.push({
      action,
      timestamp: Date.now(),
      data,
    })

    // 保持最近100个操作
    if (this.userActions.length > 100) {
      this.userActions.shift()
    }
  }

  // 用户反馈
  public showSuccessFeedback(message: string, description?: string) {
    notification.success({
      message,
      description,
    })
  }

  public showErrorFeedback(message: string, description?: string) {
    notification.error({
      message,
      description,
    })
  }

  public showWarningFeedback(message: string, description?: string) {
    notification.warning({
      message,
      description,
    })
  }

  public showInfoFeedback(message: string, description?: string) {
    notification.info({
      message,
      description,
    })
  }

  public showConfirmDialog(options: {
    title: string
    content: string
    onOk: () => void
    onCancel?: () => void
    okText?: string
    cancelText?: string
    danger?: boolean
  }) {
    Modal.confirm({
      title: options.title,
      content: options.content,
      onOk: options.onOk,
      onCancel: options.onCancel,
      okText: (options.okText !== null && options.okText !== undefined && options.okText !== '') ? options.okText : '确定',
      cancelText: (options.cancelText !== null && options.cancelText !== undefined && options.cancelText !== '') ? options.cancelText : '取消',
      okButtonProps: options.danger ? { danger: true } : undefined,
    })
  }

  // 加载状态管理
  private loadingStates: Map<string, boolean> = new Map()

  public setLoading(key: string, loading: boolean) {
    this.loadingStates.set(key, loading)

    if (loading) {
      this.recordUserAction('startLoading', { key })
    } else {
      this.recordUserAction('endLoading', { key })
    }
  }

  public isLoading(key: string): boolean {
    return this.loadingStates.get(key) || false
  }

  public clearAllLoading() {
    this.loadingStates.clear()
  }

  // 工具方法
  private getUserId(): string {
    // 从本地存储或认证状态获取用户ID
    return localStorage.getItem('userId') || 'anonymous'
  }

  private getSessionId(): string {
    // 从会话存储获取会话ID
    let sessionId = sessionStorage.getItem('sessionId')
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      sessionStorage.setItem('sessionId', sessionId)
    }
    return sessionId
  }

  // 获取统计信息
  public getStats() {
    return {
      errorCount: this.errorQueue.length,
      performanceMetrics: Object.fromEntries(this.performanceMetrics),
      userActionCount: this.userActions.length,
      loadingStates: Object.fromEntries(this.loadingStates),
    }
  }

  // 清理资源
  public cleanup() {
    this.errorQueue = []
    this.performanceMetrics.clear()
    this.userActions = []
    this.loadingStates.clear()

    notification.destroy()
    message.destroy()
  }

  // 更新配置
  public updateConfig(newConfig: Partial<UXConfig>) {
    this.config = { ...this.config, ...newConfig }

    // 重新配置组件
    notification.config({
      placement: this.config.notificationPlacement!,
      duration: this.config.notificationDuration!,
      maxCount: this.config.maxNotifications!,
    })

    message.config({
      duration: this.config.messageDuration!,
      maxCount: this.config.maxMessages!,
    })
  }
}

// 创建全局实例
export const uxManager = new UXManager()

// 导出便捷方法
export const showSuccess = (message: string, description?: string) =>
  uxManager.showSuccessFeedback(message, description)

export const showError = (message: string, description?: string) =>
  uxManager.showErrorFeedback(message, description)

export const showWarning = (message: string, description?: string) =>
  uxManager.showWarningFeedback(message, description)

export const showInfo = (message: string, description?: string) =>
  uxManager.showInfoFeedback(message, description)

export const showConfirm = (options: Parameters<typeof uxManager.showConfirmDialog>[0]) =>
  uxManager.showConfirmDialog(options)

export const recordAction = (action: string, data?: Record<string, unknown>) =>
  uxManager.recordUserAction(action, data)

export const startMeasure = (name: string) =>
  uxManager.startPerformanceMeasure(name)

export const endMeasure = (name: string) =>
  uxManager.endPerformanceMeasure(name)

export const setLoading = (key: string, loading: boolean) =>
  uxManager.setLoading(key, loading)

export const isLoading = (key: string) =>
  uxManager.isLoading(key)

export default uxManager
