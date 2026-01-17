import { useState, useEffect, useCallback, useRef } from 'react'
import { MessageManager } from '@/utils/messageManager'
import SuccessNotification from '@/components/Feedback/SuccessNotification'
import { createLogger } from '@/utils/logger'

const uxLogger = createLogger('UserExperience')

interface UseUserExperienceOptions {
  enableAutoSave?: boolean
  autoSaveInterval?: number
  enableOfflineDetection?: boolean
  enablePerformanceMonitoring?: boolean
}

export const useUserExperience = (options: UseUserExperienceOptions = {}) => {
  const {
    enableAutoSave = false,
    autoSaveInterval = 30000, // 30秒
    enableOfflineDetection = true,
    enablePerformanceMonitoring = true,
  } = options

  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [isLoading, setIsLoading] = useState(false)
  const [loadingText, setLoadingText] = useState('')
  const [progress, setProgress] = useState(0)
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null)
  const performanceRef = useRef<{ [key: string]: number }>({})

  // 网络状态监听
  useEffect(() => {
    if (!enableOfflineDetection) return

    const handleOnline = () => {
      setIsOnline(true)
      SuccessNotification.notify({
        type: 'success',
        title: '网络已连接',
        description: '网络连接已恢复正常',
        duration: 3,
      })
    }

    const handleOffline = () => {
      setIsOnline(false)
      SuccessNotification.notify({
        type: 'warning',
        title: '网络已断开',
        description: '请检查网络连接，部分功能可能无法使用',
        duration: 0, // 不自动关闭
      })
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [enableOfflineDetection])

  // 性能监控
  const startPerformanceTimer = useCallback((key: string) => {
    if (!enablePerformanceMonitoring) return

    performanceRef.current[key] = performance.now()
  }, [enablePerformanceMonitoring])

  const endPerformanceTimer = useCallback((key: string, threshold: number = 1000) => {
    if (!enablePerformanceMonitoring || !performanceRef.current[key]) return

    const duration = performance.now() - performanceRef.current[key]
    delete performanceRef.current[key]

    // 如果操作时间超过阈值，记录性能问题
    if (duration > threshold) {
      uxLogger.warn(`Performance warning: ${key} took ${duration.toFixed(2)}ms`)

      // 可以发送性能数据到监控服务
      reportPerformance(key, duration)
    }

    return duration
  }, [enablePerformanceMonitoring])

  // 自动保存功能
  const startAutoSave = useCallback((saveFunction: () => Promise<void>) => {
    if (!enableAutoSave) return

    if (autoSaveTimerRef.current) {
      clearInterval(autoSaveTimerRef.current)
    }

    autoSaveTimerRef.current = setInterval(async () => {
      try {
        await saveFunction()
        MessageManager.success('数据已自动保存')
      } catch (error) {
        uxLogger.error('Auto save failed:', error as Error)
      }
    }, autoSaveInterval)
  }, [enableAutoSave, autoSaveInterval])

  const stopAutoSave = useCallback(() => {
    if (autoSaveTimerRef.current) {
      clearInterval(autoSaveTimerRef.current)
      autoSaveTimerRef.current = null
    }
  }, [])

  // 加载状态管理
  const showLoading = useCallback((text: string = '加载中...') => {
    setIsLoading(true)
    setLoadingText(text)
    setProgress(0)
  }, [])

  const hideLoading = useCallback(() => {
    setIsLoading(false)
    setLoadingText('')
    setProgress(0)
  }, [])

  const updateProgress = useCallback((value: number) => {
    setProgress(Math.max(0, Math.min(100, value)))
  }, [])

  // 防抖函数
  const debounce = useCallback(<T extends (...args: unknown[]) => ReturnType<T>>(
    func: T,
    delay: number
  ): ((...args: Parameters<T>) => void) => {
    let timeoutId: NodeJS.Timeout

    return (...args: Parameters<T>) => {
      clearTimeout(timeoutId)
      timeoutId = setTimeout(() => func(...args), delay)
    }
  }, [])

  // 节流函数
  const throttle = useCallback(<T extends (...args: unknown[]) => ReturnType<T>>(
    func: T,
    delay: number
  ): ((...args: Parameters<T>) => void) => {
    let lastCall = 0

    return (...args: Parameters<T>) => {
      const now = Date.now()
      if (now - lastCall >= delay) {
        lastCall = now
        func(...args)
      }
    }
  }, [])

  // 异步操作包装器
  const withLoadingState = useCallback(async <T>(
    operation: () => Promise<T>,
    loadingText: string = '处理中...'
  ): Promise<T> => {
    showLoading(loadingText)
    try {
      const result = await operation()
      return result
    } finally {
      hideLoading()
    }
  }, [showLoading, hideLoading])

  // 页面可见性检测
  const [isPageVisible, setIsPageVisible] = useState(!document.hidden)

  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsPageVisible(!document.hidden)
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  // 清理函数
  useEffect(() => {
    return () => {
      stopAutoSave()
    }
  }, [stopAutoSave])

  return {
    // 网络状态
    isOnline,

    // 加载状态
    isLoading,
    loadingText,
    progress,
    showLoading,
    hideLoading,
    updateProgress,

    // 性能监控
    startPerformanceTimer,
    endPerformanceTimer,

    // 自动保存
    startAutoSave,
    stopAutoSave,

    // 工具函数
    debounce,
    throttle,
    withLoadingState,

    // 页面状态
    isPageVisible,
  }
}

// 键盘快捷键 Hook
export const useKeyboardShortcut = (
  key: string,
  callback: () => void,
  modifiers: { ctrl?: boolean; alt?: boolean; shift?: boolean } = {}
) => {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const { ctrl = false, alt = false, shift = false } = modifiers

      if (
        event.key.toLowerCase() === key.toLowerCase() &&
        event.ctrlKey === ctrl &&
        event.altKey === alt &&
        event.shiftKey === shift
      ) {
        event.preventDefault()
        callback()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [key, callback, modifiers])
}

// 性能数据报告
const reportPerformance = (_operation: string, _duration: number) => {
  // 这里可以发送性能数据到监控服务
  try {
    // 示例：发送到后端API
    // fetch('/api/performance', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({
    //     operation,
    //     duration,
    //     timestamp: new Date().toISOString(),
    //     userAgent: navigator.userAgent,
    //     url: window.location.href,
    //   }),
    // }).catch(console.error)
  } catch (error) {
    uxLogger.error('Failed to report performance:', error as Error)
  }
}

export default useUserExperience
