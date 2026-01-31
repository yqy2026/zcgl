/**
 * ConfirmDialog 组件测试
 * 测试确认对话框组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

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

const confirmSpy = vi.fn();

// Mock Ant Design components
vi.mock('antd', () => {
  const Modal = ({
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
  );

  Modal.confirm = confirmSpy;

  return {
    Modal,
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
  };
});

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

describe('ConfirmDialog - 基础渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    confirmSpy.mockClear();
  });

  it('应该支持title与content属性', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    render(
      <ConfirmDialog
        type="warning"
        visible={true}
        title="自定义标题"
        content={<div>自定义内容</div>}
      />
    );

    expect(screen.getByText('自定义标题')).toBeInTheDocument();
    expect(screen.getByText('自定义内容')).toBeInTheDocument();
    expect(screen.getByTestId('modal')).toHaveAttribute('data-open', 'true');
  });

  it('visible为false时应该关闭对话框', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    render(<ConfirmDialog type="warning" visible={false} />);

    expect(screen.getByTestId('modal')).toHaveAttribute('data-open', 'false');
  });
});

describe('ConfirmDialog - 预设类型测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    confirmSpy.mockClear();
  });

  it.each([
    ['delete', '确认删除', '删除'],
    ['edit', '确认编辑', '继续编辑'],
    ['save', '确认保存', '保存'],
    ['logout', '确认退出', '退出'],
    ['cancel', '确认取消', '确认取消'],
    ['warning', '警告', '确定'],
    ['info', '提示', '确定'],
  ])('type=%s 应该显示默认标题与按钮文案', async (type, title, okText) => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    render(<ConfirmDialog type={type as any} visible={true} />);

    expect(screen.getByText(title)).toBeInTheDocument();
    expect(screen.getByTestId('ok-button')).toHaveTextContent(okText);
  });
});

describe('ConfirmDialog - 回调与配置测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    confirmSpy.mockClear();
  });

  it('点击确定应该触发onConfirm', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    const handleConfirm = vi.fn();
    render(<ConfirmDialog type="delete" visible={true} onConfirm={handleConfirm} />);

    fireEvent.click(screen.getByTestId('ok-button'));
    expect(handleConfirm).toHaveBeenCalledTimes(1);
  });

  it('点击取消应该触发onCancel', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    const handleCancel = vi.fn();
    render(<ConfirmDialog type="warning" visible={true} onCancel={handleCancel} />);

    fireEvent.click(screen.getByTestId('cancel-button'));
    expect(handleCancel).toHaveBeenCalledTimes(1);
  });

  it('应该支持按钮与对话框配置', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    render(
      <ConfirmDialog
        type="warning"
        visible={true}
        confirmText="确认"
        cancelText="放弃"
        confirmLoading={true}
        danger={true}
        width={600}
        centered={false}
        maskClosable={true}
      />
    );

    expect(screen.getByTestId('ok-button')).toHaveTextContent('确认');
    expect(screen.getByTestId('cancel-button')).toHaveTextContent('放弃');
    expect(screen.getByTestId('ok-button')).toHaveAttribute('data-danger', 'true');
    expect(screen.getByTestId('modal')).toHaveAttribute('data-confirm-loading', 'true');
    expect(screen.getByTestId('modal')).toHaveAttribute('data-width', '600');
    expect(screen.getByTestId('modal')).toHaveAttribute('data-centered', 'false');
    expect(screen.getByTestId('modal')).toHaveAttribute('data-mask-closable', 'true');
  });
});

describe('ConfirmDialog - 内容渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    confirmSpy.mockClear();
  });

  it('delete类型应显示itemName与itemCount信息', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    render(
      <ConfirmDialog type="delete" visible={true} itemName="测试项目" itemCount={2} />
    );

    expect(screen.getByText('确定要删除这 2 个测试项目吗？')).toBeInTheDocument();
  });

  it('details应渲染在内容区域', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    render(
      <ConfirmDialog type="save" visible={true} details={['更改1', '更改2']} />
    );

    expect(screen.getByText('更改1')).toBeInTheDocument();
    expect(screen.getByText('更改2')).toBeInTheDocument();
  });
});

describe('ConfirmDialog - 预设组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    confirmSpy.mockClear();
  });

  it('DeleteConfirmDialog应该正确渲染', async () => {
    const { DeleteConfirmDialog } = await import('../ConfirmDialog');
    render(<DeleteConfirmDialog visible={true} />);
    expect(screen.getByText('确认删除')).toBeInTheDocument();
  });

  it('SaveConfirmDialog应该正确渲染', async () => {
    const { SaveConfirmDialog } = await import('../ConfirmDialog');
    render(<SaveConfirmDialog visible={true} />);
    expect(screen.getByText('确认保存')).toBeInTheDocument();
  });
});

describe('ConfirmDialog - 便捷方法测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    confirmSpy.mockClear();
  });

  it('showDeleteConfirm应该调用Modal.confirm并返回Promise', async () => {
    const { showDeleteConfirm } = await import('../ConfirmDialog');
    const result = showDeleteConfirm({ title: '删除标题' });

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(result).toBeInstanceOf(Promise);
  });

  it('showSaveConfirm应该调用Modal.confirm并返回Promise', async () => {
    const { showSaveConfirm } = await import('../ConfirmDialog');
    const result = showSaveConfirm({ title: '保存标题' });

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(result).toBeInstanceOf(Promise);
  });
});
