import { ThemeConfig } from 'antd';
import zhCN from 'antd/locale/zh_CN';

export const baseThemeConfig: ThemeConfig = {
  token: {
    colorPrimary: '#1677ff',
    colorInfo: '#1677ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorBgLayout: '#f8fafc',
    colorBgContainer: '#ffffff',
    fontFamily:
      "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji'",
    fontSize: 14,
    colorTextHeading: '#1e293b',
    colorText: '#334155',
    colorTextSecondary: '#475569',
    borderRadius: 8,
    wireframe: false,
  },
  components: {
    Layout: {
      headerBg: 'rgba(255, 255, 255, 0.95)',
      siderBg: 'rgba(255, 255, 255, 0.95)',
      triggerBg: '#fff',
    },
    Menu: {
      itemBg: 'transparent',
      subMenuItemBg: 'transparent',
      itemSelectedBg: 'rgba(22, 119, 255, 0.08)',
      itemSelectedColor: '#1677ff',
      itemColor: '#475569',
      itemHoverColor: '#1677ff',
    },
    Card: {
      boxShadow:
        '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02)',
      headerFontSize: 16,
    },
    Table: {
      headerBg: '#f8fafc',
      headerColor: '#475569',
      headerSplitColor: 'transparent',
      rowHoverBg: '#f1f5f9',
    },
    Button: {
      controlHeight: 36,
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

export const appLocale = zhCN;
