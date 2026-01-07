import React, { useState, useEffect } from 'react'
import { Card, Form, Input, Switch, Button, message, Divider, Typography, Space, Tabs, Alert } from 'antd'
import { SettingOutlined, DatabaseOutlined, CloudDownloadOutlined, CloudUploadOutlined } from '@ant-design/icons'
import { systemService } from '../../services/systemService'
import type { SystemSettings } from '../../services/systemService'
import { createLogger } from '../../utils/logger'

const pageLogger = createLogger('SystemSettings')

const { Title, Text } = Typography
const { TabPane } = Tabs

interface SystemInfo {
  version: string
  build_time: string
  database_status: string
  api_version: string
  environment: string
}

const SystemSettingsPage: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [settings, setSettings] = useState<SystemSettings | null>(null)
  const [activeTab, setActiveTab] = useState('settings')

  // 获取系统信息
  const fetchSystemInfo = React.useCallback(async () => {
    try {
      setLoading(true)
      const response = await systemService.getSystemInfo()
      setSystemInfo(response as unknown as SystemInfo)
    } catch (error: unknown) {
      pageLogger.error('获取系统信息失败:', error as Error)
      const errorMsg = error instanceof Error ? error.message : '未知错误'
      message.error('获取系统信息失败: ' + errorMsg)
    } finally {
      setLoading(false)
    }
  }, [])

  // 获取系统设置
  const fetchSettings = React.useCallback(async () => {
    try {
      setLoading(true)
      const response = await systemService.getSettings()
      setSettings(response as unknown as SystemSettings)
      form.setFieldsValue(response)
    } catch (error: unknown) {
      pageLogger.error('获取系统设置失败:', error as Error)
      const errorMsg = error instanceof Error ? error.message : '未知错误'
      message.error('获取系统设置失败: ' + errorMsg)
    } finally {
      setLoading(false)
    }
  }, [form])

  // 保存设置
  const handleSaveSettings = async (values: Partial<SystemSettings>) => {
    try {
      setLoading(true)
      await systemService.updateSettings(values)
      message.success('设置保存成功')
      void fetchSettings()
    } catch (error: unknown) {
      pageLogger.error('保存设置失败:', error as Error)
      const errorMsg = error instanceof Error ? error.message : '未知错误'
      message.error('保存设置失败: ' + errorMsg)
    } finally {
      setLoading(false)
    }
  }

  // 备份数据
  const handleBackup = async () => {
    try {
      setLoading(true)
      const response = await systemService.backupSystem()
      message.success('数据备份成功')
      // 创建下载链接
      const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `backup_${new Date().toISOString().split('T')[0]}.json`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error: unknown) {
      pageLogger.error('数据备份失败:', error as Error)
      const errorMsg = error instanceof Error ? error.message : '未知错误'
      message.error('数据备份失败: ' + errorMsg)
    } finally {
      setLoading(false)
    }
  }

  // 恢复数据
  const handleRestore = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      setLoading(true)
      await systemService.restoreSystem(file)
      message.success('数据恢复成功，请刷新页面查看最新数据')
      setTimeout(() => {
        window.location.reload()
      }, 2000)
    } catch (error: unknown) {
      pageLogger.error('数据恢复失败:', error as Error)
      const errorMsg = error instanceof Error ? error.message : '未知错误'
      message.error('数据恢复失败: ' + errorMsg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'info') {
      void fetchSystemInfo()
    } else if (activeTab === 'settings') {
      void fetchSettings()
    }
  }, [activeTab])

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title level={2}>
        <SettingOutlined /> 系统设置
      </Title>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="基本设置" key="settings">
          <Card title="系统基本设置" loading={loading}>
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSaveSettings}
              initialValues={settings || undefined}
            >
              <Form.Item
                label="站点名称"
                name="site_name"
                rules={[{ required: true, message: '请输入站点名称' }]}
              >
                <Input placeholder="请输入站点名称" />
              </Form.Item>

              <Form.Item
                label="站点描述"
                name="site_description"
              >
                <Input.TextArea rows={3} placeholder="请输入站点描述" />
              </Form.Item>

              <Form.Item
                label="允许用户注册"
                name="allow_registration"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <Form.Item
                label="会话超时时间（分钟）"
                name="session_timeout"
                rules={[{ required: true, message: '请输入会话超时时间' }]}
              >
                <Input type="number" placeholder="请输入会话超时时间" />
              </Form.Item>

              <Divider orientation="left">密码策略</Divider>

              <Form.Item
                label={['password_policy', 'min_length']}
                name={['password_policy', 'min_length']}
                rules={[{ required: true, message: '请输入最小密码长度' }]}
              >
                <Input type="number" placeholder="最小密码长度" />
              </Form.Item>

              <Form.Item
                label={['password_policy', 'require_uppercase']}
                name={['password_policy', 'require_uppercase']}
                valuePropName="checked"
              >
                <Switch /> 要求大写字母
              </Form.Item>

              <Form.Item
                label={['password_policy', 'require_lowercase']}
                name={['password_policy', 'require_lowercase']}
                valuePropName="checked"
              >
                <Switch /> 要求小写字母
              </Form.Item>

              <Form.Item
                label={['password_policy', 'require_numbers']}
                name={['password_policy', 'require_numbers']}
                valuePropName="checked"
              >
                <Switch /> 要求数字
              </Form.Item>

              <Form.Item
                label={['password_policy', 'require_special_chars']}
                name={['password_policy', 'require_special_chars']}
                valuePropName="checked"
              >
                <Switch /> 要求特殊字符
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading}>
                  保存设置
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>

        <TabPane tab="系统信息" key="info">
          <Card title="系统信息" loading={loading}>
            {systemInfo ? (
              <div>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div><strong>版本号：</strong>{systemInfo.version}</div>
                  <div><strong>构建时间：</strong>{systemInfo.build_time}</div>
                  <div><strong>数据库状态：</strong>
                    <Text type={systemInfo.database_status === 'connected' ? 'success' : 'danger'}>
                      {systemInfo.database_status === 'connected' ? '已连接' : '未连接'}
                    </Text>
                  </div>
                  <div><strong>API版本：</strong>{systemInfo.api_version}</div>
                  <div><strong>运行环境：</strong>{systemInfo.environment}</div>
                </Space>
              </div>
            ) : (
              <Alert
                message="无法获取系统信息"
                description="请检查服务器连接状态"
                type="warning"
                showIcon
              />
            )}
          </Card>
        </TabPane>

        <TabPane tab="数据备份" key="backup">
          <Card title="数据备份与恢复">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert
                message="备份说明"
                description="定期备份数据是保障系统安全的重要措施。建议每周至少备份一次数据。"
                type="info"
                showIcon
              />

              <div>
                <Title level={4}>
                  <DatabaseOutlined /> 数据备份
                </Title>
                <Button
                  type="primary"
                  icon={<CloudDownloadOutlined />}
                  onClick={handleBackup}
                  loading={loading}
                >
                  立即备份
                </Button>
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  下载当前系统的完整数据备份
                </Text>
              </div>

              <Divider />

              <div>
                <Title level={4}>
                  <CloudUploadOutlined /> 数据恢复
                </Title>
                <input
                  type="file"
                  accept=".json"
                  onChange={handleRestore}
                  style={{ display: 'none' }}
                  id="restore-file-input"
                />
                <Button
                  danger
                  icon={<CloudUploadOutlined />}
                  onClick={() => document.getElementById('restore-file-input')?.click()}
                  loading={loading}
                >
                  选择备份文件恢复
                </Button>
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  警告：恢复数据将覆盖当前所有数据，请谨慎操作！
                </Text>
              </div>
            </Space>
          </Card>
        </TabPane>
      </Tabs>
    </div>
  )
}

export default SystemSettingsPage
