/**
 * ProjectForm 组件测试
 * 对齐当前精简版表单行为
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { renderWithProviders, screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
import ProjectForm from '../ProjectForm';
import { projectService } from '@/services/projectService';
import { ownershipService } from '@/services/ownershipService';

vi.mock('@/services/projectService', () => ({
  projectService: {
    createProject: vi.fn(),
    updateProject: vi.fn(),
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
  },
}));

describe('ProjectForm', () => {
  const onSuccess = vi.fn();
  const onCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ownershipService.getOwnershipOptions).mockResolvedValue([]);
    vi.mocked(projectService.createProject).mockResolvedValue({
      id: 'project-001',
      name: '测试项目',
      code: 'PROJ-001',
      is_active: true,
      data_status: '正常',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    });
  });

  it('应该渲染表单并支持取消', async () => {
    renderWithProviders(<ProjectForm project={null} onSuccess={onSuccess} onCancel={onCancel} />);

    await waitFor(() => {
      expect(ownershipService.getOwnershipOptions).toHaveBeenCalled();
    });

    expect(screen.getByText('项目信息')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /取\s*消/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /取\s*消/ }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('应该使用语义样式类组织布局', async () => {
    renderWithProviders(<ProjectForm project={null} onSuccess={onSuccess} onCancel={onCancel} />);

    await waitFor(() => {
      expect(ownershipService.getOwnershipOptions).toHaveBeenCalled();
    });

    expect(screen.getByText('权属方关联').closest('[class*="ownershipCard"]')).toBeInTheDocument();
    expect(document.querySelector('[class*="formActions"]')).toBeInTheDocument();
  });

  it('填写项目名称后应提交创建', async () => {
    renderWithProviders(<ProjectForm project={null} onSuccess={onSuccess} onCancel={onCancel} />);

    fireEvent.change(screen.getByPlaceholderText('请输入项目名称'), {
      target: { value: '测试项目' },
    });
    fireEvent.click(screen.getByRole('button', { name: /创\s*建/ }));

    await waitFor(() => {
      expect(projectService.createProject).toHaveBeenCalled();
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
