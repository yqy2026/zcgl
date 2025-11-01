/**
 * 58字段资产测试数据生成器
 * 提供完整的、符合业务逻辑的测试数据
 */

import type { Asset, AssetCreateRequest, AssetUpdateRequest } from '../types/asset'
import { OwnershipStatus, PropertyNature, UsageStatus, TenantType, BusinessModel, OperationStatus, DataStatus } from '../types/asset'

// 权属方名称库
const OWNERSHIP_ENTITIES = [
  '北京国有资产经营有限公司',
  '上海商业地产开发集团',
  '深圳投资控股有限公司',
  '广州城市建设投资集团',
  '成都产业发展集团有限公司',
  '杭州商业资产管理有限公司',
  '武汉城市运营发展有限公司',
  '西安产业投资控股集团',
  '南京江北新区资产运营公司',
  '重庆两江新区产业发展集团'
]

// 物业名称库
const PROPERTY_NAMES = [
  '中央商务大厦',
  '科技创新中心',
  '金融贸易大厦',
  '现代物流园',
  '文化创意产业园',
  '国际会议中心',
  '综合商业广场',
  '高端购物中心',
  '甲级写字楼',
  '产业孵化基地',
  '智能制造园区',
  '数字科技大厦',
  '绿色生态园区',
  '医疗健康中心',
  '教育培训基地'
]

// 地址模板
const ADDRESS_TEMPLATES = [
  '{{city}}市{{district}}区{{street}}路{{number}}号',
  '{{city}}市{{district}}区{{street}}街道{{number}}弄',
  '{{city}}市新区{{area}}路{{number}}号',
  '{{city}}市高新技术开发区{{road}}路{{number}}号',
  '{{city}}市经济开发区{{zone}}大道{{number}}号'
]

const CITIES = ['北京', '上海', '深圳', '广州', '成都', '杭州', '武汉', '西安', '南京', '重庆']
const DISTRICTS = ['朝阳', '海淀', '浦东', '南山', '福田', '天河', '滨江', '武昌', '雁塔', '建邺']
const STREETS = ['商业', '金融', '科技', '文化', '建设', '发展', '创新', '产业', '园区', '中心']

// 租户名称库
const TENANT_NAMES = [
  '阿里巴巴集团控股有限公司',
  '腾讯计算机系统有限公司',
  '百度网络技术有限公司',
  '京东集团股份有限公司',
  '华为技术有限公司',
  '字节跳动科技有限公司',
  '美团点评集团',
  '小米科技有限责任公司',
  '网易公司',
  '拼多多控股公司',
  '中国平安保险集团',
  '招商银行股份有限公司',
  '中国移动通信集团',
  '中国电信集团公司',
  '中国国际航空股份有限公司'
]

// 业务类别
const BUSINESS_CATEGORIES = [
  '零售商业',
  '办公服务',
  '餐饮服务',
  '教育培训',
  '医疗服务',
  '金融服务',
  '科技研发',
  '文化创意',
  '物流仓储',
  '制造业',
  '咨询服务',
  '法律服务',
  '会计服务',
  '设计服务',
  '媒体传播'
]

/**
 * 58字段资产数据生成器
 */
