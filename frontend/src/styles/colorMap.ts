/**
 * Color Mapping Utilities
 * Maps legacy hardcoded color values to CSS variables
 */

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

  // Additional chart colors (mapped to semantic colors)
  '#722ed1': 'var(--color-primary)',    // purple → primary
  '#13c2c2': 'var(--color-success)',    // cyan → success
  '#fa8c16': 'var(--color-warning)',    // dark orange → warning
  '#eb2f96': 'var(--color-error)',      // pink → error
  '#3f8600': 'var(--color-success)',    // dark green → success
  '#8884d8': 'var(--color-secondary)',  // purple line → secondary
} as const;

// Helper function to get CSS variable from color value
export function toCssVar(color: string): string {
  const lowerColor = color.toLowerCase();
  const mappedColor = COLOR_MAP[lowerColor as keyof typeof COLOR_MAP];

  // Warn in development if color not found in map
  if (!mappedColor && process.env.NODE_ENV === 'development') {
    console.warn(
      `[ColorMap] Unknown color "${color}" not found in COLOR_MAP. ` +
      `Using original value. Available colors: ${Object.keys(COLOR_MAP).join(', ')}`
    );
  }

  return mappedColor || color;
}

// Helper function to create style object with CSS variables
export function createColorStyle(
  colorKey: keyof typeof COLOR_MAP | string
): { color: string } {
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
 * Chart color palette (using semantic colors)
 * Replaces hardcoded hex values like ['#1890ff', '#52c41a', '#faad14', '#f5222d', ...]
 */
export const CHART_COLORS = [
  COLORS.primary,      // #1677ff - blue
  COLORS.success,      // #52c41a - green
  COLORS.warning,      // #faad14 - orange/gold
  COLORS.error,        // #ff4d4f - red
  COLORS.secondary,    // #0ea5e9 - cyan/sky
  COLORS.primaryHover, // #4096ff - lighter blue
  COLORS.warning,      // #fa8c16 - darker orange
  COLORS.error,        // #f5222d - darker red (pink-ish)
  COLORS.secondary,    // #13c2c2 - cyan
  COLORS.success,      // Duplicate for palette length
] as const;

/**
 * Performance status colors for analytics
 */
export const PERFORMANCE_COLORS = {
  excellent: COLORS.success,    // #52c41a
  good: COLORS.primary,         // #1677ff
  average: COLORS.warning,      // #faad14
  poor: COLORS.error,           // #ff4d4f
} as const;

/**
 * Chart label colors
 */
export const CHART_LABEL_COLORS = {
  light: '#ffffff',  // For dark backgrounds
  medium: '#666666', // For light backgrounds
  dark: '#1a1a1a',   // For high contrast
} as const;

/**
 * Get performance color by status type
 * Maps Ant Design status types to actual color values
 * @param status - 'success' | 'processing' | 'warning' | 'error'
 * @returns CSS variable color
 */
export function getPerformanceColor(status: 'success' | 'processing' | 'warning' | 'error' | 'default'): string {
  const colorMap = {
    success: COLORS.success,    // #52c41a
    processing: COLORS.primary, // #1677ff
    warning: COLORS.warning,    // #faad14
    error: COLORS.error,        // #ff4d4f
    default: COLORS.textPrimary,// #262626
  };
  return colorMap[status] || colorMap.default;
}
