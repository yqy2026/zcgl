import { useState, useEffect, useCallback } from 'react';
import { UseFormWatch, FieldValues } from 'react-hook-form';
import type { AssetFormData } from '@/assetFormSchema';

/**
 * 泛型字段可见性规则接口
 */
export interface FieldVisibilityRule<T extends FieldValues> {
  field: keyof T;
  condition: (values: T) => boolean;
  dependsOn: (keyof T)[];
}

/**
 * Asset表单专用的字段可见性规则
 */
export type AssetFieldVisibilityRule = FieldVisibilityRule<AssetFormData>;

const hasProjectName = (values: AssetFormData): boolean => {
  const projectName = values.project_name;
  return projectName != null && projectName.trim() !== '';
};

// 字段显示规则配置 - Asset表单专用
const assetFieldVisibilityRules: FieldVisibilityRule<AssetFormData>[] = [
  // 经营类物业才显示出租相关字段
  {
    field: 'rentable_area',
    condition: values => values.property_nature === '经营类',
    dependsOn: ['property_nature'],
  },
  {
    field: 'rented_area',
    condition: values => values.property_nature === '经营类',
    dependsOn: ['property_nature'],
  },
  {
    field: 'unrented_area',
    condition: values => values.property_nature === '经营类',
    dependsOn: ['property_nature'],
  },
  {
    field: 'occupancy_rate',
    condition: values => values.property_nature === '经营类',
    dependsOn: ['property_nature'],
  },
  {
    field: 'include_in_occupancy_rate',
    condition: values => values.property_nature === '经营类',
    dependsOn: ['property_nature'],
  },

  // 非经营类物业显示非经营面积
  {
    field: 'non_commercial_area',
    condition: values => values.property_nature === '非经营类',
    dependsOn: ['property_nature'],
  },

  // 有业态类别时显示经营模式
  {
    field: 'revenue_mode',
    condition: values => values.business_category?.trim() !== '',
    dependsOn: ['business_category'],
  },

  // 有项目名称时显示接收协议日期
  {
    field: 'operation_agreement_start_date',
    condition: hasProjectName,
    dependsOn: ['project_name'],
  },
  {
    field: 'operation_agreement_end_date',
    condition: hasProjectName,
    dependsOn: ['project_name'],
  },
  {
    field: 'operation_agreement_attachments',
    condition: hasProjectName,
    dependsOn: ['project_name'],
  },
];

/**
 * 泛型表单字段可见性管理Hook
 *
 * @template T - 表单数据类型，必须继承FieldValues
 * @param watch - react-hook-form的watch函数
 * @param rules - 字段可见性规则数组
 * @returns 字段可见性控制函数和状态
 *
 * @example
 * // 使用自定义表单类型
 * interface MyFormData {
 *   category: string;
 *   subCategory: string;
 * }
 *
 * const rules: FieldVisibilityRule<MyFormData>[] = [
 *   {
 *     field: 'subCategory',
 *     condition: (values) => values.category === 'special',
 *     dependsOn: ['category']
 *   }
 * ];
 *
 * const { isFieldVisible } = useGenericFormFieldVisibility<MyFormData>(watch, rules);
 */
export const useGenericFormFieldVisibility = <T extends FieldValues>(
  watch: UseFormWatch<T>,
  rules: FieldVisibilityRule<T>[]
) => {
  const [visibleFields, setVisibleFields] = useState<Set<keyof T>>(new Set());
  const [hiddenFields, setHiddenFields] = useState<Set<keyof T>>(new Set());

  useEffect(() => {
    const subscription = watch(values => {
      const newVisibleFields = new Set<keyof T>();
      const newHiddenFields = new Set<keyof T>();

      // 检查每个字段的可见性规则
      rules.forEach(rule => {
        const shouldShow = rule.condition(values as T);

        if (shouldShow) {
          newVisibleFields.add(rule.field);
          newHiddenFields.delete(rule.field);
        } else {
          newHiddenFields.add(rule.field);
          newVisibleFields.delete(rule.field);
        }
      });

      setVisibleFields(newVisibleFields);
      setHiddenFields(newHiddenFields);
    });

    return () => subscription.unsubscribe();
  }, [watch, rules]);

  // 检查字段是否可见
  const isFieldVisible = useCallback(
    (fieldName: keyof T): boolean => {
      // 如果没有规则定义，默认可见
      const hasRule = rules.some(rule => rule.field === fieldName);
      if (!hasRule) return true;

      // 根据规则判断
      return visibleFields.has(fieldName) && !hiddenFields.has(fieldName);
    },
    [rules, visibleFields, hiddenFields]
  );

  // 检查字段是否隐藏
  const isFieldHidden = useCallback(
    (fieldName: keyof T): boolean => {
      return hiddenFields.has(fieldName);
    },
    [hiddenFields]
  );

  // 获取字段的依赖关系
  const getFieldDependencies = useCallback(
    (fieldName: keyof T): (keyof T)[] => {
      const rule = rules.find(r => r.field === fieldName);
      return rule?.dependsOn ?? [];
    },
    [rules]
  );

  // 获取所有隐藏字段
  const getAllHiddenFields = useCallback((): (keyof T)[] => {
    return Array.from(hiddenFields);
  }, [hiddenFields]);

  return {
    isFieldVisible,
    isFieldHidden,
    getFieldDependencies,
    getAllHiddenFields,
    visibleFields,
    hiddenFields,
  };
};

