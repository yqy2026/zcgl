/**
 * ProjectSelect 组件测试
 * 对齐当前 Select + Modal 交互实现
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
import { useProjectOptions } from '@/hooks/useProject';
import { MessageManager } from '@/utils/messageManager';
import ProjectSelect from '../ProjectSelect';

vi.mock('@/hooks/useProject', () => ({
  useProjectOptions: vi.fn(),
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    info: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock('@/components/Project/ProjectList', () => ({
  default: ({
    onSelectProject,
  }: {
    onSelectProject: (project: Record<string, unknown>) => void;
  }) => (
    <button
      data-testid="pick-modal-project"
      onClick={() =>
        onSelectProject({
          id: 'project-002',
          name: '项目二',
          code: 'PROJ-002',
          short_name: '二期',
          is_active: true,
        })
      }
    >
      pick
    </button>
  ),
}));

describe('ProjectSelect', () => {
  const refreshMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useProjectOptions).mockReturnValue({
      projects: [
        {
          id: 'project-001',
          name: '项目一',
          code: 'PROJ-001',
          short_name: '一期',
          is_active: true,
        },
        {
          id: 'project-002',
          name: '项目二',
          code: 'PROJ-002',
          short_name: '二期',
          is_active: true,
        },
      ],
      loading: false,
      error: null,
      refresh: refreshMock,
    });
  });

  it('应该渲染占位符', () => {
    renderWithProviders(<ProjectSelect placeholder="请选择项目" />);
    expect(screen.getByText('请选择项目')).toBeInTheDocument();
  });

  it('选择项目后应触发 onChange 并返回项目信息', async () => {
    const handleChange = vi.fn();
    renderWithProviders(<ProjectSelect onChange={handleChange} />);

    const combobox = screen.getByRole('combobox');
    fireEvent.mouseDown(combobox);
    fireEvent.click(await screen.findByText('项目一'));

    await waitFor(() => {
      expect(handleChange).toHaveBeenCalledWith(
        'project-001',
        expect.objectContaining({
          id: 'project-001',
          code: 'PROJ-001',
        })
      );
    });
  });

  it('点击创建按钮应提示开发中', () => {
    renderWithProviders(<ProjectSelect />);

    fireEvent.click(screen.getByRole('button', { name: '创建新项目' }));
    expect(MessageManager.info).toHaveBeenCalledWith('创建新项目功能开发中');
  });

  it('点击刷新按钮应调用 refresh', () => {
    renderWithProviders(<ProjectSelect />);

    fireEvent.click(screen.getByRole('button', { name: '刷新' }));
    expect(refreshMock).toHaveBeenCalled();
  });

  it('从弹窗选择项目应回传选中项目', async () => {
    const handleChange = vi.fn();
    renderWithProviders(<ProjectSelect onChange={handleChange} />);

    fireEvent.click(screen.getByRole('button', { name: '从列表中选择' }));
    fireEvent.click(await screen.findByTestId('pick-modal-project'));

    await waitFor(() => {
      expect(handleChange).toHaveBeenCalledWith(
        'project-002',
        expect.objectContaining({
          id: 'project-002',
          code: 'PROJ-002',
        })
      );
    });
  });
});
