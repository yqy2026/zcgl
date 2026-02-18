import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import { DynamicRouteRenderer } from '../DynamicRouteRenderer';
import type { DynamicRoute } from '../dynamicRouteTypes';

const pendingRouteComponent = React.lazy(
  () => new Promise<{ default: React.ComponentType<Record<string, unknown>> }>(() => {})
);

const mockedRoutes = new Map<string, DynamicRoute>();

vi.mock('../DynamicRouteContext', () => ({
  useDynamicRoute: () => ({
    routes: mockedRoutes,
  }),
}));

describe('DynamicRouteRenderer', () => {
  beforeEach(() => {
    mockedRoutes.clear();
    mockedRoutes.set('slow-route', {
      id: 'slow-route',
      path: '/slow',
      component: pendingRouteComponent,
      meta: {
        title: '慢页面',
      },
    });
  });

  it('renders suspense fallback text without unsupported Spin tip warning', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    renderWithProviders(<DynamicRouteRenderer />, { route: '/slow' });

    expect(screen.getByText('加载 慢页面...')).toBeInTheDocument();
    expect(
      errorSpy.mock.calls.some(([message]) =>
        typeof message === 'string' && message.includes('tip only work in nest or fullscreen pattern')
      )
    ).toBe(false);

    errorSpy.mockRestore();
  });
});
