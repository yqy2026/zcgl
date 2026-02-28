import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CapabilityGuard from '../CapabilityGuard';

const mockUseCapabilities = vi.hoisted(() => vi.fn());

vi.mock('@/hooks/useCapabilities', () => ({
  useCapabilities: mockUseCapabilities,
}));

describe('CapabilityGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when capability check passes', () => {
    mockUseCapabilities.mockReturnValue({
      canPerform: vi.fn(() => true),
      loading: false,
    });

    render(
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

    render(
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

    render(
      <CapabilityGuard action="read" resource="asset">
        <div>allowed-content</div>
      </CapabilityGuard>
    );

    expect(screen.getByText('权限检查中...')).toBeInTheDocument();
  });
});