/**
 * Asset表单字段可见性管理Hook
 * 使用预定义的Asset表单规则
 */
export const useFormFieldVisibility = (watch: UseFormWatch<AssetFormData>) => {
  const result = useGenericFormFieldVisibility<AssetFormData>(watch, assetFieldVisibilityRules);

  // 获取所有可见字段 - Asset专用
  const getAllVisibleFields = useCallback((): (keyof AssetFormData)[] => {
    const allFields = Object.keys({} as AssetFormData) as (keyof AssetFormData)[];
    return allFields.filter(field => result.isFieldVisible(field));
  }, [result]);

  return {
    ...result,
    getAllVisibleFields,
  };
};

/**
 * 泛型表单字段分组可见性Hook
 */
export const useGenericFormGroupVisibility = <T extends FieldValues>(
  watch: UseFormWatch<T>,
  rules: FieldVisibilityRule<T>[]
) => {
  const { isFieldVisible } = useGenericFormFieldVisibility(watch, rules);

  // 检查字段组是否应该显示
  const isGroupVisible = useCallback(
    (groupFields: (keyof T)[]): boolean => {
      return groupFields.some(field => isFieldVisible(field));
    },
    [isFieldVisible]
  );

  // 获取组内可见字段
  const getVisibleFieldsInGroup = useCallback(
    (groupFields: (keyof T)[]): (keyof T)[] => {
      return groupFields.filter(field => isFieldVisible(field));
    },
    [isFieldVisible]
  );

  // 获取组内隐藏字段
  const getHiddenFieldsInGroup = useCallback(
    (groupFields: (keyof T)[]): (keyof T)[] => {
      return groupFields.filter(field => !isFieldVisible(field));
    },
    [isFieldVisible]
  );

  return {
    isGroupVisible,
    getVisibleFieldsInGroup,
    getHiddenFieldsInGroup,
  };
};

/**
 * Asset表单字段分组可见性Hook（向后兼容）
 */
export const useFormGroupVisibility = (watch: UseFormWatch<AssetFormData>) => {
  return useGenericFormGroupVisibility(watch, assetFieldVisibilityRules);
};

/**
 * 泛型表单验证规则动态调整Hook
 */
export const useGenericDynamicValidation = <T extends FieldValues>(
  watch: UseFormWatch<T>,
  rules: FieldVisibilityRule<T>[]
) => {
  const { isFieldVisible } = useGenericFormFieldVisibility(watch, rules);

  // 检查字段是否需要验证
  const shouldValidateField = useCallback(
    (fieldName: keyof T): boolean => {
      return isFieldVisible(fieldName);
    },
    [isFieldVisible]
  );

  return {
    shouldValidateField,
  };
};

/**
 * Asset表单验证规则动态调整Hook（向后兼容）
 */
export const useDynamicValidation = (watch: UseFormWatch<AssetFormData>) => {
  const result = useGenericDynamicValidation(watch, assetFieldVisibilityRules);
  const { isFieldVisible } = useGenericFormFieldVisibility(watch, assetFieldVisibilityRules);

  // 获取当前应该验证的字段 - Asset专用
  const getValidationFields = useCallback((): (keyof AssetFormData)[] => {
    const allFields = Object.keys({} as AssetFormData) as (keyof AssetFormData)[];
    return allFields.filter(field => isFieldVisible(field));
  }, [isFieldVisible]);

  return {
    ...result,
    getValidationFields,
  };
};

// 导出规则以便其他地方使用
export { assetFieldVisibilityRules };

