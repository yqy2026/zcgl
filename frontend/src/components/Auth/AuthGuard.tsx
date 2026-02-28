import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Result, Button } from 'antd';
import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { useAuth } from '@/hooks/useAuth';
import { useCapabilities } from '@/hooks/useCapabilities';
import type { AuthzAction, ResourceType } from '@/types/capability';

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
  const { isAuthenticated, user } = useAuth();
  const { canPerform, loading } = useCapabilities();
  const location = useLocation();

  const normalizeAction = (action: string): AuthzAction => {
    if (action === 'view') return 'read';
    if (action === 'edit') return 'update';
    if (action === 'import') return 'create';
    return action as AuthzAction;
  };

  const normalizeResource = (resource: string): ResourceType => {
    if (resource === 'rental') return 'rent_contract';
    if (resource === 'organization') return 'party';
    return resource as ResourceType;
  };

  // 检查用户是否已认证
  if (!isAuthenticated) {
    const from = location.pathname + location.search + location.hash;
    return <Navigate to="/login" state={{ from, message: '请先登录后再访问此页面' }} replace />;
  }

  if (loading) {
    return <div>权限检查中...</div>;
  }

  // 检查单个权限
  if (requiredPermission !== undefined) {
    // 解析权限字符串，格式通常为 "resource:action" 或 "resource action"
    const [resource, action] = requiredPermission.includes(':')
      ? requiredPermission.split(':')
      : requiredPermission.split(' ');
    if (!canPerform(normalizeAction(action), normalizeResource(resource))) {
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
    requiredPermissions !== undefined &&
    requiredPermissions !== null &&
    requiredPermissions.length > 0 &&
    !requiredPermissions.some(permission =>
      canPerform(normalizeAction(permission.action), normalizeResource(permission.resource))
    )
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
  if (user !== undefined && user !== null && user.is_active === false) {
    return (
      <Result
        status="403"
        title="账户已禁用"
        subTitle="您的账户已被管理员禁用，请联系系统管理员。"
        icon={<UserOutlined />}
        extra={
          <Button type="primary" onClick={() => (window.location.href = '/login')}>
            重新登录
          </Button>
        }
      />
    );
  }

  return <>{children}</>;
};

export default AuthGuard;
