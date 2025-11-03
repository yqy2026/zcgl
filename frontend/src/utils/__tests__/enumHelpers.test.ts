// Jest imports - no explicit import needed for describe, it, expect
import {
  PropertyNatureGroups,
  UsageStatusGroups,
  OwnershipStatusOptions,
  BusinessModelOptions,
  TenantTypeOptions,
  OperationStatusOptions,
  EnumSearchHelper,
  EnumFormatter,
  EnumValidator
} from '../enumHelpers'
import { PropertyNature, UsageStatus, OwnershipStatus } from '@/types/asset'

describe('enumHelpers', () => {
  describe('EnumSearchHelper', () => {
    describe('searchInGroups', () => {
      it('应该根据关键词搜索枚举选项', () => {
        const result = EnumSearchHelper.searchInGroups(PropertyNatureGroups, '经营')

        expect(result.length).toBeGreaterThan(0)
        expect(result.every(group =>
          group.options.every(option =>
            option.label.includes('经营') ||
            option.value.includes('经营') ||
            (option.description && option.description.includes('经营'))
          )
        )).toBe(true)
      })

      it('应该搜索所有分组', () => {
        const result = EnumSearchHelper.searchInGroups(PropertyNatureGroups, '配套')

        const matchingGroups = result.filter(group =>
          group.label.includes('配套') ||
          group.options.some(option => option.label.includes('配套'))
        )

        expect(matchingGroups.length).toBeGreaterThan(0)
      })

      it('应该处理空关键词', () => {
        const result = EnumSearchHelper.searchInGroups(PropertyNatureGroups, '')

        expect(result).toEqual(PropertyNatureGroups)
      })

      it('应该处理无匹配结果', () => {
        const result = EnumSearchHelper.searchInGroups(PropertyNatureGroups, '不存在的内容')

        expect(result).toEqual([])
      })

      it('应该搜索描述信息', () => {
        const result = EnumSearchHelper.searchInGroups(UsageStatusGroups, '出租')

        const rentalOptions = result.flatMap(group => group.options)
          .filter(option =>
            option.label.includes('出租') ||
            (option.description && option.description.includes('出租'))
          )

        expect(rentalOptions.length).toBeGreaterThan(0)
      })
    })

    describe('flattenGroups', () => {
      it('应该扁平化分组选项', () => {
        const result = EnumSearchHelper.flattenGroups(PropertyNatureGroups)

        expect(Array.isArray(result)).toBe(true)
        expect(typeof result[0]).toBe('object')
        expect(result[0]).toHaveProperty('value')
        expect(result[0]).toHaveProperty('label')
      })

      it('应该包含所有选项', () => {
        const result = EnumSearchHelper.flattenGroups(PropertyNatureGroups)
        const totalOptions = PropertyNatureGroups.reduce((sum, group) => sum + group.options.length, 0)

        expect(result.length).toBe(totalOptions)
      })
    })

    describe('findByValue', () => {
      it('应该根据值找到对应选项', () => {
        const result = EnumSearchHelper.findByValue(PropertyNatureGroups, PropertyNature.COMMERCIAL)

        expect(result).toBeDefined()
        expect(result?.value).toBe(PropertyNature.COMMERCIAL)
        expect(result?.label).toBe('经营性')
      })

      it('应该处理不存在的值', () => {
        const result = EnumSearchHelper.findByValue(PropertyNatureGroups, '不存在的值')

        expect(result).toBeUndefined()
      })
    })

    describe('getLabelByValue', () => {
      it('应该返回正确的标签', () => {
        const result = EnumSearchHelper.getLabelByValue(PropertyNatureGroups, PropertyNature.COMMERCIAL)

        expect(result).toBe('经营性')
      })

      it('应该对不存在的值返回原值', () => {
        const result = EnumSearchHelper.getLabelByValue(PropertyNatureGroups, '不存在的值')

        expect(result).toBe('不存在的值')
      })
    })

    describe('getColorByValue', () => {
      it('应该返回正确的颜色', () => {
        const result = EnumSearchHelper.getColorByValue(PropertyNatureGroups, PropertyNature.COMMERCIAL)

        expect(result).toBe('blue')
      })

      it('应该对不存在的值返回默认颜色', () => {
        const result = EnumSearchHelper.getColorByValue(PropertyNatureGroups, '不存在的值')

        expect(result).toBe('default')
      })
    })

    describe('getDescriptionByValue', () => {
      it('应该返回描述信息', () => {
        const result = EnumSearchHelper.getDescriptionByValue(UsageStatusGroups, UsageStatus.RENTED)

        expect(result).toBe('已出租给租户')
      })

      it('应该对无描述的选项返回undefined', () => {
        const result = EnumSearchHelper.getDescriptionByValue(PropertyNatureGroups, PropertyNature.COMMERCIAL)

        expect(result).toBeUndefined()
      })
    })
  })

  describe('EnumFormatter', () => {
    describe('PropertyNature格式化', () => {
      it('应该格式化PropertyNature值', () => {
        const result = EnumFormatter.formatPropertyNature(PropertyNature.COMMERCIAL)

        expect(result).toBe('经营性')
      })

      it('应该获取PropertyNature颜色', () => {
        const result = EnumFormatter.getPropertyNatureColor(PropertyNature.COMMERCIAL)

        expect(result).toBe('blue')
      })
    })

    describe('UsageStatus格式化', () => {
      it('应该格式化UsageStatus值', () => {
        const result = EnumFormatter.formatUsageStatus(UsageStatus.RENTED)

        expect(result).toBe('出租')
      })

      it('应该获取UsageStatus颜色', () => {
        const result = EnumFormatter.getUsageStatusColor(UsageStatus.RENTED)

        expect(result).toBe('green')
      })

      it('应该获取UsageStatus描述', () => {
        const result = EnumFormatter.getUsageStatusDescription(UsageStatus.RENTED)

        expect(result).toBe('已出租给租户')
      })
    })

    describe('OwnershipStatus格式化', () => {
      it('应该格式化OwnershipStatus值', () => {
        const result = EnumFormatter.formatOwnershipStatus(OwnershipStatus.CONFIRMED)

        expect(result).toBe('已确权')
      })

      it('应该获取OwnershipStatus颜色', () => {
        const result = EnumFormatter.getOwnershipStatusColor(OwnershipStatus.CONFIRMED)

        expect(result).toBe('green')
      })
    })

    describe('BusinessModel格式化', () => {
      it('应该格式化BusinessModel值', () => {
        const result = EnumFormatter.formatBusinessModel('自营')

        expect(result).toBe('自营')
      })

      it('应该获取BusinessModel描述', () => {
        const result = EnumFormatter.getBusinessModelDescription('自营')

        expect(result).toBe('自主经营')
      })
    })

    describe('TenantType格式化', () => {
      it('应该格式化TenantType值', () => {
        const result = EnumFormatter.formatTenantType('个人')

        expect(result).toBe('个人')
      })

      it('应该获取TenantType颜色', () => {
        const result = EnumFormatter.getTenantTypeColor('个人')

        expect(result).toBe('blue')
      })
    })

    describe('OperationStatus格式化', () => {
      it('应该格式化OperationStatus值', () => {
        const result = EnumFormatter.formatOperationStatus('正常经营')

        expect(result).toBe('正常经营')
      })

      it('应该获取OperationStatus颜色', () => {
        const result = EnumFormatter.getOperationStatusColor('正常经营')

        expect(result).toBe('green')
      })
    })
  })

  describe('EnumValidator', () => {
    describe('PropertyNature验证', () => {
      it('应该验证有效的PropertyNature值', () => {
        expect(EnumValidator.isValidPropertyNature(PropertyNature.COMMERCIAL)).toBe(true)
        expect(EnumValidator.isValidPropertyNature(PropertyNature.NON_COMMERCIAL)).toBe(true)
      })

      it('应该拒绝无效的PropertyNature值', () => {
        expect(EnumValidator.isValidPropertyNature('无效值')).toBe(false)
        expect(EnumValidator.isValidPropertyNature('')).toBe(false)
      })
    })

    describe('UsageStatus验证', () => {
      it('应该验证有效的UsageStatus值', () => {
        expect(EnumValidator.isValidUsageStatus(UsageStatus.RENTED)).toBe(true)
        expect(EnumValidator.isValidUsageStatus(UsageStatus.VACANT)).toBe(true)
      })

      it('应该拒绝无效的UsageStatus值', () => {
        expect(EnumValidator.isValidUsageStatus('无效值')).toBe(false)
        expect(EnumValidator.isValidUsageStatus('')).toBe(false)
      })
    })

    describe('OwnershipStatus验证', () => {
      it('应该验证有效的OwnershipStatus值', () => {
        expect(EnumValidator.isValidOwnershipStatus(OwnershipStatus.CONFIRMED)).toBe(true)
        expect(EnumValidator.isValidOwnershipStatus(OwnershipStatus.UNCONFIRMED)).toBe(true)
      })

      it('应该拒绝无效的OwnershipStatus值', () => {
        expect(EnumValidator.isValidOwnershipStatus('无效值')).toBe(false)
        expect(EnumValidator.isValidOwnershipStatus('')).toBe(false)
      })
    })

    describe('BusinessModel验证', () => {
      it('应该验证有效的BusinessModel值', () => {
        expect(EnumValidator.isValidBusinessModel('自营')).toBe(true)
        expect(EnumValidator.isValidBusinessModel('承租转租')).toBe(true)
      })

      it('应该拒绝无效的BusinessModel值', () => {
        expect(EnumValidator.isValidBusinessModel('无效值')).toBe(false)
        expect(EnumValidator.isValidBusinessModel('')).toBe(false)
      })
    })

    describe('TenantType验证', () => {
      it('应该验证有效的TenantType值', () => {
        expect(EnumValidator.isValidTenantType('个人')).toBe(true)
        expect(EnumValidator.isValidTenantType('企业')).toBe(true)
      })

      it('应该拒绝无效的TenantType值', () => {
        expect(EnumValidator.isValidTenantType('无效值')).toBe(false)
        expect(EnumValidator.isValidTenantType('')).toBe(false)
      })
    })

    describe('OperationStatus验证', () => {
      it('应该验证有效的OperationStatus值', () => {
        expect(EnumValidator.isValidOperationStatus('正常经营')).toBe(true)
        expect(EnumValidator.isValidOperationStatus('停业整顿')).toBe(true)
      })

      it('应该拒绝无效的OperationStatus值', () => {
        expect(EnumValidator.isValidOperationStatus('无效值')).toBe(false)
        expect(EnumValidator.isValidOperationStatus('')).toBe(false)
      })
    })

    describe('getInvalidEnumValues', () => {
      it('应该检测所有有效的枚举值', () => {
        const validData = {
          property_nature: PropertyNature.COMMERCIAL,
          usage_status: UsageStatus.RENTED,
          ownership_status: OwnershipStatus.CONFIRMED,
          business_model: '自营',
          tenant_type: '个人',
          operation_status: '正常经营'
        }

        const errors = EnumValidator.getInvalidEnumValues(validData)

        expect(errors).toHaveLength(0)
      })

      it('应该检测所有无效的枚举值', () => {
        const invalidData = {
          property_nature: '无效物业性质',
          usage_status: '无效使用状态',
          ownership_status: '无效确权状态',
          business_model: '无效经营模式',
          tenant_type: '无效租户类型',
          operation_status: '无效经营状态'
        }

        const errors = EnumValidator.getInvalidEnumValues(invalidData)

        expect(errors).toHaveLength(6)
        expect(errors.map(e => e.field)).toEqual([
          'property_nature',
          'usage_status',
          'ownership_status',
          'business_model',
          'tenant_type',
          'operation_status'
        ])
      })

      it('应该处理部分有效部分无效的数据', () => {
        const mixedData = {
          property_nature: PropertyNature.COMMERCIAL, // 有效
          usage_status: '无效使用状态', // 无效
          ownership_status: OwnershipStatus.CONFIRMED, // 有效
          business_model: '无效经营模式' // 无效
        }

        const errors = EnumValidator.getInvalidEnumValues(mixedData)

        expect(errors).toHaveLength(2)
        expect(errors.map(e => e.field)).toEqual(['usage_status', 'business_model'])
      })

      it('应该忽略null和undefined值', () => {
        const dataWithNulls = {
          property_nature: null,
          usage_status: undefined,
          ownership_status: OwnershipStatus.CONFIRMED
        }

        const errors = EnumValidator.getInvalidEnumValues(dataWithNulls)

        expect(errors).toHaveLength(0)
      })

      it('应该处理空对象', () => {
        const errors = EnumValidator.getInvalidEnumValues({})

        expect(errors).toHaveLength(0)
      })
    })
  })

  describe('枚举配置验证', () => {
    it('PropertyNatureGroups应该包含所有预期的分组', () => {
      const groupLabels = PropertyNatureGroups.map(g => g.label)

      expect(groupLabels).toContain('经营性物业')
      expect(groupLabels).toContain('非经营性物业')
      expect(groupLabels).toContain('配套物业')
      expect(groupLabels).toContain('处置类物业')
    })

    it('UsageStatusGroups应该包含所有预期的分组', () => {
      const groupLabels = UsageStatusGroups.map(g => g.label)

      expect(groupLabels).toContain('使用中')
      expect(groupLabels).toContain('空置状态')
      expect(groupLabels).toContain('特殊用途')
      expect(groupLabels).toContain('待处理状态')
      expect(groupLabels).toContain('其他')
    })

    it('OwnershipStatusOptions应该包含所有预期选项', () => {
      const values = OwnershipStatusOptions.map(o => o.value)

      expect(values).toContain(OwnershipStatus.CONFIRMED)
      expect(values).toContain(OwnershipStatus.UNCONFIRMED)
      expect(values).toContain(OwnershipStatus.PARTIAL)
      expect(values).toContain(OwnershipStatus.CANNOT_CONFIRM)
    })

    it('BusinessModelOptions应该包含所有预期选项', () => {
      const labels = BusinessModelOptions.map(o => o.label)

      expect(labels).toContain('承租转租')
      expect(labels).toContain('委托经营')
      expect(labels).toContain('自营')
      expect(labels).toContain('其他')
    })

    it('每个选项都应该有必要的属性', () => {
      const allOptions = [
        ...EnumSearchHelper.flattenGroups(PropertyNatureGroups),
        ...EnumSearchHelper.flattenGroups(UsageStatusGroups),
        ...OwnershipStatusOptions,
        ...BusinessModelOptions,
        ...TenantTypeOptions,
        ...OperationStatusOptions
      ]

      allOptions.forEach(option => {
        expect(option).toHaveProperty('value')
        expect(option).toHaveProperty('label')
        expect(typeof option.value).toBe('string')
        expect(typeof option.label).toBe('string')
        expect(option.value.length).toBeGreaterThan(0)
        expect(option.label.length).toBeGreaterThan(0)
      })
    })
  })
})