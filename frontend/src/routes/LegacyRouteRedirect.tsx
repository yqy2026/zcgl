import React, { useMemo } from 'react';
import { Navigate } from 'react-router-dom';
import { Spin } from 'antd';

import {
  ASSET_ROUTES,
  BASE_PATHS,
  CONTRACT_GROUP_ROUTES,
  PROJECT_ROUTES,
  PROPERTY_CERTIFICATE_ROUTES,
} from '@/constants/routes';
import { useAuth } from '@/contexts/AuthContext';
import PerspectiveResolutionPage from '@/routes/PerspectiveResolutionPage';
import {
  resolveLegacyPerspectiveFailure,
  resolveLegacyPerspectiveTarget,
} from '@/routes/perspectiveResolution';

type LegacyListPath =
  | typeof BASE_PATHS.ASSETS
  | typeof ASSET_ROUTES.LIST
  | typeof CONTRACT_GROUP_ROUTES.LIST
  | typeof PROJECT_ROUTES.LIST
  | typeof PROPERTY_CERTIFICATE_ROUTES.LIST;

interface LegacyRouteRedirectProps {
  legacyPath: LegacyListPath;
}

const LegacyRouteRedirect: React.FC<LegacyRouteRedirectProps> = ({ legacyPath }) => {
  const { capabilities, capabilitiesLoading, error } = useAuth();

  const target = useMemo(() => {
    return resolveLegacyPerspectiveTarget(legacyPath, capabilities);
  }, [capabilities, legacyPath]);
  const resolution = useMemo(() => {
    return resolveLegacyPerspectiveFailure(legacyPath, capabilities);
  }, [capabilities, legacyPath]);

  if (capabilitiesLoading) {
    return (
      <div>
        <Spin size="small" /> 路由跳转计算中...
      </div>
    );
  }

  if (error != null) {
    return <Navigate to={BASE_PATHS.DASHBOARD} replace />;
  }

  if (resolution != null) {
    return <PerspectiveResolutionPage resolution={resolution} />;
  }

  if (target == null) {
    return <Navigate to={BASE_PATHS.DASHBOARD} replace />;
  }

  return <Navigate to={target} replace />;
};

export default LegacyRouteRedirect;
