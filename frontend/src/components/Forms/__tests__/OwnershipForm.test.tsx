/**
 * OwnershipForm 组件测试
 * 对齐当前表单契约（创建 + 取消）
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
import OwnershipForm from '../OwnershipForm';
import { ownershipService } from '@/services/ownershipService';
import { projectService } from '@/services/projectService';

const formatStderrWrites = (calls: unknown[][]) => calls.map(call => String(call[0] ?? '')).join(' ');

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

describe('OwnershipForm', () => {
  const onSuccess = vi.fn();
  const onCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ownershipService.createOwnership).mockResolvedValue({
      id: 'ownership-001',
      name: '测试权属方',
      code: 'OWN-001',
      is_active: true,
      data_status: '正常',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    });
  });

  it('应该渲染表单并支持取消', async () => {
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

    try {
      renderWithProviders(
        <OwnershipForm initialValues={null} onSuccess={onSuccess} onCancel={onCancel} />
      );

      expect(screen.getByText('基本信息')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /取\s*消/ })).toBeInTheDocument();

      await waitFor(() => {
        expect(projectService.getProjectOptions).toHaveBeenCalledWith('active');
      });

      fireEvent.click(screen.getByRole('button', { name: /取\s*消/ }));
      expect(onCancel).toHaveBeenCalledTimes(1);
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain('not wrapped in act');
    } finally {
      stderrWriteSpy.mockRestore();
    }
  });

  it('等待项目选项加载后取消时不应输出 act 告警', async () => {
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

    try {
      renderWithProviders(
        <OwnershipForm initialValues={null} onSuccess={onSuccess} onCancel={onCancel} />
      );

      await waitFor(() => {
        expect(projectService.getProjectOptions).toHaveBeenCalledWith('active');
      });

      fireEvent.click(screen.getByRole('button', { name: /取\s*消/ }));
      expect(onCancel).toHaveBeenCalledTimes(1);
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain('not wrapped in act');
    } finally {
      stderrWriteSpy.mockRestore();
    }
  });

  it('填写必填项后应提交创建', async () => {
    renderWithProviders(
      <OwnershipForm initialValues={null} onSuccess={onSuccess} onCancel={onCancel} />
    );

    fireEvent.change(screen.getByPlaceholderText('请输入权属方全称'), {
      target: { value: '测试权属方' },
    });
    fireEvent.click(screen.getByRole('button', { name: /创\s*建/ }));

    await waitFor(() => {
      expect(ownershipService.createOwnership).toHaveBeenCalled();
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
