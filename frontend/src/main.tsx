import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'

import App from './App.tsx'
import './styles/index.css'
import { baseThemeConfig, appLocale } from './theme/config'
import { initErrorMonitoring } from './utils/errorMonitoring'

// Initialize error monitoring as early as possible
initErrorMonitoring()

// 配置dayjs中文
dayjs.locale('zh-cn')

// 创建React Query客户端 - 优化配置
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnMount: false,          // 避免重复请求
      staleTime: 5 * 60 * 1000,       // 5分钟缓存
      gcTime: 10 * 60 * 1000,         // 10分钟缓存时间 (v5语法)
    },
    mutations: {
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={appLocale} theme={baseThemeConfig}>
        <App />
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
