import React, { createContext, useCallback, useContext, useState, useRef, useEffect } from 'react'
import { message, notification, Modal, Drawer, Button, Space, Typography } from 'antd'
import {
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  FullscreenOutlined,
  CompressOutlined,
  ExpandOutlined
} from '@ant-design/icons'

const { Text, Title } = Typography

export type InteractionType = 'click' | 'hover' | 'focus' | 'input' | 'scroll' | 'drag' | 'resize'
export type FeedbackType = 'success' | 'info' | 'warning' | 'error'

// 撤销/重做操作接口
interface UndoRedoAction {
  type: string
  data: unknown
  timestamp: Date
  description?: string
}
export type ActionType = 'confirm' | 'cancel' | 'retry' | 'help' | 'undo' | 'save'

interface UserBehavior {
  sessionId: string
  userId?: string
  actions: Array<{
    type: InteractionType
    element: string
    timestamp: Date
    data?: unknown
    duration?: number
  }>
  preferences: {
    theme: 'light' | 'dark'
    language: 'zh-CN' | 'en-US'
    autoSave: boolean
    notifications: boolean
    animations: boolean
    compactMode: boolean
  }
}

interface FeedbackConfig {
  type: FeedbackType
  duration?: number
  position?: 'topLeft' | 'topRight' | 'bottomLeft' | 'bottomRight' | 'top'
  message: string
  description?: string
  action?: {
    type: ActionType
    text: string
    onClick: () => void
  }
}

interface SmartInteractionManagerProps {
  children: React.ReactNode
  enableBehaviorTracking?: boolean
  enableUserPreferences?: boolean
  enableSmartNotifications?: boolean
  enableKeyboardShortcuts?: boolean
  enableUndoRedo?: boolean
}

const InteractionContext = createContext<any>(null)

export const useSmartInteraction = () => {
  const context = useContext(InteractionContext)
  if (!context) {
    throw new Error('useSmartInteraction must be used within SmartInteractionProvider')
  }
  return context
}

