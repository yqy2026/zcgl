/**
 * Dark Theme Configuration
 *
 * Color tokens and design tokens for dark mode
 *
 * Key principles:
 * - Avoid pure black (#000000) - use dark grays instead
 * - Maintain sufficient contrast (WCAG 2.1 AA)
 * - Adjust shadow effects for dark backgrounds
 * - Reduce eye strain with proper brightness
 */

import type { DarkThemeColors, ThemeTokens } from '@/types/theme';

/**
 * Dark theme color palette
 *
 * Design principles:
 * 1. Background: Use #141414 instead of #000000 (less harsh)
 * 2. Container: Slightly lighter #1f1f1f for elevation
 * 3. Elevated: #262626 for cards and modals
 * 4. Border: Subtle #424242 for separation
 * 5. Text: High contrast for readability
 */
export const darkColors: DarkThemeColors = {
  // Primary colors (adjust for dark backgrounds)
  colorPrimary: '#3b82f6', // Lighter blue for better contrast
  colorPrimaryLight: 'rgba(59, 130, 246, 0.15)',
  colorPrimaryDark: '#2563eb',

  // Semantic colors (optimized for dark mode)
  colorSuccess: '#52c41a',
  colorWarning: '#faad14',
  colorError: '#ff4d4f',
  colorInfo: '#1677ff',

  // Text colors (high contrast for readability)
  colorTextPrimary: 'rgba(255, 255, 255, 0.85)', // WCAG AAA: 12.6:1
  colorTextSecondary: 'rgba(255, 255, 255, 0.65)', // WCAG AA: 7:1
  colorTextTertiary: 'rgba(255, 255, 255, 0.45)',
  colorTextQuaternary: 'rgba(255, 255, 255, 0.25)',

  // Background colors (avoid pure black)
  colorBgBase: '#141414', // Very dark gray (not pure black)
  colorBgSecondary: '#0f0f0f',
  colorBgTertiary: '#1a1a1a',
  colorBgElevated: '#1f1f1f', // For cards and modals
  colorBgLayout: '#000000', // Layout background

  // Border colors (subtle but visible)
  colorBorder: '#424242',
  colorBorderLight: '#303030',
  colorBorderSecondary: '#262626',
};

/**
 * Dark theme tokens
 */
export const darkTheme: ThemeTokens = {
  colors: darkColors,
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
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
    md: '0 1px 3px 0 rgba(0, 0, 0, 0.5), 0 1px 2px 0 rgba(0, 0, 0, 0.3)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.3)',
  },
};

/**
 * Convert theme tokens to CSS variables
 */
export function getDarkThemeCSSVariables(): Record<string, string> {
  const variables: Record<string, string> = {};

  // Color variables
  Object.entries(darkTheme.colors).forEach(([key, value]) => {
    variables[`--${key}`] = value as string;
  });

  // Spacing variables
  Object.entries(darkTheme.spacing).forEach(([key, value]) => {
    variables[`--spacing-${key}`] = value as string;
  });

  // Font size variables
  Object.entries(darkTheme.fontSize).forEach(([key, value]) => {
    variables[`--font-size-${key}`] = value as string;
  });

  // Border radius variables
  Object.entries(darkTheme.borderRadius).forEach(([key, value]) => {
    variables[`--radius-${key}`] = value as string;
  });

  // Box shadow variables
  Object.entries(darkTheme.boxShadow).forEach(([key, value]) => {
    variables[`--shadow-${key}`] = value as string;
  });

  return variables;
}

export default darkTheme;
