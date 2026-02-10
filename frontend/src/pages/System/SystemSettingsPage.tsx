import React, { useEffect, useRef, useState } from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  Divider,
  Typography,
  Space,
  Tabs,
  Alert,
  Tag,
} from 'antd';
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
import PageContainer from '@/components/Common/PageContainer';
import styles from './SystemSettingsPage.module.css';

const pageLogger = createLogger('SystemSettings');

const { Title, Text } = Typography;
type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';

const SystemSettingsPage: React.FC = () => {
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('settings');
  const restoreFileInputRef = useRef<HTMLInputElement>(null);
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
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
    neutral: styles.toneNeutral,
  };
  const getToneClassName = (tone: Tone): string => {
    return toneClassMap[tone];
  };
  const databaseStatusMeta = (() => {
    if (systemInfo?.database_status === 'connected') {
      return {
        label: '已连接',
        description: '数据库连接正常',
        tone: 'success' as const,
      };
    }
    if (systemInfo?.database_status === 'disconnected') {
      return {
        label: '未连接',
        description: '数据库连接异常',
        tone: 'error' as const,
      };
    }
    return {
      label: '未知',
      description: '数据库状态待确认',
      tone: 'neutral' as const,
    };
  })();

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
    if (file == null) {
      return;
    }
    restoreMutation.mutate(file);
    event.target.value = '';
  };

  const handleSelectRestoreFile = () => {
    const fileInput = restoreFileInputRef.current;
    if (fileInput != null) {
      fileInput.click();
    }
  };

  const tabItems = [
    {
      key: 'settings',
      label: (
        <Space size={8} className={styles.tabLabel}>
          <SettingOutlined className={styles.tabIcon} />
          <span>基本设置</span>
        </Space>
      ),
      children: (
        <Card
          title="系统基本设置"
          loading={isSettingsLoading || updateSettingsMutation.isPending}
          className={styles.settingsCard}
        >
          <Alert
            type="info"
            showIcon
            className={styles.settingsNotice}
            message="配置提示"
            description="修改系统参数后将立即生效；建议先确认密码策略与会话超时配置。"
          />
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSaveSettings}
            initialValues={settings ?? undefined}
            className={styles.settingsForm}
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
              <InputNumber
                min={5}
                max={1440}
                controls
                className={styles.numberInput}
                placeholder="请输入会话超时时间"
              />
            </Form.Item>

            <Divider titlePlacement="start">密码策略</Divider>

            <Form.Item
              label="最小密码长度"
              name={['password_policy', 'min_length']}
              rules={[{ required: true, message: '请输入最小密码长度' }]}
            >
              <InputNumber
                min={6}
                max={128}
                controls
                className={styles.numberInput}
                placeholder="最小密码长度"
              />
            </Form.Item>

            <Form.Item
              label="要求大写字母"
              name={['password_policy', 'require_uppercase']}
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>

            <Form.Item
              label="要求小写字母"
              name={['password_policy', 'require_lowercase']}
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>

            <Form.Item
              label="要求数字"
              name={['password_policy', 'require_numbers']}
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>

            <Form.Item
              label="要求特殊字符"
              name={['password_policy', 'require_special_chars']}
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>

            <Form.Item className={styles.settingsFormActions}>
              <Button
                type="primary"
                htmlType="submit"
                loading={updateSettingsMutation.isPending}
                disabled={updateSettingsMutation.isPending}
                className={styles.actionButton}
                aria-label="保存系统设置"
              >
                保存设置
              </Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'info',
      label: (
        <Space size={8} className={styles.tabLabel}>
          <DatabaseOutlined className={styles.tabIcon} />
          <span>系统信息</span>
        </Space>
      ),
      children: (
        <Card title="系统信息" loading={isInfoLoading} className={styles.infoCard}>
          {systemInfo != null ? (
            <Space direction="vertical" size={12} className={styles.infoList}>
              <div className={styles.infoItem}>
                <Text strong className={styles.infoLabel}>
                  版本号：
                </Text>
                <Text className={styles.infoValue}>{systemInfo.version}</Text>
              </div>
              <div className={styles.infoItem}>
                <Text strong className={styles.infoLabel}>
                  构建时间：
                </Text>
                <Text className={styles.infoValue}>{systemInfo.build_time}</Text>
              </div>
              <div className={styles.infoItem}>
                <Text strong className={styles.infoLabel}>
                  数据库状态：
                </Text>
                <Space size={8} wrap className={styles.databaseStatusWrap}>
                  <Tag
                    className={`${styles.statusTag} ${getToneClassName(databaseStatusMeta.tone)}`}
                  >
                    {databaseStatusMeta.label}
                  </Tag>
                  <Text className={styles.statusDescription}>{databaseStatusMeta.description}</Text>
                </Space>
              </div>
              <div className={styles.infoItem}>
                <Text strong className={styles.infoLabel}>
                  API版本：
                </Text>
                <Text className={styles.infoValue}>{systemInfo.api_version}</Text>
              </div>
              <div className={styles.infoItem}>
                <Text strong className={styles.infoLabel}>
                  运行环境：
                </Text>
                <Text className={styles.infoValue}>{systemInfo.environment}</Text>
              </div>
            </Space>
          ) : (
            <Alert
              title="无法获取系统信息"
              description="请检查服务器连接状态"
              type="warning"
              showIcon
            />
          )}
        </Card>
      ),
    },
    {
      key: 'backup',
      label: (
        <Space size={8} className={styles.tabLabel}>
          <CloudDownloadOutlined className={styles.tabIcon} />
          <span>数据备份</span>
        </Space>
      ),
      children: (
        <Card title="数据备份与恢复" className={styles.backupCard}>
          <Space direction="vertical" size={16} className={styles.backupStack}>
            <Alert
              title="备份说明"
              description="定期备份数据是保障系统安全的重要措施。建议每周至少备份一次数据。"
              type="info"
              showIcon
            />

            <div className={styles.backupSection}>
              <Title level={4} className={styles.sectionTitle}>
                <DatabaseOutlined /> 数据备份
              </Title>
              <Space direction="vertical" size={8} className={styles.actionRow}>
                <Button
                  type="primary"
                  icon={<CloudDownloadOutlined />}
                  onClick={handleBackup}
                  loading={backupMutation.isPending}
                  disabled={backupMutation.isPending}
                  className={styles.actionButton}
                  aria-label="立即备份系统数据"
                >
                  立即备份
                </Button>
                <Text type="secondary" className={styles.actionHint}>
                  下载当前系统的完整数据备份
                </Text>
              </Space>
            </div>

            <Divider />

            <div className={styles.backupSection}>
              <Title level={4} className={styles.sectionTitle}>
                <CloudUploadOutlined /> 数据恢复
              </Title>
              <input
                type="file"
                accept=".json"
                onChange={handleRestore}
                className={styles.restoreInput}
                ref={restoreFileInputRef}
                aria-label="选择系统备份文件"
              />
              <Space direction="vertical" size={8} className={styles.actionRow}>
                <Button
                  danger
                  icon={<CloudUploadOutlined />}
                  onClick={handleSelectRestoreFile}
                  loading={restoreMutation.isPending}
                  disabled={restoreMutation.isPending}
                  className={styles.actionButton}
                  aria-label="选择备份文件并恢复数据"
                >
                  选择备份文件恢复
                </Button>
                <Text type="secondary" className={`${styles.actionHint} ${styles.warningText}`}>
                  警告：恢复数据将覆盖当前所有数据，请谨慎操作！
                </Text>
              </Space>
            </div>
          </Space>
        </Card>
      ),
    },
  ];

  return (
    <PageContainer
      title={
        <Space size={8} className={styles.pageTitle}>
          <SettingOutlined className={styles.pageTitleIcon} />
          <span>系统设置</span>
        </Space>
      }
      subTitle="管理基础参数、系统信息与备份恢复流程"
      className={styles.pageContainer}
    >
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} className={styles.tabs} />
    </PageContainer>
  );
};

export default SystemSettingsPage;
