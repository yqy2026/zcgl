import { useState, useEffect } from 'react'
import { UseFormWatch } from 'react-hook-form'
import type { AssetFormData } from '@/schemas/assetFormSchema'

interface FieldVisibilityRule {
  field: keyof AssetFormData
  condition: (values: AssetFormData) => boolean
  dependsOn: (keyof AssetFormData)[]
}

// 字段显示规则配置
const fieldVisibilityRules: FieldVisibilityRule[] = [
  // 经营类物业才显示出租相关字段
  {
    field: 'rentable_area',
    condition: (values) => values.property_nature === '经营类',
    dependsOn: ['property_nature'],
  },
  {
    field: 'rented_area',
    condition: (values) => values.property_nature === '经营类',
    dependsOn: ['property_nature'],
  },
  {
    field: 'unrented_area',
    condition: (values) => values.property_nature === '经营类',
    dependsOn: ['property_nature'],
  },
  {
    field: 'occupancy_rate',
    condition: (values) => values.property_nature === '经营类',
    dependsOn: ['property_nature'],
  },
  {
    field: 'include_in_occupancy_rate',
    condition: (values) => values.property_nature === '经营类',
    dependsOn: ['property_nature'],
  },

  // 出租状态才显示租户和合同信息
  {
    field: 'tenant_name',
    condition: (values) => values.usage_status === '出租',
    dependsOn: ['usage_status'],
  },
  {
    field: 'lease_contract',
    condition: (values) => values.usage_status === '出租',
    dependsOn: ['usage_status'],
  },
  {
    field: 'current_contract_start_date',
    condition: (values) => values.usage_status === '出租',
    dependsOn: ['usage_status'],
  },
  {
    field: 'current_contract_end_date',
    condition: (values) => values.usage_status === '出租',
    dependsOn: ['usage_status'],
  },
  {
    field: 'current_lease_contract',
    condition: (values) => values.usage_status === '出租',
    dependsOn: ['usage_status'],
  },

  // 非经营类物业显示非经营面积
  {
    field: 'non_commercial_area',
    condition: (values) => values.property_nature === '非经营类',
    dependsOn: ['property_nature'],
  },

  // 有业态类别时显示接收模式
  {
    field: 'business_model',
    condition: (values) => Boolean(values.business_category && values.business_category.trim()),
    dependsOn: ['business_category'],
  },

  // 有五羊项目名称时显示接收协议日期
  {
    field: 'operation_agreement_start_date',
    condition: (values) => Boolean(values.wuyang_project_name && values.wuyang_project_name.trim()),
    dependsOn: ['wuyang_project_name'],
  },
  {
    field: 'operation_agreement_end_date',
    condition: (values) => Boolean(values.wuyang_project_name && values.wuyang_project_name.trim()),
    dependsOn: ['wuyang_project_name'],
  },
  {
    field: 'operation_agreement_attachments',
    condition: (values) => Boolean(values.wuyang_project_name && values.wuyang_project_name.trim()),
    dependsOn: ['wuyang_project_name'],
  },
]

/**
 * 表单字段可见性管理Hook
 */
export const useFormFieldVisibility = (watch: UseFormWatch<AssetFormData>) => {
  const [visibleFields, setVisibleFields] = useState<Set<keyof AssetFormData>>(new Set())
  const [hiddenFields, setHiddenFields] = useState<Set<keyof AssetFormData>>(new Set())

  useEffect(() => {
    const subscription = watch((values) => {
      const newVisibleFields = new Set<keyof AssetFormData>()
      const newHiddenFields = new Set<keyof AssetFormData>()

      // 检查每个字段的可见性规则
      fieldVisibilityRules.forEach((rule) => {
        const shouldShow = rule.condition(values as AssetFormData)
        
        if (shouldShow) {
          newVisibleFields.add(rule.field)
          newHiddenFields.delete(rule.field)
        } else {
          newHiddenFields.add(rule.field)
          newVisibleFields.delete(rule.field)
        }
      })

      setVisibleFields(newVisibleFields)
      setHiddenFields(newHiddenFields)
    })

    return () => subscription.unsubscribe()
  }, [watch])

  // 检查字段是否可见
  const isFieldVisible = (fieldName: keyof AssetFormData): boolean => {
    // 如果没有规则定义，默认可见
    const hasRule = fieldVisibilityRules.some(rule => rule.field === fieldName)
    if (!hasRule) return true

    // 根据规则判断
    return visibleFields.has(fieldName) && !hiddenFields.has(fieldName)
  }

  // 检查字段是否隐藏
  const isFieldHidden = (fieldName: keyof AssetFormData): boolean => {
    return hiddenFields.has(fieldName)
  }

  // 获取字段的依赖关系
  const getFieldDependencies = (fieldName: keyof AssetFormData): (keyof AssetFormData)[] => {
    const rule = fieldVisibilityRules.find(rule => rule.field === fieldName)
    return rule?.dependsOn || []
  }

  // 获取所有可见字段
  const getAllVisibleFields = (): (keyof AssetFormData)[] => {
    const allFields = Object.keys({} as AssetFormData) as (keyof AssetFormData)[]
    return allFields.filter(field => isFieldVisible(field))
  }

  // 获取所有隐藏字段
  const getAllHiddenFields = (): (keyof AssetFormData)[] => {
    return Array.from(hiddenFields)
  }

  return {
    isFieldVisible,
    isFieldHidden,
    getFieldDependencies,
    getAllVisibleFields,
    getAllHiddenFields,
    visibleFields,
    hiddenFields,
  }
}

/**
 * 表单字段分组可见性Hook
 */
export const useFormGroupVisibility = (watch: UseFormWatch<AssetFormData>) => {
  const { isFieldVisible } = useFormFieldVisibility(watch)

  // 检查字段组是否应该显示
  const isGroupVisible = (groupFields: string[]): boolean => {
    return groupFields.some(field => isFieldVisible(field as keyof AssetFormData))
  }

  // 获取组内可见字段
  const getVisibleFieldsInGroup = (groupFields: string[]): string[] => {
    return groupFields.filter(field => isFieldVisible(field as keyof AssetFormData))
  }

  // 获取组内隐藏字段
  const getHiddenFieldsInGroup = (groupFields: string[]): string[] => {
    return groupFields.filter(field => !isFieldVisible(field as keyof AssetFormData))
  }

  return {
    isGroupVisible,
    getVisibleFieldsInGroup,
    getHiddenFieldsInGroup,
  }
}

/**
 * 表单验证规则动态调整Hook
 */
export const useDynamicValidation = (watch: UseFormWatch<AssetFormData>) => {
  const { isFieldVisible } = useFormFieldVisibility(watch)

  // 获取当前应该验证的字段
  const getValidationFields = (): (keyof AssetFormData)[] => {
    const allFields = Object.keys({} as AssetFormData) as (keyof AssetFormData)[]
    return allFields.filter(field => isFieldVisible(field))
  }

  // 检查字段是否需要验证
  const shouldValidateField = (fieldName: keyof AssetFormData): boolean => {
    return isFieldVisible(fieldName)
  }

  return {
    getValidationFields,
    shouldValidateField,
  }
}