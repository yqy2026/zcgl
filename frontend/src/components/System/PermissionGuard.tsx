import React from 'react';
import { Button, Result } from 'antd';
import { useCapabilities } from '@/hooks/useCapabilities';
import type { AuthzAction, ResourceType } from '@/types/capability';

interface PermissionGuardProps {
  permissions: Array<{ resource: string; action: string }>;
  fallback?: React.ReactNode;
  children: React.ReactNode;
  mode?: 'any' | 'all'; // 任意权限或所有权限
}

const ACTION_ALIASES: Record<string, AuthzAction> = {
  view: 'read',
  edit: 'update',
  import: 'create',
  settings: 'update',
  logs: 'read',
  dictionary: 'read',
  lock: 'update',
  assign_permissions: 'update',
};

const RESOURCE_ALIASES: Record<string, ResourceType> = {
  rental: 'contract',
  organization: 'party',
  ownership: 'party',
  system_settings: 'system',
  operation_log: 'system',
  dictionary: 'system',
  llm_prompt: 'system',
};

const normalizePermission = (permission: { resource: string; action: string }) => {
  const action = ACTION_ALIASES[permission.action] ?? (permission.action as AuthzAction);
  const resource = RESOURCE_ALIASES[permission.resource] ?? (permission.resource as ResourceType);
  return { action, resource };
};

/**
 * @deprecated Phase 3 迁移期兼容壳，请改用 CapabilityGuard。
 */
const PermissionGuard: React.FC<PermissionGuardProps> = ({
  permissions,
  fallback,
  children,
  mode = 'any',
}) => {
  const { canPerform, loading } = useCapabilities();
  const normalizedPermissions = permissions.map(permission => normalizePermission(permission));

  if (loading) {
    return <div>权限检查中...</div>;
  }

  const hasRequiredPermissions =
    normalizedPermissions.length === 0
      ? true
      : mode === 'all'
        ? normalizedPermissions.every(permission =>
            canPerform(permission.action, permission.resource)
          )
        : normalizedPermissions.some(permission =>
            canPerform(permission.action, permission.resource)
          );

  if (!hasRequiredPermissions) {
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
