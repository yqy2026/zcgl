/**
 * Theme Toggle Component
 *
 * Switch between light and dark mode
 *
 * Accessibility: Fully WCAG 2.1 AA compliant
 */

import React from 'react';
import { Switch, Tooltip, Space, Typography } from 'antd';
import { SunOutlined, MoonOutlined, BgColorsOutlined } from '@ant-design/icons';
import { useAppStore } from '@/store/useAppStore';
import styles from './ThemeToggle.module.css';

const { Text } = Typography;

/**
 * Theme toggle props
 */
export interface ThemeToggleProps {
  /**
   * Display size
   * @default 'default'
   */
  size?: 'small' | 'default' | 'large';
  /**
   * Show text label
   * @default false
   */
  showLabel?: boolean;
  /**
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

/**
 * Theme Toggle Component
 *
 * Provides a switch to toggle between light and dark mode
 */
export const ThemeToggle: React.FC<ThemeToggleProps> = ({
  size = 'default',
  showLabel = false,
  className,
  style,
}) => {
  const { theme, toggleTheme } = useAppStore();

  const isDark = theme === 'dark';

  const handleChange = (_checked: boolean) => {
    toggleTheme();
  };

  const modeIconSizeClass = size === 'small' ? styles.modeIconSmall : styles.modeIconDefault;

  const switchElement = (
    <Switch
      checked={isDark}
      onChange={handleChange}
      checkedChildren={<MoonOutlined aria-label="深色模式" />}
      unCheckedChildren={<SunOutlined aria-label="浅色模式" />}
      aria-label={isDark ? '切换到浅色模式' : '切换到深色模式'}
      size={size === 'small' ? 'small' : 'default'}
      className={className}
      style={style}
    />
  );

  if (showLabel) {
    return (
      <Space size="small" className={styles.toggleLabelSpace}>
        <SunOutlined
          className={`${modeIconSizeClass} ${isDark ? styles.lightIconInactive : styles.lightIconActive}`}
          aria-label="浅色模式图标"
        />
        {switchElement}
        <MoonOutlined
          className={`${modeIconSizeClass} ${isDark ? styles.darkIconActive : styles.darkIconInactive}`}
          aria-label="深色模式图标"
        />
      </Space>
    );
  }

  return (
    <Tooltip title={isDark ? '切换到浅色模式' : '切换到深色模式'}>
      {switchElement}
    </Tooltip>
  );
};

/**
 * Theme Toggle Button Component
 *
 * A button-style theme toggle for use in headers or toolbars
 */
export interface ThemeToggleButtonProps {
  /**
   * Button size
   * @default 'middle'
   */
  size?: 'small' | 'middle' | 'large';
  /**
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

export const ThemeToggleButton: React.FC<ThemeToggleButtonProps> = ({
  size = 'middle',
  className,
  style,
}) => {
  const { theme, toggleTheme } = useAppStore();

  const isDark = theme === 'dark';
  const buttonSizeClass =
    size === 'large'
      ? styles.themeToggleButtonLarge
      : size === 'middle'
        ? styles.themeToggleButtonMiddle
        : styles.themeToggleButtonSmall;
  const iconSizeClass =
    size === 'large'
      ? styles.toggleButtonIconLarge
      : size === 'middle'
        ? styles.toggleButtonIconMiddle
        : styles.toggleButtonIconSmall;

  return (
    <Tooltip title={isDark ? '切换到浅色模式' : '切换到深色模式'}>
      <button
        onClick={toggleTheme}
        aria-label={isDark ? '切换到浅色模式' : '切换到深色模式'}
        className={`theme-toggle-button ${styles.themeToggleButtonBase} ${buttonSizeClass} ${className ?? ''}`}
        style={style}
      >
        {isDark ? (
          <SunOutlined
            className={`${iconSizeClass} ${styles.toggleButtonSunIcon}`}
            aria-label="浅色模式"
          />
        ) : (
          <MoonOutlined
            className={`${iconSizeClass} ${styles.toggleButtonMoonIcon}`}
            aria-label="深色模式"
          />
        )}
      </button>
    </Tooltip>
  );
};

/**
 * Theme Selector Component
 *
 * A dropdown-style theme selector with light/dark/auto options
 */
export const ThemeSelector: React.FC<{
  className?: string;
  style?: React.CSSProperties;
}> = ({ className, style }) => {
  const { theme, setTheme } = useAppStore();
  const lightButtonStateClass =
    theme === 'light' ? styles.selectorButtonActive : styles.selectorButtonInactive;
  const darkButtonStateClass =
    theme === 'dark' ? styles.selectorButtonActive : styles.selectorButtonInactive;

  return (
    <Space size="small" style={style} className={`${styles.selectorSpace} ${className ?? ''}`}>
      <BgColorsOutlined
        className={styles.selectorIcon}
        aria-label="主题选择"
      />
      <Text type="secondary" className={styles.selectorLabel}>
        主题:
      </Text>
      <Space.Compact>
        <button
          onClick={() => setTheme('light')}
          aria-label="浅色模式"
          aria-pressed={theme === 'light'}
          className={`${styles.selectorButtonBase} ${styles.selectorButtonLeft} ${lightButtonStateClass}`}
        >
          浅色
        </button>
        <button
          onClick={() => setTheme('dark')}
          aria-label="深色模式"
          aria-pressed={theme === 'dark'}
          className={`${styles.selectorButtonBase} ${styles.selectorButtonRight} ${darkButtonStateClass}`}
        >
          深色
        </button>
      </Space.Compact>
    </Space>
  );
};

export default ThemeToggle;
