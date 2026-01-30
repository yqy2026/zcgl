/**
 * 数据转换工具
 * 处理前后端数据类型转换，特别是Decimal/number转换
 */

import { DecimalUtils } from '@/types/asset';

// 数据对象接口 - 支持数组和对象
type DataValue = string | number | boolean | null | undefined | DataObject | DataValue[];
interface DataObject {
  [key: string]: DataValue;
}

// 需要Decimal转换的字段列表
const DECIMAL_FIELDS = [
  // 面积字段
  'land_area',
  'actual_property_area',
  'rentable_area',
  'rented_area',
  'unrented_area',
  'non_commercial_area',
  'occupancy_rate',
  'area', // 通用面积字段

  // 金额字段
  'monthly_rent',
  'deposit',
  'annual_income',
  'annual_expense',
  'net_income',

  // 汇总字段
  'total_area',
  'total_income',
] as const;

type DecimalField = (typeof DECIMAL_FIELDS)[number];

const isDecimalField = (key: string): key is DecimalField => {
  return DECIMAL_FIELDS.includes(key as DecimalField);
};

/**
 * 类型守卫：检查是否为普通对象
 */
function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * 类型守卫：检查是否为数组
 */
function isArray(value: unknown): value is unknown[] {
  return Array.isArray(value);
}

/**
 * 将后端数据转换为前端数据
 * 处理Decimal字符串转换为number类型
 */
export const convertBackendToFrontend = <T = unknown>(data: unknown): T => {
  // 处理基本类型和null
  if (data === null || data === undefined || typeof data !== 'object') {
    return data as T;
  }

  // 处理数组
  if (isArray(data)) {
    return data.map(item => convertBackendToFrontend(item)) as T;
  }

  // 处理对象
  if (isObject(data)) {
    const result: Record<string, unknown> = {};

    for (const key in data) {
      if (Object.prototype.hasOwnProperty.call(data, key)) {
        const value = data[key];

        if (value === null || value === undefined) {
          result[key] = value;
        } else if (isDecimalField(key) && typeof value === 'string') {
          // 处理Decimal字段
          result[key] = DecimalUtils.parseDecimal(value);
        } else if (isObject(value) || isArray(value)) {
          // 递归处理嵌套对象和数组
          result[key] = convertBackendToFrontend(value);
        } else {
          result[key] = value;
        }
      }
    }

    return result as T;
  }

  return data as T;
};

/**
 * 将前端数据转换为后端数据
 * 处理number类型转换为Decimal字符串
 */
export const convertFrontendToBackend = <T = unknown>(data: unknown): T => {
  // 处理基本类型和null
  if (data === null || data === undefined || typeof data !== 'object') {
    return data as T;
  }

  // 处理数组
  if (isArray(data)) {
    return data.map(item => convertFrontendToBackend(item)) as T;
  }

  // 处理对象
  if (isObject(data)) {
    const result: Record<string, unknown> = {};

    for (const key in data) {
      if (Object.prototype.hasOwnProperty.call(data, key)) {
        const value = data[key];

        if (value === null || value === undefined) {
          result[key] = value;
        } else if (isDecimalField(key) && typeof value === 'number') {
          // 处理Decimal字段
          result[key] = DecimalUtils.formatDecimal(value);
        } else if (isObject(value) || isArray(value)) {
          // 递归处理嵌套对象和数组
          result[key] = convertFrontendToBackend(value);
        } else {
          result[key] = value;
        }
      }
    }

    return result as T;
  }

  return data as T;
};

/**
 * 安全的数值计算函数，用于前端的自动计算字段
 */
export const calculateDerivedFields = (asset: Record<string, unknown>): Record<string, unknown> => {
  const derived: Record<string, unknown> = {};

  // 计算未出租面积 = 可出租面积 - 已出租面积
  const rentableArea = asset.rentable_area;
  const rentedArea = asset.rented_area;
  if (typeof rentableArea === 'number' && typeof rentedArea === 'number') {
    derived.unrented_area = DecimalUtils.safeSubtract(rentableArea, rentedArea);
  }

  // 计算出租率 = (已出租面积 / 可出租面积) × 100%
  if (typeof rentableArea === 'number' && typeof rentedArea === 'number' && rentableArea > 0) {
    derived.occupancy_rate = DecimalUtils.safeMultiply(
      DecimalUtils.safeDivide(rentedArea, rentableArea),
      100
    );
  }

  // 计算净收益 = 年收益 - 年支出
  const annualIncome = asset.annual_income;
  const annualExpense = asset.annual_expense;
  if (typeof annualIncome === 'number' && typeof annualExpense === 'number') {
    derived.net_income = DecimalUtils.safeSubtract(annualIncome, annualExpense);
  }

  return derived;
};

/**
 * 验证数值字段的合理性
 */
export const validateNumericFields = (asset: Record<string, unknown>): string[] => {
  const errors: string[] = [];

  // 验证面积字段
  const areaFields = [
    { field: 'land_area', name: '土地面积' },
    { field: 'actual_property_area', name: '实际房产面积' },
    { field: 'rentable_area', name: '可出租面积' },
    { field: 'rented_area', name: '已出租面积' },
    { field: 'non_commercial_area', name: '非经营物业面积' },
  ];

  areaFields.forEach(({ field, name }) => {
    const value = asset[field];
    if (value !== undefined && value !== null) {
      const numValue = typeof value === 'number' ? value : parseFloat(String(value));
      if (isNaN(numValue) || numValue < 0) {
        errors.push(`${name}必须是非负数`);
      }
    }
  });

  // 验证金额字段
  const moneyFields = [
    { field: 'monthly_rent', name: '月租金' },
    { field: 'deposit', name: '押金' },
    { field: 'annual_income', name: '年收益' },
    { field: 'annual_expense', name: '年支出' },
  ];

  moneyFields.forEach(({ field, name }) => {
    const value = asset[field];
    if (value !== undefined && value !== null) {
      const numValue = typeof value === 'number' ? value : parseFloat(String(value));
      if (isNaN(numValue) || numValue < 0) {
        errors.push(`${name}必须是非负数`);
      }
    }
  });

  // 验证出租率
  const occupancyRate = asset.occupancy_rate;
  if (occupancyRate !== undefined && occupancyRate !== null) {
    const value =
      typeof occupancyRate === 'number' ? occupancyRate : parseFloat(String(occupancyRate));
    if (isNaN(value) || value < 0 || value > 100) {
      errors.push('出租率必须在0-100之间');
    }
  }

  // 验证面积逻辑关系
  const rentableArea = asset.rentable_area;
  const rentedArea = asset.rented_area;
  if (rentableArea != null && rentedArea != null) {
    const rArea =
      typeof rentableArea === 'number' ? rentableArea : parseFloat(String(rentableArea));
    const rdArea = typeof rentedArea === 'number' ? rentedArea : parseFloat(String(rentedArea));
    if (!isNaN(rArea) && !isNaN(rdArea) && rdArea > rArea) {
      errors.push('已出租面积不能大于可出租面积');
    }
  }

  return errors;
};
