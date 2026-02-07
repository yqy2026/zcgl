/**
 * Theme Types
 *
 * Theme system type definitions for light and dark mode support
 */

/**
 * Theme mode
 */
export type ThemeMode = 'light' | 'dark';

/**
 * Theme configuration
 */
export interface ThemeConfig {
  /**
   * Current theme mode
   */
  mode: ThemeMode;
  /**
   * Whether to use system preference
   */
  useSystemPreference: boolean;
}

/**
 * Color palette for light theme
 */
export interface LightThemeColors {
  // Primary colors
  colorPrimary: string;
  colorPrimaryLight: string;
  colorPrimaryDark: string;

  // Semantic colors
  colorSuccess: string;
  colorWarning: string;
  colorError: string;
  colorInfo: string;

  // Text colors
  colorTextPrimary: string;
  colorTextSecondary: string;
  colorTextTertiary: string;
  colorTextQuaternary: string;

  // Background colors
  colorBgBase: string;
  colorBgSecondary: string;
  colorBgTertiary: string;
  colorBgElevated: string;
  colorBgLayout: string;

  // Border colors
  colorBorder: string;
  colorBorderLight: string;
  colorBorderSecondary: string;
}

/**
 * Color palette for dark theme
 */
export interface DarkThemeColors {
  // Primary colors
  colorPrimary: string;
  colorPrimaryLight: string;
  colorPrimaryDark: string;

  // Semantic colors
  colorSuccess: string;
  colorWarning: string;
  colorError: string;
  colorInfo: string;

  // Text colors
  colorTextPrimary: string;
  colorTextSecondary: string;
  colorTextTertiary: string;
  colorTextQuaternary: string;

  // Background colors
  colorBgBase: string;
  colorBgSecondary: string;
  colorBgTertiary: string;
  colorBgElevated: string;
  colorBgLayout: string;

  // Border colors
  colorBorder: string;
  colorBorderLight: string;
  colorBorderSecondary: string;
}

/**
 * Theme tokens
 */
export interface ThemeTokens {
  colors: LightThemeColors | DarkThemeColors;
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
    xxl: string;
  };
  fontSize: {
    xs: string;
    sm: string;
    base: string;
    lg: string;
    xl: string;
    xxl: string;
  };
  borderRadius: {
    sm: string;
    md: string;
    lg: string;
  };
  boxShadow: {
    sm: string;
    md: string;
    lg: string;
  };
}
