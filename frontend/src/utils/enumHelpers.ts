/**
 * 枚举值辅助工具
 * 提供枚举值的分组、搜索、格式化等功能
 */

import {
  PropertyNature,
  UsageStatus,
  OwnershipStatus,
  RevenueMode,
  TenantType,
  OperationStatus,
} from '@/types/asset';

// 枚举选项接口
export interface EnumOption {
  value: string;
  label: string;
  group?: string;
  description?: string;
  color?: string;
}

// 分组接口
export interface EnumGroup {
  label: string;
  options: EnumOption[];
}

// PropertyNature 分组配置
export const PropertyNatureGroups: EnumGroup[] = [
  {
    label: '经营性物业',
    options: [
      { value: PropertyNature.COMMERCIAL, label: '经营性', color: 'blue' },
      { value: PropertyNature.COMMERCIAL_CLASS, label: '经营类', color: 'blue' },
      { value: PropertyNature.COMMERCIAL_EXTERNAL, label: '经营-外部', color: 'blue' },
      { value: PropertyNature.COMMERCIAL_INTERNAL, label: '经营-内部', color: 'blue' },
      { value: PropertyNature.COMMERCIAL_LEASE, label: '经营-租赁', color: 'blue' },
    ],
  },
  {
    label: '非经营性物业',
    options: [
      { value: PropertyNature.NON_COMMERCIAL, label: '非经营性', color: 'green' },
      { value: PropertyNature.NON_COMMERCIAL_CLASS, label: '非经营类', color: 'green' },
      { value: PropertyNature.NON_COMMERCIAL_PUBLIC, label: '非经营类-公配', color: 'green' },
      { value: PropertyNature.NON_COMMERCIAL_OTHER, label: '非经营类-其他', color: 'green' },
      {
        value: PropertyNature.NON_COMMERCIAL_PUBLIC_HOUSING,
        label: '非经营-公配房',
        color: 'green',
      },
    ],
  },
  {
    label: '配套物业',
    options: [
      { value: PropertyNature.COMMERCIAL_SUPPORTING, label: '经营-配套', color: 'orange' },
      { value: PropertyNature.NON_COMMERCIAL_SUPPORTING, label: '非经营-配套', color: 'orange' },
      { value: PropertyNature.COMMERCIAL_SUPPORTING_TOWN, label: '经营-配套镇', color: 'orange' },
      {
        value: PropertyNature.NON_COMMERCIAL_SUPPORTING_TOWN,
        label: '非经营-配套镇',
        color: 'orange',
      },
      {
        value: PropertyNature.NON_COMMERCIAL_SUPPORTING_HOUSING,
        label: '非经营类-配套',
        color: 'orange',
      },
    ],
  },
  {
    label: '处置类物业',
    options: [
      { value: PropertyNature.COMMERCIAL_DISPOSAL, label: '经营-处置类', color: 'red' },
      { value: PropertyNature.NON_COMMERCIAL_DISPOSAL, label: '非经营-处置类', color: 'red' },
    ],
  },
];

// UsageStatus 分组配置
export const UsageStatusGroups: EnumGroup[] = [
  {
    label: '使用中',
    options: [
      { value: UsageStatus.RENTED, label: '出租', color: 'green', description: '已出租给租户' },
      { value: UsageStatus.SELF_USED, label: '自用', color: 'blue', description: '单位自用' },
      { value: UsageStatus.SUBLEASE, label: '转租', color: 'cyan', description: '转租给第三方' },
    ],
  },
  {
    label: '空置状态',
    options: [
      { value: UsageStatus.VACANT, label: '空置', color: 'orange', description: '完全空置' },
      {
        value: UsageStatus.VACANT_PLANNING,
        label: '空置规划',
        color: 'orange',
        description: '规划中空置',
      },
      {
        value: UsageStatus.VACANT_RESERVED,
        label: '空置预留',
        color: 'orange',
        description: '预留空置',
      },
      {
        value: UsageStatus.VACANT_SUPPORTING,
        label: '空置配套',
        color: 'orange',
        description: '配套空置',
      },
      {
        value: UsageStatus.VACANT_SUPPORTING_SHORT,
        label: '空置配',
        color: 'orange',
        description: '空置配套（简称）',
      },
      { value: UsageStatus.VACANT_DISPOSAL, label: '闲置', color: 'red', description: '长期闲置' },
    ],
  },
  {
    label: '特殊用途',
    options: [
      {
        value: UsageStatus.PUBLIC_HOUSING,
        label: '公房',
        color: 'purple',
        description: '公共住房',
      },
      {
        value: UsageStatus.PUBLIC_FACILITY,
        label: '公配',
        color: 'purple',
        description: '公共配套设施',
      },
      {
        value: UsageStatus.SUPPORTING_FACILITY,
        label: '配套',
        color: 'purple',
        description: '配套设施',
      },
    ],
  },
  {
    label: '待处理状态',
    options: [
      {
        value: UsageStatus.PENDING_DISPOSAL,
        label: '待处置',
        color: 'red',
        description: '等待处置',
      },
      {
        value: UsageStatus.PENDING_HANDOVER,
        label: '待移交',
        color: 'red',
        description: '等待移交',
      },
    ],
  },
  {
    label: '其他',
    options: [
      { value: UsageStatus.OTHER, label: '其他', color: 'default', description: '其他状态' },
    ],
  },
];

