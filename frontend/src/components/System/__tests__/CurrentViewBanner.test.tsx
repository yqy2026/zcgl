import React from 'react';
import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test/utils/test-helpers';
import CurrentViewBanner from '../CurrentViewBanner';

describe('CurrentViewBanner', () => {
  it('shows owner banner on owner-prefixed routes', () => {
    renderWithProviders(<CurrentViewBanner />, { route: '/owner/assets' });

    expect(screen.getByText('当前视角')).toBeInTheDocument();
    expect(screen.getByText('业主视角')).toBeInTheDocument();
  });

  it('shows manager banner on manager-prefixed routes', () => {
    renderWithProviders(<CurrentViewBanner />, { route: '/manager/projects' });

    expect(screen.getByText('当前视角')).toBeInTheDocument();
    expect(screen.getByText('经营视角')).toBeInTheDocument();
  });

  it('hides banner on shared or legacy routes', () => {
    renderWithProviders(<CurrentViewBanner />, { route: '/assets/list' });

    expect(screen.queryByText('当前视角')).not.toBeInTheDocument();
    expect(screen.queryByText('业主视角')).not.toBeInTheDocument();
    expect(screen.queryByText('经营视角')).not.toBeInTheDocument();
  });
});
