import React from 'react';
import { renderWithProviders } from '@/test/utils/test-helpers';
import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import GlobalViewSwitcher from '../GlobalViewSwitcher';

const mockUseView = vi.fn();

vi.mock('@/contexts/ViewContext', () => ({
  useView: () => mockUseView(),
}));

vi.mock('antd', async importOriginal => {
  const actual = await importOriginal<typeof import('antd')>();
  return {
    ...actual,
    Modal: ({ open, title, children, footer }: any) =>
      open ? (
        <div data-testid="view-modal">
          <div>{title}</div>
          {children}
          {footer}
        </div>
      ) : null,
  };
});

describe('GlobalViewSwitcher', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseView.mockReturnValue({
      currentView: {
        key: 'owner:party-1',
        perspective: 'owner',
        partyId: 'party-1',
        partyName: '主体A',
        label: '产权方 · 主体A',
      },
      availableViews: [
        {
          key: 'owner:party-1',
          perspective: 'owner',
          partyId: 'party-1',
          partyName: '主体A',
          label: '产权方 · 主体A',
        },
      ],
      selectionRequired: false,
      selectorOpen: false,
      openSelector: vi.fn(),
      closeSelector: vi.fn(),
      selectView: vi.fn(),
    });
  });

  it('renders current view label', () => {
    renderWithProviders(<GlobalViewSwitcher />);

    expect(screen.getByText('产权方 · 主体A')).toBeInTheDocument();
  });

  it('opens blocking modal when reselection is required', () => {
    mockUseView.mockReturnValue({
      currentView: null,
      availableViews: [
        {
          key: 'owner:party-1',
          perspective: 'owner',
          partyId: 'party-1',
          partyName: '主体A',
          label: '产权方 · 主体A',
        },
        {
          key: 'manager:party-2',
          perspective: 'manager',
          partyId: 'party-2',
          partyName: '主体B',
          label: '运营方 · 主体B',
        },
      ],
      selectionRequired: true,
      selectorOpen: true,
      openSelector: vi.fn(),
      closeSelector: vi.fn(),
      selectView: vi.fn(),
    });

    renderWithProviders(<GlobalViewSwitcher />);

    expect(screen.getByTestId('view-modal')).toBeInTheDocument();
    expect(screen.getByTestId('view-modal')).toHaveTextContent('请选择当前主体/视角');
  });
});
