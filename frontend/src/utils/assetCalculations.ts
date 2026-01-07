/**
 * 资产计算工具函数
 * 用于前端计算和显示计算字段，与后端逻辑保持一致
 */

import type { Asset } from '@/types/asset';
import { DecimalUtils, UsageStatus } from '@/types/asset';

/**
 * 计算未出租面积
 * 公式: rentableArea - rentedArea
 *
 * @param asset 资产对象
 * @returns 未出租面积，如果无法计算则返回 undefined
 */
export const calculateUnrentedArea = (asset: Partial<Asset>): number | undefined => {
  const rentableArea = DecimalUtils.parseDecimal(asset.rentable_area);
  const rentedArea = DecimalUtils.parseDecimal(asset.rented_area);

  if (rentableArea === undefined || rentedArea === undefined) {
    return undefined;
  }

  return DecimalUtils.safeSubtract(rentableArea, rentedArea);
};

/**
 * 计算出租率（百分比）
 * 公式: (rentedArea / rentableArea) * 100
 *
 * @param asset 资产对象
 * @returns 出租率百分比（0-100），如果无法计算则返回 undefined
 */
export const calculateOccupancyRate = (asset: Partial<Asset>): number | undefined => {
  const rentableArea = DecimalUtils.parseDecimal(asset.rentable_area);
  const rentedArea = DecimalUtils.parseDecimal(asset.rented_area);

  // 如果不计入出租率统计，返回0
  if (asset.include_in_occupancy_rate === false) {
    return 0;
  }

  // 如果可出租面积为0或未定义，返回0
  if (rentableArea === undefined || rentableArea === 0) {
    return 0;
  }

  if (rentedArea === undefined) {
    return 0;
  }

  return DecimalUtils.safeDivide(DecimalUtils.safeMultiply(rentedArea, 100), rentableArea);
};

/**
 * 验证面积数据的合理性
 *
 * @param asset 资产对象
 * @returns 验证结果，包含是否有效和错误信息
 */
export const validateAreaData = (
  asset: Partial<Asset>
): {
  isValid: boolean;
  errors: string[];
} => {
  const errors: string[] = [];

  const rentableArea = DecimalUtils.parseDecimal(asset.rentable_area);
  const rentedArea = DecimalUtils.parseDecimal(asset.rented_area);
  const landArea = DecimalUtils.parseDecimal(asset.land_area);
  const actualPropertyArea = DecimalUtils.parseDecimal(asset.actual_property_area);
  const nonCommercialArea = DecimalUtils.parseDecimal(asset.non_commercial_area);

  // 检查基本逻辑：已出租面积不能大于可出租面积
  if (rentableArea !== undefined && rentedArea !== undefined) {
    if (rentedArea > rentableArea) {
      errors.push('已出租面积不能大于可出租面积');
    }
  }

  // 检查实际房产面积合理性
  if (actualPropertyArea !== undefined && landArea !== undefined) {
    if (actualPropertyArea > landArea) {
      errors.push('实际房产面积不能大于土地面积');
    }
  }

  // 检查非经营面积合理性
  if (rentableArea !== undefined && nonCommercialArea !== undefined) {
    if (nonCommercialArea > rentableArea) {
      errors.push('非经营物业面积不能大于可出租面积');
    }
  }

  // 检查所有面积都应该是正数
  const areas = [
    { name: '土地面积', value: landArea },
    { name: '实际房产面积', value: actualPropertyArea },
    { name: '可出租面积', value: rentableArea },
    { name: '已出租面积', value: rentedArea },
    { name: '非经营物业面积', value: nonCommercialArea },
  ];

  areas.forEach(area => {
    if (area.value !== undefined && area.value < 0) {
      errors.push(`${area.name}不能为负数`);
    }
  });

  return {
    isValid: errors.length === 0,
    errors,
  };
};

/**
 * 获取计算字段的显示格式
 *
 * @param value 数值
 * @param decimals 小数位数
 * @param suffix 单位后缀
 * @returns 格式化后的字符串
 */
export const formatCalculationResult = (
  value: number | undefined,
  decimals: number = 2,
  suffix: string = ''
): string => {
  if (value === undefined || isNaN(value)) {
    return '-';
  }

  return `${value.toFixed(decimals)}${suffix}`;
};

/**
 * 格式化面积显示
 *
 * @param area 面积数值
 * @returns 格式化后的面积字符串（带单位）
 */
export const formatArea = (area: number | undefined): string => {
  return formatCalculationResult(area, 2, ' m²');
};

/**
 * 格式化出租率显示
 *
 * @param rate 出租率数值
 * @returns 格式化后的出租率字符串（带百分比符号）
 */
export const formatOccupancyRate = (rate: number | undefined): string => {
  return formatCalculationResult(rate, 2, '%');
};