// OwnershipStatus 配置
export const OwnershipStatusOptions: EnumOption[] = [
  { value: OwnershipStatus.CONFIRMED, label: '已确权', color: 'green', description: '业权已确认' },
  { value: OwnershipStatus.UNCONFIRMED, label: '未确权', color: 'red', description: '业权未确认' },
  {
    value: OwnershipStatus.PARTIAL,
    label: '部分确权',
    color: 'orange',
    description: '部分业权已确认',
  },
  {
    value: OwnershipStatus.CANNOT_CONFIRM,
    label: '无法确认业权',
    color: 'red',
    description: '业权无法确认',
  },
];

// RevenueMode 配置
export const RevenueModeOptions: EnumOption[] = [
  { value: RevenueMode.LEASE_SUBLEASE, label: '承租转租', description: '从第三方承租后转租' },
  { value: RevenueMode.ENTRUSTED_OPERATION, label: '委托经营', description: '委托第三方经营' },
  { value: RevenueMode.SELF_OPERATION, label: '自营', description: '自主经营' },
  { value: RevenueMode.OTHER, label: '其他', description: '其他经营模式' },
];

// TenantType 配置
export const TenantTypeOptions: EnumOption[] = [
  { value: TenantType.INDIVIDUAL, label: '个人', color: 'blue' },
  { value: TenantType.ENTERPRISE, label: '企业', color: 'green' },
  { value: TenantType.GOVERNMENT, label: '政府机构', color: 'purple' },
  { value: TenantType.OTHER, label: '其他', color: 'default' },
];

// OperationStatus 配置
export const OperationStatusOptions: EnumOption[] = [
  { value: OperationStatus.NORMAL, label: '正常经营', color: 'green' },
  { value: OperationStatus.SUSPENDED, label: '停业整顿', color: 'red' },
  { value: OperationStatus.RENOVATING, label: '装修中', color: 'orange' },
  { value: OperationStatus.SEEKING_TENANT, label: '待招租', color: 'blue' },
];

/**
 * 枚举值搜索工具
 */
export class EnumSearchHelper {
  /**
   * 在分组中搜索枚举选项
   */
  static searchInGroups(groups: EnumGroup[], keyword: string): EnumGroup[] {
    const trimmedKeyword = keyword.trim();
    if (trimmedKeyword === '') {
      return groups;
    }

    const lowercaseKeyword = keyword.toLowerCase();

    return groups
      .map(group => ({
        ...group,
        options: group.options.filter(
          option =>
            option.label.toLowerCase().includes(lowercaseKeyword) ||
            option.value.toLowerCase().includes(lowercaseKeyword) ||
            (option.description !== null &&
              option.description !== undefined &&
              option.description.toLowerCase().includes(lowercaseKeyword))
        ),
      }))
      .filter(group => group.options.length > 0);
  }

  /**
   * 获取所有选项的扁平列表
   */
  static flattenGroups(groups: EnumGroup[]): EnumOption[] {
    return groups.reduce((acc: EnumOption[], group) => [...acc, ...group.options], []);
  }

