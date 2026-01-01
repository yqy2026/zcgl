import { ThemeConfig } from 'antd'
import zhCN from 'antd/locale/zh_CN'

/**
 * Base theme configuration for the application
 * Consolidated from main.tsx and App.tsx ConfigProvider configurations
 */
export const baseThemeConfig: ThemeConfig = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#f5222d',
    borderRadius: 8, // Unified value from App.tsx (more modern standard)
    fontSize: 14,
  },
  components: {
    Layout: {
      headerBg: '#fff',
      siderBg: '#fff',
    },
    Menu: {
      itemBg: 'transparent',
      subMenuItemBg: 'transparent',
    },
  },
}

/**
 * Application locale configuration
 */
export const appLocale = zhCN
