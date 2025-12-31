/**
 * useProject Hook 测试
 * 测试项目管理相关的自定义Hooks（简化版本）
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'

// =============================================================================
// Mock projectService
// =============================================================================

vi.mock('@/services/projectService', () => ({
  projectService: {
    getProjectOptions: vi.fn(() => Promise.resolve([
      { label: '项目1', value: '1' },
      { label: '项目2', value: '2' }
    ])),
    getProject: vi.fn(() => Promise.resolve({
      id: '1',
      name: '项目1',
      code: 'PRJ001'
    })),
    getProjects: vi.fn(() => Promise.resolve({
      items: [],
      page: 1,
      size: 10,
      total: 0
    })),
    getProjectStatistics: vi.fn(() => Promise.resolve({
      total: 10,
      active: 8
    })),
    createProject: vi.fn(() => Promise.resolve({
      id: 'new-1',
      name: '新项目'
    })),
    updateProject: vi.fn(() => Promise.resolve({
      id: '1',
      name: '更新项目'
    })),
    deleteProject: vi.fn(() => Promise.resolve({ success: true })),
    toggleProjectStatus: vi.fn(() => Promise.resolve({
      id: '1',
      is_active: false
    })),
    validateProjectCode: vi.fn(() => Promise.resolve({ valid: true })),
    validateProjectName: vi.fn(() => Promise.resolve({ valid: true }))
  }
}))

// =============================================================================
// Mock antd message
// =============================================================================

vi.mock('antd', () => ({
  message: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn()
  }
}))

// =============================================================================
// useProject Hook 测试
// =============================================================================

describe('useProject - Hook验证', () => {
  it('应该导出useProjectOptions hook', async () => {
    const { useProjectOptions } = await import('../useProject')
    expect(typeof useProjectOptions).toBe('function')
  })

  it('应该导出useProjectDetail hook', async () => {
    const { useProjectDetail } = await import('../useProject')
    expect(typeof useProjectDetail).toBe('function')
  })

  it('应该导出useProjectList hook', async () => {
    const { useProjectList } = await import('../useProject')
    expect(typeof useProjectList).toBe('function')
  })

  it('应该导出useProjectStatistics hook', async () => {
    const { useProjectStatistics } = await import('../useProject')
    expect(typeof useProjectStatistics).toBe('function')
  })

  it('应该导出useCreateProject hook', async () => {
    const { useCreateProject } = await import('../useProject')
    expect(typeof useCreateProject).toBe('function')
  })

  it('应该导出useUpdateProject hook', async () => {
    const { useUpdateProject } = await import('../useProject')
    expect(typeof useUpdateProject).toBe('function')
  })

  it('应该导出useDeleteProject hook', async () => {
    const { useDeleteProject } = await import('../useProject')
    expect(typeof useDeleteProject).toBe('function')
  })

  it('应该导出useToggleProjectStatus hook', async () => {
    const { useToggleProjectStatus } = await import('../useProject')
    expect(typeof useToggleProjectStatus).toBe('function')
  })

  it('应该导出useValidateProjectCode hook', async () => {
    const { useValidateProjectCode } = await import('../useProject')
    expect(typeof useValidateProjectCode).toBe('function')
  })

  it('应该导出useValidateProjectName hook', async () => {
    const { useValidateProjectName } = await import('../useProject')
    expect(typeof useValidateProjectName).toBe('function')
  })
})