  /**
   * 根据值查找选项
   */
  static findByValue(groups: EnumGroup[], value: string): EnumOption | undefined {
    const allOptions = this.flattenGroups(groups);
    return allOptions.find(option => option.value === value);
  }

  /**
   * 根据值获取标签
   */
  static getLabelByValue(groups: EnumGroup[], value: string): string {
    const option = this.findByValue(groups, value);
    return option !== null &&
      option !== undefined &&
      option.label !== null &&
      option.label !== undefined &&
      option.label !== ''
      ? option.label
      : value;
  }

  /**
   * 根据值获取颜色
   */
  static getColorByValue(groups: EnumGroup[], value: string): string {
    const option = this.findByValue(groups, value);
    return option !== null &&
      option !== undefined &&
      option.color !== null &&
      option.color !== undefined &&
      option.color !== ''
      ? option.color
      : 'default';
  }

  /**
   * 根据值获取描述
   */
  static getDescriptionByValue(groups: EnumGroup[], value: string): string | undefined {
    const option = this.findByValue(groups, value);
    return option?.description;
  }
}

/**
 * 枚举值格式化工具
 */
export class EnumFormatter {
  /**
   * 获取枚举值的显示文本
   */
  static formatPropertyNature(value: string): string {
    return EnumSearchHelper.getLabelByValue(PropertyNatureGroups, value);
  }

  static formatUsageStatus(value: string): string {
    return EnumSearchHelper.getLabelByValue(UsageStatusGroups, value);
  }

  static formatOwnershipStatus(value: string): string {
    const option = OwnershipStatusOptions.find(opt => opt.value === value);
    return option !== null &&
      option !== undefined &&
      option.label !== null &&
      option.label !== undefined &&
      option.label !== ''
      ? option.label
      : value;
  }

  static formatRevenueMode(value: string): string {
    const option = RevenueModeOptions.find(opt => opt.value === value);
    return option !== null &&
      option !== undefined &&
      option.label !== null &&
      option.label !== undefined &&
      option.label !== ''
      ? option.label
      : value;
  }

  static formatTenantType(value: string): string {
    const option = TenantTypeOptions.find(opt => opt.value === value);
    return option !== null &&
      option !== undefined &&
      option.label !== null &&
      option.label !== undefined &&
      option.label !== ''
      ? option.label
      : value;
  }

  static formatOperationStatus(value: string): string {
    const option = OperationStatusOptions.find(opt => opt.value === value);
    return option !== null &&
      option !== undefined &&
      option.label !== null &&
      option.label !== undefined &&
      option.label !== ''
      ? option.label
      : value;
  }

  /**
   * 获取枚举值的颜色标识
   */
  static getPropertyNatureColor(value: string): string {
    return EnumSearchHelper.getColorByValue(PropertyNatureGroups, value);
  }

  static getUsageStatusColor(value: string): string {
    return EnumSearchHelper.getColorByValue(UsageStatusGroups, value);
  }

  static getOwnershipStatusColor(value: string): string {
    const option = OwnershipStatusOptions.find(opt => opt.value === value);
    return option !== null &&
      option !== undefined &&
      option.color !== null &&
      option.color !== undefined &&
      option.color !== ''
      ? option.color
      : 'default';
  }

  static getRevenueModeColor(value: string): string {
    const option = RevenueModeOptions.find(opt => opt.value === value);
    return option !== null &&
      option !== undefined &&
      option.color !== null &&
      option.color !== undefined &&
      option.color !== ''
      ? option.color
      : 'default';
  }

  static getTenantTypeColor(value: string): string {
    const option = TenantTypeOptions.find(opt => opt.value === value);
    return option !== null &&
      option !== undefined &&
      option.color !== null &&
      option.color !== undefined &&
      option.color !== ''
      ? option.color
      : 'default';
  }

  static getOperationStatusColor(value: string): string {
    const option = OperationStatusOptions.find(opt => opt.value === value);
    return option !== null &&
      option !== undefined &&
      option.color !== null &&
      option.color !== undefined &&
      option.color !== ''
      ? option.color
      : 'default';
  }

  /**
   * 获取枚举值的描述信息
   */
  static getPropertyNatureDescription(value: string): string | undefined {
    return EnumSearchHelper.getDescriptionByValue(PropertyNatureGroups, value);
  }

