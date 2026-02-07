/**
 * ProjectForm 组件测试 - 简化版本
 *
 * 修复说明：移除 antd UI 组件 mock，保留 Form mock
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
import { createMockProject } from '@/test-utils/factories';

vi.mock('@/services/projectService', () => ({
  projectService: {
    createProject: vi.fn(),
    updateProject: vi.fn(),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockFormInstance = {
  resetFields: vi.fn(),
  validateFields: vi.fn(() => Promise.resolve({})),
};

vi.mock('antd', () => ({
  Form: {
    useForm: () => [mockFormInstance],
  },
}));

import ProjectForm from '../ProjectForm';
import { projectService } from '@/services/projectService';

describe('ProjectForm', () => {
  const mockOnSuccess = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该正确渲染表单', () => {
    renderWithProviders(
      <ProjectForm project={null} onSuccess={mockOnSuccess} onCancel={mockOnCancel} />
    );
    expect(screen.getByRole('form')).toBeInTheDocument();
  });

  it('应该调用创建服务', async () => {
    vi.mocked(projectService.createProject).mockResolvedValue(
      createMockProject({ id: '1', name: '测试项目' })
    );

    renderWithProviders(
      <ProjectForm project={null} onSuccess={mockOnSuccess} onCancel={mockOnCancel} />
    );

    const submitBtn = screen.getByRole('button', { name: /提交/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(projectService.createProject).toHaveBeenCalled();
    });
  });
});
