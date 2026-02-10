/**
 * PropertyCertificateUpload 组件测试
 * 测试产权证上传组件的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, act } from '@/test/utils/test-helpers';
import { PropertyCertificateUpload } from '../PropertyCertificateUpload';
import type { CertificateExtractionResult, CertificateType } from '@/types/propertyCertificate';

const { uploadDraggerMock, messageSuccessMock, messageErrorMock } = vi.hoisted(() => ({
  uploadDraggerMock: vi.fn(),
  messageSuccessMock: vi.fn(),
  messageErrorMock: vi.fn(),
}));

// Mock service
vi.mock('@/services/propertyCertificateService', () => ({
  propertyCertificateService: {
    uploadCertificate: vi.fn(),
  },
}));

// Mock Ant Design
vi.mock('antd', () => {
  uploadDraggerMock.mockImplementation(
    ({ children, disabled }: { children?: React.ReactNode; disabled?: boolean }) => (
      <div data-testid="upload-dragger" data-disabled={disabled}>
        {children}
      </div>
    )
  );

  const Upload = vi.fn(({ children }) => <div data-testid="upload">{children}</div>);
  (Upload as unknown as Record<string, unknown>).Dragger = uploadDraggerMock;

  return {
    Upload,
    Card: vi.fn(({ children }) => <div data-testid="card">{children}</div>),
    Alert: vi.fn(({ title, message, description, type }) => (
      <div data-testid="alert" data-type={type}>
        <span>{title ?? message}</span>
        <span>{description}</span>
      </div>
    )),
    Space: vi.fn(({ children }) => <div data-testid="space">{children}</div>),
    message: {
      success: messageSuccessMock,
      error: messageErrorMock,
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  InboxOutlined: () => <span data-testid="inbox-icon" />,
}));

// Helper to create mock extraction result
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

describe('PropertyCertificateUpload - 组件导入测试', () => {
  it('应该能够导入组件', () => {
    expect(PropertyCertificateUpload).toBeDefined();
    expect(typeof PropertyCertificateUpload).toBe('function');
  });
});

describe('PropertyCertificateUpload - 渲染与交互测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    uploadDraggerMock.mockClear();
    messageSuccessMock.mockClear();
    messageErrorMock.mockClear();
  });

  it('应该渲染上传说明与拖拽区域', () => {
    renderWithProviders(<PropertyCertificateUpload onSuccess={vi.fn()} />);

    expect(screen.getByTestId('alert')).toBeInTheDocument();
    expect(screen.getByTestId('upload-dragger')).toHaveAttribute('data-disabled', 'false');
    expect(screen.getByText('点击或拖拽文件到此区域上传')).toBeInTheDocument();
  });

  it('loading为true时应禁用上传并显示处理中提示', () => {
    renderWithProviders(<PropertyCertificateUpload onSuccess={vi.fn()} loading={true} />);

    expect(screen.getByTestId('upload-dragger')).toHaveAttribute('data-disabled', 'true');
    expect(screen.getByText('正在处理...')).toBeInTheDocument();
  });

  it('beforeUpload应校验文件类型与大小', () => {
    renderWithProviders(<PropertyCertificateUpload onSuccess={vi.fn()} />);
    const draggerProps = uploadDraggerMock.mock.calls[0][0] as {
      beforeUpload?: (file: File) => boolean;
    };

    const invalidTypeFile = { type: 'text/plain', size: 1024 * 1024 } as File;
    const validTypeOversizeFile = {
      type: 'application/pdf',
      size: 11 * 1024 * 1024,
    } as File;

    expect(draggerProps.beforeUpload?.(invalidTypeFile)).toBe(false);
    expect(messageErrorMock).toHaveBeenCalledWith('只支持 PDF、JPG、PNG 格式');

    expect(draggerProps.beforeUpload?.(validTypeOversizeFile)).toBe(false);
    expect(messageErrorMock).toHaveBeenCalledWith('文件大小不能超过 10MB');
  });

  it('上传成功应调用服务与回调', async () => {
    const { propertyCertificateService } = await import('@/services/propertyCertificateService');
    const mockResult = createMockExtractionResult();
    vi.mocked(propertyCertificateService.uploadCertificate).mockResolvedValue(mockResult);

    const onSuccess = vi.fn();
    renderWithProviders(<PropertyCertificateUpload onSuccess={onSuccess} />);
    const draggerProps = uploadDraggerMock.mock.calls[0][0] as {
      customRequest?: (options: {
        file: File;
        onSuccess?: (result: unknown) => void;
        onError?: (error: Error) => void;
      }) => Promise<void>;
    };

    const uploadSuccess = vi.fn();
    const uploadError = vi.fn();
    await act(async () => {
      await draggerProps.customRequest?.({
        file: { type: 'application/pdf', size: 1024 } as File,
        onSuccess: uploadSuccess,
        onError: uploadError,
      });
    });

    expect(propertyCertificateService.uploadCertificate).toHaveBeenCalledTimes(1);
    expect(onSuccess).toHaveBeenCalledWith(mockResult);
    expect(uploadSuccess).toHaveBeenCalled();
    expect(messageSuccessMock).toHaveBeenCalledWith('文件上传并提取成功');
    expect(uploadError).not.toHaveBeenCalled();
  });

  it('上传失败应提示错误并触发onError', async () => {
    const { propertyCertificateService } = await import('@/services/propertyCertificateService');
    vi.mocked(propertyCertificateService.uploadCertificate).mockRejectedValue(
      new Error('Upload failed')
    );

    const onSuccess = vi.fn();
    renderWithProviders(<PropertyCertificateUpload onSuccess={onSuccess} />);
    const draggerProps = uploadDraggerMock.mock.calls[0][0] as {
      customRequest?: (options: {
        file: File;
        onSuccess?: (result: unknown) => void;
        onError?: (error: Error) => void;
      }) => Promise<void>;
    };

    const uploadSuccess = vi.fn();
    const uploadError = vi.fn();
    await act(async () => {
      await draggerProps.customRequest?.({
        file: { type: 'application/pdf', size: 1024 } as File,
        onSuccess: uploadSuccess,
        onError: uploadError,
      });
    });

    expect(propertyCertificateService.uploadCertificate).toHaveBeenCalledTimes(1);
    expect(onSuccess).not.toHaveBeenCalled();
    expect(uploadError).toHaveBeenCalled();
    expect(messageErrorMock).toHaveBeenCalledWith('上传失败，请重试');
  });
});
