import React from 'react';
import { Button, Result, Spin } from 'antd';
import { useCapabilities } from '@/hooks/useCapabilities';
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

  if (loading) {
    return (
      <div>
        <Spin size="small" /> 权限检查中...
      </div>
    );
  }

  const allowed = canPerform(action, resource, perspective);
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
