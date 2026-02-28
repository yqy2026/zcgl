import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PermissionGuard from '../PermissionGuard';

const mockUseCapabilities = vi.hoisted(() => vi.fn());

vi.mock('@/hooks/useCapabilities', () => ({
  useCapabilities: mockUseCapabilities,
}));

describe('PermissionGuard (deprecated compat shell)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when permission check passes', () => {
    mockUseCapabilities.mockReturnValue({
      canPerform: vi.fn(() => true),
      loading: false,
    });

    render(
      <PermissionGuard permissions={[{ resource: 'asset', action: 'read' }]}>
        <div>allowed-content</div>
      </PermissionGuard>
    );

    expect(screen.getByText('allowed-content')).toBeInTheDocument();
  });

  it('renders fallback when permission check fails', () => {
    mockUseCapabilities.mockReturnValue({
      canPerform: vi.fn(() => false),
      loading: false,
    });

    render(
      <PermissionGuard
        permissions={[{ resource: 'asset', action: 'read' }]}
        fallback={<div>custom-forbidden</div>}
      >
        <div>allowed-content</div>
      </PermissionGuard>
    );

    expect(screen.queryByText('allowed-content')).not.toBeInTheDocument();
    expect(screen.getByText('custom-forbidden')).toBeInTheDocument();
  });

  it('supports all-mode checks', () => {
    const canPerform = vi.fn().mockReturnValueOnce(true).mockReturnValueOnce(false);

    mockUseCapabilities.mockReturnValue({
      canPerform,
      loading: false,
    });

    render(
      <PermissionGuard
        mode="all"
        permissions={[
          { resource: 'asset', action: 'read' },
          { resource: 'asset', action: 'update' },
        ]}
        fallback={<div>denied</div>}
      >
        <div>allowed-content</div>
      </PermissionGuard>
    );

    expect(screen.getByText('denied')).toBeInTheDocument();
  });

  it('renders loading state while capabilities are loading', () => {
    mockUseCapabilities.mockReturnValue({
      canPerform: vi.fn(() => false),
      loading: true,
    });

    render(
      <PermissionGuard permissions={[{ resource: 'asset', action: 'read' }]}>
        <div>allowed-content</div>
      </PermissionGuard>
    );

    expect(screen.getByText('权限检查中...')).toBeInTheDocument();
  });

  it('keeps hook order stable when loading changes between renders', () => {
    let loading = true;
    const canPerform = vi.fn(() => true);

    mockUseCapabilities.mockImplementation(() => ({
      canPerform,
      loading,
    }));

    const { rerender } = render(
      <PermissionGuard permissions={[{ resource: 'asset', action: 'read' }]}>
        <div>allowed-content</div>
      </PermissionGuard>
    );

    expect(screen.getByText('权限检查中...')).toBeInTheDocument();

    loading = false;
    expect(() =>
      rerender(
        <PermissionGuard permissions={[{ resource: 'asset', action: 'read' }]}>
          <div>allowed-content</div>
        </PermissionGuard>
      )
    ).not.toThrow();

    expect(screen.getByText('allowed-content')).toBeInTheDocument();
  });
});
