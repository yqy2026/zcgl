/**
 * Color Mapping Utilities
 * Maps legacy hardcoded color values to CSS variables
 */

import { isDevelopmentMode } from '@/utils/runtimeEnv';

// Color value to CSS variable mapping
export const COLOR_MAP = {
  // Primary colors
  '#1677ff': 'var(--color-primary)',
  '#1890ff': 'var(--color-primary)',
  '#4096ff': 'var(--color-primary-hover)',
  '#0958d9': 'var(--color-primary-active)',
  '#e6f4ff': 'var(--color-primary-light)',

  // Secondary colors
  '#0ea5e9': 'var(--color-secondary)',
  '#38bdf8': 'var(--color-secondary-hover)',
  '#0284c7': 'var(--color-secondary-active)',

  // Semantic colors
  '#52c41a': 'var(--color-success)',
  '#faad14': 'var(--color-warning)',
  '#ff4d4f': 'var(--color-error)',
  '#f5222d': 'var(--color-error)',

  // Neutral colors - text
  '#262626': 'var(--color-text-primary)',
  '#595959': 'var(--color-text-secondary)',
  '#8c8c8c': 'var(--color-text-tertiary)',
  '#bfbfbf': 'var(--color-text-quaternary)',

  // Neutral colors - background
  '#ffffff': 'var(--color-bg-primary)',
  '#fff': 'var(--color-bg-primary)',
  '#fafafa': 'var(--color-bg-secondary)',
  '#f5f5f5': 'var(--color-bg-tertiary)',
  '#f0f0f0': 'var(--color-bg-quaternary)',

  // Neutral colors - border
  '#d9d9d9': 'var(--color-border)',
  '#e8e8e8': 'var(--color-border-light)',
  '#cccccc': 'var(--color-border-dark)',
  '#666666': 'var(--color-text-secondary)',
  '#1a1a1a': 'var(--color-text-primary)',

  // Additional chart colors (mapped to chart tokens)
  '#722ed1': 'var(--color-chart-purple)', // purple
  '#13c2c2': 'var(--color-chart-cyan)', // cyan
  '#fa8c16': 'var(--color-chart-gold)', // dark orange
  '#eb2f96': 'var(--color-chart-magenta)', // pink
  '#3f8600': 'var(--color-chart-green)', // dark green
  '#8884d8': 'var(--color-chart-purple)', // purple line
} as const;

// Helper function to get CSS variable from color value
export function toCssVar(color: string): string {
  const lowerColor = color.toLowerCase();
  const mappedColor = COLOR_MAP[lowerColor as keyof typeof COLOR_MAP];

  // Warn in development if color not found in map
  if (!mappedColor && isDevelopmentMode()) {
    console.warn(
      `[ColorMap] Unknown color "${color}" not found in COLOR_MAP. ` +
        `Using original value. Available colors: ${Object.keys(COLOR_MAP).join(', ')}`
    );
  }

  return mappedColor || color;
}

// Helper function to create style object with CSS variables
export function createColorStyle(colorKey: keyof typeof COLOR_MAP | string): { color: string } {
  return {
    color: toCssVar(colorKey),
  };
}

// Type for color keys
export type ColorKey = keyof typeof COLOR_MAP;

