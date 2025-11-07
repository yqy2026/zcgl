/**
 * 数据转换工具
 * 处理前后端数据类型转换，特别是Decimal/number转换
 */

import { DecimalUtils } from '@/types/asset'

// 数据对象接口
interface DataObject {
  [key: string]: unknown;
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

  // 金额字段
  'monthly_rent',
  'deposit',
  'annual_income',
  'annual_expense',
  'net_income'
]

/**
 * 将后端数据转换为前端数据
 * 处理Decimal字符串转换为number类型
 */
export const convertBackendToFrontend = <T = unknown>(data: unknown): T => {
  if (!data || typeof data !== 'object') {
    return data
  }

  const result: DataObject = Array.isArray(data) ? [] : {}

  for (const key in data) {
    if (Object.prototype.hasOwnProperty.call(data, key)) {
      const value = data[key]

      if (value === null || value === undefined) {
        result[key] = value
      } else if (DECIMAL_FIELDS.includes(key) && typeof value === 'string') {
        // 处理Decimal字段
        result[key] = DecimalUtils.parseDecimal(value)
      } else if (typeof value === 'object') {
        // 递归处理嵌套对象
        result[key] = convertBackendToFrontend(value)
      } else {
        result[key] = value
      }
    }
  }

  return result as T
}

/**
 * 将前端数据转换为后端数据
 * 处理number类型转换为Decimal字符串
 */
export const convertFrontendToBackend = <T = unknown>(data: unknown): T => {
  if (!data || typeof data !== 'object') {
    return data
  }

  const result: DataObject = Array.isArray(data) ? [] : {}

  for (const key in data) {
    if (Object.prototype.hasOwnProperty.call(data, key)) {
      const value = data[key]

      if (value === null || value === undefined) {
        result[key] = value
      } else if (DECIMAL_FIELDS.includes(key) && typeof value === 'number') {
        // 处理Decimal字段
        result[key] = DecimalUtils.formatDecimal(value)
      } else if (typeof value === 'object') {
        // 递归处理嵌套对象
        result[key] = convertFrontendToBackend(value)
      } else {
        result[key] = value
      }
    }
  }

  return result as T
}

/**
 * 安全的数值计算函数，用于前端的自动计算字段
 */
export const calculateDerivedFields = (asset: DataObject) => {
  const derived: DataObject = {}

  // 计算未出租面积 = 可出租面积 - 已出租面积
  if (asset.rentable_area && asset.rented_area) {
    derived.unrented_area = DecimalUtils.safeSubtract(asset.rentable_area, asset.rented_area)
  }

  // 计算出租率 = (已出租面积 / 可出租面积) × 100%
  if (asset.rentable_area && asset.rented_area && asset.rentable_area > 0) {
    derived.occupancy_rate = DecimalUtils.safeMultiply(
      DecimalUtils.safeDivide(asset.rented_area, asset.rentable_area),
      100
    )
  }

  // 计算净收益 = 年收益 - 年支出
  if (asset.annual_income && asset.annual_expense) {
    derived.net_income = DecimalUtils.safeSubtract(asset.annual_income, asset.annual_expense)
  }

  return derived
}

/**
 * 验证数值字段的合理性
 */
export const validateNumericFields = (asset: DataObject) => {
  const errors: string[] = []

  // 验证面积字段
  const areaFields = [
    { field: 'land_area', name: '土地面积' },
    { field: 'actual_property_area', name: '实际房产面积' },
    { field: 'rentable_area', name: '可出租面积' },
    { field: 'rented_area', name: '已出租面积' },
    { field: 'non_commercial_area', name: '非经营物业面积' }
  ]

  areaFields.forEach(({ field, name }) => {
    if (asset[field] !== undefined && asset[field] !== null) {
      const value = parseFloat(asset[field])
      if (isNaN(value) || value < 0) {
        errors.push(`${name}必须是非负数`)
      }
    }
  })

  // 验证金额字段
  const moneyFields = [
    { field: 'monthly_rent', name: '月租金' },
    { field: 'deposit', name: '押金' },
    { field: 'annual_income', name: '年收益' },
    { field: 'annual_expense', name: '年支出' }
  ]

  moneyFields.forEach(({ field, name }) => {
    const fieldValue = (asset as any)[field]
    if (fieldValue !== undefined && fieldValue !== null) {
      const value = parseFloat(String(fieldValue))
      if (isNaN(value) || value < 0) {
        errors.push(`${name}必须是非负数`)
      }
    }
  })

  // 验证出租率
  if (asset.occupancy_rate !== undefined && asset.occupancy_rate !== null) {
    const value = parseFloat(String(asset.occupancy_rate))
    if (isNaN(value) || value < 0 || value > 100) {
      errors.push('出租率必须在0-100之间')
    }
  }

  // 验证面积逻辑关系
  if (asset.rentable_area && asset.rented_area) {
    const rentableArea = parseFloat(String(asset.rentable_area))
    const rentedArea = parseFloat(String(asset.rented_area))
    if (rentedArea > rentableArea) {
      errors.push('已出租面积不能大于可出租面积')
    }
  }

  return errors
}