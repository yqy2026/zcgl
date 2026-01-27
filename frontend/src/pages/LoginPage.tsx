import React, { useState } from 'react';
import { Form, Input, Button, Card, Checkbox, Space, Typography, Divider, Alert } from 'antd';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';
import {
  UserOutlined,
  LockOutlined,
  SafetyCertificateOutlined,
  LoginOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import type { LoginFormData } from '../types/auth';
import styles from './LoginPage.module.css';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loading, error } = useAuth();
  const [formData, setFormData] = useState<LoginFormData>({
    username: '',
    password: '',
    remember: false,
  });

  const handleSubmit = async (values: LoginFormData) => {
    try {
      await login({ username: values.username, password: values.password });

      // 登录成功，跳转到目标页面或默认工作台
      const state = location.state as { from?: { pathname?: string } } | null;
      const from = state?.from?.pathname ?? '/dashboard';
      navigate(from, { replace: true });
    } catch {
      // 错误处理已在useAuth中完成，这里不需要额外处理
    }
  };

  const handleUsernameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, username: e.target.value }));
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, password: e.target.value }));
  };

  const handleRememberChange = (e: CheckboxChangeEvent) => {
    setFormData(prev => ({ ...prev, remember: e.target.checked }));
  };

  return (
    <div className={styles['login-page']}>
      <div className={styles['login-container']}>
        <Card className={styles['login-card']} variant="borderless">
          {/* 登录头部 */}
          <div className={styles['login-header']}>
            <Space orientation="vertical" size="middle" align="center">
              <div className={styles['login-logo']}>
                <SafetyCertificateOutlined className={styles['login-icon']} />
              </div>
              <Title level={2} className={styles['login-title']}>
                土地房产资产管理系统
              </Title>
              <Text type="secondary" className={styles['login-subtitle']}>
                请输入您的用户名和密码进行登录
              </Text>
            </Space>
          </div>

          <Divider />

          {/* 登录表单 */}
          <Form
            name="login"
            className={styles['login-form']}
            initialValues={formData}
            onFinish={handleSubmit}
            size="large"
            autoComplete="off"
            layout="vertical"
          >
            <Form.Item
              label="用户名"
              name="username"
              rules={[
                { required: true, message: '请输入用户名' },
                { min: 2, message: '用户名至少2个字符' },
                { max: 50, message: '用户名最多50个字符' },
              ]}
            >
              <Input
                prefix={<UserOutlined className={styles['input-icon']} />}
                placeholder="请输入用户名"
                value={formData.username}
                onChange={handleUsernameChange}
                autoComplete="username"
                size="large"
              />
            </Form.Item>

            <Form.Item
              label="密码"
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少6个字符' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined className={styles['input-icon']} />}
                placeholder="请输入密码"
                value={formData.password}
                onChange={handlePasswordChange}
                autoComplete="current-password"
                size="large"
              />
            </Form.Item>

            <Form.Item name="remember" valuePropName="checked">
              <Checkbox checked={formData.remember} onChange={handleRememberChange}>
                记住我的登录状态
              </Checkbox>
            </Form.Item>

            {error !== undefined && error !== null && error !== '' && (
              <Alert
                message="登录失败"
                description={error}
                type="error"
                showIcon
                className={styles['login-error']}
                closable
              />
            )}

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                className={styles['login-button']}
                loading={loading}
                block
                size="large"
                icon={<LoginOutlined />}
              >
                {loading ? '登录中...' : '立即登录'}
              </Button>
            </Form.Item>
          </Form>

          <Divider />

          {/* 登录底部 */}
          <div className={styles['login-footer']}>
            <Space orientation="vertical" size="small" align="center">
              <Text type="secondary" className={styles['login-help']}>
                <SafetyCertificateOutlined /> 如遇登录问题，请联系系统管理员
              </Text>
              <Text type="secondary" className={styles['login-tips']}>
                为保护账户安全，请定期更换密码
              </Text>
            </Space>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default LoginPage;
