import { ThemeConfig } from 'antd';
import zhCN from 'antd/locale/zh_CN';

/**
 * Base theme configuration for the application
 * Consolidated from main.tsx and App.tsx ConfigProvider configurations
 */
export const baseThemeConfig: ThemeConfig = {
  token: {
    // Modern "Asset Blue" - Clean, professional, trustworthy
    colorPrimary: '#1677ff',
    colorInfo: '#1677ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',

    // Backgrounds
    colorBgLayout: '#f8fafc', // Slate 50 - Cleaner, cooler gray
    colorBgContainer: '#ffffff',

    // Typography
    fontFamily:
      "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji'",
    fontSize: 14,
    colorTextHeading: '#1e293b', // Slate 800
    colorText: '#334155', // Slate 700
    colorTextSecondary: '#64748b', // Slate 500

    // Modern Borders & Radius
    borderRadius: 8,
    wireframe: false,
  },
  components: {
    Layout: {
      headerBg: 'rgba(255, 255, 255, 0.8)', // Stronger glass base
      siderBg: 'rgba(255, 255, 255, 0.8)', // Stronger glass base
      triggerBg: '#fff',
    },
    Menu: {
      itemBg: 'transparent',
      subMenuItemBg: 'transparent',
      itemSelectedBg: 'rgba(22, 119, 255, 0.08)', // Very subtle active state
      itemSelectedColor: '#1677ff',
      itemColor: '#64748b', // Slate 500
      itemHoverColor: '#1677ff',
    },
    Card: {
      boxShadow:
        '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02)', // Soft, modern shadow
      headerFontSize: 16,
    },
    Table: {
      headerBg: '#f8fafc',
      headerColor: '#475569', // Slate 600
      headerSplitColor: 'transparent',
      rowHoverBg: '#f1f5f9', // Slate 100
    },
    Button: {
      controlHeight: 36, // Slightly taller for better click targets
      contentFontSize: 14,
      borderRadius: 6,
      boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    },
    Statistic: {
      titleFontSize: 14,
      contentFontSize: 24,
    },
  },
};

/**
 * Application locale configuration
 */
export const appLocale = zhCN;
