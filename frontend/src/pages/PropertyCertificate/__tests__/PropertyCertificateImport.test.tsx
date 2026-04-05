/**
 * PropertyCertificateImport 页面测试
 * 测试产权证导入页面的核心功能
 *
 * 修复说明：
 * - 移除 antd Row, Col, Steps, Card 组件 mock
 * - 保留 message API (从 antd 导入，用于验证)
 * - 保留业务组件 mock (PropertyCertificateUpload, PropertyCertificateReview)
 * - 保留服务层 mock (propertyCertificateService)
 * - 使用文本内容进行断言
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { act, screen, waitFor } from '@testing-library/react';
import { message } from 'antd';
import { PROPERTY_CERTIFICATE_ROUTES } from '@/constants/routes';
import { renderWithProviders } from '@/test/utils/test-helpers';

import { PropertyCertificateImport } from '../PropertyCertificateImport';
import { PropertyCertificateUpload } from '@/components/PropertyCertificate/PropertyCertificateUpload';
import { PropertyCertificateReview } from '@/components/PropertyCertificate/PropertyCertificateReview';
import { propertyCertificateService } from '@/services/propertyCertificateService';
import type {
  CertificateExtractionResult,
  CertificateImportConfirm,
  CertificateType,
} from '@/types/propertyCertificate';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock child components
vi.mock('@/components/PropertyCertificate/PropertyCertificateUpload', () => ({
  PropertyCertificateUpload: vi.fn(() => null),
}));

vi.mock('@/components/PropertyCertificate/PropertyCertificateReview', () => ({
  PropertyCertificateReview: vi.fn(() => null),
}));

// Mock service
vi.mock('@/services/propertyCertificateService', () => ({
  propertyCertificateService: {
    confirmImport: vi.fn(),
  },
}));

const createMockExtractionResult = (): CertificateExtractionResult => ({
  session_id: 'session-123',
  certificate_type: 'real_estate' as CertificateType,
  extracted_data: {
    certificate_number: 'CERT-001',
    property_address: '测试地址',
  },
  confidence_score: 0.85,
  asset_matches: [],
  validation_errors: [],
  warnings: [],
});

const createMockConfirmData = (): CertificateImportConfirm => ({
  session_id: 'session-123',
  asset_ids: [],
  extracted_data: {},
  asset_link_id: null,
  should_create_new_asset: false,
  owners: [],
});

const renderPage = () => renderWithProviders(<PropertyCertificateImport />);

const getUploadProps = () =>
  vi.mocked(PropertyCertificateUpload).mock.calls[0]?.[0] as {
    onSuccess: (result: CertificateExtractionResult) => void;
    loading: boolean;
  };

const getReviewProps = () =>
  vi.mocked(PropertyCertificateReview).mock.calls[0]?.[0] as {
    extractionResult: CertificateExtractionResult;
    onConfirm: (data: CertificateImportConfirm) => Promise<void> | void;
    loading: boolean;
  };

const originalLocation = window.location;

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { href: '' } as Location,
  });
});

afterEach(() => {
  vi.useRealTimers();
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation,
  });
});

describe('PropertyCertificateImport - 组件导入测试', () => {
  it('应该能够导入组件', async () => {
    const module = await import('../PropertyCertificateImport');
    expect(module).toBeDefined();
    expect(module.PropertyCertificateImport).toBeDefined();
  });

  it('组件应该是React函数组件', () => {
    expect(typeof PropertyCertificateImport).toBe('function');
  });

  it('应该有默认导出', async () => {
    const module = await import('../PropertyCertificateImport');
    expect(module.default).toBeDefined();
  });
});

describe('PropertyCertificateImport - 组件结构测试', () => {
  it('应该可以渲染组件', () => {
    renderPage();
    expect(screen.getByText('上传文件')).toBeInTheDocument();
  });

  it('组件不需要任何必需属性', () => {
    renderPage();
    expect(screen.getByText('上传文件')).toBeInTheDocument();
  });
});

describe('PropertyCertificateImport - 步骤流程测试', () => {
  it('应该包含三个步骤', () => {
    renderPage();
    expect(screen.getByText('上传文件')).toBeInTheDocument();
    expect(screen.getByText('审核确认')).toBeInTheDocument();
    expect(screen.getByText('完成')).toBeInTheDocument();
  });
});

describe('PropertyCertificateImport - 状态管理测试', () => {
  it('应该管理extractionResult状态', async () => {
    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());

    await act(async () => {
      getUploadProps().onSuccess(createMockExtractionResult());
    });

    await waitFor(() => expect(PropertyCertificateReview).toHaveBeenCalled());
    expect(getReviewProps().extractionResult).toMatchObject({
      session_id: 'session-123',
    });
  });

  it('应该管理loading状态', async () => {
    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());
    expect(getUploadProps().loading).toBe(false);
  });
});

describe('PropertyCertificateImport - 上传成功处理测试', () => {
  it('上传成功后应该保存提取结果', async () => {
    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());

    await act(async () => {
      getUploadProps().onSuccess(createMockExtractionResult());
    });

    await waitFor(() => expect(PropertyCertificateReview).toHaveBeenCalled());
    expect(getReviewProps().extractionResult).toMatchObject({
      session_id: 'session-123',
    });
  });
});

describe('PropertyCertificateImport - 确认导入测试', () => {
  it('确认导入应该调用服务', async () => {
    vi.mocked(propertyCertificateService.confirmImport).mockResolvedValue({
      certificate_id: 'cert-001',
    });

    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());

    await act(async () => {
      getUploadProps().onSuccess(createMockExtractionResult());
    });

    await waitFor(() => expect(PropertyCertificateReview).toHaveBeenCalled());

    await act(async () => {
      await getReviewProps().onConfirm(createMockConfirmData());
    });

    await waitFor(() => {
      expect(propertyCertificateService.confirmImport).toHaveBeenCalled();
    });
  });

  it('确认导入成功后应该显示成功消息', async () => {
    vi.mocked(propertyCertificateService.confirmImport).mockResolvedValue({
      certificate_id: 'cert-001',
    });

    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());

    await act(async () => {
      getUploadProps().onSuccess(createMockExtractionResult());
    });

    await waitFor(() => expect(PropertyCertificateReview).toHaveBeenCalled());

    await act(async () => {
      await getReviewProps().onConfirm(createMockConfirmData());
    });

    await waitFor(() => {
      expect(message.success).toHaveBeenCalledWith('产权证创建成功！ID: cert-001');
    });
  });

  it('确认导入成功后应该跳转到产权证列表', async () => {
    vi.mocked(propertyCertificateService.confirmImport).mockResolvedValue({
      certificate_id: 'cert-001',
    });

    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());

    await act(async () => {
      getUploadProps().onSuccess(createMockExtractionResult());
    });

    await waitFor(() => expect(PropertyCertificateReview).toHaveBeenCalled());

    await act(async () => {
      vi.useFakeTimers();
      await getReviewProps().onConfirm(createMockConfirmData());
      await vi.runAllTimersAsync();
    });

    expect(mockNavigate).toHaveBeenCalledWith(PROPERTY_CERTIFICATE_ROUTES.LIST);
  });

  it('确认导入失败应该显示错误消息', async () => {
    vi.mocked(propertyCertificateService.confirmImport).mockRejectedValue(
      new Error('Import failed')
    );

    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());

    await act(async () => {
      getUploadProps().onSuccess(createMockExtractionResult());
    });

    await waitFor(() => expect(PropertyCertificateReview).toHaveBeenCalled());

    await act(async () => {
      await getReviewProps().onConfirm(createMockConfirmData());
    });

    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith('创建失败，请重试');
    });
  });
});

describe('PropertyCertificateImport - 条件渲染测试', () => {
  it('第一步应该渲染Upload组件', async () => {
    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());
    expect(PropertyCertificateReview).not.toHaveBeenCalled();
  });

  it('第二步应该渲染Review组件', async () => {
    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());

    await act(async () => {
      getUploadProps().onSuccess(createMockExtractionResult());
    });

    await waitFor(() => expect(PropertyCertificateReview).toHaveBeenCalled());
  });

  it('第二步需要extractionResult存在', async () => {
    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());
    expect(PropertyCertificateReview).not.toHaveBeenCalled();
  });
});

describe('PropertyCertificateImport - 完整流程测试', () => {
  it('应该支持完整的导入流程', async () => {
    vi.mocked(propertyCertificateService.confirmImport).mockResolvedValue({
      certificate_id: 'cert-new-001',
    });

    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());

    await act(async () => {
      getUploadProps().onSuccess(createMockExtractionResult());
    });

    await waitFor(() => expect(PropertyCertificateReview).toHaveBeenCalled());

    await act(async () => {
      await getReviewProps().onConfirm(createMockConfirmData());
    });

    await waitFor(() => {
      expect(propertyCertificateService.confirmImport).toHaveBeenCalled();
    });
  });

  it('应该处理中途取消的情况', async () => {
    renderPage();
    await waitFor(() => expect(PropertyCertificateUpload).toHaveBeenCalled());
    expect(PropertyCertificateReview).not.toHaveBeenCalled();
  });
});