  static getUsageStatusDescription(value: string): string | undefined {
    return EnumSearchHelper.getDescriptionByValue(UsageStatusGroups, value);
  }

  static getRevenueModeDescription(value: string): string | undefined {
    const option = RevenueModeOptions.find(opt => opt.value === value);
    return option?.description;
  }

  static getTenantTypeDescription(value: string): string | undefined {
    const option = TenantTypeOptions.find(opt => opt.value === value);
    return option?.description;
  }

  static getOperationStatusDescription(value: string): string | undefined {
    const option = OperationStatusOptions.find(opt => opt.value === value);
    return option?.description;
  }
}

// 枚举验证错误接口
export interface EnumValidationError {
  field: string;
  value: unknown;
  expectedType: string;
}

// 待验证数据接口
export interface EnumValidationData {
  property_nature?: string;
  usage_status?: string;
  ownership_status?: string;
  revenue_mode?: string;
  tenant_type?: string;
  operation_status?: string;
  [key: string]: unknown;
}

/**
 * 枚举值验证工具
 */
export class EnumValidator {
  /**
   * 验证PropertyNature值是否有效
   */
  static isValidPropertyNature(value: string): boolean {
    const allOptions = EnumSearchHelper.flattenGroups(PropertyNatureGroups);
    return allOptions.some(option => option.value === value);
  }

  /**
   * 验证UsageStatus值是否有效
   */
  static isValidUsageStatus(value: string): boolean {
    const allOptions = EnumSearchHelper.flattenGroups(UsageStatusGroups);
    return allOptions.some(option => option.value === value);
  }

  /**
   * 验证OwnershipStatus值是否有效
   */
  static isValidOwnershipStatus(value: string): boolean {
    return OwnershipStatusOptions.some(option => option.value === value);
  }

  /**
   * 验证RevenueMode值是否有效
   */
  static isValidRevenueMode(value: string): boolean {
    return RevenueModeOptions.some(option => option.value === value);
  }

  /**
   * 验证TenantType值是否有效
   */
  static isValidTenantType(value: string): boolean {
    return TenantTypeOptions.some(option => option.value === value);
  }

  /**
   * 验证OperationStatus值是否有效
   */
  static isValidOperationStatus(value: string): boolean {
    return OperationStatusOptions.some(option => option.value === value);
  }

  /**
   * 获取所有无效的枚举值
   */
  static getInvalidEnumValues(data: EnumValidationData): EnumValidationError[] {
    const errors: EnumValidationError[] = [];

    if (
      data.property_nature !== null &&
      data.property_nature !== undefined &&
      !this.isValidPropertyNature(data.property_nature)
    ) {
      errors.push({
        field: 'property_nature',
        value: data.property_nature,
        expectedType: 'PropertyNature',
      });
    }

    if (
      data.usage_status !== null &&
      data.usage_status !== undefined &&
      !this.isValidUsageStatus(data.usage_status)
    ) {
      errors.push({ field: 'usage_status', value: data.usage_status, expectedType: 'UsageStatus' });
    }

    if (
      data.ownership_status !== null &&
      data.ownership_status !== undefined &&
      !this.isValidOwnershipStatus(data.ownership_status)
    ) {
      errors.push({
        field: 'ownership_status',
        value: data.ownership_status,
        expectedType: 'OwnershipStatus',
      });
    }

    if (
      data.revenue_mode !== null &&
      data.revenue_mode !== undefined &&
      !this.isValidRevenueMode(data.revenue_mode)
    ) {
      errors.push({
        field: 'revenue_mode',
        value: data.revenue_mode,
        expectedType: 'RevenueMode',
      });
    }

    if (
      data.tenant_type !== null &&
      data.tenant_type !== undefined &&
      !this.isValidTenantType(data.tenant_type)
    ) {
      errors.push({ field: 'tenant_type', value: data.tenant_type, expectedType: 'TenantType' });
    }

    if (
      data.operation_status !== null &&
      data.operation_status !== undefined &&
      !this.isValidOperationStatus(data.operation_status)
    ) {
      errors.push({
        field: 'operation_status',
        value: data.operation_status,
        expectedType: 'OperationStatus',
      });
    }

    return errors;
  }
}

