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
      <Space size="small" style={{ gap: 'var(--spacing-sm)' }}>
        <SunOutlined
          style={{
            fontSize: size === 'small' ? '14px' : '16px',
            color: isDark ? 'var(--color-text-tertiary)' : 'var(--color-warning)',
          }}
          aria-label="浅色模式图标"
        />
        {switchElement}
        <MoonOutlined
          style={{
            fontSize: size === 'small' ? '14px' : '16px',
            color: isDark ? 'var(--color-primary)' : 'var(--color-text-tertiary)',
          }}
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

  return (
    <Tooltip title={isDark ? '切换到浅色模式' : '切换到深色模式'}>
      <button
        onClick={toggleTheme}
        aria-label={isDark ? '切换到浅色模式' : '切换到深色模式'}
        className={`theme-toggle-button ${className ?? ''}`}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: size === 'large' ? '44px' : size === 'middle' ? '40px' : '36px',
          height: size === 'large' ? '44px' : size === 'middle' ? '40px' : '36px',
          minWidth: size === 'large' ? '44px' : size === 'middle' ? '40px' : '36px',
          minHeight: size === 'large' ? '44px' : size === 'middle' ? '40px' : '36px',
          padding: 'var(--spacing-sm)',
          background: 'transparent',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          cursor: 'pointer',
          transition: 'all var(--transition-fast)',
          ...style,
        }}
      >
        {isDark ? (
          <SunOutlined
            style={{
              fontSize: size === 'large' ? '18px' : size === 'middle' ? '16px' : '14px',
              color: 'var(--color-warning)',
            }}
            aria-label="浅色模式"
          />
        ) : (
          <MoonOutlined
            style={{
              fontSize: size === 'large' ? '18px' : size === 'middle' ? '16px' : '14px',
              color: 'var(--color-primary)',
            }}
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

  return (
    <Space size="small" style={{ gap: 'var(--spacing-sm)', ...style }} className={className}>
      <BgColorsOutlined
        style={{
          fontSize: '16px',
          color: 'var(--color-text-secondary)',
        }}
        aria-label="主题选择"
      />
      <Text type="secondary" style={{ fontSize: 'var(--font-size-sm)' }}>
        主题:
      </Text>
      <Space.Compact>
        <button
          onClick={() => setTheme('light')}
          aria-label="浅色模式"
          aria-pressed={theme === 'light'}
          style={{
            padding: 'var(--spacing-xs) var(--spacing-md)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm) 0 0 var(--radius-sm)',
            background: theme === 'light' ? 'var(--color-primary-light)' : 'transparent',
            color: theme === 'light' ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            cursor: 'pointer',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          浅色
        </button>
        <button
          onClick={() => setTheme('dark')}
          aria-label="深色模式"
          aria-pressed={theme === 'dark'}
          style={{
            padding: 'var(--spacing-xs) var(--spacing-md)',
            border: '1px solid var(--color-border)',
            borderLeft: 'none',
            borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
            background: theme === 'dark' ? 'var(--color-primary-light)' : 'transparent',
            color: theme === 'dark' ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            cursor: 'pointer',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          深色
        </button>
      </Space.Compact>
    </Space>
  );
};

export default ThemeToggle;
