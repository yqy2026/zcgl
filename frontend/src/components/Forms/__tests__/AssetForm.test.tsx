/**
 * AssetForm 组件测试 - 简化版本
 *
 * 修复说明：移除 antd UI 组件 mock，保留 Form mock
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
import { createMockAsset } from '@/test-utils/factories';

vi.mock('@/services/assetService', () => ({
  assetService: {
    createAsset: vi.fn(),
    updateAsset: vi.fn(),
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

import AssetForm from '../AssetForm';
import { assetService } from '@/services/assetService';

describe('AssetForm', () => {
  const mockOnSuccess = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该正确渲染表单', () => {
    renderWithProviders(
      <AssetForm asset={null} onSuccess={mockOnSuccess} onCancel={mockOnCancel} />
    );
    expect(screen.getByRole('form')).toBeInTheDocument();
  });

  it('应该调用创建服务', async () => {
    vi.mocked(assetService.createAsset).mockResolvedValue(
      createMockAsset({ id: '1', property_name: '测试资产' })
    );

    renderWithProviders(
      <AssetForm asset={null} onSuccess={mockOnSuccess} onCancel={mockOnCancel} />
    );

    const submitBtn = screen.getByRole('button', { name: /提交/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(assetService.createAsset).toHaveBeenCalled();
    });
  });
});
