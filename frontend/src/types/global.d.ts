// 全局类型声明文件，用于解决TypeScript类型错误

declare module '*.svg' {
  const content: any;
  export default content;
}

declare module '*.png' {
  const content: any;
  export default content;
}

declare module '*.jpg' {
  const content: any;
  export default content;
}

declare module '*.jpeg' {
  const content: any;
  export default content;
}

declare module '*.gif' {
  const content: any;
  export default content;
}

declare module '*.webp' {
  const content: any;
  export default content;
}

// 全局变量声明
declare global {
  interface Window {
    progressInterval?: NodeJS.Timeout;
    modulePath?: string;
    loadingComponent?: any;
    fallback?: any;
  }
}

// 扩展Asset接口，添加一些可能缺失的属性
import { Asset } from './asset';

declare module '@/types/asset' {
  interface Asset {
    // 添加一些测试数据中可能使用的属性
    contract_status?: string;
    annual_income?: number;
    annual_expense?: number;
    net_income?: number;
    agreement_start_date?: string;
  }
}

// 导出空类型以避免导入错误
export const PropertyNature: any = {};
export const OwnershipStatus: any = {};
export const UsageStatus: any = {};
export const TenantType: any = {};
export const BusinessModel: any = {};
export const OperationStatus: any = {};
export const DataStatus: any = {};