import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CapabilityGuard from '../CapabilityGuard';

const memoryRouterFuture = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const;

const mockUseCapabilities = vi.hoisted(() => vi.fn());

vi.mock('@/hooks/useCapabilities', () => ({
  useCapabilities: mockUseCapabilities,
}));

describe('CapabilityGuard', () => {
  const renderInRouter = (ui: ReactNode) => {
    return render(<MemoryRouter future={memoryRouterFuture}>{ui}</MemoryRouter>);
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when capability check passes', () => {
    mockUseCapabilities.mockReturnValue({
      canPerform: vi.fn(() => true),
      loading: false,
    });

    renderInRouter(
      <CapabilityGuard action="read" resource="asset">
        <div>allowed-content</div>
      </CapabilityGuard>
    );

    expect(screen.getByText('allowed-content')).toBeInTheDocument();
  });

  it('renders fallback when capability check fails', () => {
    mockUseCapabilities.mockReturnValue({
      canPerform: vi.fn(() => false),
      loading: false,
    });

    renderInRouter(
      <CapabilityGuard action="read" resource="asset" fallback={<div>custom-forbidden</div>}>
        <div>allowed-content</div>
      </CapabilityGuard>
    );

    expect(screen.queryByText('allowed-content')).not.toBeInTheDocument();
    expect(screen.getByText('custom-forbidden')).toBeInTheDocument();
  });

  it('renders loading state while capabilities are loading', () => {
    mockUseCapabilities.mockReturnValue({
      canPerform: vi.fn(() => false),
      loading: true,
    });

    renderInRouter(
      <CapabilityGuard action="read" resource="asset">
        <div>allowed-content</div>
      </CapabilityGuard>
    );

    expect(screen.getByText('权限检查中...')).toBeInTheDocument();
  });

  it('passes the current route perspective into capability checks by default', () => {
    const canPerform = vi.fn(() => false);
    mockUseCapabilities.mockReturnValue({
      canPerform,
      loading: false,
    });

    render(
      <MemoryRouter future={memoryRouterFuture} initialEntries={['/owner/assets']}>
        <Routes>
          <Route
            path="/owner/assets"
            element={
              <CapabilityGuard action="read" resource="asset" fallback={<div>forbidden</div>}>
                <div>allowed-content</div>
              </CapabilityGuard>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(canPerform).toHaveBeenCalledWith('read', 'asset', 'owner');
    expect(screen.getByText('forbidden')).toBeInTheDocument();
  });
});
