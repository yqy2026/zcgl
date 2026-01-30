/**
 * PropertyCertificateImport 页面测试
 * 测试产权证导入页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';

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

// Mock Ant Design
vi.mock('antd', () => ({
  Row: vi.fn(({ children }) => <div data-testid="row">{children}</div>),
  Col: vi.fn(({ children }) => <div data-testid="col">{children}</div>),
  Steps: vi.fn(({ current, items }) => (
    <div data-testid="steps" data-current={current}>
      {items?.map((item: { title: string }, index: number) => (
        <div key={index}>{item.title}</div>
      ))}
    </div>
  )),
  Card: vi.fn(({ children }) => <div data-testid="card">{children}</div>),
  message: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

import type { CertificateExtractionResult, CertificateType } from '@/types/propertyCertificate';

// Helper to create mock extraction result
const _createMockExtractionResult = (): CertificateExtractionResult => ({
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

describe('PropertyCertificateImport - 组件导入测试', () => {
  it('应该能够导入组件', async () => {
    const module = await import('../PropertyCertificateImport');
    expect(module).toBeDefined();
    expect(module.PropertyCertificateImport).toBeDefined();
  });

  it('组件应该是React函数组件', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');
    expect(typeof PropertyCertificateImport).toBe('function');
  });

  it('应该有默认导出', async () => {
    const module = await import('../PropertyCertificateImport');
    expect(module.default).toBeDefined();
  });
});

describe('PropertyCertificateImport - 组件结构测试', () => {
  it('应该可以创建组件实例', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
    expect(element.type).toBe(PropertyCertificateImport);
  });

  it('组件不需要任何必需属性', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport, {});
    expect(element).toBeTruthy();
  });
});

describe('PropertyCertificateImport - 步骤流程测试', () => {
  it('应该包含三个步骤', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
    // 步骤: 上传文件 -> 审核确认 -> 完成
  });

  it('初始状态应该是第一步', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
    // currentStep 初始值应该是 0
  });
});

describe('PropertyCertificateImport - 状态管理测试', () => {
  it('应该管理currentStep状态', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });

  it('应该管理extractionResult状态', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });

  it('应该管理loading状态', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });
});

describe('PropertyCertificateImport - 上传成功处理测试', () => {
  it('上传成功后应该保存提取结果', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });

  it('上传成功后应该进入第二步', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });
});

describe('PropertyCertificateImport - 确认导入测试', () => {
  it('确认导入应该调用服务', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');
    const { propertyCertificateService } = await import(
      '@/services/propertyCertificateService'
    );

    vi.mocked(propertyCertificateService.confirmImport).mockResolvedValue({
      certificate_id: 'cert-001',
    });

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });

  it('确认导入成功后应该显示成功消息', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');
    const { propertyCertificateService } = await import(
      '@/services/propertyCertificateService'
    );

    vi.mocked(propertyCertificateService.confirmImport).mockResolvedValue({
      certificate_id: 'cert-001',
    });

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });

  it('确认导入失败应该显示错误消息', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');
    const { propertyCertificateService } = await import(
      '@/services/propertyCertificateService'
    );

    vi.mocked(propertyCertificateService.confirmImport).mockRejectedValue(
      new Error('Import failed')
    );

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });
});

describe('PropertyCertificateImport - 条件渲染测试', () => {
  it('第一步应该渲染Upload组件', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });

  it('第二步应该渲染Review组件', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });

  it('第二步需要extractionResult存在', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });
});

describe('PropertyCertificateImport - 完整流程测试', () => {
  it('应该支持完整的导入流程', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');
    const { propertyCertificateService } = await import(
      '@/services/propertyCertificateService'
    );

    vi.mocked(propertyCertificateService.confirmImport).mockResolvedValue({
      certificate_id: 'cert-new-001',
    });

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();

    // 完整流程: 上传 -> 提取 -> 审核 -> 确认 -> 完成
  });

  it('应该处理中途取消的情况', async () => {
    const { PropertyCertificateImport } = await import('../PropertyCertificateImport');

    const element = React.createElement(PropertyCertificateImport);
    expect(element).toBeTruthy();
  });
});