export class AssetDataGenerator {
  /**
   * 生成完整的58字段资产数据
   */
  static generateCompleteAssetData(overrides: Partial<Asset> = {}): Asset {
    const city = CITIES[Math.floor(Math.random() * CITIES.length)]
    const district = DISTRICTS[Math.floor(Math.random() * DISTRICTS.length)]
    const street = STREETS[Math.floor(Math.random() * STREETS.length)]
    const addressTemplate = ADDRESS_TEMPLATES[Math.floor(Math.random() * ADDRESS_TEMPLATES.length)]
    const address = addressTemplate
      .replace('{{city}}', city)
      .replace('{{district}}', district)
      .replace('{{street}}', street)
      .replace('{{number}}', String(Math.floor(Math.random() * 999) + 1))
      .replace('{{area}}', street)
      .replace('{{road}}', street)
      .replace('{{zone}}', street)

    const landArea = Math.floor(Math.random() * 20000) + 1000 // 1000-21000
    const actualPropertyArea = Math.floor(landArea * (0.6 + Math.random() * 0.3)) // 60-90%
    const rentableArea = Math.floor(actualPropertyArea * (0.7 + Math.random() * 0.2)) // 70-90%
    const rentedArea = Math.floor(rentableArea * Math.random()) // 0-100%
    const unrentedArea = rentableArea - rentedArea
    const occupancyRate = rentableArea > 0 ? (rentedArea / rentableArea) * 100 : 0

    const monthlyRent = Math.floor(rentableArea * (50 + Math.random() * 200)) // 50-250元/平米
    const annualIncome = monthlyRent * 12
    const annualExpense = Math.floor(annualIncome * (0.2 + Math.random() * 0.3)) // 20-50%
    const netIncome = annualIncome - annualExpense

    const contractStart = new Date(2023 + Math.floor(Math.random() * 2), Math.floor(Math.random() * 12), 1)
    const contractEnd = new Date(contractStart)
    contractEnd.setFullYear(contractEnd.getFullYear() + 1 + Math.floor(Math.random() * 4)) // 1-5年合同

    return {
      id: Math.random().toString(36).substr(2, 9),
      ownership_entity: OWNERSHIP_ENTITIES[Math.floor(Math.random() * OWNERSHIP_ENTITIES.length)],
      ownership_category: ['国有企业', '民营企业', '外资企业', '合资企业'][Math.floor(Math.random() * 4)],
      project_name: PROPERTY_NAMES[Math.floor(Math.random() * PROPERTY_NAMES.length)] + '项目',
      property_name: PROPERTY_NAMES[Math.floor(Math.random() * PROPERTY_NAMES.length)],
      address,
      ownership_status: OwnershipStatus.CONFIRMED,
      property_nature: [
        PropertyNature.COMMERCIAL,
        PropertyNature.NON_COMMERCIAL,
        PropertyNature.COMMERCIAL_LEASE,
        PropertyNature.NON_COMMERCIAL_PUBLIC
      ][Math.floor(Math.random() * 4)],
      usage_status: [
        UsageStatus.RENTED,
        UsageStatus.VACANT,
        UsageStatus.SELF_USED,
        UsageStatus.OTHER
      ][Math.floor(Math.random() * 4)],
      business_category: BUSINESS_CATEGORIES[Math.floor(Math.random() * BUSINESS_CATEGORIES.length)],
      is_litigated: Math.random() > 0.9,
      notes: '这是一个测试资产，包含了完整的58个字段数据。',

      // 面积相关字段 (8个)
      land_area: landArea,
      actual_property_area: actualPropertyArea,
      rentable_area: rentableArea,
      rented_area: rentedArea,
      unrented_area: unrentedArea,
      occupancy_rate: Number(occupancyRate.toFixed(2)),
      non_commercial_area: Math.floor(actualPropertyArea * Math.random() * 0.2),
      include_in_occupancy_rate: Math.random() > 0.2,

      // 用途相关字段 (2个)
      certificated_usage: ['商业用地', '办公用地', '工业用地', '住宅用地'][Math.floor(Math.random() * 4)],
      actual_usage: ['零售商场', '办公楼', '工厂', '住宅', '仓库'][Math.floor(Math.random() * 5)],

      // 租户相关字段 (2个)
      tenant_name: rentedArea > 0 ? TENANT_NAMES[Math.floor(Math.random() * TENANT_NAMES.length)] : '',
      tenant_type: rentedArea > 0 ? [
        TenantType.ENTERPRISE,
        TenantType.INDIVIDUAL,
        TenantType.GOVERNMENT,
        TenantType.OTHER
      ][Math.floor(Math.random() * 4)] : undefined,

      // 合同相关字段 (10个)
      lease_contract_number: `LC${contractStart.getFullYear()}${Math.floor(Math.random() * 10000).toString().padStart(4, '0')}`,
      contract_start_date: contractStart.toISOString().split('T')[0],
      contract_end_date: contractEnd.toISOString().split('T')[0],
            rent_payment_method: ['月付', '季付', '半年付', '年付'][Math.floor(Math.random() * 4)],
      deposit_amount: monthlyRent * (2 + Math.floor(Math.random() * 3)), // 2-4个月押金
      rent_increase_clause: Math.random() > 0.5 ? `每年递增${(Math.random() * 5 + 3).toFixed(1)}%` : '',
      termination_clause: '合同到期前30天书面通知',
      renewal_option: Math.random() > 0.5,
      special_terms: Math.random() > 0.7 ? '包含物业管理费' : '',

      // 管理相关字段 (3个)
      business_model: [
        BusinessModel.SELF_OPERATION,
        BusinessModel.ENTRUSTED_OPERATION,
        BusinessModel.LEASE_SUBLEASE,
        BusinessModel.OTHER
      ][Math.floor(Math.random() * 4)],
      operation_status: [
        OperationStatus.NORMAL,
        OperationStatus.RENOVATING,
        OperationStatus.SUSPENDED,
        OperationStatus.SEEKING_TENANT
      ][Math.floor(Math.random() * 4)],
      manager_name: ['张经理', '李经理', '王经理', '陈经理', '刘经理'][Math.floor(Math.random() * 5)],

      // 接收相关字段 (3个)
      operation_agreement_start_date: new Date(contractStart.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      operation_agreement_end_date: new Date(contractEnd.getTime() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      operation_agreement_attachments: Math.random() > 0.5 ? 'operation_agreement.pdf' : '',

      // 终端合同字段 (1个)
      terminal_contract_files: Math.random() > 0.6 ? 'terminal_contract.pdf' : '',

      // 项目相关字段
      project_phase: ['一期', '二期', '三期', '整体'][Math.floor(Math.random() * 4)],

      // 财务相关字段 (12个)
      annual_income: annualIncome,
      annual_expense: annualExpense,
      net_income: netIncome,
      rent_price_per_sqm: Number((monthlyRent / rentableArea).toFixed(2)),
      management_fee_per_sqm: Number((monthlyRent * 0.05 / rentableArea).toFixed(2)),
      property_tax: Math.floor(annualIncome * 0.012),
      insurance_fee: Math.floor(actualPropertyArea * 2),
      maintenance_fee: Math.floor(actualPropertyArea * (10 + Math.random() * 20)),
      other_fees: Math.floor(Math.random() * 50000),
      rent_income_tax: Math.floor(annualIncome * 0.12),
      net_rental_income: Math.floor(monthlyRent * 0.88),
      total_cost: annualExpense + Math.floor(monthlyRent * 0.12),

      monthly_rent: monthlyRent,
      deposit: monthlyRent * 3,

      // 系统字段 (6个)
      data_status: DataStatus.NORMAL,
      version: 1,
      tags: ['优质资产', '商业地产', '稳定收益'][Math.floor(Math.random() * 3)],
      audit_notes: '数据录入完成，审核通过',
      created_by: 'test_user',
      updated_by: 'test_user',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),

      ...overrides
    }
  }

  /**
   * 生成资产创建请求数据
   */
  static generateAssetCreateRequest(overrides: Partial<AssetCreateRequest> = {}): AssetCreateRequest {
    const asset = this.generateCompleteAssetData()
    const { id, created_at, updated_at, version, ...createData } = asset

    return {
      ...createData,
      ...overrides
    } as AssetCreateRequest
  }

  /**
   * 生成资产更新请求数据
   */
  static generateAssetUpdateRequest(overrides: Partial<AssetUpdateRequest> = {}): AssetUpdateRequest {
    const updateFields = [
      'ownership_entity', 'ownership_category', 'project_name', 'property_name', 'address',
      'ownership_status', 'property_nature', 'usage_status', 'business_category', 'is_litigated',
      'land_area', 'actual_property_area', 'rentable_area', 'rented_area', 'non_commercial_area',
      'include_in_occupancy_rate', 'certificated_usage', 'actual_usage', 'tenant_name', 'tenant_type',
      'lease_contract_number', 'contract_start_date', 'contract_end_date', 'contract_term',
      'rent_payment_method', 'deposit_amount', 'rent_increase_clause', 'termination_clause',
      'renewal_option', 'special_terms', 'business_model', 'operation_status', 'manager_name',
      'operation_agreement_start_date', 'operation_agreement_end_date', 'operation_agreement_attachments',
      'terminal_contract_files', 'project_phase', 'annual_income', 'annual_expense',
      'rent_price_per_sqm', 'management_fee_per_sqm', 'property_tax', 'insurance_fee',
      'maintenance_fee', 'other_fees', 'rent_income_tax', 'net_rental_income', 'total_cost',
      'monthly_rent', 'deposit', 'data_status', 'tags', 'audit_notes'
    ]

    const updateData: any = {}

    // 随机选择要更新的字段
    const numFields = Math.floor(Math.random() * 5) + 1
    const selectedFields: string[] = []
    for (let i = 0; i < numFields; i++) {
      const field = updateFields[Math.floor(Math.random() * updateFields.length)]
      if (!selectedFields.includes(field)) {
        selectedFields.push(field)
      }
    }

    selectedFields.forEach(field => {
      if (field.includes('date')) {
        updateData[field] = new Date(2024 + Math.floor(Math.random() * 2), Math.floor(Math.random() * 12), 1).toISOString().split('T')[0]
      } else if (field.includes('area') || field.includes('rent') || field.includes('fee') || field.includes('tax')) {
        updateData[field] = Math.floor(Math.random() * 1000000) + 1000
      } else if (field === 'is_litigated' || field === 'include_in_occupancy_rate' || field === 'renewal_option') {
        updateData[field] = Math.random() > 0.5
      } else if (field === 'tags') {
        updateData[field] = ['更新标签1', '更新标签2'][Math.floor(Math.random() * 2)]
      } else {
        updateData[field] = `更新后的${field}`
      }
    })

    return {
      ...updateData,
      ...overrides
    } as AssetUpdateRequest
  }

  /**
   * 生成高出租率资产数据
   */
  static generateHighOccupancyAsset(overrides: Partial<Asset> = {}): Asset {
    const baseAsset = this.generateCompleteAssetData()
    const rentableArea = baseAsset.rentable_area
    const rentedArea = Math.floor(rentableArea * (0.9 + Math.random() * 0.09)) // 90-99%

    return this.generateCompleteAssetData({
      ...baseAsset,
      rented_area: rentedArea,
      unrented_area: rentableArea - rentedArea,
      occupancy_rate: Number(((rentedArea / (rentableArea || 1)) * 100).toFixed(2)),
      usage_status: UsageStatus.RENTED,
      tenant_name: TENANT_NAMES[Math.floor(Math.random() * TENANT_NAMES.length)],
      tenant_type: TenantType.ENTERPRISE,
      operation_status: OperationStatus.NORMAL,
      monthly_rent: Math.floor((rentableArea || 0) * (150 + Math.random() * 100)), // 高租金
      ...overrides
    })
  }

  /**
   * 生成低出租率资产数据
   */
  static generateLowOccupancyAsset(overrides: Partial<Asset> = {}): Asset {
    const baseAsset = this.generateCompleteAssetData()
    const rentableArea = baseAsset.rentable_area
    const rentedArea = Math.floor(rentableArea * (0.05 + Math.random() * 0.15)) // 5-20%

    return this.generateCompleteAssetData({
      ...baseAsset,
      rented_area: rentedArea,
      unrented_area: rentableArea - rentedArea,
      occupancy_rate: Number(((rentedArea / (rentableArea || 1)) * 100).toFixed(2)),
      usage_status: UsageStatus.VACANT,
      tenant_name: '',
      tenant_type: TenantType.INDIVIDUAL,
      operation_status: OperationStatus.SUSPENDED,
      monthly_rent: Math.floor((rentableArea || 0) * (30 + Math.random() * 50)), // 低租金
      ...overrides
    })
  }

  /**
   * 生成完整财务数据资产
   */
  static generateFinancialDataAsset(overrides: Partial<Asset> = {}): Asset {
    const landArea = Math.floor(Math.random() * 10000) + 5000
    const actualPropertyArea = Math.floor(landArea * 0.8)
    const rentableArea = Math.floor(actualPropertyArea * 0.85)
    const rentedArea = Math.floor(rentableArea * 0.75)
    const monthlyRent = Math.floor(rentableArea * (100 + Math.random() * 150))
    const annualIncome = monthlyRent * 12
    const annualExpense = Math.floor(annualIncome * (0.25 + Math.random() * 0.2))

    return this.generateCompleteAssetData({
      land_area: landArea,
      actual_property_area: actualPropertyArea,
      rentable_area: rentableArea,
      rented_area: rentedArea,
      unrented_area: rentableArea - rentedArea,
      occupancy_rate: Number(((rentedArea / rentableArea) * 100).toFixed(2)),
      monthly_rent: monthlyRent,
      annual_income: annualIncome,
      annual_expense: annualExpense,
      net_income: annualIncome - annualExpense,
      // 移除Asset接口中不存在的字段
      ...overrides
    })
  }

  /**
   * 生成资产组合数据
   */
  static generateAssetPortfolio(count: number, options: {
    highOccupancyRatio?: number
    lowOccupancyRatio?: number
    includeFinancialData?: boolean
  } = {}): Asset[] {
    const {
      highOccupancyRatio = 0.3,
      lowOccupancyRatio = 0.2,
      includeFinancialData = true
    } = options

    const assets: Asset[] = []
    const highOccupancyCount = Math.floor(count * highOccupancyRatio)
    const lowOccupancyCount = Math.floor(count * lowOccupancyRatio)
    const normalCount = count - highOccupancyCount - lowOccupancyCount

    // 生成高出租率资产
    for (let i = 0; i < highOccupancyCount; i++) {
      assets.push(this.generateHighOccupancyAsset({
        property_name: `高出租率资产_${i + 1}`,
        ownership_entity: `${OWNERSHIP_ENTITIES[i % OWNERSHIP_ENTITIES.length]}`
      }))
    }

    // 生成低出租率资产
    for (let i = 0; i < lowOccupancyCount; i++) {
      assets.push(this.generateLowOccupancyAsset({
        property_name: `低出租率资产_${i + 1}`,
        ownership_entity: `${OWNERSHIP_ENTITIES[(i + highOccupancyCount) % OWNERSHIP_ENTITIES.length]}`
      }))
    }

    // 生成普通资产
    for (let i = 0; i < normalCount; i++) {
      const asset = includeFinancialData
        ? this.generateFinancialDataAsset({
            property_name: `普通资产_${i + 1}`,
            ownership_entity: `${OWNERSHIP_ENTITIES[(i + highOccupancyCount + lowOccupancyCount) % OWNERSHIP_ENTITIES.length]}`
          })
        : this.generateCompleteAssetData({
            property_name: `普通资产_${i + 1}`,
            ownership_entity: `${OWNERSHIP_ENTITIES[(i + highOccupancyCount + lowOccupancyCount) % OWNERSHIP_ENTITIES.length]}`
          })
      assets.push(asset)
    }

    return assets
  }

  /**
   * 生成测试搜索数据
   */
  static generateSearchTestData() {
    return {
      // 基本搜索关键词
      basicKeywords: ['中心', '广场', '大厦', '科技', '金融', '商业', '创意'],

      // 权属状态选项
      ownershipStatuses: ['已确权', '待确权', '确权中'],

      // 物业性质选项
      propertyNatures: ['商业用途', '办公用途', '工业用途', '住宅用途'],

      // 使用状态选项
      usageStatuses: ['使用中', '空置', '装修中', '待租'],

      // 业务类别选项
      businessCategories: BUSINESS_CATEGORIES,

      // 面积范围
      areaRanges: [
        { min: 0, max: 1000, label: '1000平米以下' },
        { min: 1000, max: 5000, label: '1000-5000平米' },
        { min: 5000, max: 10000, label: '5000-10000平米' },
        { min: 10000, max: 50000, label: '10000平米以上' }
      ],

      // 租金范围
      rentRanges: [
        { min: 0, max: 100000, label: '10万以下' },
        { min: 100000, max: 500000, label: '10-50万' },
        { min: 500000, max: 1000000, label: '50-100万' },
        { min: 1000000, max: 5000000, label: '100万以上' }
      ],

      // 出租率范围
      occupancyRanges: [
        { min: 0, max: 30, label: '30%以下' },
        { min: 30, max: 70, label: '30-70%' },
        { min: 70, max: 90, label: '70-90%' },
        { min: 90, max: 100, label: '90%以上' }
      ]
    }
  }
}

/**
 * 导出便捷函数
 */
export const createTestAsset = (overrides?: Partial<Asset>) =>
  AssetDataGenerator.generateCompleteAssetData(overrides)

export const createTestAssetCreateRequest = (overrides?: Partial<AssetCreateRequest>) =>
  AssetDataGenerator.generateAssetCreateRequest(overrides)

export const createTestAssetUpdateRequest = (overrides?: Partial<AssetUpdateRequest>) =>
  AssetDataGenerator.generateAssetUpdateRequest(overrides)

export const createHighOccupancyAsset = (overrides?: Partial<Asset>) =>
  AssetDataGenerator.generateHighOccupancyAsset(overrides)

export const createLowOccupancyAsset = (overrides?: Partial<Asset>) =>
  AssetDataGenerator.generateLowOccupancyAsset(overrides)

export const createFinancialDataAsset = (overrides?: Partial<Asset>) =>
  AssetDataGenerator.generateFinancialDataAsset(overrides)

export const createAssetPortfolio = (count: number, options?: any) =>
  AssetDataGenerator.generateAssetPortfolio(count, options)

export const getSearchTestData = () => AssetDataGenerator.generateSearchTestData()