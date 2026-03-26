import React from 'react';
import { Button, Result, Spin } from 'antd';
import { useLocation } from 'react-router-dom';
import { useCapabilities } from '@/hooks/useCapabilities';
import { getRoutePerspective } from '@/routes/perspective';
import type { AuthzAction, Perspective, ResourceType } from '@/types/capability';

interface CapabilityGuardProps {
  action: AuthzAction;
  resource: ResourceType;
  perspective?: Perspective;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

const CapabilityGuard: React.FC<CapabilityGuardProps> = ({
  action,
  resource,
  perspective,
  fallback,
  children,
}) => {
  const { canPerform, loading } = useCapabilities();
  const location = useLocation();

  if (loading) {
    return (
      <div>
        <Spin size="small" /> 权限检查中...
      </div>
    );
  }

  const resolvedPerspective = perspective ?? getRoutePerspective(location.pathname) ?? undefined;
  const allowed = canPerform(action, resource, resolvedPerspective);
  if (!allowed) {
    return (
      fallback ?? (
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
      )
    );
  }

  return <>{children}</>;
};

export default CapabilityGuard;
export { CapabilityGuard };
export type { CapabilityGuardProps };
