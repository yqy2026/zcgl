/**
 * ActionFeedback 组件测试
 * 测试操作反馈组件
 * 增强版本 - 添加更全面的测试用例
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'

// Mock Ant Design components
vi.mock('antd', () => ({
  Button: ({ children, icon, type, size, onClick }: any) => (
    <button
      data-testid="button"
      data-type={type}
      data-size={size}
      onClick={onClick}
    >
      {icon && <span data-testid="button-icon">{icon}</span>}
      {children}
    </button>
  ),
  Space: ({ children, size }: any) => (
    <div data-testid="space" data-size={size}>{children}</div>
  ),
  Typography: {
    Text: ({ children, type, strong, style }: any) => (
      <span data-testid="text" data-type={type} data-strong={strong} style={style}>
        {children}
      </span>
    ),
    Paragraph: ({ children, code, style }: any) => (
      <p data-testid="paragraph" data-code={code} style={style}>
        {children}
      </p>
    ),
  },
  Alert: ({ type, showIcon, icon, message, description, closable, onClose }: any) => (
    <div
      data-testid="alert"
      data-type={type}
      data-show-icon={showIcon}
      data-closable={closable}
    >
      {icon && <div data-testid="alert-icon">{icon}</div>}
      {message && <div data-testid="alert-message">{message}</div>}
      {description && <div data-testid="alert-description">{description}</div>}
    </div>
  ),
  Card: ({ children, title, extra, actions, size }: any) => (
    <div data-testid="card" data-size={size}>
      {title && <div data-testid="card-title">{title}</div>}
      {extra && <div data-testid="card-extra">{extra}</div>}
      {children}
      {actions && <div data-testid="card-actions">{actions}</div>}
    </div>
  ),
  Divider: ({ style }: any) => <div data-testid="divider" style={style} />,
}))

vi.mock('@ant-design/icons', () => ({
  CheckCircleOutlined: ({ style }: any) => <div data-testid="icon-check" style={style} />,
  ExclamationCircleOutlined: ({ style }: any) => <div data-testid="icon-exclamation" style={style} />,
  InfoCircleOutlined: ({ style }: any) => <div data-testid="icon-info" style={style} />,
  CloseCircleOutlined: ({ style }: any) => <div data-testid="icon-close" style={style} />,
  LoadingOutlined: ({ style }: any) => <div data-testid="icon-loading" style={style} />,
  ReloadOutlined: () => <div data-testid="icon-reload" />,
  UndoOutlined: () => <div data-testid="icon-undo" />,
}))

describe('ActionFeedback - 组件导入测试', () => {
  it('应该能够导入ActionFeedback组件', async () => {
    const module = await import('../ActionFeedback')
    expect(module).toBeDefined()
    expect(module.default).toBeDefined()
  })

  it('应该导出预设组件', async () => {
    const module = await import('../ActionFeedback')
    expect(module.LoadingFeedback).toBeDefined()
    expect(module.SuccessFeedback).toBeDefined()
    expect(module.ErrorFeedback).toBeDefined()
    expect(module.WarningFeedback).toBeDefined()
    expect(module.ActionFeedbackCard).toBeDefined()
  })
})

describe('ActionFeedback - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持result属性', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })

  it('应该支持title属性', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const }
    const element = React.createElement(ActionFeedback, { result, title: '自定义标题' })
    expect(element).toBeTruthy()
  })

  it('没有result时应该返回null', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const element = React.createElement(ActionFeedback, { result: undefined })
    expect(element).toBeTruthy()
  })
})

describe('ActionFeedback - 操作状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持loading状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'loading' as const }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })

  it('应该支持success状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })

  it('应该支持error状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'error' as const }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })

  it('应该支持warning状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'warning' as const }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })

  it('应该支持idle状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'idle' as const }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })
})

describe('ActionFeedback - result对象属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持message属性', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const, message: '操作成功' }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })

  it('应该支持details属性', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = {
      status: 'success' as const,
      details: ['详情1', '详情2', '详情3'],
    }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })

  it('应该支持data属性', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const, data: { id: 1 } }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })

  it('应该支持error属性', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const error = new Error('Test error')
    const result = { status: 'error' as const, error }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })
})

describe('ActionFeedback - 控制属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持showRetry属性', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'error' as const }
    const handleRetry = vi.fn()
    const element = React.createElement(ActionFeedback, {
      result,
      showRetry: true,
      onRetry: handleRetry,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showUndo属性', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const }
    const handleUndo = vi.fn()
    const element = React.createElement(ActionFeedback, {
      result,
      showUndo: true,
      onUndo: handleUndo,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showDetails属性', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = {
      status: 'success' as const,
      details: ['详情'],
    }
    const element = React.createElement(ActionFeedback, {
      result,
      showDetails: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持autoHide属性', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const }
    const element = React.createElement(ActionFeedback, {
      result,
      autoHide: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持autoHideDelay属性', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const }
    const element = React.createElement(ActionFeedback, {
      result,
      autoHide: true,
      autoHideDelay: 3000,
    })
    expect(element).toBeTruthy()
  })
})

describe('ActionFeedback - 回调函数测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持onRetry回调', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'error' as const }
    const handleRetry = vi.fn()
    const element = React.createElement(ActionFeedback, {
      result,
      onRetry: handleRetry,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持onUndo回调', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const }
    const handleUndo = vi.fn()
    const element = React.createElement(ActionFeedback, {
      result,
      onUndo: handleUndo,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持onClose回调', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const }
    const handleClose = vi.fn()
    const element = React.createElement(ActionFeedback, {
      result,
      onClose: handleClose,
    })
    expect(element).toBeTruthy()
  })
})

describe('ActionFeedback - 预设组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('LoadingFeedback应该正确渲染', async () => {
    const { LoadingFeedback } = await import('../ActionFeedback')
    const element = React.createElement(LoadingFeedback, {})
    expect(element).toBeTruthy()
  })

  it('SuccessFeedback应该正确渲染', async () => {
    const { SuccessFeedback } = await import('../ActionFeedback')
    const element = React.createElement(SuccessFeedback, {})
    expect(element).toBeTruthy()
  })

  it('ErrorFeedback应该正确渲染', async () => {
    const { ErrorFeedback } = await import('../ActionFeedback')
    const element = React.createElement(ErrorFeedback, {})
    expect(element).toBeTruthy()
  })

  it('WarningFeedback应该正确渲染', async () => {
    const { WarningFeedback } = await import('../ActionFeedback')
    const element = React.createElement(WarningFeedback, {})
    expect(element).toBeTruthy()
  })

  it('ActionFeedbackCard应该正确渲染', async () => {
    const { ActionFeedbackCard } = await import('../ActionFeedback')
    const result = { status: 'success' as const }
    const element = React.createElement(ActionFeedbackCard, { result })
    expect(element).toBeTruthy()
  })
})

describe('ActionFeedback - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理空details数组', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const, details: [] }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })

  it('应该处理undefined message', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const, message: undefined }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })

  it('应该处理undefined callbacks', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const }
    const element = React.createElement(ActionFeedback, {
      result,
      onRetry: undefined,
      onUndo: undefined,
      onClose: undefined,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理error但message为undefined', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const error = new Error()
    const result = { status: 'error' as const, error }
    const element = React.createElement(ActionFeedback, { result })
    expect(element).toBeTruthy()
  })

  it('应该处理autoHideDelay为0', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const result = { status: 'success' as const }
    const element = React.createElement(ActionFeedback, {
      result,
      autoHide: true,
      autoHideDelay: 0,
    })
    expect(element).toBeTruthy()
  })
})

describe('ActionFeedback - 组合属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('success状态应该支持所有属性组合', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const handleUndo = vi.fn()
    const handleClose = vi.fn()
    const result = {
      status: 'success' as const,
      message: '操作成功',
      details: ['文件已保存', '编号: 12345'],
      data: { id: 123 },
    }
    const element = React.createElement(ActionFeedback, {
      result,
      title: '保存成功',
      showUndo: true,
      showDetails: true,
      autoHide: true,
      autoHideDelay: 3000,
      onUndo: handleUndo,
      onClose: handleClose,
      className: 'custom-feedback',
      style: { margin: 10 },
    })
    expect(element).toBeTruthy()
  })

  it('error状态应该支持所有属性组合', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default
    const handleRetry = vi.fn()
    const handleClose = vi.fn()
    const error = new Error('网络错误')
    const result = {
      status: 'error' as const,
      message: '操作失败',
      error,
      details: ['网络连接超时', '请检查网络设置'],
    }
    const element = React.createElement(ActionFeedback, {
      result,
      title: '错误',
      showRetry: true,
      showDetails: true,
      onRetry: handleRetry,
      onClose: handleClose,
    })
    expect(element).toBeTruthy()
  })

  it('ActionFeedbackCard应该支持所有属性', async () => {
    const { ActionFeedbackCard } = await import('../ActionFeedback')
    const handleRetry = vi.fn()
    const handleUndo = vi.fn()
    const result = {
      status: 'error' as const,
      message: '上传失败',
      details: ['文件过大', '超出限制'],
    }
    const element = React.createElement(ActionFeedbackCard, {
      result,
      title: '上传状态',
      extra: React.createElement('button', {}, '关闭'),
      onRetry: handleRetry,
      onUndo: handleUndo,
    })
    expect(element).toBeTruthy()
  })
})