const SmartInteractionProvider: React.FC<SmartInteractionManagerProps> = ({
  children,
  enableBehaviorTracking = true,
  enableUserPreferences = true,
  enableSmartNotifications = true,
  enableKeyboardShortcuts = true,
  enableUndoRedo = true
}) => {
  const [userBehavior, setUserBehavior] = useState<UserBehavior>({
    sessionId: `session_${Date.now()}`,
    actions: []
  })
  const [userPreferences, setUserPreferences] = useState({
    theme: 'light',
    language: 'zh-CN',
    autoSave: true,
    notifications: true,
    animations: true,
    compactMode: false
  })
  const [undoStack, setUndoStack] = useState<UndoRedoAction[]>([])
  const [redoStack, setRedoStack] = useState<UndoRedoAction[]>([])
  const [helpDrawer, setHelpDrawer] = useState(false)
  const [shortcuts, setShortcuts] = useState<Record<string, string>>({})

  // 跟踪用户行为
  const trackInteraction = useCallback((type: InteractionType, element: string, data?: unknown, duration?: number) => {
    if (!enableBehaviorTracking) return

    const action = {
      type,
      element,
      timestamp: new Date(),
      data
    }

    if (duration) {
      setTimeout(() => {
        setUserBehavior(prev => ({
          ...prev,
          actions: [...prev.actions, { ...action, duration }]
        }))
      }, duration)
    } else {
      setUserBehavior(prev => ({
        ...prev,
        actions: [...prev.actions, action]
      }))
    }
  }, [enableBehaviorTracking])

  // 显示智能通知
  const showNotification = useCallback((config: FeedbackConfig) => {
    if (!enableSmartNotifications) return

    const configWithDefaults = {
      duration: 4500,
      position: 'topRight',
      ...config
    }

    const { type, message, description, action } = configWithDefaults

    switch (type) {
      case 'success':
        notification.success({
          message,
          description,
          btn: action?.text ? (
            <Button type="primary" size="small" onClick={action?.onClick}>
              {action.text}
            </Button>
          ) : undefined
        })
        break
      case 'error':
        notification.error({
          message,
          description,
          btn: action?.text ? (
            <Button type="primary" size="small" onClick={action?.onClick}>
              {action.text}
            </Button>
          ) : undefined
        })
        break
      case 'warning':
        notification.warning({
          message,
          description,
          btn: action?.text ? (
            <Button type="primary" size="small" onClick={action?.onClick}>
              {action.text}
            </Button>
          ) : undefined
        })
        break
      case 'info':
        notification.info({
          message,
          description,
          btn: action?.text ? (
            <Button type="primary" size="small" onClick={action?.onClick}>
              {action.text}
            </Button>
          ) : undefined
        })
        break
    }
  }, [enableSmartNotifications])

  // 键盘快捷键支持
  const setupKeyboardShortcuts = useCallback(() => {
    if (!enableKeyboardShortcuts) return

    const shortcuts = [
      { key: 'ctrl+z', description: '撤销', action: 'undo' },
      { key: 'ctrl+y', description: '重做', action: 'redo' },
      { key: 'ctrl+s', description: '保存', action: 'save' },
      { key: 'f1', description: '帮助', action: 'help' },
      { key: 'f11', description: '全屏', action: 'fullscreen' },
      { key: 'esc', description: '取消', action: 'cancel' }
    ]

    setShortcuts(shortcuts.reduce((acc, shortcut) => {
      acc[shortcut.key] = shortcut.description
      return acc
    }, {}))

    const handleKeyDown = (e: KeyboardEvent) => {
      const { ctrlKey, key, shiftKey, altKey } = e
      const combo = `${ctrlKey ? 'ctrl+' : ''}${altKey ? 'alt+' : ''}${shiftKey ? 'shift+' : ''}${key}`

      const action = shortcuts.find(s => s.key === combo)?.action
      if (action) {
        e.preventDefault()

        switch (action) {
          case 'undo':
            if (undoStack.length > 0 && enableUndoRedo) {
              setRedoStack(prev => [...prev, undoStack[undoStack.length - 1]])
              setUndoStack(prev => prev.slice(0, -1))
              showNotification({
                type: 'info',
                message: '撤销操作',
                duration: 2000
              })
            }
            break
          case 'redo':
            if (redoStack.length > 0 && enableUndoRedo) {
              setUndoStack(prev => [...prev, redoStack[redoStack.length - 1]])
              setRedoStack(prev => prev.slice(0, -1))
              showNotification({
                type: 'info',
                message: '重做操作',
                duration: 2000
              })
            }
            break
          case 'save':
            showNotification({
              type: 'success',
              message: '自动保存完成',
              duration: 2000
            })
            break
          case 'help':
            setHelpDrawer(true)
            break
          case 'fullscreen':
            if (document.fullscreenElement) {
              document.exitFullscreen()
            } else {
              document.documentElement.requestFullscreen()
            }
            break
          case 'cancel':
            // 触发取消操作
            break
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [enableKeyboardShortcuts, enableUndoRedo])

  // 自动保存
  const autoSave = useCallback(() => {
    if (!userPreferences.autoSave) return

    try {
      // 模拟自动保存逻辑
      const currentData = {
        timestamp: new Date(),
        data: '用户数据'
      }

      localStorage.setItem('autoSave', JSON.stringify(currentData))

      showNotification({
        type: 'success',
        message: '自动保存成功',
        duration: 3000
      })
    } catch (error) {
      showNotification({
        type: 'error',
        message: '自动保存失败',
        duration: 4500
      })
    }
  }, [userPreferences.autoSave])

  // 防抖操作
  const debouncedAutoSave = useCallback(() => {
    const timer = setTimeout(() => {
      autoSave()
    }, 2000) // 2秒后自动保存

    return () => {
      clearTimeout(timer)
    }
  }, [autoSave])

  // 撤销重做
  const undo = useCallback(() => {
    if (!enableUndoRedo || undoStack.length === 0) return

    setRedoStack(prev => [...prev, undoStack[undoStack.length - 1]])
    setUndoStack(prev => prev.slice(0, -1))
  }, [enableUndoRedo, undoStack])

  const redo = useCallback(() => {
    if (!enableUndoRedo || redoStack.length === 0) return

    setUndoStack(prev => [...prev, redoStack[redoStack.length - 1]])
    setRedoStack(prev => prev.slice(0, -1))
  }, [enableUndoRedo, redoStack])

  // 智能确认对话框
  const confirmAction = useCallback((config: {
    title: string
    content: string
    onConfirm: () => void
    onCancel?: () => void
    type: 'warning' | 'error' | 'info'
  }) => {
    Modal.confirm({
      title: config.title,
      content: config.content,
      okText: '确认',
      cancelText: '取消',
      okType: config.type === 'error' ? 'danger' : 'primary',
      onOk: config.onConfirm,
      onCancel: config.onCancel
    })
  }, [])

  const contextValue = {
    userBehavior,
    userPreferences,
    undoStack,
    redoStack,
    shortcuts,
    trackInteraction,
    showNotification,
    confirmAction,
    undo,
    redo,
    autoSave: debouncedAutoSave,
    setUserPreferences
  }

  // 初始化
  useEffect(() => {
    setupKeyboardShortcuts()
  }, [setupKeyboardShortcuts])

  return (
    <InteractionContext.Provider value={contextValue}>
      {children}
      <HelpDrawer visible={helpDrawer} onClose={() => setHelpDrawer(false)} />
    </InteractionContext.Provider>
  )
}

interface HelpDrawerProps {
  visible: boolean
  onClose: () => void
}

const HelpDrawer: React.FC<HelpDrawerProps> = ({ visible, onClose }) => {
  const shortcutData = [
    { key: 'ctrl+z', description: '撤销', action: '撤销最近的操作' },
    { key: 'ctrl+y', description: '重做', action: '重做撤销的操作' },
    { key: 'ctrl+s', description: '保存', action: '自动保存当前数据' },
    { key: 'f1', description: '帮助', action: '打开帮助文档' },
    { key: 'f11', description: '全屏', action: '切换全屏模式' }
  ]

  return (
    <Drawer
      title="快捷键帮助"
      placement="right"
      open={visible}
      onClose={onClose}
      width={300}
    >
      <div style={{ padding: '16px' }}>
        <Text strong>快捷键列表</Text>
        <div style={{ marginTop: '16px' }}>
          {shortcutData.map(shortcut => (
            <div key={shortcut.key} style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '8px 0',
              marginBottom: '8px',
              backgroundColor: '#f8f9fa',
              borderRadius: '4px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <Text code>{shortcut.key}</Text>
                <Text style={{ marginLeft: '8px', color: '#666' }}>
                  {shortcut.description}
                </Text>
              </div>
              <Text style={{ fontSize: '12px', color: '#999' }}>
                  {shortcut.action}
                </Text>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginTop: '24px' }}>
        <Title level={5}>其他功能</Title>
        <div style={{ marginTop: '16px' }}>
          <p>• 智能自动保存：输入数据2秒后自动保存</p>
          <p>• 撤销/重做：支持多步操作撤销重做</p>
          <p>• 智能通知：操作成功/失败自动提示</p>
          <p>• 防抖操作：避免频繁重复操作</p>
        </div>
      </div>
    </Drawer>
  )
}

// 使用示例
const SmartInteractionExample: React.FC = () => {
  const {
    showNotification,
    confirmAction,
    userPreferences,
    setUserPreferences,
    undoStack,
    redoStack
  } = useSmartInteraction()

  const handleToggleTheme = () => {
    setUserPreferences(prev => ({
      ...prev,
      theme: prev.theme === 'light' ? 'dark' : 'light'
    }))
  }

  const handleConfirmDelete = () => {
    confirmAction({
      title: '确认删除',
      content: '此操作不可撤销，确定要删除吗？',
      type: 'warning',
      onConfirm: () => {
        showNotification({
          type: 'success',
          message: '删除成功'
        })
      },
      onCancel: () => {
        showNotification({
          type: 'info',
          message: '已取消删除'
        })
      }
    })
  }

  const handleTrackClick = () => {
    // 模拟点击行为追踪
    // User clicked button
  }

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical">
        <Button onClick={() => handleToggleTheme()}>
          {userPreferences.theme === 'light' ? '🌙' : '🌙'} 切换主题
        </Button>

        <Space>
          <Button onClick={undo} disabled={undoStack.length === 0}>
            撤销 ({undoStack.length})
          </Button>
          <Button onClick={redo} disabled={redoStack.length === 0}>
            重做 ({redoStack.length})
          </Button>
        </Space>

        <Button onClick={handleConfirmDelete}>危险操作</Button>
        <Button onClick={handleTrackClick}>测试点击追踪</Button>
      </Space>

      <div style={{ marginTop: '24px' }}>
        <h4>用户偏好</h4>
        <p>主题：{userPreferences.theme}</p>
        <p>语言：{userPreferences.language}</p>
        <p>自动保存：{userPreferences.autoSave ? '启用' : '禁用'}</p>
        <p>通知：{userPreferences.notifications ? '启用' : '禁用'}</p>
      </div>
    </div>
  )
}

export default SmartInteractionProvider
export { SmartInteractionExample, SmartInteractionProvider }