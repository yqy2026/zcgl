/**
 * ProjectDetail 组件测试
 * 对齐当前精简版 ProjectDetail 组件契约
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { screen, fireEvent } from '@/test/utils/test-helpers';
import type { Project } from '@/types/project';
import ProjectDetail from '../ProjectDetail';

const createMockProject = (overrides: Partial<Project> = {}): Project => ({
  id: 'project-001',
  name: '测试项目',
  code: 'PROJ-001',
  description: '项目描述',
  is_active: true,
  data_status: '正常',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-02T00:00:00Z',
  created_by: 'admin',
  updated_by: 'admin',
  asset_count: 5,
  ...overrides,
});

describe('ProjectDetail', () => {
  it('应该渲染项目核心信息', () => {
    renderWithProviders(<ProjectDetail project={createMockProject()} onEdit={vi.fn()} />);

    expect(screen.getByText('测试项目')).toBeInTheDocument();
    expect(screen.getByText('PROJ-001')).toBeInTheDocument();
    expect(screen.getByText('编辑项目')).toBeInTheDocument();
    expect(screen.getByText('项目信息')).toBeInTheDocument();
    expect(screen.getByText('系统信息')).toBeInTheDocument();
  });

  it('缺失字段时应显示默认占位符', () => {
    renderWithProviders(
      <ProjectDetail
        project={createMockProject({
          description: '',
          created_by: '',
          updated_by: '',
          created_at: '',
          updated_at: '',
        })}
        onEdit={vi.fn()}
      />
    );

    expect(screen.getAllByText('-').length).toBeGreaterThan(0);
  });

  it('点击编辑项目应触发回调', () => {
    const handleEdit = vi.fn();

    renderWithProviders(<ProjectDetail project={createMockProject()} onEdit={handleEdit} />);

    fireEvent.click(screen.getByRole('button', { name: /编\s*辑\s*项\s*目/ }));
    expect(handleEdit).toHaveBeenCalledTimes(1);
  });
});
