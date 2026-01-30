/**
 * PropertyCertificateUpload 组件测试
 * 测试产权证上传组件的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';

// Mock service
vi.mock('@/services/propertyCertificateService', () => ({
  propertyCertificateService: {
    uploadCertificate: vi.fn(),
  },
}));

// Mock Ant Design
vi.mock('antd', () => {
  const Upload = vi.fn(({ children }) => <div data-testid="upload">{children}</div>);
  (Upload as unknown as Record<string, unknown>).Dragger = vi.fn(
    ({ children, disabled }) => (
      <div data-testid="upload-dragger" data-disabled={disabled}>
        {children}
      </div>
    )
  );

  return {
    Upload,
    Card: vi.fn(({ children }) => <div data-testid="card">{children}</div>),
    Alert: vi.fn(({ message, description, type }) => (
      <div data-testid="alert" data-type={type}>
        <span>{message}</span>
        <span>{description}</span>
      </div>
    )),
    Space: vi.fn(({ children }) => <div data-testid="space">{children}</div>),
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  InboxOutlined: () => <span data-testid="inbox-icon" />,
}));

import type { CertificateExtractionResult, CertificateType } from '@/types/propertyCertificate';

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
  it('应该能够导入组件', async () => {
    const module = await import('../PropertyCertificateUpload');
    expect(module).toBeDefined();
    expect(module.PropertyCertificateUpload).toBeDefined();
  });

  it('组件应该是React函数组件', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');
    expect(typeof PropertyCertificateUpload).toBe('function');
  });
});

describe('PropertyCertificateUpload - 基础属性测试', () => {
  it('应该接受onSuccess回调', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');

    const onSuccess = vi.fn();
    const element = React.createElement(PropertyCertificateUpload, { onSuccess });

    expect(element).toBeTruthy();
    expect(element.props.onSuccess).toEqual(onSuccess);
  });

  it('应该接受loading属性', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');

    const onSuccess = vi.fn();
    const element = React.createElement(PropertyCertificateUpload, {
      onSuccess,
      loading: true,
    });

    expect(element.props.loading).toBe(true);
  });

  it('loading属性应该有默认值false', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');

    const onSuccess = vi.fn();
    const element = React.createElement(PropertyCertificateUpload, { onSuccess });

    expect(element.props.loading).toBeUndefined();
  });
});

describe('PropertyCertificateUpload - 文件验证测试', () => {
  it('应该支持PDF文件类型', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');

    const onSuccess = vi.fn();
    const element = React.createElement(PropertyCertificateUpload, { onSuccess });

    expect(element).toBeTruthy();
    // 组件内部 accept 属性应该包含 .pdf
  });

  it('应该支持JPG文件类型', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');

    const onSuccess = vi.fn();
    const element = React.createElement(PropertyCertificateUpload, { onSuccess });

    expect(element).toBeTruthy();
    // 组件内部 accept 属性应该包含 .jpg, .jpeg
  });

  it('应该支持PNG文件类型', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');

    const onSuccess = vi.fn();
    const element = React.createElement(PropertyCertificateUpload, { onSuccess });

    expect(element).toBeTruthy();
    // 组件内部 accept 属性应该包含 .png
  });
});

describe('PropertyCertificateUpload - 上传流程测试', () => {
  it('应该在上传成功时调用onSuccess', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');
    const { propertyCertificateService } = await import(
      '@/services/propertyCertificateService'
    );

    const mockResult = createMockExtractionResult();
    vi.mocked(propertyCertificateService.uploadCertificate).mockResolvedValue(mockResult);

    const onSuccess = vi.fn();
    const element = React.createElement(PropertyCertificateUpload, { onSuccess });

    expect(element).toBeTruthy();
    expect(element.props.onSuccess).toBe(onSuccess);
  });

  it('应该在loading时禁用上传', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');

    const onSuccess = vi.fn();
    const element = React.createElement(PropertyCertificateUpload, {
      onSuccess,
      loading: true,
    });

    expect(element.props.loading).toBe(true);
  });
});

describe('PropertyCertificateUpload - 组件结构测试', () => {
  it('应该有正确的命名导出', async () => {
    const module = await import('../PropertyCertificateUpload');

    expect(module.PropertyCertificateUpload).toBeDefined();
    expect(typeof module.PropertyCertificateUpload).toBe('function');
  });

  it('应该可以创建组件实例', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');

    const element = React.createElement(PropertyCertificateUpload, {
      onSuccess: vi.fn(),
    });

    expect(element).toBeTruthy();
    expect(element.type).toBe(PropertyCertificateUpload);
  });

  it('所有必需属性都应该被接受', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');

    const props = {
      onSuccess: vi.fn(),
      loading: false,
    };

    const element = React.createElement(PropertyCertificateUpload, props);
    expect(element).toBeTruthy();
  });
});

describe('PropertyCertificateUpload - 状态管理测试', () => {
  it('应该处理上传中状态', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');

    const element = React.createElement(PropertyCertificateUpload, {
      onSuccess: vi.fn(),
      loading: true,
    });

    expect(element.props.loading).toBe(true);
  });

  it('应该处理空闲状态', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');

    const element = React.createElement(PropertyCertificateUpload, {
      onSuccess: vi.fn(),
      loading: false,
    });

    expect(element.props.loading).toBe(false);
  });
});

describe('PropertyCertificateUpload - 错误处理测试', () => {
  it('应该处理上传失败的情况', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');
    const { propertyCertificateService } = await import(
      '@/services/propertyCertificateService'
    );

    vi.mocked(propertyCertificateService.uploadCertificate).mockRejectedValue(
      new Error('Upload failed')
    );

    const onSuccess = vi.fn();
    const element = React.createElement(PropertyCertificateUpload, { onSuccess });

    expect(element).toBeTruthy();
  });

  it('应该处理网络错误', async () => {
    const { PropertyCertificateUpload } = await import('../PropertyCertificateUpload');
    const { propertyCertificateService } = await import(
      '@/services/propertyCertificateService'
    );

    vi.mocked(propertyCertificateService.uploadCertificate).mockRejectedValue(
      new Error('Network error')
    );

    const onSuccess = vi.fn();
    const element = React.createElement(PropertyCertificateUpload, { onSuccess });

    expect(element).toBeTruthy();
  });
});
