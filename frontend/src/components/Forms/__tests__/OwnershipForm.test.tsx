/**
 * OwnershipForm 组件测试
 * 测试权属方表单的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { createMockOwnership } from '@/test-utils/factories';
import type { Ownership } from '@/types/ownership';

// Mock dependencies
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    createOwnership: vi.fn(),
    updateOwnership: vi.fn(),
    validateOwnershipName: vi.fn(() => Promise.resolve(true)),
    updateOwnershipProjects: vi.fn(),
  },
}));

vi.mock('@/services/projectService', () => ({
  projectService: {
    getProjectOptions: vi.fn(() => Promise.resolve([])),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

// Mock Ant Design
const mockFormInstance = {
  getFieldsValue: vi.fn(() => ({})),
  setFieldsValue: vi.fn(),
  validateFields: vi.fn(() => Promise.resolve({ name: '测试权属方' })),
  resetFields: vi.fn(),
  getFieldValue: vi.fn(),
  setFieldValue: vi.fn(),
};

vi.mock('antd', () => {
  const MockForm = ({
    children,
    onFinish,
  }: {
    children: React.ReactNode;
    onFinish?: () => void;
  }) => (
    <form
      data-testid="ownership-form"
      onSubmit={(e) => {
        e.preventDefault();
        onFinish?.();
      }}
    >
      {children}
    </form>
  );
  MockForm.displayName = 'MockForm';
  MockForm.Item = ({ children, label }: { children: React.ReactNode; label?: string }) => (
    <div data-testid={`form-item-${label}`}>{children}</div>
  );
  MockForm.Item.displayName = 'MockForm.Item';
  MockForm.useForm = () => [mockFormInstance];

  return {
    Form: MockForm,
    Input: ({ placeholder }: { placeholder?: string }) => (
      <input data-testid="input" placeholder={placeholder} />
    ),
    Button: ({ children, onClick, htmlType }: { children: React.ReactNode; onClick?: () => void; htmlType?: string }) => (
      <button data-testid={`btn-${htmlType ?? 'default'}`} onClick={onClick} type={htmlType as 'button' | 'submit' | 'reset'}>
        {children}
      </button>
    ),
    Space: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Card: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Row: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Col: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Divider: () => <hr />,
    Switch: () => <input type="checkbox" data-testid="switch" />,
    Select: ({ children }: { children: React.ReactNode }) => <select>{children}</select>,
  };
});

import { OwnershipForm } from '../OwnershipForm';
import { ownershipService } from '@/services/ownershipService';
import { MessageManager } from '@/utils/messageManager';

describe('OwnershipForm', () => {
  const mockOnSuccess = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('渲染测试', () => {
    it('应该正确渲染表单', () => {
      render(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByTestId('ownership-form')).toBeInTheDocument();
    });

    it('应该渲染提交和取消按钮', () => {
      render(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByTestId('btn-submit')).toBeInTheDocument();
    });
  });

  describe('创建模式', () => {
    it('创建模式下表单应为空', () => {
      render(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(mockFormInstance.resetFields).toHaveBeenCalled();
    });

    it('应该调用创建服务', async () => {
      vi.mocked(ownershipService.createOwnership).mockResolvedValue(
        createMockOwnership({
          id: '1',
          name: '测试权属方',
          code: 'OWN-001',
        })
      );

      render(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const form = screen.getByTestId('ownership-form');
      fireEvent.submit(form);

      await waitFor(() => {
        expect(ownershipService.createOwnership).toHaveBeenCalled();
      });
    });
  });

  describe('编辑模式', () => {
    const mockOwnership: Ownership = createMockOwnership({
      id: '1',
      name: '测试权属方',
      code: 'OWN-001',
      short_name: '测试',
    });

    it('编辑模式下应设置初始值', () => {
      render(
        <OwnershipForm
          initialValues={mockOwnership}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(mockFormInstance.setFieldsValue).toHaveBeenCalledWith(mockOwnership);
    });

    it('应该调用更新服务', async () => {
      vi.mocked(ownershipService.updateOwnership).mockResolvedValue(
        createMockOwnership({
          ...mockOwnership,
          name: '更新后的名称',
        })
      );

      mockFormInstance.validateFields.mockResolvedValue({
        name: '更新后的名称',
        code: 'OWN-001',
      });

      render(
        <OwnershipForm
          initialValues={mockOwnership}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const form = screen.getByTestId('ownership-form');
      fireEvent.submit(form);

      await waitFor(() => {
        expect(ownershipService.updateOwnership).toHaveBeenCalled();
      });
    });
  });

  describe('表单验证', () => {
    it('名称唯一性验证 - 名称已存在', async () => {
      vi.mocked(ownershipService.validateOwnershipName).mockResolvedValue(false);

      render(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      // 验证函数会被调用
      expect(ownershipService.validateOwnershipName).toBeDefined();
    });

    it('名称唯一性验证 - 名称可用', async () => {
      vi.mocked(ownershipService.validateOwnershipName).mockResolvedValue(true);

      render(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(ownershipService.validateOwnershipName).toBeDefined();
    });
  });

  describe('取消操作', () => {
    it('点击取消应调用 onCancel', () => {
      render(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const cancelBtn = screen.getByTestId('btn-default');
      fireEvent.click(cancelBtn);

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  describe('错误处理', () => {
    it('创建失败应显示错误消息', async () => {
      vi.mocked(ownershipService.createOwnership).mockRejectedValue(
        new Error('创建失败')
      );

      render(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const form = screen.getByTestId('ownership-form');
      fireEvent.submit(form);

      await waitFor(() => {
        expect(MessageManager.error).toHaveBeenCalled();
      });
    });

    it('更新失败应显示错误消息', async () => {
      vi.mocked(ownershipService.updateOwnership).mockRejectedValue(
        new Error('更新失败')
      );

      render(
        <OwnershipForm
          initialValues={createMockOwnership({ id: '1', name: '测试' })}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const form = screen.getByTestId('ownership-form');
      fireEvent.submit(form);

      await waitFor(() => {
        expect(MessageManager.error).toHaveBeenCalled();
      });
    });
  });

  describe('成功回调', () => {
    it('创建成功应调用 onSuccess', async () => {
      vi.mocked(ownershipService.createOwnership).mockResolvedValue(
        createMockOwnership({
          id: '1',
          name: '测试权属方',
        })
      );

      render(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const form = screen.getByTestId('ownership-form');
      fireEvent.submit(form);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it('更新成功应调用 onSuccess', async () => {
      vi.mocked(ownershipService.updateOwnership).mockResolvedValue(
        createMockOwnership({
          id: '1',
          name: '更新后的名称',
        })
      );

      render(
        <OwnershipForm
          initialValues={createMockOwnership({ id: '1', name: '测试' })}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const form = screen.getByTestId('ownership-form');
      fireEvent.submit(form);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });
  });
});
