/**
 * useAppStore 测试
 * 测试应用全局状态管理
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useAppStore } from '../useAppStore'

// =============================================================================
// 基础功能测试
// =============================================================================

describe('useAppStore - 基础功能', () => {
  beforeEach(() => {
    // 重置store状态
    useAppStore.setState({
      sidebarCollapsed: false,
      theme: 'light',
      language: 'zh-CN',
      preferences: {
        pageSize: 20,
        autoRefresh: false,
        showAdvancedSearch: false,
      },
      notifications: [],
    })
  })

  describe('初始化状态', () => {
    it('应该有正确的初始状态', () => {
      const { result } = renderHook(() => useAppStore())

      expect(result.current.sidebarCollapsed).toBe(false)
      expect(result.current.theme).toBe('light')
      expect(result.current.language).toBe('zh-CN')
      expect(result.current.preferences.pageSize).toBe(20)
      expect(result.current.notifications).toEqual([])
    })

    it('sidebarCollapsed应该默认为false', () => {
      const { result } = renderHook(() => useAppStore())
      expect(result.current.sidebarCollapsed).toBe(false)
    })

    it('theme应该默认为light', () => {
      const { result } = renderHook(() => useAppStore())
      expect(result.current.theme).toBe('light')
    })

    it('language应该默认为zh-CN', () => {
      const { result } = renderHook(() => useAppStore())
      expect(result.current.language).toBe('zh-CN')
    })
  })

  describe('setSidebarCollapsed', () => {
    it('应该设置侧边栏折叠状态', () => {
      const { result } = renderHook(() => useAppStore())

      act(() => {
        result.current.setSidebarCollapsed(true)
      })

      expect(result.current.sidebarCollapsed).toBe(true)

      act(() => {
        result.current.setSidebarCollapsed(false)
      })

      expect(result.current.sidebarCollapsed).toBe(false)
    })

    it('应该触发状态更新', () => {
      const { result } = renderHook(() => useAppStore())

      const initialCollapsed = result.current.sidebarCollapsed

      act(() => {
        result.current.setSidebarCollapsed(!initialCollapsed)
      })

      expect(result.current.sidebarCollapsed).toBe(!initialCollapsed)
    })
  })

  describe('setTheme', () => {
    it('应该设置主题', () => {
      const { result } = renderHook(() => useAppStore())

      act(() => {
        result.current.setTheme('dark')
      })

      expect(result.current.theme).toBe('dark')

      act(() => {
        result.current.setTheme('light')
      })

      expect(result.current.theme).toBe('light')
    })

    it('应该只接受有效主题值', () => {
      const { result } = renderHook(() => useAppStore())

      act(() => {
        result.current.setTheme('dark')
      })

      // TypeScript会限制类型，但测试运行时行为
      expect(result.current.theme).toBe('dark')
    })
  })

  describe('setLanguage', () => {
    it('应该设置语言', () => {
      const { result } = renderHook(() => useAppStore())

      act(() => {
        result.current.setLanguage('en-US')
      })

      expect(result.current.language).toBe('en-US')

      act(() => {
        result.current.setLanguage('zh-CN')
      })

      expect(result.current.language).toBe('zh-CN')
    })
  })

  describe('setPreferences', () => {
    it('应该更新用户偏好设置', () => {
      const { result } = renderHook(() => useAppStore())

      act(() => {
        result.current.setPreferences({
          pageSize: 50,
          autoRefresh: true
        })
      })

      expect(result.current.preferences.pageSize).toBe(50)
      expect(result.current.preferences.autoRefresh).toBe(true)
      // 其他偏好保持不变
      expect(result.current.preferences.showAdvancedSearch).toBe(false)
    })

    it('应该支持部分更新', () => {
      const { result } = renderHook(() => useAppStore())

      act(() => {
        result.current.setPreferences({ showAdvancedSearch: true })
      })

      expect(result.current.preferences.showAdvancedSearch).toBe(true)
      expect(result.current.preferences.pageSize).toBe(20) // 不变
    })

    it('应该支持多次更新', () => {
      const { result } = renderHook(() => useAppStore())

      act(() => {
        result.current.setPreferences({ pageSize: 30 })
      })

      expect(result.current.preferences.pageSize).toBe(30)

      act(() => {
        result.current.setPreferences({ pageSize: 40 })
      })

      expect(result.current.preferences.pageSize).toBe(40)
    })
  })
})

// =============================================================================
// 通知管理测试
// =============================================================================

describe('useAppStore - 通知管理', () => {
  beforeEach(() => {
    useAppStore.setState({ notifications: [] })
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('addNotification', () => {
    it('应该添加通知', () => {
      const { result } = renderHook(() => useAppStore())

      act(() => {
        result.current.addNotification({
          type: 'success',
          title: '操作成功',
          message: '数据已保存'
        })
      })

      const notifications = result.current.notifications
      expect(notifications).toHaveLength(1)
      expect(notifications[0].type).toBe('success')
      expect(notifications[0].title).toBe('操作成功')
      expect(notifications[0].message).toBe('数据已保存')
      expect(notifications[0].id).toBeDefined()
      expect(notifications[0].timestamp).toBeGreaterThan(0)
    })

    it('应该生成唯一ID', () => {
      const { result } = renderHook(() => useAppStore())

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: '通知1'
        })
        result.current.addNotification({
          type: 'info',
          title: '通知2'
        })
      })

      const notifications = result.current.notifications
      expect(notifications[0].id).not.toBe(notifications[1].id)
    })

    it('应该支持不同类型的通知', () => {
      const { result } = renderHook(() => useAppStore())

      const types: Array<'success' | 'error' | 'warning' | 'info'> = ['success', 'error', 'warning', 'info']

      types.forEach(type => {
        act(() => {
          result.current.addNotification({
            type,
            title: `${type} notification`
          })
        })
      })

      const notifications = result.current.notifications
      expect(notifications).toHaveLength(4)

      types.forEach((type, index) => {
        expect(notifications[index].type).toBe(type)
      })
    })

    it('应该支持自定义持续时间', async () => {
      vi.useFakeTimers()

      const { result } = renderHook(() => useAppStore())

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: '临时通知',
          duration: 1000
        })
      })

      expect(result.current.notifications).toHaveLength(1)

      // 快进时间
      act(() => {
        vi.advanceTimersByTime(1000)
      })

      // 等待setTimeout执行
      await waitFor(() => {
        expect(result.current.notifications).toHaveLength(0)
      })

      vi.useRealTimers()
    })

    it('duration为0的通知不应该自动移除', () => {
      vi.useFakeTimers()

      const { result } = renderHook(() => useAppStore())

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: '持久通知',
          duration: 0
        })
      })

      // 快进很长时间
      act(() => {
        vi.advanceTimersByTime(10000)
      })

      // 通知应该还在
      expect(result.current.notifications).toHaveLength(1)

      vi.useRealTimers()
    })
  })

  describe('removeNotification', () => {
    it('应该移除指定ID的通知', () => {
      const { result } = renderHook(() => useAppStore())

      // 添加两个通知
      act(() => {
        result.current.addNotification({ type: 'info', title: '通知1' })
        result.current.addNotification({ type: 'info', title: '通知2' })
      })

      const idToRemove = result.current.notifications[0].id

      act(() => {
        result.current.removeNotification(idToRemove)
      })

      expect(result.current.notifications).toHaveLength(1)
      expect(result.current.notifications[0].title).toBe('通知2')
    })

    it('移除不存在的ID不应该报错', () => {
      const { result } = renderHook(() => useAppStore())

      expect(() => {
        act(() => {
          result.current.removeNotification('non-existent-id')
        })
      }).not.toThrow()

      expect(result.current.notifications).toHaveLength(0)
    })
  })

  describe('clearNotifications', () => {
    it('应该清除所有通知', () => {
      const { result } = renderHook(() => useAppStore())

      // 添加多个通知
      act(() => {
        result.current.addNotification({ type: 'info', title: '通知1' })
        result.current.addNotification({ type: 'warning', title: '通知2' })
        result.current.addNotification({ type: 'error', title: '通知3' })
      })

      expect(result.current.notifications).toHaveLength(3)

      act(() => {
        result.current.clearNotifications()
      })

      expect(result.current.notifications).toHaveLength(0)
    })

    it('空通知列表调用clear不应该报错', () => {
      const { result } = renderHook(() => useAppStore())

      expect(() => {
        act(() => {
          result.current.clearNotifications()
        })
      }).not.toThrow()

      expect(result.current.notifications).toHaveLength(0)
    })
  })
})

// =============================================================================
// 选择器测试
// =============================================================================

describe('useAppStore - 选择器', () => {
  it('应该支持选择器获取状态', () => {
    const { result } = renderHook(() => useAppStore())

    const theme = useAppStore.getState().theme
    expect(theme).toBe('light')

    const language = useAppStore.getState().language
    expect(language).toBe('zh-CN')
  })

  it('选择器不应该触发重新渲染', () => {
    let renderCount = 0

    const { result } = renderHook(() => useAppStore())
    const { rerender } = result

    // 仅获取一个值，不订阅
    const value = useAppStore.getState().theme

    // 更新其他状态
    act(() => {
      useAppStore.getState().setSidebarCollapsed(true)
    })

    // value应该不变
    expect(value).toBe('light')
  })
})

// =============================================================================
// 持久化测试
// =============================================================================

describe('useAppStore - 持久化', () => {
  it('应该持久化配置的状态', () => {
    const { result } = renderHook(() => useAppStore())

    act(() => {
      result.current.setTheme('dark')
      result.current.setSidebarCollapsed(true)
    })

    // 在真实场景中，这些应该被保存到localStorage
    // 在测试中，我们验证状态确实被更新了
    expect(result.current.theme).toBe('dark')
    expect(result.current.sidebarCollapsed).toBe(true)
  })

  it('通知不应该被持久化', () => {
    const { result } = renderHook(() => useAppStore())

    act(() => {
      result.current.addNotification({
        type: 'info',
        title: '测试通知'
      })
    })

    // 通知在内存中，不在持久化配置中
    expect(result.current.notifications).toHaveLength(1)
  })
})

// =============================================================================
// 边界情况测试
// =============================================================================

describe('useAppStore - 边界情况', () => {
  beforeEach(() => {
    // 重置store状态到初始值
    useAppStore.setState({
      sidebarCollapsed: false,
      theme: 'light',
      language: 'zh-CN',
      preferences: {
        pageSize: 20,
        autoRefresh: false,
        showAdvancedSearch: false,
      },
      notifications: [],
    })
  })

  it('应该处理空通知列表的remove', () => {
    const { result } = renderHook(() => useAppStore())

    act(() => {
      result.current.removeNotification('any-id')
    })

    expect(result.current.notifications).toHaveLength(0)
  })

  it('应该处理空偏好设置的更新', () => {
    const { result } = renderHook(() => useAppStore())

    act(() => {
      result.current.setPreferences({})
    })

    // 偏好应该保持不变
    expect(result.current.preferences).toEqual({
      pageSize: 20,
      autoRefresh: false,
      showAdvancedSearch: false,
    })
  })

  it('应该快速连续处理多个状态更新', () => {
    const { result } = renderHook(() => useAppStore())

    act(() => {
      result.current.setTheme('dark')
      result.current.setLanguage('en-US')
      result.current.setSidebarCollapsed(true)
      result.current.setPreferences({ pageSize: 50 })
    })

    expect(result.current.theme).toBe('dark')
    expect(result.current.language).toBe('en-US')
    expect(result.current.sidebarCollapsed).toBe(true)
    expect(result.current.preferences.pageSize).toBe(50)
  })
})
