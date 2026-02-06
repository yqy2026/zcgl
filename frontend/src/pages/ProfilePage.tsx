import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Card,
  Row,
  Col,
  Descriptions,
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Skeleton,
  Typography,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { UserOutlined, EditOutlined, LockOutlined, HistoryOutlined } from '@ant-design/icons';
import { COLORS } from '@/styles/colorMap';
import { useAuth } from '@/hooks/useAuth';
import { AuthService } from '@/services/authService';

const { Title, Text } = Typography;

interface ProfileFormData {
  full_name: string;
  email?: string;
  phone?: string;
}

const ProfilePage: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [passwordForm] = Form.useForm();

  // 初始化数据
  useEffect(() => {
    if (user != null) {
      form.setFieldsValue({
        username: user.username ?? '',
        full_name: user.full_name ?? '',
        email: user.email ?? '',
        phone: user.phone ?? '',
      });
    }
  }, [form, user]);

  const updateProfileMutation = useMutation({
    mutationFn: async (values: ProfileFormData) => {
      return await AuthService.updateProfile(values);
    },
    onSuccess: async () => {
      MessageManager.success('个人资料更新成功');
      setEditModalVisible(false);
      await refreshUser();
    },
    onError: (error: unknown) => {
      MessageManager.error((error as Error).message || '更新失败，请稍后重试');
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: async (values: { oldPassword: string; newPassword: string }) => {
      await AuthService.changePassword(values.oldPassword, values.newPassword);
    },
    onSuccess: () => {
      MessageManager.success('密码修改成功');
      setPasswordModalVisible(false);
      passwordForm.resetFields();
    },
    onError: (error: unknown) => {
      MessageManager.error((error as Error).message || '密码修改失败');
    },
  });

  // 处理个人资料更新
  const handleUpdateProfile = (values: ProfileFormData) => {
    if (user == null) {
      MessageManager.error('用户信息缺失，请重新登录');
      return;
    }
    updateProfileMutation.mutate({
      full_name: values.full_name,
      email: values.email,
      phone: values.phone,
    });
  };

  // 处理密码修改
  const handleChangePassword = (values: { oldPassword: string; newPassword: string }) => {
    changePasswordMutation.mutate(values);
  };

  // 获取角色显示名称
  const getRoleDisplay = (roleName?: string, roleCodes?: string[]) => {
    const roleMap: Record<string, { text: string; color: string }> = {
      super_admin: { text: '超级管理员', color: 'red' },
      admin: { text: '系统管理员', color: 'red' },
      manager: { text: '管理员', color: 'orange' },
      user: { text: '普通用户', color: 'blue' },
      asset_viewer: { text: '资产查看员', color: 'blue' },
      asset_admin: { text: '资产管理员', color: 'orange' },
    };
    const primaryCode = roleCodes?.[0]?.toLowerCase();
    const mapped = primaryCode != null ? roleMap[primaryCode] : undefined;
    const displayText = roleName ?? mapped?.text ?? roleCodes?.[0] ?? '-';
    const color = mapped?.color ?? 'default';
    return <Tag color={color}>{displayText}</Tag>;
  };

  // 获取状态显示
  const getStatusDisplay = (isActive: boolean) => {
    return <Tag color={isActive ? 'green' : 'red'}>{isActive ? '活跃' : '停用'}</Tag>;
  };

  if (user == null) {
    return (
      <div style={{ padding: '24px' }}>
        <Skeleton loading={true} avatar active>
          <Card>
            <Skeleton paragraph={{ rows: 4 }} />
          </Card>
        </Skeleton>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', background: COLORS.bgTertiary, minHeight: '100vh' }}>
      {/* 页面标题 */}
      <Title level={2} style={{ marginBottom: '24px', color: COLORS.primary }}>
        个人资料
      </Title>

      <Row gutter={[24, 24]}>
        {/* 基本信息 */}
        <Col span={24}>
          <Card
            title={
              <Space>
                <UserOutlined />
                <span>基本信息</span>
              </Space>
            }
            extra={
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={() => setEditModalVisible(true)}
              >
                编辑资料
              </Button>
            }
          >
            <Row gutter={[24, 24]}>
              <Col xs={24} md={8}>
                <div style={{ textAlign: 'center' }}>
                  <div
                    style={{
                      width: '80px',
                      height: '80px',
                      margin: '0 auto 16px',
                      borderRadius: '50%',
                      background: COLORS.bgQuaternary,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <UserOutlined style={{ fontSize: '32px', color: COLORS.primary }} />
                  </div>
                  <Text type="secondary">用户头像</Text>
                </div>
              </Col>

              <Col xs={24} md={16}>
                <Descriptions column={{ xs: 1, sm: 1, md: 2 }} bordered>
                  <Descriptions.Item label="用户名">
                    <Text strong>{user.username}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="姓名">
                    <Text strong>
                      {user.full_name !== null &&
                      user.full_name !== undefined &&
                      user.full_name !== ''
                        ? user.full_name
                        : '-'}
                    </Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="邮箱">
                    {user.email !== null && user.email !== undefined && user.email !== ''
                      ? user.email
                      : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="电话">
                    {user.phone !== null && user.phone !== undefined && user.phone !== ''
                      ? user.phone
                      : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="角色">
                    {getRoleDisplay(user.role_name, user.roles)}
                  </Descriptions.Item>
                  <Descriptions.Item label="状态">
                    {getStatusDisplay(user.is_active)}
                  </Descriptions.Item>
                  <Descriptions.Item label="最后登录时间">
                    {user.last_login_at !== null &&
                    user.last_login_at !== undefined &&
                    user.last_login_at !== ''
                      ? new Date(user.last_login_at).toLocaleString()
                      : '从未登录'}
                  </Descriptions.Item>
                  <Descriptions.Item label="密码最后修改时间">
                    {user.password_last_changed !== null &&
                    user.password_last_changed !== undefined &&
                    user.password_last_changed !== ''
                      ? new Date(user.password_last_changed).toLocaleString()
                      : '未修改'}
                  </Descriptions.Item>
                </Descriptions>
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 安全设置 */}
        <Col span={24}>
          <Card
            title={
              <Space>
                <LockOutlined />
                <span>安全设置</span>
              </Space>
            }
          >
            <Space orientation="vertical" size="large" style={{ width: '100%' }}>
              <div
                style={{
                  padding: '16px',
                  background: COLORS.bgSecondary,
                  borderRadius: '6px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <Text strong>登录密码</Text>
                  <br />
                  <Text type="secondary">建议定期修改密码，确保账户安全</Text>
                </div>
                <Button icon={<LockOutlined />} onClick={() => setPasswordModalVisible(true)}>
                  修改密码
                </Button>
              </div>

              <div
                style={{
                  padding: '16px',
                  background: COLORS.bgSecondary,
                  borderRadius: '6px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <Text strong>登录历史</Text>
                  <br />
                  <Text type="secondary">查看最近的登录记录</Text>
                </div>
                <Button
                  icon={<HistoryOutlined />}
                  onClick={() => {
                    void MessageManager.info('登录历史功能开发中');
                  }}
                >
                  查看历史
                </Button>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 编辑资料模态框 */}
      <Modal
        title="编辑个人资料"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
        width={600}
        forceRender
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={values => void handleUpdateProfile(values as ProfileFormData)}
          style={{ marginTop: '16px' }}
        >
          <Form.Item
            label="用户名"
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input disabled />
          </Form.Item>

          <Form.Item
            label="姓名"
            name="full_name"
            rules={[{ required: true, message: '请输入姓名' }]}
          >
            <Input placeholder="请输入姓名" />
          </Form.Item>

          <Form.Item
            label="邮箱"
            name="email"
            rules={[{ type: 'email', message: '请输入正确的邮箱格式' }]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>

          <Form.Item
            label="电话"
            name="phone"
            rules={[{ pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号格式' }]}
          >
            <Input placeholder="请输入手机号" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setEditModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={updateProfileMutation.isPending}>
                保存更改
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 修改密码模态框 */}
      <Modal
        title="修改密码"
        open={passwordModalVisible}
        onCancel={() => {
          setPasswordModalVisible(false);
          passwordForm.resetFields();
        }}
        footer={null}
        width={500}
        forceRender
      >
        <Form
          form={passwordForm}
          layout="vertical"
          onFinish={values =>
            void handleChangePassword(values as { oldPassword: string; newPassword: string })
          }
          style={{ marginTop: '16px' }}
        >
          <Form.Item
            label="当前密码"
            name="oldPassword"
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password placeholder="请输入当前密码" />
          </Form.Item>

          <Form.Item
            label="新密码"
            name="newPassword"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码长度至少6位' },
            ]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>

          <Form.Item
            label="确认新密码"
            name="confirmPassword"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (
                    value === null ||
                    value === undefined ||
                    value === '' ||
                    getFieldValue('newPassword') === value
                  ) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="请再次输入新密码" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button
                onClick={() => {
                  setPasswordModalVisible(false);
                  passwordForm.resetFields();
                }}
              >
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={changePasswordMutation.isPending}>
                确认修改
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ProfilePage;
