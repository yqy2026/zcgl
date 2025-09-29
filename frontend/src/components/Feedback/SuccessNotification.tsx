import { notification } from 'antd'
import { 
  CheckCircleOutlined, 
  ExclamationCircleOutlined, 
  InfoCircleOutlined, 
  CloseCircleOutlined,
  WifiOutlined,
  LockOutlined,
  CheckCircleOutlined as ServerOutlined
} from '@ant-design/icons'

interface NotificationOptions {
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  description?: string
  duration?: number
}

class SuccessNotification {
  static notify(options: NotificationOptions) {
    const { type, title, description, duration = 4.5 } = options
    
    const iconMap = {
      success: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
      error: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
      warning: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
      info: <InfoCircleOutlined style={{ color: '#1890ff' }} />,
    }

    notification[type]({
      message: title,
      description,
      duration,
      icon: iconMap[type],
      placement: 'topRight',
    })
  }

  static success = {
    save: () => SuccessNotification.notify({
      type: 'success',
      title: '保存成功',
      description: '数据已成功保存到系统中',
    }),
    
    create: () => SuccessNotification.notify({
      type: 'success',
      title: '创建成功',
      description: '新记录已成功创建',
    }),
    
    update: () => SuccessNotification.notify({
      type: 'success',
      title: '更新成功',
      description: '记录已成功更新',
    }),
    
    delete: () => SuccessNotification.notify({
      type: 'success',
      title: '删除成功',
      description: '记录已成功删除',
    }),
    
    import: (count: number) => SuccessNotification.notify({
      type: 'success',
      title: '导入成功',
      description: `成功导入 ${count} 条记录`,
    }),
    
    export: () => SuccessNotification.notify({
      type: 'success',
      title: '导出成功',
      description: '数据已成功导出到文件',
    }),
  }

  static error = {
    network: () => notification.error({
      message: '网络错误',
      description: '网络连接失败，请检查网络设置后重试',
      duration: 0,
      icon: <WifiOutlined style={{ color: '#ff4d4f' }} />,
    }),
    
    server: () => SuccessNotification.notify({
      type: 'error',
      title: '服务器错误',
      description: '服务器暂时无法响应，请稍后重试',
      duration: 0,
    }),
    
    validation: (message: string) => SuccessNotification.notify({
      type: 'error',
      title: '数据验证失败',
      description: message,
    }),
    
    permission: () => notification.error({
      message: '权限不足',
      description: '您没有执行此操作的权限，请联系管理员',
      icon: <LockOutlined style={{ color: '#ff4d4f' }} />,
    }),
    
    notFound: () => SuccessNotification.notify({
      type: 'error',
      title: '资源不存在',
      description: '请求的资源不存在或已被删除',
    }),
  }

  static warning = {
    unsaved: () => SuccessNotification.notify({
      type: 'warning',
      title: '有未保存的更改',
      description: '您有未保存的更改，离开页面将丢失这些更改',
      duration: 0,
    }),
    
    permission: () => notification.warning({
      message: '权限受限',
      description: '您的权限受限，某些功能可能无法使用',
      icon: <LockOutlined style={{ color: '#faad14' }} />,
    }),
    
    maintenance: () => SuccessNotification.notify({
      type: 'warning',
      title: '系统维护',
      description: '系统正在维护中，部分功能可能受到影响',
      duration: 0,
    }),
  }

  static info = {
    loading: (message: string = '正在处理...') => SuccessNotification.notify({
      type: 'info',
      title: '处理中',
      description: message,
      duration: 2,
    }),
    
    autoSave: () => SuccessNotification.notify({
      type: 'info',
      title: '自动保存',
      description: '数据已自动保存',
      duration: 2,
    }),
    
    offline: () => SuccessNotification.notify({
      type: 'info',
      title: '离线模式',
      description: '当前处于离线模式，数据将在网络恢复后同步',
      duration: 0,
    }),
  }
}

export default SuccessNotification