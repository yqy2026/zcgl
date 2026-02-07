/**
 * 数据转换工具测试
 */

import { describe, it, expect, vi } from 'vitest';

import {
  convertBackendToFrontend,
  convertFrontendToBackend,
  calculateDerivedFields,
  validateNumericFields,
} from '../dataConversion';

// Mock DecimalUtils
vi.mock('@/types/asset', () => ({
  DecimalUtils: {
    parseDecimal: (value: string) => parseFloat(value),
    formatDecimal: (value: number) => value.toString(),
    safeSubtract: (a: number, b: number) => a - b,
    safeMultiply: (a: number, b: number) => a * b,
    safeDivide: (a: number, b: number) => a / b,
  },
}));

describe('convertBackendToFrontend', () => {
  describe('基本类型处理', () => {
    it('应该返回 null', () => {
      expect(convertBackendToFrontend(null)).toBeNull();
    });

    it('应该返回 undefined', () => {
      expect(convertBackendToFrontend(undefined)).toBeUndefined();
    });

    it('应该返回字符串原值', () => {
      expect(convertBackendToFrontend('test')).toBe('test');
    });

    it('应该返回数字原值', () => {
      expect(convertBackendToFrontend(123)).toBe(123);
    });

    it('应该返回布尔值原值', () => {
      expect(convertBackendToFrontend(true)).toBe(true);
    });
  });

  describe('Decimal 字段转换', () => {
    it('应该将 land_area 字符串转换为数字', () => {
      const data = { land_area: '100.50' };
      const result = convertBackendToFrontend<{ land_area: number }>(data);
      expect(result.land_area).toBe(100.5);
    });

    it('应该将 monthly_rent 字符串转换为数字', () => {
      const data = { monthly_rent: '5000.00' };
      const result = convertBackendToFrontend<{ monthly_rent: number }>(data);
      expect(result.monthly_rent).toBe(5000);
    });

    it('应该将 occupancy_rate 字符串转换为数字', () => {
      const data = { occupancy_rate: '85.5' };
      const result = convertBackendToFrontend<{ occupancy_rate: number }>(data);
      expect(result.occupancy_rate).toBe(85.5);
    });

    it('应该保持非 Decimal 字段不变', () => {
      const data = { name: 'Test Asset', status: 'active' };
      const result = convertBackendToFrontend(data);
      expect(result).toEqual({ name: 'Test Asset', status: 'active' });
    });

    it('应该处理 null 值的 Decimal 字段', () => {
      const data = { land_area: null };
      const result = convertBackendToFrontend(data);
      expect(result).toEqual({ land_area: null });
    });
  });

  describe('嵌套对象处理', () => {
    it('应该递归处理嵌套对象', () => {
      const data = {
        asset: {
          land_area: '200.00',
          name: 'Test',
        },
      };
      const result = convertBackendToFrontend<{ asset: { land_area: number; name: string } }>(data);
      expect(result.asset.land_area).toBe(200);
      expect(result.asset.name).toBe('Test');
    });

    it('应该递归处理数组', () => {
      const data = [{ land_area: '100.00' }, { land_area: '200.00' }];
      const result = convertBackendToFrontend<Array<{ land_area: number }>>(data);
      expect(result[0].land_area).toBe(100);
      expect(result[1].land_area).toBe(200);
    });

    it('应该处理混合嵌套结构', () => {
      const data = {
        items: [{ rentable_area: '50.00' }],
        total_area: '150.00',
      };
      const result = convertBackendToFrontend(data);
      expect(
        (result as { items: Array<{ rentable_area: number }>; total_area: number }).items[0]
          .rentable_area
      ).toBe(50);
      expect((result as { total_area: number }).total_area).toBe(150);
    });
  });
});

describe('convertFrontendToBackend', () => {
  describe('基本类型处理', () => {
    it('应该返回 null', () => {
      expect(convertFrontendToBackend(null)).toBeNull();
    });

    it('应该返回 undefined', () => {
      expect(convertFrontendToBackend(undefined)).toBeUndefined();
    });
  });

  describe('Decimal 字段转换', () => {
    it('应该将 land_area 数字转换为字符串', () => {
      const data = { land_area: 100.5 };
      const result = convertFrontendToBackend<{ land_area: string }>(data);
      expect(result.land_area).toBe('100.5');
    });

    it('应该将 monthly_rent 数字转换为字符串', () => {
      const data = { monthly_rent: 5000 };
      const result = convertFrontendToBackend<{ monthly_rent: string }>(data);
      expect(result.monthly_rent).toBe('5000');
    });

    it('应该保持非 Decimal 字段不变', () => {
      const data = { name: 'Test', count: 10 };
      const result = convertFrontendToBackend(data);
      expect(result).toEqual({ name: 'Test', count: 10 });
    });
  });

  describe('嵌套对象处理', () => {
    it('应该递归处理嵌套对象', () => {
      const data = {
        asset: {
          land_area: 200,
          name: 'Test',
        },
      };
      const result = convertFrontendToBackend(data);
      expect((result as { asset: { land_area: string } }).asset.land_area).toBe('200');
    });

    it('应该递归处理数组', () => {
      const data = [{ land_area: 100 }, { land_area: 200 }];
      const result = convertFrontendToBackend<Array<{ land_area: string }>>(data);
      expect(result[0].land_area).toBe('100');
      expect(result[1].land_area).toBe('200');
    });
  });
});

