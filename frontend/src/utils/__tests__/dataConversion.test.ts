// Jest imports - no explicit import needed for describe, it, expect
import {
  convertBackendToFrontend,
  convertFrontendToBackend,
  calculateDerivedFields,
  validateNumericFields
} from '../dataConversion'

describe('dataConversion', () => {
  describe('convertBackendToFrontend', () => {
    it('应该正确转换Decimal字符串为number', () => {
      const backendData = {
        id: '1',
        land_area: '1000.50',
        monthly_rent: '5000.25',
        annual_income: '60000.00'
      }

      const result = convertBackendToFrontend(backendData) as any

      expect(result.land_area).toBe(1000.50)
      expect(result.monthly_rent).toBe(5000.25)
      expect(result.annual_income).toBe(60000.00)
    })

    it('应该处理null和undefined值', () => {
      const backendData = {
        id: '1',
        land_area: null,
        monthly_rent: undefined,
        rentable_area: '1000'
      }

      const result = convertBackendToFrontend(backendData) as any

      expect(result.land_area).toBeNull()
      expect(result.monthly_rent).toBeUndefined()
      expect(result.rentable_area).toBe(1000)
    })

    it('应该递归处理嵌套对象', () => {
      const backendData = {
        id: '1',
        asset: {
          land_area: '1000.50',
          details: {
            monthly_rent: '5000.25'
          }
        }
      }

      const result = convertBackendToFrontend(backendData) as any

      expect(result.asset.land_area).toBe(1000.50)
      expect(result.asset.details.monthly_rent).toBe(5000.25)
    })

    it('应该处理数组', () => {
      const backendData = {
        assets: [
          { land_area: '1000.50' },
          { land_area: '2000.75' }
        ]
      }

      const result = convertBackendToFrontend(backendData) as any

      expect(result.assets[0].land_area).toBe(1000.50)
      expect(result.assets[1].land_area).toBe(2000.75)
    })

    it('应该处理非Decimal字段', () => {
      const backendData = {
        id: '1',
        property_name: '测试物业',
        ownership_status: '已确权',
        is_litigated: true
      }

      const result = convertBackendToFrontend(backendData) as any

      expect(result.property_name).toBe('测试物业')
      expect(result.ownership_status).toBe('已确权')
      expect(result.is_litigated).toBe(true)
    })
  })

  describe('convertFrontendToBackend', () => {
    it('应该正确转换number为Decimal字符串', () => {
      const frontendData = {
        land_area: 1000.50,
        monthly_rent: 5000.25,
        annual_income: 60000.00
      }

      const result = convertFrontendToBackend(frontendData) as any

      expect(result.land_area).toBe('1000.5')
      expect(result.monthly_rent).toBe('5000.25')
      expect(result.annual_income).toBe('60000')
    })

    it('应该处理null和undefined值', () => {
      const frontendData = {
        land_area: null,
        monthly_rent: undefined,
        rentable_area: 1000
      }

      const result = convertFrontendToBackend(frontendData) as any

      expect(result.land_area).toBeNull()
      expect(result.monthly_rent).toBeUndefined()
      expect(result.rentable_area).toBe('1000')
    })

    it('应该递归处理嵌套对象', () => {
      const frontendData = {
        asset: {
          land_area: 1000.50,
          details: {
            monthly_rent: 5000.25
          }
        }
      }

      const result = convertFrontendToBackend(frontendData) as any

      expect(result.asset.land_area).toBe('1000.5')
      expect(result.asset.details.monthly_rent).toBe('5000.25')
    })

    it('应该处理非数值字段', () => {
      const frontendData = {
        property_name: '测试物业',
        ownership_status: '已确权',
        is_litigated: true
      }

      const result = convertFrontendToBackend(frontendData) as any

      expect(result.property_name).toBe('测试物业')
      expect(result.ownership_status).toBe('已确权')
      expect(result.is_litigated).toBe(true)
    })
  })

  describe('calculateDerivedFields', () => {
    it('应该正确计算未出租面积', () => {
      const asset = {
        rentable_area: 1000,
        rented_area: 800
      }

      const result = calculateDerivedFields(asset) as any

      expect(result.unrented_area).toBe(200)
    })

    it('应该正确计算出租率', () => {
      const asset = {
        rentable_area: 1000,
        rented_area: 800
      }

      const result = calculateDerivedFields(asset) as any

      expect(result.occupancy_rate).toBe(80)
    })

    it('应该正确计算净收益', () => {
      const asset = {
        annual_income: 100000,
        annual_expense: 20000
      }

      const result = calculateDerivedFields(asset) as any

      expect(result.net_income).toBe(80000)
    })

    it('应该处理缺失字段', () => {
      const asset = {
        rentable_area: 1000
        // 缺少rented_area
      }

      const result = calculateDerivedFields(asset) as any

      expect(result.unrented_area).toBeUndefined()
      expect(result.occupancy_rate).toBeUndefined()
    })

    it('应该处理除零情况', () => {
      const asset = {
        rentable_area: 0,
        rented_area: 800
      }

      const result = calculateDerivedFields(asset) as any

      expect(result.occupancy_rate).toBeUndefined()
    })

    it('应该计算多个派生字段', () => {
      const asset = {
        rentable_area: 1000,
        rented_area: 800,
        annual_income: 100000,
        annual_expense: 20000
      }

      const result = calculateDerivedFields(asset) as any

      expect(result.unrented_area).toBe(200)
      expect(result.occupancy_rate).toBe(80)
      expect(result.net_income).toBe(80000)
    })
  })

  describe('validateNumericFields', () => {
    it('应该验证有效的数值字段', () => {
      const asset = {
        land_area: 1000,
        monthly_rent: 5000,
        annual_income: 60000,
        occupancy_rate: 80
      }

      const errors = validateNumericFields(asset)

      expect(errors).toHaveLength(0)
    })

    it('应该检测负数值', () => {
      const asset = {
        land_area: -1000,
        monthly_rent: -5000
      }

      const errors = validateNumericFields(asset)

      expect(errors).toContain('土地面积必须是非负数')
      expect(errors).toContain('月租金必须是非负数')
    })

    it('应该检测无效的出租率', () => {
      const asset = {
        occupancy_rate: 150
      }

      const errors = validateNumericFields(asset)

      expect(errors).toContain('出租率必须在0-100之间')
    })

    it('应该检测负出租率', () => {
      const asset = {
        occupancy_rate: -10
      }

      const errors = validateNumericFields(asset)

      expect(errors).toContain('出租率必须在0-100之间')
    })

    it('应该检测面积逻辑错误', () => {
      const asset = {
        rentable_area: 1000,
        rented_area: 1200
      }

      const errors = validateNumericFields(asset)

      expect(errors).toContain('已出租面积不能大于可出租面积')
    })

    it('应该处理NaN值', () => {
      const asset = {
        land_area: NaN,
        monthly_rent: 'invalid'
      }

      const errors = validateNumericFields(asset)

      expect(errors).toContain('土地面积必须是非负数')
    })

    it('应该接受null和undefined值', () => {
      const asset = {
        land_area: null,
        monthly_rent: undefined
      }

      const errors = validateNumericFields(asset)

      expect(errors).toHaveLength(0)
    })

    it('应该验证字符串形式的数值', () => {
      const asset = {
        land_area: '1000',
        monthly_rent: '5000.50'
      }

      const errors = validateNumericFields(asset)

      expect(errors).toHaveLength(0)
    })

    it('应该检测边界值', () => {
      const asset = {
        occupancy_rate: 0,
        occupancy_rate2: 100
      }

      const errors = validateNumericFields(asset)

      expect(errors).toHaveLength(0)
    })

    it('应该检测超出范围的值', () => {
      const asset = {
        occupancy_rate: 100.1,
        occupancy_rate2: -0.1
      }

      const errors = validateNumericFields(asset)

      expect(errors.length).toBeGreaterThan(0)
    })
  })

  describe('复杂场景测试', () => {
    it('应该处理完整的资产数据转换', () => {
      const backendAsset = {
        id: '1',
        property_name: '测试物业',
        land_area: '1000.50',
        rentable_area: '800.25',
        rented_area: '600.75',
        monthly_rent: '5000.50',
        annual_income: '60000.00',
        annual_expense: '10000.25',
        ownership_status: '已确权',
        property_nature: '经营性',
        usage_status: '出租',
        is_litigated: false
      }

      // 后端转前端
      const frontendAsset = convertBackendToFrontend(backendAsset) as any

      expect(frontendAsset.land_area).toBe(1000.50)
      expect(frontendAsset.rentable_area).toBe(800.25)
      expect(frontendAsset.rented_area).toBe(600.75)
      expect(frontendAsset.monthly_rent).toBe(5000.50)
      expect(frontendAsset.annual_income).toBe(60000)
      expect(frontendAsset.annual_expense).toBe(10000.25)

      // 计算派生字段
      const derived = calculateDerivedFields(frontendAsset) as any
      expect(derived.unrented_area).toBe(199.5)
      expect(derived.occupancy_rate).toBe(75.075)
      expect(derived.net_income).toBe(49999.75)

      // 前端转后端
      const backToBackend = convertFrontendToBackend({
        ...frontendAsset,
        ...derived
      }) as any

      expect(backToBackend.land_area).toBe('1000.5')
      expect(backToBackend.rentable_area).toBe('800.25')
      expect(backToBackend.rented_area).toBe('600.75')
      expect(backToBackend.monthly_rent).toBe('5000.5')
      expect(backToBackend.annual_income).toBe('60000')
      expect(backToBackend.annual_expense).toBe('10000.25')
      expect(backToBackend.unrented_area).toBe('199.5')
      expect(backToBackend.occupancy_rate).toBe('75.08')
      expect(backToBackend.net_income).toBe('49999.75')
    })

    it('应该处理空的输入数据', () => {
      expect(convertBackendToFrontend(null)).toBeNull()
      expect(convertBackendToFrontend(undefined)).toBeUndefined()
      expect(convertFrontendToBackend(null)).toBeNull()
      expect(convertFrontendToBackend(undefined)).toBeUndefined()
      expect(calculateDerivedFields({})).toEqual({})
      expect(validateNumericFields({})).toEqual([])
    })

    it('应该处理数组和对象的复杂嵌套', () => {
      const complexData = {
        assets: [
          {
            id: '1',
            land_area: '1000.50',
            details: {
              monthly_rent: '5000.25',
              features: [
                { area: '100.00' },
                { area: '200.50' }
              ]
            }
          }
        ],
        summary: {
          total_area: '3000.75',
          total_income: '150000.00'
        }
      }

      const result = convertBackendToFrontend(complexData) as any

      expect(result.assets[0].land_area).toBe(1000.50)
      expect(result.assets[0].details.monthly_rent).toBe(5000.25)
      expect(result.assets[0].details.features[0].area).toBe(100)
      expect(result.assets[0].details.features[1].area).toBe(200.5)
      expect(result.summary.total_area).toBe(3000.75)
      expect(result.summary.total_income).toBe(150000)
    })
  })
})