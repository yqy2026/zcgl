/**
 * ProjectForm 组件测试
 * 测试项目表单的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { createMockProject } from '@/test-utils/factories';
import type { Project } from '@/types/project';

// Mock dependencies
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock('@/services/projectService', () => ({
  projectService: {
    createProject: vi.fn(),
    updateProject: vi.fn(),
    validateProjectName: vi.fn(() => Promise.resolve(true)),
    validateProjectCode: vi.fn(() => Promise.resolve(true)),
  },
}));

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    getOwnershipOptions: vi.fn(() => Promise.resolve([])),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

// Mock Ant Design
const mockFormInstance = {
  getFieldsValue: vi.fn(() => ({})),
  setFieldsValue: vi.fn(),
  validateFields: vi.fn(() => Promise.resolve({ name: '测试项目' })),
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
      data-testid="project-form"
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
    Input: Object.assign(
      ({ placeholder }: { placeholder?: string }) => (
        <input data-testid="input" placeholder={placeholder} />
      ),
      {
        TextArea: ({ placeholder }: { placeholder?: string }) => (
          <textarea data-testid="textarea" placeholder={placeholder} />
        ),
      }
    ),
    Button: ({ children, onClick, htmlType }: { children: React.ReactNode; onClick?: () => void; htmlType?: string }) => (
      <button data-testid={`btn-${htmlType ?? 'default'}`} onClick={onClick} type={htmlType as 'button' | 'submit' | 'reset'}>
        {children}
      </button>
    ),
    Space: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Card: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Select: ({ children }: { children: React.ReactNode }) => <select data-testid="select">{children}</select>,
    Tag: ({ children, onClose }: { children: React.ReactNode; onClose?: () => void }) => (
      <span data-testid="tag" onClick={onClose}>{children}</span>
    ),
  };
});

import ProjectForm from '../ProjectForm';
import { projectService } from '@/services/projectService';
import { MessageManager } from '@/utils/messageManager';

describe('ProjectForm', () => {
  const mockOnSuccess = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('渲染测试', () => {
    it('应该正确渲染表单', () => {
      render(
        <ProjectForm
          project={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByTestId('project-form')).toBeInTheDocument();
    });

    it('应该渲染提交按钮', () => {
      render(
        <ProjectForm
          project={null}
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
        <ProjectForm
          project={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(mockFormInstance.resetFields).toHaveBeenCalled();
    });

    it('应该调用创建服务', async () => {
      vi.mocked(projectService.createProject).mockResolvedValue(
        createMockProject({
          id: '1',
          name: '测试项目',
          code: 'PRJ-001',
        })
      );

      render(
        <ProjectForm
          project={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const form = screen.getByTestId('project-form');
      fireEvent.submit(form);

      await waitFor(() => {
        expect(projectService.createProject).toHaveBeenCalled();
      });
    });
  });

  describe('编辑模式', () => {
    const mockProject: Project = createMockProject({
      id: '1',
      name: '测试项目',
      code: 'PRJ-001',
      description: '项目描述',
      ownership_relations: [],
    });

    it('编辑模式下应设置初始值', () => {
      render(
        <ProjectForm
          project={mockProject}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(mockFormInstance.setFieldsValue).toHaveBeenCalled();
    });

    it('应该调用更新服务', async () => {
      vi.mocked(projectService.updateProject).mockResolvedValue(
        createMockProject({
          ...mockProject,
          name: '更新后的名称',
        })
      );

      mockFormInstance.validateFields.mockResolvedValue({
        name: '更新后的名称',
      });

      render(
        <ProjectForm
          project={mockProject}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const form = screen.getByTestId('project-form');
      fireEvent.submit(form);

      await waitFor(() => {
        expect(projectService.updateProject).toHaveBeenCalled();
      });
    });
  });

  describe('取消操作', () => {
    it('点击取消应调用 onCancel', () => {
      render(
        <ProjectForm
          project={null}
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
      vi.mocked(projectService.createProject).mockRejectedValue(
        new Error('创建失败')
      );

      render(
        <ProjectForm
          project={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const form = screen.getByTestId('project-form');
      fireEvent.submit(form);

      await waitFor(() => {
        expect(MessageManager.error).toHaveBeenCalled();
      });
    });
  });

  describe('成功回调', () => {
    it('创建成功应调用 onSuccess', async () => {
      vi.mocked(projectService.createProject).mockResolvedValue(
        createMockProject({
          id: '1',
          name: '测试项目',
        })
      );

      render(
        <ProjectForm
          project={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const form = screen.getByTestId('project-form');
      fireEvent.submit(form);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });
  });
});