describe('calculateDerivedFields', () => {
  it('应该计算未出租面积', () => {
    const asset = { rentable_area: 1000, rented_area: 800 };
    const result = calculateDerivedFields(asset);
    expect(result.unrented_area).toBe(200);
  });

  it('应该计算出租率', () => {
    const asset = { rentable_area: 1000, rented_area: 800 };
    const result = calculateDerivedFields(asset);
    expect(result.occupancy_rate).toBe(80);
  });

  it('应该计算净收益', () => {
    const asset = { annual_income: 100000, annual_expense: 30000 };
    const result = calculateDerivedFields(asset);
    expect(result.net_income).toBe(70000);
  });

  it('当可出租面积为0时不应计算出租率', () => {
    const asset = { rentable_area: 0, rented_area: 0 };
    const result = calculateDerivedFields(asset);
    expect(result.occupancy_rate).toBeUndefined();
  });

  it('当缺少必要字段时不应计算', () => {
    const asset = { name: 'Test' };
    const result = calculateDerivedFields(asset);
    expect(result.unrented_area).toBeUndefined();
    expect(result.occupancy_rate).toBeUndefined();
    expect(result.net_income).toBeUndefined();
  });
});

describe('validateNumericFields', () => {
  describe('面积字段验证', () => {
    it('应该通过有效的面积值', () => {
      const asset = { land_area: 100, rentable_area: 50 };
      const errors = validateNumericFields(asset);
      expect(errors).toHaveLength(0);
    });

    it('应该拒绝负数面积', () => {
      const asset = { land_area: -100 };
      const errors = validateNumericFields(asset);
      expect(errors).toContain('土地面积必须是非负数');
    });

    it('应该拒绝非数字面积', () => {
      const asset = { land_area: 'abc' };
      const errors = validateNumericFields(asset);
      expect(errors).toContain('土地面积必须是非负数');
    });
  });

  describe('金额字段验证', () => {
    it('应该通过有效的金额值', () => {
      const asset = { monthly_rent: 5000, deposit: 10000 };
      const errors = validateNumericFields(asset);
      expect(errors).toHaveLength(0);
    });

    it('应该拒绝负数金额', () => {
      const asset = { monthly_rent: -1000 };
      const errors = validateNumericFields(asset);
      expect(errors).toContain('月租金必须是非负数');
    });
  });

  describe('出租率验证', () => {
    it('应该通过有效的出租率', () => {
      const asset = { occupancy_rate: 85.5 };
      const errors = validateNumericFields(asset);
      expect(errors).toHaveLength(0);
    });

    it('应该拒绝超过100的出租率', () => {
      const asset = { occupancy_rate: 150 };
      const errors = validateNumericFields(asset);
      expect(errors).toContain('出租率必须在0-100之间');
    });

    it('应该拒绝负数出租率', () => {
      const asset = { occupancy_rate: -10 };
      const errors = validateNumericFields(asset);
      expect(errors).toContain('出租率必须在0-100之间');
    });
  });

  describe('面积逻辑验证', () => {
    it('应该通过已出租面积小于可出租面积', () => {
      const asset = { rentable_area: 1000, rented_area: 800 };
      const errors = validateNumericFields(asset);
      expect(errors).toHaveLength(0);
    });

    it('应该拒绝已出租面积大于可出租面积', () => {
      const asset = { rentable_area: 500, rented_area: 800 };
      const errors = validateNumericFields(asset);
      expect(errors).toContain('已出租面积不能大于可出租面积');
    });
  });

  describe('空值处理', () => {
    it('应该忽略 undefined 字段', () => {
      const asset = { land_area: undefined };
      const errors = validateNumericFields(asset);
      expect(errors).toHaveLength(0);
    });

    it('应该忽略 null 字段', () => {
      const asset = { land_area: null };
      const errors = validateNumericFields(asset);
      expect(errors).toHaveLength(0);
    });
  });
});
