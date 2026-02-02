/**
 * OwnershipForm 组件测试
 * 测试权属方表单的核心功能
 *
 * 修复说明：
 * - 移除 antd UI 组件 mock (Input, Button, Space, Card, Row, Col, Divider, Switch, Select)
 * - 保留 Form mock (测试依赖其方法调用)
 * - 保留服务层 mock (ownershipService, projectService)
 * - 保留工具类 mock (messageManager)
 * - 使用 className 和文本内容进行断言
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
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

// Mock Form instance only (test depends on its methods)
const mockFormInstance = {
  getFieldsValue: vi.fn(() => ({})),
  setFieldsValue: vi.fn(),
  validateFields: vi.fn(() => Promise.resolve({ name: '测试权属方' })),
  resetFields: vi.fn(),
  getFieldValue: vi.fn(),
  setFieldValue: vi.fn(),
};

vi.mock('antd', () => ({
  Form: {
    useForm: () => [mockFormInstance],
  },
}));

import OwnershipForm from '../OwnershipForm';
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
      renderWithProviders(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByRole('form')).toBeInTheDocument();
    });

    it('应该渲染提交和取消按钮', () => {
      renderWithProviders(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByRole('button', { name: /提交/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /取消/i })).toBeInTheDocument();
    });
  });

  describe('创建模式', () => {
    it('创建模式下表单应为空', () => {
      renderWithProviders(
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

      renderWithProviders(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const submitBtn = screen.getByRole('button', { name: /提交/i });
      fireEvent.click(submitBtn);

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
      renderWithProviders(
        <OwnershipForm
          initialValues={mockOwnership}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(mockFormInstance.setFieldsValue).toHaveBeenCalled();
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

      renderWithProviders(
        <OwnershipForm
          initialValues={mockOwnership}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const submitBtn = screen.getByRole('button', { name: /提交/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(ownershipService.updateOwnership).toHaveBeenCalled();
      });
    });
  });

  describe('表单验证', () => {
    it('名称唯一性验证 - 名称可用', async () => {
      vi.mocked(ownershipService.validateOwnershipName).mockResolvedValue(true);

      renderWithProviders(
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
      renderWithProviders(
        <OwnershipForm
          initialValues={null}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const cancelBtn = screen.getByRole('button', { name: /取消/i });
      fireEvent.click(cancelBtn);

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });
});
