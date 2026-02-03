import React, { useEffect, useState } from 'react';
import { Card, Form, Input, Switch, Button, Divider, Typography, Space, Tabs, Alert } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MessageManager } from '@/utils/messageManager';
import {
  SettingOutlined,
  DatabaseOutlined,
  CloudDownloadOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import { systemService } from '@/services/systemService';
import type { SystemInfo, SystemSettings } from '@/services/systemService';
import { createLogger } from '@/utils/logger';

const pageLogger = createLogger('SystemSettings');

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const SystemSettingsPage: React.FC = () => {
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('settings');
  const queryClient = useQueryClient();

  const systemInfoQuery = useQuery<SystemInfo, Error>({
    queryKey: ['system', 'info'],
    queryFn: async () => {
      try {
        return await systemService.getSystemInfo();
      } catch (error: unknown) {
        pageLogger.error('获取系统信息失败:', error as Error);
        throw error;
      }
    },
    enabled: activeTab === 'info',
    refetchOnWindowFocus: false,
  });

  const settingsQuery = useQuery<SystemSettings, Error>({
    queryKey: ['system', 'settings'],
    queryFn: async () => {
      try {
        return await systemService.getSettings();
      } catch (error: unknown) {
        pageLogger.error('获取系统设置失败:', error as Error);
        throw error;
      }
    },
    enabled: activeTab === 'settings',
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (systemInfoQuery.isError === true) {
      const errorMsg = systemInfoQuery.error?.message ?? '未知错误';
      MessageManager.error('获取系统信息失败: ' + errorMsg);
    }
  }, [systemInfoQuery.error, systemInfoQuery.isError]);

  useEffect(() => {
    if (settingsQuery.data != null) {
      form.setFieldsValue(settingsQuery.data);
    }
  }, [form, settingsQuery.data]);

  useEffect(() => {
    if (settingsQuery.isError === true) {
      const errorMsg = settingsQuery.error?.message ?? '未知错误';
      MessageManager.error('获取系统设置失败: ' + errorMsg);
    }
  }, [settingsQuery.error, settingsQuery.isError]);

  const systemInfo: SystemInfo | null = systemInfoQuery.data ?? null;
  const settings: SystemSettings | null = settingsQuery.data ?? null;
  const isSettingsLoading = settingsQuery.isLoading || settingsQuery.isFetching;
  const isInfoLoading = systemInfoQuery.isLoading || systemInfoQuery.isFetching;


  // 保存设置
  const updateSettingsMutation = useMutation({
    mutationFn: async (values: Partial<SystemSettings>) => {
      return await systemService.updateSettings(values);
    },
    onSuccess: () => {
      MessageManager.success('设置保存成功');
      void queryClient.invalidateQueries({ queryKey: ['system', 'settings'] });
    },
    onError: (error: unknown) => {
      pageLogger.error('保存设置失败:', error as Error);
      const errorMsg = error instanceof Error ? error.message : '未知错误';
      MessageManager.error('保存设置失败: ' + errorMsg);
    },
  });

  // 备份数据
  const backupMutation = useMutation({
    mutationFn: async () => {
      return await systemService.backupSystem();
    },
    onSuccess: response => {
      MessageManager.success('数据备份成功');
      const blob = new Blob([JSON.stringify(response, null, 2)], {
        type: 'application/json',
      });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `backup_${new Date().toISOString().split('T')[0]}.json`;
      anchor.click();
      window.URL.revokeObjectURL(url);
    },
    onError: (error: unknown) => {
      pageLogger.error('数据备份失败:', error as Error);
      const errorMsg = error instanceof Error ? error.message : '未知错误';
      MessageManager.error('数据备份失败: ' + errorMsg);
    },
  });

  // 恢复数据
  const restoreMutation = useMutation({
    mutationFn: async (file: File) => {
      return await systemService.restoreSystem(file);
    },
    onSuccess: () => {
      MessageManager.success('数据恢复成功，请刷新页面查看最新数据');
      setTimeout(() => {
        window.location.reload();
      }, 2000);
    },
    onError: (error: unknown) => {
      pageLogger.error('数据恢复失败:', error as Error);
      const errorMsg = error instanceof Error ? error.message : '未知错误';
      MessageManager.error('数据恢复失败: ' + errorMsg);
    },
  });

  const handleSaveSettings = (values: Partial<SystemSettings>) => {
    updateSettingsMutation.mutate(values);
  };

  const handleBackup = () => {
    backupMutation.mutate();
  };

  const handleRestore = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file == null) return;
    restoreMutation.mutate(file);
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title level={2}>
        <SettingOutlined /> 系统设置
      </Title>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="基本设置" key="settings">
          <Card
            title="系统基本设置"
            loading={isSettingsLoading || updateSettingsMutation.isPending}
          >
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

              <Form.Item label="站点描述" name="site_description">
                <Input.TextArea rows={3} placeholder="请输入站点描述" />
              </Form.Item>

              <Form.Item label="允许用户注册" name="allow_registration" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Form.Item
                label="会话超时时间（分钟）"
                name="session_timeout"
                rules={[{ required: true, message: '请输入会话超时时间' }]}
              >
                <Input type="number" placeholder="请输入会话超时时间" />
              </Form.Item>

              <Divider titlePlacement="start">密码策略</Divider>

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
                <Button type="primary" htmlType="submit" loading={updateSettingsMutation.isPending}>
                  保存设置
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>

        <TabPane tab="系统信息" key="info">
          <Card title="系统信息" loading={isInfoLoading}>
            {systemInfo ? (
              <div>
                <Space orientation="vertical" style={{ width: '100%' }}>
                  <div>
                    <strong>版本号：</strong>
                    {systemInfo.version}
                  </div>
                  <div>
                    <strong>构建时间：</strong>
                    {systemInfo.build_time}
                  </div>
                  <div>
                    <strong>数据库状态：</strong>
                    <Text type={systemInfo.database_status === 'connected' ? 'success' : 'danger'}>
                      {systemInfo.database_status === 'connected' ? '已连接' : '未连接'}
                    </Text>
                  </div>
                  <div>
                    <strong>API版本：</strong>
                    {systemInfo.api_version}
                  </div>
                  <div>
                    <strong>运行环境：</strong>
                    {systemInfo.environment}
                  </div>
                </Space>
              </div>
            ) : (
              <Alert
                title="无法获取系统信息"
                description="请检查服务器连接状态"
                type="warning"
                showIcon
              />
            )}
          </Card>
        </TabPane>

        <TabPane tab="数据备份" key="backup">
          <Card title="数据备份与恢复">
            <Space orientation="vertical" style={{ width: '100%' }}>
              <Alert
                title="备份说明"
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
                  loading={backupMutation.isPending}
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
                  loading={restoreMutation.isPending}
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
  );
};

export default SystemSettingsPage;