/**
 * 获取资产统计摘要
 *
 * @param assets 资产列表
 * @returns 统计摘要信息
 */
export const getAssetSummary = (assets: Partial<Asset>[]) => {
  const totalAssets = assets.length;

  let totalRentableArea = 0;
  let totalRentedArea = 0;
  let totalNonCommercialArea = 0;

  let rentedAssets = 0;
  let vacantAssets = 0;

  assets.forEach(asset => {
    const rentableArea =
      DecimalUtils.parseDecimal(asset.rentable_area) !== null &&
      DecimalUtils.parseDecimal(asset.rentable_area) !== undefined
        ? DecimalUtils.parseDecimal(asset.rentable_area)
        : 0;
    const rentedArea =
      DecimalUtils.parseDecimal(asset.rented_area) !== null &&
      DecimalUtils.parseDecimal(asset.rented_area) !== undefined
        ? DecimalUtils.parseDecimal(asset.rented_area)
        : 0;
    const nonCommercialArea =
      DecimalUtils.parseDecimal(asset.non_commercial_area) !== null &&
      DecimalUtils.parseDecimal(asset.non_commercial_area) !== undefined
        ? DecimalUtils.parseDecimal(asset.non_commercial_area)
        : 0;
    const usageStatus = asset.usage_status;

    totalRentableArea = DecimalUtils.safeAdd(totalRentableArea, rentableArea);
    totalRentedArea = DecimalUtils.safeAdd(totalRentedArea, rentedArea);
    totalNonCommercialArea = DecimalUtils.safeAdd(totalNonCommercialArea, nonCommercialArea);

    if (usageStatus === UsageStatus.RENTED || usageStatus === UsageStatus.SUBLEASE) {
      rentedAssets++;
    } else if (usageStatus === UsageStatus.VACANT || usageStatus === UsageStatus.VACANT_PLANNING) {
      vacantAssets++;
    }
  });

  const totalUnrentedArea = DecimalUtils.safeSubtract(totalRentableArea, totalRentedArea);
  const overallOccupancyRate =
    totalRentableArea > 0
      ? DecimalUtils.safeDivide(DecimalUtils.safeMultiply(totalRentedArea, 100), totalRentableArea)
      : 0;

  return {
    totalAssets,
    totalRentableArea,
    totalRentedArea,
    totalUnrentedArea,
    totalNonCommercialArea,
    overallOccupancyRate,
    rentedAssets,
    vacantAssets,
    summary: {
      totalArea: totalRentableArea + totalNonCommercialArea,
      utilizedArea: totalRentedArea + totalNonCommercialArea,
      utilizationRate:
        totalRentableArea + totalNonCommercialArea > 0
          ? ((totalRentedArea + totalNonCommercialArea) /
              (totalRentableArea + totalNonCommercialArea)) *
            100
          : 0,
    },
  };
};

/**
 * 检查资产数据完整性
 *
 * @param asset 资产对象
 * @returns 完整性检查结果
 */
export const checkAssetDataCompleteness = (
  asset: Partial<Asset>
): {
  completeness: number;
  missingFields: string[];
  optionalFields: string[];
} => {
  // 必填字段
  const requiredFields = [
    'ownership_entity',
    'property_name',
    'address',
    'ownership_status',
    'property_nature',
    'usage_status',
  ];

  // 重要但可选的字段
  const importantOptionalFields = [
    'rentable_area',
    'rented_area',
    'monthly_rent',
    'contract_start_date',
    'contract_end_date',
  ];

  // 真正可选的字段
  const trulyOptionalFields = [
    'project_name',
    'ownership_category',
    'business_category',
    'certificated_usage',
    'actual_usage',
    'tenant_name',
    'tenant_type',
    'lease_contract_number',
    'deposit',
    'manager_name',
    'business_model',
    'operation_status',
    'notes',
  ];

  const missingRequired: string[] = [];
  const missingImportant: string[] = [];

  // 检查必填字段
  requiredFields.forEach(field => {
    const value = asset[field as keyof Asset];
    if (value === null || value === undefined || (typeof value === 'string' && !value.trim())) {
      missingRequired.push(field);
    }
  });

  // 检查重要可选字段
  importantOptionalFields.forEach(field => {
    if (asset[field as keyof Asset] === undefined || asset[field as keyof Asset] === null) {
      missingImportant.push(field);
    }
  });

  const allMissingFields = [...missingRequired, ...missingImportant];
  const totalFields = requiredFields.length + importantOptionalFields.length;

  const completeness =
    totalFields > 0 ? ((totalFields - allMissingFields.length) / totalFields) * 100 : 100;

  return {
    completeness: Math.round(completeness),
    missingFields: allMissingFields,
    optionalFields: trulyOptionalFields,
  };
};
