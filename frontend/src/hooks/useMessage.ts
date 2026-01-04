import { App, message as globalMessage } from 'antd'

/**
 * 统一的消息提示Hook
 * 替代Antd 5.x中已弃用的静态方法调用
 */
export const useMessage = () => {
  const { message } = App.useApp()

  return {
    success: (content: string, duration?: number) => {
      return message.success({
        content,
        duration: duration || 3,
        key: `success-${Date.now()}`,
      })
    },
    error: (content: string, duration?: number) => {
      return message.error({
        content,
        duration: duration || 4,
        key: `error-${Date.now()}`,
      })
    },
    warning: (content: string, duration?: number) => {
      return message.warning({
        content,
        duration: duration || 3,
        key: `warning-${Date.now()}`,
      })
    },
    info: (content: string, duration?: number) => {
      return message.info({
        content,
        duration: duration || 3,
        key: `info-${Date.now()}`,
      })
    },
    loading: (content: string, duration?: number) => {
      return message.loading({
        content,
        duration: duration || 0,
        key: `loading-${Date.now()}`,
      })
    },
    destroy: (key?: string) => {
      if (key !== null && key !== undefined && key !== '') {
        message.destroy(key)
      } else {
        message.destroy()
      }
    },
    open: (config: Parameters<typeof globalMessage.open>[0]) => {
      return message.open({
        ...config,
        key: config.key || `message-${Date.now()}`,
      })
    },
    config: (config: Parameters<typeof globalMessage.config>[0]) => {
      globalMessage.config(config)
    },
  }
}

export default useMessage