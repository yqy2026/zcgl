/**
 * Chart.js Type Definitions and Guards
 * 解决Chart.js类型不兼容问题
 */

/**
 * Chart数据点类型
 */
export interface ChartDataPoint {
  y: number;
  x?: string | number;
  label?: string;
}

/**
 * Chart上下文（包含解析后的数据）
 */
export interface ChartContextWithParsed {
  dataset: {
    label: string;
    [key: string]: unknown;
  };
  parsed: number | ChartDataPoint;
  [key: string]: unknown;
}

/**
 * Chart.js Tooltip Context
 */
export interface ChartTooltipContext {
  dataset: {
    label: string;
    [key: string]: unknown;
  };
  parsed: number | ChartDataPoint;
  label?: string;
  dataPoints?: Array<{ parsed: number | ChartDataPoint }>;
  [key: string]: unknown;
}

/**
 * 类型守卫：检查是否为ChartDataPoint
 */
export function isChartDataPoint(value: unknown): value is ChartDataPoint {
  return (
    typeof value === 'object' &&
    value !== null &&
    'y' in value &&
    typeof (value as ChartDataPoint).y === 'number'
  );
}

/**
 * 类型守卫：检查是否为ChartContext
 */
export function isChartContext(value: unknown): value is ChartContextWithParsed {
  return (
    typeof value === 'object' &&
    value !== null &&
    'dataset' in value &&
    'parsed' in value
  );
}

/**
 * 安全获取Chart数据点的Y值
 */
export function getChartYValue(context: unknown): number {
  if (isChartContext(context)) {
    const parsed = context.parsed;
    if (typeof parsed === 'number') {
      return parsed;
    }
    if (isChartDataPoint(parsed)) {
      return parsed.y;
    }
  }
  return 0;
}

/**
 * 安全获取Chart数据集标签
 */
export function getChartDatasetLabel(context: unknown): string {
  if (isChartContext(context)) {
    return context.dataset.label || '';
  }
  return '';
}