// Export color constants for use in components
export const COLORS = {
  primary: 'var(--color-primary)',
  primaryHover: 'var(--color-primary-hover)',
  primaryActive: 'var(--color-primary-active)',
  primaryLight: 'var(--color-primary-light)',

  secondary: 'var(--color-secondary)',
  secondaryHover: 'var(--color-secondary-hover)',
  secondaryActive: 'var(--color-secondary-active)',

  success: 'var(--color-success)',
  successLight: 'var(--color-success-light)',
  warning: 'var(--color-warning)',
  warningLight: 'var(--color-warning-light)',
  error: 'var(--color-error)',
  errorLight: 'var(--color-error-light)',
  info: 'var(--color-info)',
  infoLight: 'var(--color-info-light)',

  // Tag 状态文字深档（浅底上对比度 ≥4.5:1）
  blueText: 'var(--color-blue-text)',
  greenText: 'var(--color-green-text)',
  goldText: 'var(--color-gold-text)',
  redText: 'var(--color-red-text)',
  cyanText: 'var(--color-cyan-text)',
  orangeText: 'var(--color-orange-text)',
  limeText: 'var(--color-lime-text)',
  volcanoText: 'var(--color-volcano-text)',

  // 图表序列色（冷色系谱，相邻色相距离 ≥30°）
  chartBlue: 'var(--color-chart-blue)',
  chartCyan: 'var(--color-chart-cyan)',
  chartGreen: 'var(--color-chart-green)',
  chartGold: 'var(--color-chart-gold)',
  chartRed: 'var(--color-chart-red)',
  chartMagenta: 'var(--color-chart-magenta)',
  chartPurple: 'var(--color-chart-purple)',
  chartGeekblue: 'var(--color-chart-geekblue)',

  textPrimary: 'var(--color-text-primary)',
  textSecondary: 'var(--color-text-secondary)',
  textTertiary: 'var(--color-text-tertiary)',
  textQuaternary: 'var(--color-text-quaternary)',

  bgPrimary: 'var(--color-bg-primary)',
  bgSecondary: 'var(--color-bg-secondary)',
  bgTertiary: 'var(--color-bg-tertiary)',
  bgQuaternary: 'var(--color-bg-quaternary)',

  border: 'var(--color-border)',
  borderLight: 'var(--color-border-light)',
  borderDark: 'var(--color-border-dark)',
} as const;

/**
 * Helper to get occupancy rate color
 * @param rate - Occupancy rate (0-100)
 * @returns CSS variable color
 */
export function getOccupancyRateColor(rate: number): string {
  if (rate >= 80) return COLORS.success;
  if (rate >= 60) return COLORS.warning;
  return COLORS.error;
}

/**
 * Helper to get trend color (positive/negative)
 * @param value - Trend value
 * @param trendType - 'up' means up is good, 'down' means down is good
 * @returns CSS variable color
 */
export function getTrendColor(value: number, trendType?: 'up' | 'down'): string {
  const isPositive = value > 0;
  if (trendType === 'up') {
    return isPositive ? COLORS.success : COLORS.error;
  } else {
    return isPositive ? COLORS.error : COLORS.success;
  }
}

/**
 * Chart color palette (冷色系谱序列色)
 * 相邻色相距离 ≥30°，保证多系列图表可区分；顺序由 contrastFloors 测试守护
 */
export const CHART_COLORS = [
  COLORS.chartBlue, // #1677ff - blue
  COLORS.chartCyan, // #13c2c2 - cyan
  COLORS.chartGreen, // #52c41a - green
  COLORS.chartGold, // #faad14 - gold
  COLORS.chartRed, // #f5222d - red
  COLORS.chartGeekblue, // #2f54eb - geekblue
  COLORS.chartMagenta, // #eb2f96 - magenta
  COLORS.chartPurple, // #722ed1 - purple
] as const;

/**
 * Performance status colors for analytics
 */
export const PERFORMANCE_COLORS = {
  excellent: COLORS.success, // #52c41a
  good: COLORS.primary, // #1677ff
  average: COLORS.warning, // #faad14
  poor: COLORS.error, // #ff4d4f
} as const;

/**
 * Chart label colors — 直接色值，与中性 token 严格对齐：
 * light = --color-bg-primary (#ffffff)、medium = --color-text-secondary (#595959)、
 * dark = --color-text-primary (#262626)。
 * 例外说明：G2/AntD Charts 的 label.style.fill 走 SVG presentation attribute，
 * 不支持 CSS var() 语法，因此此处必须使用字面值（值漂移由 contrastFloors 测试守护）。
 */
export const CHART_LABEL_COLORS = {
  light: '#ffffff', // 深色切片内标签
  medium: '#595959', // 浅色切片内标签
  dark: '#262626', // 高对比标签
} as const;

/**
 * Get performance color by status type
 * Maps Ant Design status types to actual color values
 * @param status - 'success' | 'processing' | 'warning' | 'error'
 * @returns CSS variable color
 */
export function getPerformanceColor(
  status: 'success' | 'processing' | 'warning' | 'error' | 'default'
): string {
  const colorMap = {
    success: COLORS.success, // #52c41a
    processing: COLORS.primary, // #1677ff
    warning: COLORS.warning, // #faad14
    error: COLORS.error, // #ff4d4f
    default: COLORS.textPrimary, // #262626
  };
  return colorMap[status] || colorMap.default;
}
