/**
 * Light Theme Configuration
 *
 * Color tokens and design tokens for light mode
 */

import type { LightThemeColors, ThemeTokens } from '@/types/theme';

/**
 * Light theme color palette
 */
export const lightColors: LightThemeColors = {
  // Primary colors
  colorPrimary: '#1677ff',
  colorPrimaryLight: '#e6f4ff',
  colorPrimaryDark: '#0958d9',

  // Semantic colors
  colorSuccess: '#52c41a',
  colorWarning: '#faad14',
  colorError: '#ff4d4f',
  colorInfo: '#1677ff',

  // Text colors
  colorTextPrimary: 'rgba(0, 0, 0, 0.88)',
  colorTextSecondary: 'rgba(0, 0, 0, 0.65)',
  colorTextTertiary: 'rgba(0, 0, 0, 0.45)',
  colorTextQuaternary: 'rgba(0, 0, 0, 0.25)',

  // Background colors
  colorBgBase: '#ffffff',
  colorBgSecondary: '#f5f5f5',
  colorBgTertiary: '#fafafa',
  colorBgElevated: '#ffffff',
  colorBgLayout: '#f5f5f5',

  // Border colors
  colorBorder: '#d9d9d9',
  colorBorderLight: '#f0f0f0',
  colorBorderSecondary: '#f0f0f0',
};

/**
 * Light theme tokens
 */
export const lightTheme: ThemeTokens = {
  colors: lightColors,
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
    xxl: '48px',
  },
  fontSize: {
    xs: '12px',
    sm: '14px',
    base: '16px',
    lg: '18px',
    xl: '20px',
    xxl: '24px',
  },
  borderRadius: {
    sm: '4px',
    md: '6px',
    lg: '8px',
  },
  boxShadow: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.03)',
    md: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  },
};

/**
 * Convert theme tokens to CSS variables
 */
export function getLightThemeCSSVariables(): Record<string, string> {
  const variables: Record<string, string> = {};

  // Color variables
  Object.entries(lightTheme.colors).forEach(([key, value]) => {
    variables[`--${key}`] = value;
  });

  // Spacing variables
  Object.entries(lightTheme.spacing).forEach(([key, value]) => {
    variables[`--spacing-${key}`] = value;
  });

  // Font size variables
  Object.entries(lightTheme.fontSize).forEach(([key, value]) => {
    variables[`--font-size-${key}`] = value;
  });

  // Border radius variables
  Object.entries(lightTheme.borderRadius).forEach(([key, value]) => {
    variables[`--radius-${key}`] = value;
  });

  // Box shadow variables
  Object.entries(lightTheme.boxShadow).forEach(([key, value]) => {
    variables[`--shadow-${key}`] = value;
  });

  return variables;
}

export default lightTheme;
