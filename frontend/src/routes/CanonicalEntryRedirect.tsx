import React from 'react';
import { Navigate } from 'react-router-dom';
import { Spin } from 'antd';
import { BASE_PATHS } from '@/constants/routes';
import { useAuth } from '@/contexts/AuthContext';
import { useCapabilities } from '@/hooks/useCapabilities';
import { useDataScopeStore } from '@/stores/dataScopeStore';
import type { AuthzAction, ResourceType } from '@/types/capability';

interface CanonicalEntryRedirectProps {
  targetPath: string;
  resource: ResourceType;
  action?: AuthzAction;
}

const CanonicalEntryRedirect: React.FC<CanonicalEntryRedirectProps> = ({
  targetPath,
  resource,
  action = 'read',
}) => {
  const { capabilitiesLoading, error } = useAuth();
  const initialized = useDataScopeStore(state => state.initialized);
  const { canPerform } = useCapabilities();

  if (capabilitiesLoading || !initialized) {
    return (
      <div>
        <Spin size="small" /> Loading...
      </div>
    );
  }

  if (error != null || !canPerform(action, resource)) {
    return <Navigate to={BASE_PATHS.DASHBOARD} replace />;
  }

  return <Navigate to={targetPath} replace />;
};

export default CanonicalEntryRedirect;
