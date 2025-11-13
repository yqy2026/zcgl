/**
 * 全局Loading状态管理组件
 * 提供统一的加载状态管理，支持嵌套加载和防抖
 */

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { Spin, message } from 'antd'

// Loading状态接口
interface LoadingState {
  loading: boolean
  text?: string
  tip?: string
  delay?: number
}

// Loading上下文接口
interface LoadingContextType {
  globalLoading: LoadingState
  localLoadings: Map<string, LoadingState>
  showGlobalLoading: (state: Partial<LoadingState>) => void
  hideGlobalLoading: () => void
  showLocalLoading: (key: string, state: Partial<LoadingState>) => void
  hideLocalLoading: (key: string) => void
  withLoading: <T>(
    key: string,
    asyncFn: () => Promise<T>,
    loadingState?: Partial<LoadingState>
  ) => Promise<T>
}

// 创建Loading上下文
const LoadingContext = createContext<LoadingContextType | undefined>(undefined)

// Loading Provider组件
export const LoadingProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [globalLoading, setGlobalLoading] = useState<LoadingState>({ loading: false })
  const [localLoadings, setLocalLoadings] = useState<Map<string, LoadingState>>(new Map())

  // 显示全局Loading
  const showGlobalLoading = useCallback((state: Partial<LoadingState>) => {
    setGlobalLoading(prev => ({
      loading: true,
      text: state.text || prev.text,
      tip: state.tip || prev.tip,
      delay: state.delay || prev.delay,
    }))
  }, [])

  // 隐藏全局Loading
  const hideGlobalLoading = useCallback(() => {
    setGlobalLoading({ loading: false })
  }, [])

  // 显示局部Loading
  const showLocalLoading = useCallback((key: string, state: Partial<LoadingState>) => {
    setLocalLoadings(prev => {
      const newMap = new Map(prev)
      const current = newMap.get(key) || { loading: false }
      newMap.set(key, {
        ...current,
        ...state,
        loading: true,
      })
      return newMap
    })
  }, [])

  // 隐藏局部Loading
  const hideLocalLoading = useCallback((key: string) => {
    setLocalLoadings(prev => {
      const newMap = new Map(prev)
      const current = newMap.get(key)
      if (current) {
        newMap.set(key, { ...current, loading: false })
      }
      return newMap
    })
  }, [])

  // 带Loading的异步函数包装器
  const withLoading = useCallback(async <T,>(
    key: string,
    asyncFn: () => Promise<T>,
    loadingState?: Partial<LoadingState>
  ): Promise<T> => {
    try {
      showLocalLoading(key, loadingState || {})
      const result = await asyncFn()
      return result
    } catch (error) {
      console.error(`Error in withLoading (${key}):`, error)
      throw error
    } finally {
      hideLocalLoading(key)
    }
  }, [showLocalLoading, hideLocalLoading])

  const contextValue: LoadingContextType = {
    globalLoading,
    localLoadings,
    showGlobalLoading,
    hideGlobalLoading,
    showLocalLoading,
    hideLocalLoading,
    withLoading,
  }

  return (
    <LoadingContext.Provider value={contextValue}>
      {children}
    </LoadingContext.Provider>
  )
}

// Hook：使用Loading上下文
export const useLoading = (): LoadingContextType => {
  const context = useContext(LoadingContext)
  if (!context) {
    throw new Error('useLoading must be used within a LoadingProvider')
  }
  return context
}

// 便捷的Loading Hook
export const useGlobalLoading = () => {
  const { showGlobalLoading, hideGlobalLoading, globalLoading } = useLoading()

  return {
    loading: globalLoading.loading,
    show: showGlobalLoading,
    hide: hideGlobalLoading,
  }
}

export const useLocalLoading = (key: string) => {
  const { showLocalLoading, hideLocalLoading, localLoadings } = useLoading()

  const loading = localLoadings.get(key)?.loading || false
  const loadingState = localLoadings.get(key) || { loading: false }

  return {
    loading,
    loadingState,
    show: (state: Partial<LoadingState>) => showLocalLoading(key, state),
    hide: () => hideLocalLoading(key),
  }
}

// 全局Loading组件
export const GlobalLoadingOverlay: React.FC = () => {
  const { globalLoading } = useLoading()

  if (!globalLoading.loading) {
    return null
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
      }}
    >
      <Spin
        size="large"
        tip={globalLoading.tip || globalLoading.text || '加载中...'}
        delay={globalLoading.delay}
      />
    </div>
  )
}

// 局部Loading组件
interface LocalLoadingProps {
  loading: boolean
  children: ReactNode
  text?: string
  tip?: string
  delay?: number
  size?: 'small' | 'default' | 'large'
  className?: string
  style?: React.CSSProperties
}

export const LocalLoading: React.FC<LocalLoadingProps> = ({
  loading,
  children,
  text,
  tip,
  delay,
  size = 'default',
  className,
  style,
}) => {
  return (
    <Spin
      spinning={loading}
      tip={tip || text}
      delay={delay}
      size={size}
      className={className}
      style={style}
    >
      {children}
    </Spin>
  )
}

// Loading按钮组件
interface LoadingButtonProps {
  loading: boolean
  children: ReactNode
  onClick?: () => void | Promise<void>
  disabled?: boolean
  className?: string
  style?: React.CSSProperties
}

export const LoadingButton: React.FC<LoadingButtonProps> = ({
  loading,
  children,
  onClick,
  disabled,
  className,
  style,
}) => {
  const handleClick = useCallback(async () => {
    if (onClick && !loading) {
      try {
        await onClick()
      } catch (error) {
        console.error('LoadingButton onClick error:', error)
      }
    }
  }, [onClick, loading])

  return (
    <button
      className={className}
      style={{
        ...style,
        opacity: loading ? 0.6 : 1,
        cursor: loading ? 'not-allowed' : disabled ? 'not-allowed' : 'pointer',
      }}
      disabled={disabled || loading}
      onClick={handleClick}
    >
      {loading && (
        <span style={{ marginRight: '8px' }}>
          <Spin size="small" />
        </span>
      )}
      {children}
    </button>
  )
}

export default LoadingProvider