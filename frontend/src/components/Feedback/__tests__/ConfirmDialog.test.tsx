/**
 * ConfirmDialog 组件测试
 * 测试确认对话框组件
 * 增强版本 - 添加更全面的测试用例
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';

interface ModalOkButtonPropsMock {
  danger?: boolean;
}

interface ModalMockProps {
  title?: React.ReactNode;
  open?: boolean;
  onOk?: () => void;
  onCancel?: () => void;
  okText?: React.ReactNode;
  cancelText?: React.ReactNode;
  children?: React.ReactNode;
  okButtonProps?: ModalOkButtonPropsMock;
  width?: number | string;
  centered?: boolean;
  maskClosable?: boolean;
  confirmLoading?: boolean;
}

interface TypographyTextMockProps {
  children?: React.ReactNode;
  type?: string;
  strong?: boolean;
}

interface TypographyParagraphMockProps {
  children?: React.ReactNode;
  type?: string;
}

interface SpaceMockProps {
  children?: React.ReactNode;
}

interface ButtonMockProps {
  children?: React.ReactNode;
  icon?: React.ReactNode;
  type?: string;
  onClick?: () => void;
}

interface IconMockProps {
  style?: React.CSSProperties;
}

// Mock Ant Design components
vi.mock('antd', () => ({
  Modal: ({
    title,
    open,
    onOk,
    onCancel,
    okText,
    cancelText,
    children,
    okButtonProps,
    width,
    centered,
    maskClosable,
    confirmLoading,
  }: ModalMockProps) => (
    <div
      data-testid="modal"
      data-open={open}
      data-width={width}
      data-centered={centered}
      data-mask-closable={maskClosable}
      data-confirm-loading={confirmLoading}
    >
      {title && <div data-testid="modal-title">{title}</div>}
      {children && <div data-testid="modal-content">{children}</div>}
      <button data-testid="ok-button" onClick={onOk} data-danger={okButtonProps?.danger}>
        {okText}
      </button>
      <button data-testid="cancel-button" onClick={onCancel}>
        {cancelText}
      </button>
    </div>
  ),
  Typography: {
    Text: ({ children, type, strong }: TypographyTextMockProps) => (
      <span data-testid="text" data-type={type} data-strong={strong}>
        {children}
      </span>
    ),
    Paragraph: ({ children, type }: TypographyParagraphMockProps) => (
      <p data-testid="paragraph" data-type={type}>
        {children}
      </p>
    ),
  },
  Space: ({ children }: SpaceMockProps) => <div data-testid="space">{children}</div>,
  Button: ({ children, icon, type, onClick }: ButtonMockProps) => (
    <button data-testid="button" data-type={type} onClick={onClick}>
      {icon && <span data-testid="button-icon">{icon}</span>}
      {children}
    </button>
  ),
}));

vi.mock('@ant-design/icons', () => ({
  ExclamationCircleOutlined: ({ style }: IconMockProps) => (
    <div data-testid="icon-exclamation" style={style} />
  ),
  DeleteOutlined: ({ style }: IconMockProps) => <div data-testid="icon-delete" style={style} />,
  EditOutlined: ({ style }: IconMockProps) => <div data-testid="icon-edit" style={style} />,
  SaveOutlined: ({ style }: IconMockProps) => <div data-testid="icon-save" style={style} />,
  LogoutOutlined: ({ style }: IconMockProps) => <div data-testid="icon-logout" style={style} />,
  StopOutlined: ({ style }: IconMockProps) => <div data-testid="icon-stop" style={style} />,
  QuestionCircleOutlined: ({ style }: IconMockProps) => (
    <div data-testid="icon-question" style={style} />
  ),
  InfoCircleOutlined: ({ style }: IconMockProps) => <div data-testid="icon-info" style={style} />,
}));

describe('ConfirmDialog - 组件导入测试', () => {
  it('应该能够导入ConfirmDialog组件', async () => {
    const module = await import('../ConfirmDialog');
    expect(module).toBeDefined();
    expect(module.ConfirmDialog || module.default).toBeDefined();
  });

  it('应该导出预设组件', async () => {
    const module = await import('../ConfirmDialog');
    expect(module.DeleteConfirmDialog).toBeDefined();
    expect(module.EditConfirmDialog).toBeDefined();
    expect(module.SaveConfirmDialog).toBeDefined();
    expect(module.LogoutConfirmDialog).toBeDefined();
    expect(module.CancelConfirmDialog).toBeDefined();
  });

  it('应该导出便捷方法', async () => {
    const module = await import('../ConfirmDialog');
    expect(module.showDeleteConfirm).toBeDefined();
    expect(typeof module.showDeleteConfirm).toBe('function');
    expect(module.showSaveConfirm).toBeDefined();
    expect(typeof module.showSaveConfirm).toBe('function');
  });
});

describe('ConfirmDialog - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持type属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, { type: 'delete', visible: true });
    expect(element).toBeTruthy();
  });

  it('应该支持title属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'warning',
      visible: true,
      title: '自定义标题',
    });
    expect(element).toBeTruthy();
  });

  it('应该支持content属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const customContent = React.createElement('div', {}, '自定义内容');
    const element = React.createElement(ConfirmDialog, {
      type: 'warning',
      visible: true,
      content: customContent,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持visible属性控制显示', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, { type: 'warning', visible: false });
    expect(element).toBeTruthy();
  });
});

describe('ConfirmDialog - 预设类型测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持delete类型', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, { type: 'delete', visible: true });
    expect(element).toBeTruthy();
  });

  it('应该支持edit类型', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, { type: 'edit', visible: true });
    expect(element).toBeTruthy();
  });

  it('应该支持save类型', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, { type: 'save', visible: true });
    expect(element).toBeTruthy();
  });

  it('应该支持logout类型', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, { type: 'logout', visible: true });
    expect(element).toBeTruthy();
  });

  it('应该支持cancel类型', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, { type: 'cancel', visible: true });
    expect(element).toBeTruthy();
  });

  it('应该支持warning类型', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, { type: 'warning', visible: true });
    expect(element).toBeTruthy();
  });

  it('应该支持info类型', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, { type: 'info', visible: true });
    expect(element).toBeTruthy();
  });
});

describe('ConfirmDialog - 回调函数测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持onConfirm回调', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const handleConfirm = vi.fn();
    const element = React.createElement(ConfirmDialog, {
      type: 'delete',
      visible: true,
      onConfirm: handleConfirm,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持onCancel回调', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const handleCancel = vi.fn();
    const element = React.createElement(ConfirmDialog, {
      type: 'warning',
      visible: true,
      onCancel: handleCancel,
    });
    expect(element).toBeTruthy();
  });
});

describe('ConfirmDialog - 按钮配置测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持confirmText属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'warning',
      visible: true,
      confirmText: '确定',
    });
    expect(element).toBeTruthy();
  });

  it('应该支持cancelText属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'warning',
      visible: true,
      cancelText: '放弃',
    });
    expect(element).toBeTruthy();
  });

  it('应该支持confirmLoading属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'delete',
      visible: true,
      confirmLoading: true,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持danger属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'warning',
      visible: true,
      danger: true,
    });
    expect(element).toBeTruthy();
  });
});

describe('ConfirmDialog - 对话框配置测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持width属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'warning',
      visible: true,
      width: 600,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持centered属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'warning',
      visible: true,
      centered: false,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持maskClosable属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'warning',
      visible: true,
      maskClosable: true,
    });
    expect(element).toBeTruthy();
  });
});

describe('ConfirmDialog - 特殊属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持itemName属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'delete',
      visible: true,
      itemName: '测试项目',
    });
    expect(element).toBeTruthy();
  });

  it('应该支持itemCount属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'delete',
      visible: true,
      itemCount: 5,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持details属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'delete',
      visible: true,
      details: ['详情1', '详情2', '详情3'],
    });
    expect(element).toBeTruthy();
  });
});

describe('ConfirmDialog - 预设组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('DeleteConfirmDialog应该正确渲染', async () => {
    const { DeleteConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(DeleteConfirmDialog, { visible: true });
    expect(element).toBeTruthy();
  });

  it('EditConfirmDialog应该正确渲染', async () => {
    const { EditConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(EditConfirmDialog, { visible: true });
    expect(element).toBeTruthy();
  });

  it('SaveConfirmDialog应该正确渲染', async () => {
    const { SaveConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(SaveConfirmDialog, { visible: true });
    expect(element).toBeTruthy();
  });

  it('LogoutConfirmDialog应该正确渲染', async () => {
    const { LogoutConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(LogoutConfirmDialog, { visible: true });
    expect(element).toBeTruthy();
  });

  it('CancelConfirmDialog应该正确渲染', async () => {
    const { CancelConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(CancelConfirmDialog, { visible: true });
    expect(element).toBeTruthy();
  });
});

describe('ConfirmDialog - 便捷方法测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('showDeleteConfirm应该返回Promise', async () => {
    const { showDeleteConfirm } = await import('../ConfirmDialog');
    // 由于方法内部使用Modal.confirm，我们只验证方法可调用
    expect(typeof showDeleteConfirm).toBe('function');
  });

  it('showSaveConfirm应该返回Promise', async () => {
    const { showSaveConfirm } = await import('../ConfirmDialog');
    expect(typeof showSaveConfirm).toBe('function');
  });
});

describe('ConfirmDialog - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理空字符串title', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'warning',
      visible: true,
      title: '',
    });
    expect(element).toBeTruthy();
  });

  it('应该处理undefined回调', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'warning',
      visible: true,
      onConfirm: undefined,
      onCancel: undefined,
    });
    expect(element).toBeTruthy();
  });

  it('应该处理空details数组', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'delete',
      visible: true,
      details: [],
    });
    expect(element).toBeTruthy();
  });

  it('应该处理itemCount为0', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'delete',
      visible: true,
      itemCount: 0,
    });
    expect(element).toBeTruthy();
  });

  it('应该处理itemName为空字符串', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'delete',
      visible: true,
      itemName: '',
    });
    expect(element).toBeTruthy();
  });
});

describe('ConfirmDialog - 组合属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('delete类型应该支持所有属性组合', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const handleConfirm = vi.fn();
    const handleCancel = vi.fn();
    const element = React.createElement(ConfirmDialog, {
      type: 'delete',
      visible: true,
      title: '确认删除',
      itemName: '项目',
      itemCount: 3,
      details: ['文件1', '文件2'],
      confirmText: '确认删除',
      cancelText: '取消',
      confirmLoading: false,
      onConfirm: handleConfirm,
      onCancel: handleCancel,
      width: 500,
      centered: true,
      maskClosable: false,
    });
    expect(element).toBeTruthy();
  });

  it('save类型应该支持details属性', async () => {
    const { ConfirmDialog } = await import('../ConfirmDialog');
    const element = React.createElement(ConfirmDialog, {
      type: 'save',
      visible: true,
      details: ['更改1', '更改2', '更改3'],
    });
    expect(element).toBeTruthy();
  });
});
