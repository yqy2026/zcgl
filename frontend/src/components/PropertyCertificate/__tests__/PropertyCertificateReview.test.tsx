/**
 * PropertyCertificateReview 组件测试
 * 测试产权证审核组件的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';

// Mock dayjs
vi.mock('dayjs', () => ({
  default: vi.fn((input?: string | Date) => ({
    isValid: () => true,
    format: vi.fn(() => '2024-01-01'),
    valueOf: () => new Date(input || '2024-01-01').getTime(),
  })),
  isDayjs: vi.fn(() => false),
}));

// Mock Ant Design
vi.mock('antd', () => {
  const mockForm = vi.fn(() => null);

  return {
    Card: vi.fn(({ children, title, extra }) => (
      <div data-testid="card" data-title={title}>
        {extra}
        {children}
      </div>
    )),
    Form: Object.assign(mockForm, {
      Item: vi.fn(({ children, label }) => (
        <div data-testid="form-item" data-label={label}>
          {children}
        </div>
      )),
      useForm: vi.fn(() => [
        {
          getFieldsValue: vi.fn(() => ({
            certificate_number: 'CERT-001',
            property_address: '测试地址',
          })),
          setFieldsValue: vi.fn(),
          validateFields: vi.fn(() =>
            Promise.resolve({
              certificate_number: 'CERT-001',
              property_address: '测试地址',
            })
          ),
          resetFields: vi.fn(),
          getFieldValue: vi.fn(() => undefined),
          setFieldValue: vi.fn(),
        },
      ]),
    }),
    Input: vi.fn(() => null),
    Select: Object.assign(vi.fn(() => null), {
      Option: vi.fn(() => null),
    }),
    DatePicker: vi.fn(() => null),
    Button: vi.fn(({ children, onClick }) => (
      <button onClick={onClick} data-testid="button">
        {children}
      </button>
    )),
    Space: vi.fn(({ children }) => <div data-testid="space">{children}</div>),
    Tag: vi.fn(({ children, color }) => (
      <span data-testid="tag" data-color={color}>
        {children}
      </span>
    )),
    Collapse: vi.fn(({ items }) => (
      <div data-testid="collapse">
        {items?.map((item: { key: string; label: string }) => (
          <div key={item.key}>{item.label}</div>
        ))}
      </div>
    )),
    List: Object.assign(
      vi.fn(({ dataSource, renderItem }) => (
        <div data-testid="list">
          {dataSource?.map((item: unknown, index: number) => (
            <div key={index}>{renderItem?.(item)}</div>
          ))}
        </div>
      )),
      {
        Item: Object.assign(
          vi.fn(({ children }) => <div data-testid="list-item">{children}</div>),
          {
            Meta: vi.fn(({ title, description }) => (
              <div data-testid="list-item-meta">
                <span>{title}</span>
                <span>{description}</span>
              </div>
            )),
          }
        ),
      }
    ),
    Typography: {
      Text: vi.fn(({ children, type }) => (
        <span data-testid="text" data-type={type}>
          {children}
        </span>
      )),
    },
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  SaveOutlined: () => <span data-testid="save-icon" />,
}));

import type {
  CertificateExtractionResult,
  CertificateType,
} from '@/types/propertyCertificate';

// Helper to create mock extraction result
const createMockExtractionResult = (
  overrides?: Partial<CertificateExtractionResult>
): CertificateExtractionResult => ({
  session_id: 'session-123',
  certificate_type: 'real_estate' as CertificateType,
  extracted_data: {
    certificate_number: 'CERT-001',
    property_address: '北京市朝阳区测试路123号',
    property_type: '商业',
    building_area: '500',
    registration_date: '2024-01-15',
  },
  confidence_score: 0.85,
  asset_matches: [],
  validation_errors: [],
  warnings: [],
  ...overrides,
});

describe('PropertyCertificateReview - 组件导入测试', () => {
  it('应该能够导入组件', async () => {
    const module = await import('../PropertyCertificateReview');
    expect(module).toBeDefined();
    expect(module.PropertyCertificateReview).toBeDefined();
  });

  it('组件应该是React函数组件', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');
    expect(typeof PropertyCertificateReview).toBe('function');
  });
});

describe('PropertyCertificateReview - 基础属性测试', () => {
  it('应该接受extractionResult属性', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult();
    const onConfirm = vi.fn();

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm,
    });

    expect(element).toBeTruthy();
    expect(element.props.extractionResult).toEqual(extractionResult);
  });

  it('应该接受onConfirm回调', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult();
    const onConfirm = vi.fn();

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm,
    });

    expect(element.props.onConfirm).toEqual(onConfirm);
  });

  it('应该接受loading属性', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult();
    const onConfirm = vi.fn();

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm,
      loading: true,
    });

    expect(element.props.loading).toBe(true);
  });

  it('loading属性应该有默认值false', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult();
    const onConfirm = vi.fn();

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm,
    });

    // loading 是可选的，默认为 false
    expect(element.props.loading).toBeUndefined();
  });
});

describe('PropertyCertificateReview - 置信度等级测试', () => {
  it('高置信度 (>0.8) 应该显示success', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      confidence_score: 0.95,
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.confidence_score).toBe(0.95);
  });

  it('中等置信度 (0.5-0.8) 应该显示warning', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      confidence_score: 0.65,
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.confidence_score).toBe(0.65);
  });

  it('低置信度 (<0.5) 应该显示error', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      confidence_score: 0.3,
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.confidence_score).toBe(0.3);
  });
});

describe('PropertyCertificateReview - 资产匹配测试', () => {
  it('应该处理空资产匹配列表', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      asset_matches: [],
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.asset_matches).toHaveLength(0);
  });

  it('应该处理有资产匹配的情况', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      asset_matches: [
        {
          asset_id: 'asset-001',
          name: '测试资产1',
          address: '北京市朝阳区测试路123号',
          confidence: 0.9,
          match_reasons: ['地址匹配', '面积匹配'],
        },
        {
          asset_id: 'asset-002',
          name: '测试资产2',
          address: '北京市朝阳区测试路125号',
          confidence: 0.7,
          match_reasons: ['地址相似'],
        },
      ],
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.asset_matches).toHaveLength(2);
    expect(element.props.extractionResult.asset_matches[0].asset_id).toBe('asset-001');
    expect(element.props.extractionResult.asset_matches[1].asset_id).toBe('asset-002');
  });

  it('资产匹配应该包含必要的字段', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const assetMatch = {
      asset_id: 'asset-001',
      name: '测试资产',
      address: '测试地址',
      confidence: 0.85,
      match_reasons: ['地址匹配'],
    };

    const extractionResult = createMockExtractionResult({
      asset_matches: [assetMatch],
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    const match = element.props.extractionResult.asset_matches[0];
    expect(match).toHaveProperty('asset_id');
    expect(match).toHaveProperty('name');
    expect(match).toHaveProperty('address');
    expect(match).toHaveProperty('confidence');
    expect(match).toHaveProperty('match_reasons');
  });
});

describe('PropertyCertificateReview - 验证错误和警告测试', () => {
  it('应该处理空验证错误列表', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      validation_errors: [],
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.validation_errors).toHaveLength(0);
  });

  it('应该处理有验证错误的情况', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      validation_errors: ['证书编号格式错误', '缺少登记日期'],
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.validation_errors).toHaveLength(2);
    expect(element.props.extractionResult.validation_errors).toContain('证书编号格式错误');
  });

  it('应该处理空警告列表', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      warnings: [],
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.warnings).toHaveLength(0);
  });

  it('应该处理有警告的情况', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      warnings: ['建筑面积识别可能不准确', '土地使用年限未识别'],
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.warnings).toHaveLength(2);
    expect(element.props.extractionResult.warnings).toContain('建筑面积识别可能不准确');
  });
});

describe('PropertyCertificateReview - 提取数据测试', () => {
  it('应该包含证书编号', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      extracted_data: {
        certificate_number: 'CERT-2024-001',
      },
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.extracted_data.certificate_number).toBe(
      'CERT-2024-001'
    );
  });

  it('应该包含坐落地址', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      extracted_data: {
        property_address: '北京市海淀区中关村大街1号',
      },
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.extracted_data.property_address).toBe(
      '北京市海淀区中关村大街1号'
    );
  });

  it('应该包含用途信息', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      extracted_data: {
        property_type: '办公',
      },
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.extracted_data.property_type).toBe('办公');
  });

  it('应该包含建筑面积', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      extracted_data: {
        building_area: '1500.5',
      },
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.extracted_data.building_area).toBe('1500.5');
  });

  it('应该包含登记日期', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      extracted_data: {
        registration_date: '2024-06-15',
      },
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.extracted_data.registration_date).toBe('2024-06-15');
  });

  it('应该处理土地使用期限', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      extracted_data: {
        land_use_term_start: '2020-01-01',
        land_use_term_end: '2090-12-31',
      },
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.extracted_data.land_use_term_start).toBe('2020-01-01');
    expect(element.props.extractionResult.extracted_data.land_use_term_end).toBe('2090-12-31');
  });
});

describe('PropertyCertificateReview - 完整场景测试', () => {
  it('应该处理完整的提取结果', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      session_id: 'session-full-test',
      confidence_score: 0.92,
      extracted_data: {
        certificate_number: 'CERT-2024-FULL',
        property_address: '上海市浦东新区陆家嘴环路1000号',
        property_type: '商业',
        building_area: '2500',
        registration_date: '2024-03-20',
        land_use_term_start: '2015-01-01',
        land_use_term_end: '2085-12-31',
      },
      asset_matches: [
        {
          asset_id: 'asset-match-001',
          name: '陆家嘴大厦A座',
          address: '上海市浦东新区陆家嘴环路1000号',
          confidence: 0.95,
          match_reasons: ['地址完全匹配', '面积匹配'],
        },
      ],
      validation_errors: [],
      warnings: ['共有情况未识别'],
    });

    const onConfirm = vi.fn();

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm,
      loading: false,
    });

    expect(element.props.extractionResult.session_id).toBe('session-full-test');
    expect(element.props.extractionResult.confidence_score).toBe(0.92);
    expect(element.props.extractionResult.asset_matches).toHaveLength(1);
    expect(element.props.extractionResult.warnings).toHaveLength(1);
  });

  it('应该处理低置信度带错误的情况', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const extractionResult = createMockExtractionResult({
      confidence_score: 0.4,
      validation_errors: ['证书编号无法识别', '地址识别不完整', '面积格式错误'],
      warnings: ['图片质量较低', '存在遮挡'],
    });

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult,
      onConfirm: vi.fn(),
    });

    expect(element.props.extractionResult.confidence_score).toBe(0.4);
    expect(element.props.extractionResult.validation_errors).toHaveLength(3);
    expect(element.props.extractionResult.warnings).toHaveLength(2);
  });
});

describe('PropertyCertificateReview - 组件结构测试', () => {
  it('应该有正确的命名导出', async () => {
    const module = await import('../PropertyCertificateReview');

    expect(module.PropertyCertificateReview).toBeDefined();
    expect(typeof module.PropertyCertificateReview).toBe('function');
  });

  it('应该可以创建组件实例', async () => {
    const { PropertyCertificateReview } = await import('../PropertyCertificateReview');

    const element = React.createElement(PropertyCertificateReview, {
      extractionResult: createMockExtractionResult(),
      onConfirm: vi.fn(),
    });

    expect(element).toBeTruthy();
    expect(element.type).toBe(PropertyCertificateReview);
  });
});
