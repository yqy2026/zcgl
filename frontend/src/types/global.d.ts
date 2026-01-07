// 全局类型声明文件，用于解决TypeScript类型错误

// Jest DOM类型声明
declare global {
  namespace jest {
    interface Matchers<R, _T> {
      toBeInTheDocument(): R;
      toHaveClass(className: string): R;
      toBeVisible(): R;
      toBeDisabled(): R;
      toBeEnabled(): R;
      toHaveAttribute(attr: string, value?: string): R;
      toHaveTextContent(text: string | RegExp): R;
      toHaveValue(value: string | number): R;
      toBeChecked(): R;
      toHaveFocus(): R;
      toBeEmpty(): R;
      toContainElement(element: HTMLElement | null): R;
      toContainHTML(html: string): R;
      toHaveStyle(style: Record<string, string>): R;
      toHaveDescription(text: string | RegExp): R;
      toHaveDisplayValue(value: string | RegExp | (string | RegExp)[]): R;
      toHaveErrorMessage(text: string | RegExp): R;
      toHaveFormValues(values: Record<string, unknown>): R;
      toHaveRole(role: string): R;
      toHaveAccessibleDescription(text: string | RegExp): R;
      toHaveAccessibleName(text: string | RegExp): R;
      toBePartiallyChecked(): R;
      toBeRequired(): R;
      toBeInvalid(): R;
      toBeValid(): R;
      toHaveErrorMessage(text: string | RegExp): R;
    }
  }
}

declare module "*.svg" {
  const content: string;
  export default content;
}

declare module "*.png" {
  const content: string;
  export default content;
}

declare module "*.jpg" {
  const content: string;
  export default content;
}

declare module "*.jpeg" {
  const content: string;
  export default content;
}

declare module "*.gif" {
  const content: string;
  export default content;
}

declare module "*.webp" {
  const content: string;
  export default content;
}

// 全局变量声明
declare global {
  interface Window {
    progressInterval?: NodeJS.Timeout;
    modulePath?: string;
    loadingComponent?: React.ComponentType;
    fallback?: React.ComponentType;
  }
}

// 扩展Asset接口，添加一些可能缺失的属性
declare module "@/types/asset" {
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
export const PropertyNature: Record<string, unknown> = {};
export const OwnershipStatus: Record<string, unknown> = {};
export const UsageStatus: Record<string, unknown> = {};
export const TenantType: Record<string, unknown> = {};
export const BusinessModel: Record<string, unknown> = {};
export const OperationStatus: Record<string, unknown> = {};
export const DataStatus: Record<string, unknown> = {};
