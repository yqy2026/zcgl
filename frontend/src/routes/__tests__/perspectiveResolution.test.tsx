import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import PerspectiveResolutionPage from '@/routes/PerspectiveResolutionPage';
import { resolvePerspectiveMismatch } from '@/routes/perspectiveResolution';

describe('perspective resolution', () => {
  it('routes invalid /owner/assets/:id sessions to deterministic manager/detail fallback', () => {
    const resolution = resolvePerspectiveMismatch({
      pathname: '/owner/assets/asset-1',
      resource: 'asset',
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
    });

    expect(resolution).not.toBeNull();
    expect(resolution?.targetPath).toBe('/manager/assets/asset-1');
    expect(resolution?.availablePerspectives).toEqual(['manager']);
  });

  it('renders the perspective resolution page when current route perspective is no longer allowed', () => {
    const resolution = resolvePerspectiveMismatch({
      pathname: '/owner/assets/asset-1',
      resource: 'asset',
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
    });

    if (resolution == null) {
      throw new Error('Expected perspective mismatch resolution');
    }

    render(
      <MemoryRouter>
        <PerspectiveResolutionPage resolution={resolution} />
      </MemoryRouter>
    );

    expect(screen.getByText('当前视角已失效')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '切换到经营视角' })).toHaveAttribute(
      'href',
      '/manager/assets/asset-1'
    );
  });
});
