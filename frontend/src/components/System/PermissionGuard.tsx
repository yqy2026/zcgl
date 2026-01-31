import React from 'react';
import { Result, Button } from 'antd';
import usePermission, { PERMISSIONS } from '@/hooks/usePermission';

interface PermissionGuardProps {
  permissions: Array<{ resource: string; action: string }>;
  fallback?: React.ReactNode;
  children: React.ReactNode;
  mode?: 'any' | 'all'; // 任意权限或所有权限
}

const PermissionGuard: React.FC<PermissionGuardProps> = ({
  permissions,
  fallback,
  children,
  mode = 'any',
}) => {
  const { hasAnyPermission, hasAllPermissions, loading } = usePermission();

  if (loading === true) {
    return <div>权限检查中...</div>;
  }

  const hasRequiredPermissions =
    mode === 'any' ? hasAnyPermission(permissions) : hasAllPermissions(permissions);

  if (hasRequiredPermissions === false) {
    return fallback !== null && fallback !== undefined ? (
      fallback
    ) : (
      <Result
        status="403"
        title="访问被拒绝"
        subTitle="抱歉，您没有权限访问此页面。"
        extra={
          <Button type="primary" onClick={() => void window.history.back()}>
            返回上一页
          </Button>
        }
      />
    );
  }

  return <>{children}</>;
};

export default PermissionGuard;
export { PermissionGuard };

// 预定义的权限保护组件
export const UserManagementGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <PermissionGuard permissions={[PERMISSIONS.USER_VIEW]}>{children}</PermissionGuard>
);

export const RoleManagementGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <PermissionGuard permissions={[PERMISSIONS.ROLE_VIEW]}>{children}</PermissionGuard>
);

export const OrganizationManagementGuard: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => <PermissionGuard permissions={[PERMISSIONS.ORGANIZATION_VIEW]}>{children}</PermissionGuard>;

export const SystemLogsGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <PermissionGuard permissions={[PERMISSIONS.SYSTEM_LOGS]}>{children}</PermissionGuard>
);

export const AssetManagementGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <PermissionGuard permissions={[PERMISSIONS.ASSET_VIEW]}>{children}</PermissionGuard>
);

export const AssetCreateGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <PermissionGuard permissions={[PERMISSIONS.ASSET_CREATE]}>{children}</PermissionGuard>
);

export const RentalManagementGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <PermissionGuard permissions={[PERMISSIONS.RENTAL_VIEW]}>{children}</PermissionGuard>
);
