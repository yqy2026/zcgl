/**
 * useFormFieldVisibility Hook 测试
 * 覆盖经营模式（revenue_mode）随业态类别显隐的规则
 */

import { describe, it, expect } from 'vitest';
import type { UseFormWatch } from 'react-hook-form';
import { renderHook, act } from '@/test/utils/test-helpers';
import type { AssetFormData } from '@/assetFormSchema';
import { useFormFieldVisibility } from '../useFormFieldVisibility';

const setup = () => {
  let emit: (values: Partial<AssetFormData>) => void = () => {};
  const watch = ((callback: (values: Partial<AssetFormData>) => void) => {
    emit = callback;
    return { unsubscribe: () => {} };
  }) as unknown as UseFormWatch<AssetFormData>;

  const { result } = renderHook(() => useFormFieldVisibility(watch));
  const isRevenueModeVisible = (values: Partial<AssetFormData>): boolean => {
    act(() => emit(values));
    return result.current.isFieldVisible('revenue_mode');
  };
  return { isRevenueModeVisible };
};

describe('useFormFieldVisibility - revenue_mode', () => {
  it('有业态类别时显示经营模式', () => {
    const { isRevenueModeVisible } = setup();
    expect(isRevenueModeVisible({ business_category: '零售' })).toBe(true);
  });

  it('业态类别缺失时隐藏经营模式', () => {
    const { isRevenueModeVisible } = setup();
    expect(isRevenueModeVisible({})).toBe(false);
    expect(isRevenueModeVisible({ business_category: undefined })).toBe(false);
  });

  it('业态类别为空串或纯空白时隐藏经营模式', () => {
    const { isRevenueModeVisible } = setup();
    expect(isRevenueModeVisible({ business_category: '' })).toBe(false);
    expect(isRevenueModeVisible({ business_category: '   ' })).toBe(false);
  });
});
