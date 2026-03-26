import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import {
  ASSET_ROUTES,
  BASE_PATHS,
  CONTRACT_GROUP_ROUTES,
  MANAGER_ROUTES,
  OWNER_ROUTES,
  PROJECT_ROUTES,
  PROPERTY_CERTIFICATE_ROUTES,
} from '@/constants/routes';
import { protectedRoutes } from '@/routes/AppRoutes';

const memoryRouterFuture = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const;

const mockUseAuth = vi.hoisted(() => vi.fn());

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: mockUseAuth,
}));

const LocationProbe = () => {
  const location = useLocation();
  return <div data-testid="location-probe">{location.pathname}</div>;
};

const findRouteElement = (path: string) => {
  const route = protectedRoutes.find(item => item.path === path);
  expect(route).toBeDefined();
  return route?.element ?? null;
};

const renderLegacyRoute = (path: string) => {
  const RouteElement = findRouteElement(path);
  expect(RouteElement).not.toBeNull();

  render(
    <MemoryRouter future={memoryRouterFuture} initialEntries={[path]}>
      <Routes>
        <Route path={path} element={RouteElement != null ? <RouteElement /> : null} />
        <Route path="*" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('legacy perspective route redirects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      capabilities: [],
      capabilitiesLoading: false,
      error: null,
    });
  });

  it('redirects legacy asset routes to owner assets first', () => {
    mockUseAuth.mockReturnValue({
      capabilitiesLoading: false,
      capabilities: [
        {
          resource: 'asset',
          actions: ['read'],
          perspectives: ['owner'],
          data_scope: {
            owner_party_ids: ['owner-1'],
            manager_party_ids: [],
          },
        },
      ],
      error: null,
    });

    renderLegacyRoute(BASE_PATHS.ASSETS);
    expect(screen.getByTestId('location-probe')).toHaveTextContent(OWNER_ROUTES.ASSETS);
  });

  it('redirects /assets/list to manager assets when owner binding is absent', () => {
    mockUseAuth.mockReturnValue({
      capabilitiesLoading: false,
      capabilities: [
        {
          resource: 'asset',
          actions: ['read'],
          perspectives: ['manager'],
          data_scope: {
            owner_party_ids: [],
            manager_party_ids: ['manager-1'],
          },
        },
      ],
      error: null,
    });

    renderLegacyRoute(ASSET_ROUTES.LIST);
    expect(screen.getByTestId('location-probe')).toHaveTextContent(MANAGER_ROUTES.ASSETS);
  });

  it('redirects shared legacy routes to owner first, then manager', () => {
    mockUseAuth.mockReturnValue({
      capabilitiesLoading: false,
      capabilities: [
        {
          resource: 'contract_group',
          actions: ['read'],
          perspectives: ['owner', 'manager'],
          data_scope: {
            owner_party_ids: ['owner-1'],
            manager_party_ids: ['manager-1'],
          },
        },
        {
          resource: 'property_certificate',
          actions: ['read'],
          perspectives: ['owner'],
          data_scope: {
            owner_party_ids: ['owner-1'],
            manager_party_ids: [],
          },
        },
      ],
      error: null,
    });

    renderLegacyRoute(CONTRACT_GROUP_ROUTES.LIST);
    expect(screen.getByTestId('location-probe')).toHaveTextContent(OWNER_ROUTES.CONTRACT_GROUPS);
  });

  it('redirects legacy project route to manager projects', () => {
    mockUseAuth.mockReturnValue({
      capabilitiesLoading: false,
      capabilities: [
        {
          resource: 'project',
          actions: ['read'],
          perspectives: ['manager'],
          data_scope: {
            owner_party_ids: [],
            manager_party_ids: ['manager-1'],
          },
        },
      ],
      error: null,
    });

    renderLegacyRoute(PROJECT_ROUTES.LIST);
    expect(screen.getByTestId('location-probe')).toHaveTextContent(MANAGER_ROUTES.PROJECTS);
  });

  it('redirects legacy project route from backend perspectives even when data scope bindings are empty', () => {
    mockUseAuth.mockReturnValue({
      capabilitiesLoading: false,
      capabilities: [
        {
          resource: 'project',
          actions: ['read'],
          perspectives: ['manager'],
          data_scope: {
            owner_party_ids: [],
            manager_party_ids: [],
          },
        },
      ],
      error: null,
    });

    renderLegacyRoute(PROJECT_ROUTES.LIST);
    expect(screen.getByTestId('location-probe')).toHaveTextContent(MANAGER_ROUTES.PROJECTS);
  });

  it('redirects legacy property certificate route to owner route and falls back to dashboard', () => {
    mockUseAuth.mockReturnValue({
      capabilitiesLoading: false,
      capabilities: [
        {
          resource: 'property_certificate',
          actions: ['read'],
          perspectives: ['owner'],
          data_scope: {
            owner_party_ids: ['owner-1'],
            manager_party_ids: [],
          },
        },
      ],
      error: null,
    });

    renderLegacyRoute(PROPERTY_CERTIFICATE_ROUTES.LIST);
    expect(screen.getByTestId('location-probe')).toHaveTextContent(
      OWNER_ROUTES.PROPERTY_CERTIFICATES
    );
  });

  it('shows loading state while capabilities are still loading', () => {
    mockUseAuth.mockReturnValue({
      capabilitiesLoading: true,
      capabilities: [],
      error: null,
    });

    renderLegacyRoute(CONTRACT_GROUP_ROUTES.LIST);
    expect(screen.getByText('路由跳转计算中...')).toBeInTheDocument();
  });

  it('falls back to dashboard when no matching perspective binding exists', () => {
    mockUseAuth.mockReturnValue({
      capabilitiesLoading: false,
      capabilities: [],
      error: null,
    });

    renderLegacyRoute(CONTRACT_GROUP_ROUTES.LIST);
    expect(screen.getByText('当前视角已失效')).toBeInTheDocument();
  });

  it('shows fail-closed resolution for legacy /project when no project perspective is available', () => {
    mockUseAuth.mockReturnValue({
      capabilitiesLoading: false,
      capabilities: [],
      error: null,
    });

    renderLegacyRoute(PROJECT_ROUTES.LIST);
    expect(screen.getByText('当前视角已失效')).toBeInTheDocument();
  });
});
