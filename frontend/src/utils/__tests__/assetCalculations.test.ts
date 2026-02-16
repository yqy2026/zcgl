import { describe, expect, it } from 'vitest';

import { UsageStatus, type Asset } from '@/types/asset';
import {
  calculateOccupancyRate,
  calculateUnrentedArea,
  checkAssetDataCompleteness,
  formatArea,
  formatCalculationResult,
  formatOccupancyRate,
  getAssetSummary,
  validateAreaData,
} from '@/utils/assetCalculations';

describe('assetCalculations', () => {
  it('calculateUnrentedArea 应按可出租面积减去已出租面积计算', () => {
    const result = calculateUnrentedArea({
      rentable_area: 100,
      rented_area: 60,
    });

    expect(result).toBe(40);
    expect(calculateUnrentedArea({ rentable_area: undefined, rented_area: 20 })).toBeUndefined();
  });

  it('calculateOccupancyRate 应处理开关与边界值', () => {
    expect(
      calculateOccupancyRate({
        include_in_occupancy_rate: false,
        rentable_area: 100,
        rented_area: 80,
      })
    ).toBe(0);

    expect(
      calculateOccupancyRate({
        include_in_occupancy_rate: true,
        rentable_area: 0,
        rented_area: 80,
      })
    ).toBe(0);

    expect(
      calculateOccupancyRate({
        include_in_occupancy_rate: true,
        rentable_area: 100,
        rented_area: undefined,
      })
    ).toBe(0);

    expect(
      calculateOccupancyRate({
        include_in_occupancy_rate: true,
        rentable_area: 200,
        rented_area: 50,
      })
    ).toBe(25);
  });

  it('validateAreaData 应返回面积逻辑错误', () => {
    const result = validateAreaData({
      land_area: 100,
      actual_property_area: 120,
      rentable_area: 80,
      rented_area: 90,
      non_commercial_area: 81,
    });

    expect(result.isValid).toBe(false);
    expect(result.errors).toEqual(
      expect.arrayContaining([
        '已出租面积不能大于可出租面积',
        '实际房产面积不能大于土地面积',
        '非经营物业面积不能大于可出租面积',
      ])
    );
  });

  it('validateAreaData 应校验负数面积', () => {
    const result = validateAreaData({
      land_area: -1,
      actual_property_area: -2,
      rentable_area: -3,
      rented_area: -4,
      non_commercial_area: -5,
    });

    expect(result.errors).toEqual(
      expect.arrayContaining([
        '土地面积不能为负数',
        '实际房产面积不能为负数',
        '可出租面积不能为负数',
        '已出租面积不能为负数',
        '非经营物业面积不能为负数',
      ])
    );
  });

  it('格式化函数应按预期输出', () => {
    expect(formatCalculationResult(undefined)).toBe('-');
    expect(formatCalculationResult(Number.NaN)).toBe('-');
    expect(formatCalculationResult(12.3456)).toBe('12.35');
    expect(formatCalculationResult(12.3456, 1, ' m2')).toBe('12.3 m2');
    expect(formatArea(10)).toBe('10.00 m²');
    expect(formatOccupancyRate(88.888)).toBe('88.89%');
  });

  it('getAssetSummary 应汇总面积与状态统计', () => {
    const assets: Partial<Asset>[] = [
      {
        rentable_area: 100,
        rented_area: 60,
        non_commercial_area: 10,
        usage_status: UsageStatus.RENTED,
      },
      {
        rentable_area: 200,
        rented_area: 40,
        non_commercial_area: 20,
        usage_status: UsageStatus.SUBLEASE,
      },
      {
        rentable_area: 50,
        rented_area: 0,
        non_commercial_area: 5,
        usage_status: UsageStatus.VACANT,
      },
      {
        rentable_area: undefined,
        rented_area: undefined,
        non_commercial_area: undefined,
        usage_status: UsageStatus.VACANT_PLANNING,
      },
    ];

    const summary = getAssetSummary(assets);
    expect(summary.totalAssets).toBe(4);
    expect(summary.totalRentableArea).toBe(350);
    expect(summary.totalRentedArea).toBe(100);
    expect(summary.totalUnrentedArea).toBe(250);
    expect(summary.totalNonCommercialArea).toBe(35);
    expect(summary.overallOccupancyRate).toBeCloseTo(28.57, 2);
    expect(summary.rentedAssets).toBe(2);
    expect(summary.vacantAssets).toBe(2);
    expect(summary.summary.totalArea).toBe(385);
    expect(summary.summary.utilizedArea).toBe(135);
    expect(summary.summary.utilizationRate).toBeCloseTo(35.06, 2);
  });

  it('checkAssetDataCompleteness 应返回完整度与缺失字段', () => {
    const result = checkAssetDataCompleteness({
      ownership_id: 'own-1',
      property_name: 'P1',
      address: 'A1',
      ownership_status: '已确权' as Asset['ownership_status'],
      property_nature: '经营性' as Asset['property_nature'],
      usage_status: '出租' as Asset['usage_status'],
      rentable_area: 100,
    });

    expect(result.completeness).toBe(64);
    expect(result.missingFields).toEqual(
      expect.arrayContaining(['rented_area', 'monthly_rent', 'contract_start_date', 'contract_end_date'])
    );
    expect(result.optionalFields).toContain('notes');
  });
});
