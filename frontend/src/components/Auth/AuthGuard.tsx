import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Result, Button } from 'antd';
import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { useAuth } from '../../hooks/useAuth';

interface AuthGuardProps {
  children: React.ReactNode;
  requiredPermission?: string;
  requiredPermissions?: Array<{ resource: string; action: string }>;
  fallback?: React.ComponentType;
  _fallback?: React.ComponentType;
}

const AuthGuard: React.FC<AuthGuardProps> = ({
  children,
  requiredPermission,
  requiredPermissions,
  _fallback = () => (
    <Result
      status="403"
      title="403"
      subTitle="抱歉，您没有权限访问此页面。"
      icon={<LockOutlined />}
      extra={
        <Button type="primary" onClick={() => window.history.back()}>
          返回上一页
        </Button>
      }
    />
  ),
}) => {
  const { isAuthenticated, hasPermission, hasAnyPermission, user } = useAuth();
  const location = useLocation();

  // 检查用户是否已认证
  if (!isAuthenticated) {
    const from = location.pathname + location.search + location.hash;
    return <Navigate to="/login" state={{ from, message: '请先登录后再访问此页面' }} replace />;
  }

  // 检查单个权限
  if (requiredPermission != null) {
    // 解析权限字符串，格式通常为 "resource:action" 或 "resource action"
    const [resource, action] = requiredPermission.includes(':')
      ? requiredPermission.split(':')
      : requiredPermission.split(' ');
    if (!hasPermission(resource, action)) {
      return (
        <Result
          status="403"
          title="403 - 权限不足"
          subTitle={`您需要 "${requiredPermission}" 权限才能访问此页面。`}
          icon={<LockOutlined />}
          extra={
            <Button type="primary" onClick={() => window.history.back()}>
              返回上一页
            </Button>
          }
        />
      );
    }
  }

  // 检查多个权限（任一满足即可）
  if (
    requiredPermissions &&
    requiredPermissions.length > 0 &&
    !hasAnyPermission(requiredPermissions)
  ) {
    const permissionNames = requiredPermissions.map(p => `${p.resource}:${p.action}`).join(', ');
    return (
      <Result
        status="403"
        title="403 - 权限不足"
        subTitle={`您需要以下任一权限才能访问此页面：${permissionNames}`}
        icon={<LockOutlined />}
        extra={
          <Button type="primary" onClick={() => window.history.back()}>
            返回上一页
          </Button>
        }
      />
    );
  }

  // 检查用户是否激活
  if (user != null && user.isActive === false) {
    return (
      <Result
        status="403"
        title="账户已禁用"
        subTitle="您的账户已被管理员禁用，请联系系统管理员。"
        icon={<UserOutlined />}
        extra={
          <Button
            type="primary"
            onClick={() => {
              window.location.href = '/login';
            }}
          >
            重新登录
          </Button>
        }
      />
    );
  }

  return <>{children}</>;
};

export default AuthGuard;
