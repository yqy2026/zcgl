import { ThemeConfig } from 'antd';
import zhCN from 'antd/locale/zh_CN';

export const baseThemeConfig: ThemeConfig = {
  token: {
    colorPrimary: '#0e63e5',
    colorPrimaryHover: '#1169f0',
    colorPrimaryActive: '#0958d9',
    colorInfo: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorBgLayout: '#f8fafc',
    colorBgContainer: '#ffffff',
    fontFamily:
      "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji'",
    fontSize: 14,
    colorTextHeading: '#262626',
    colorText: '#262626',
    colorTextSecondary: '#595959',
    colorTextTertiary: '#717171',
    colorTextQuaternary: '#bfbfbf',
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
      itemSelectedBg: 'rgba(14, 99, 229, 0.08)',
      itemSelectedColor: '#0e63e5',
      itemColor: '#595959',
      itemHoverColor: '#0e63e5',
    },
    Card: {
      boxShadow:
        '0 0.0625rem 0.125rem 0 rgba(0, 0, 0, 0.03), 0 0.0625rem 0.375rem -0.0625rem rgba(0, 0, 0, 0.02), 0 0.125rem 0.25rem 0 rgba(0, 0, 0, 0.02)',
      headerFontSize: 16,
    },
    Table: {
      headerBg: '#f8fafc',
      headerColor: '#595959',
      headerSplitColor: 'transparent',
      rowHoverBg: '#f1f5f9',
    },
    Button: {
      controlHeight: 36,
      contentFontSize: 14,
      borderRadius: 6,
      boxShadow: '0 0.0625rem 0.125rem 0 rgba(0, 0, 0, 0.05)',
    },
    Statistic: {
      titleFontSize: 14,
      contentFontSize: 24,
    },
  },
};

export const appLocale = zhCN;
