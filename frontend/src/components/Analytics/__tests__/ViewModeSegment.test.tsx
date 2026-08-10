import React from 'react';
import { beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, renderWithProviders, screen } from '@/test/utils/test-helpers';
import { useDataScopeStore } from '@/stores/dataScopeStore';
import ViewModeSegment from '../ViewModeSegment';

describe('ViewModeSegment', () => {
  beforeEach(() => {
    useDataScopeStore.getState().reset();
  });

  it('hides the segment for non-dual-binding users', () => {
    useDataScopeStore.setState({
      bindingTypes: ['owner'],
      ownerPartyIds: ['owner-1'],
      managerPartyIds: [],
      isAdmin: false,
      initialized: true,
      isOwner: true,
      isManager: false,
      isDualBinding: false,
      isSingleOwner: true,
      isSingleManager: false,
      currentViewMode: 'owner',
    });

    renderWithProviders(<ViewModeSegment />);

    expect(screen.queryByText('产权方口径')).not.toBeInTheDocument();
  });

  it('renders for dual-binding users and switches currentViewMode', () => {
    useDataScopeStore.setState({
      bindingTypes: ['owner', 'manager'],
      ownerPartyIds: ['owner-1'],
      managerPartyIds: ['manager-1'],
      isAdmin: false,
      initialized: true,
      isOwner: true,
      isManager: true,
      isDualBinding: true,
      isSingleOwner: false,
      isSingleManager: false,
      currentViewMode: 'owner',
    });

    renderWithProviders(<ViewModeSegment />);

    expect(screen.getByText('产权方口径')).toBeInTheDocument();
    expect(screen.getByText('运营方口径')).toBeInTheDocument();

    fireEvent.click(screen.getByText('运营方口径'));

    expect(useDataScopeStore.getState().currentViewMode).toBe('manager');
  });
  it('renders for admins and switches analytics perspective', () => {
    useDataScopeStore.setState({
      bindingTypes: [],
      ownerPartyIds: [],
      managerPartyIds: [],
      isAdmin: true,
      initialized: true,
      isOwner: false,
      isManager: false,
      isDualBinding: false,
      isSingleOwner: false,
      isSingleManager: false,
      currentViewMode: 'owner',
    });

    renderWithProviders(<ViewModeSegment />);

    const options = screen.getAllByRole('radio');
    expect(options).toHaveLength(2);

    fireEvent.click(options[1]);

    expect(useDataScopeStore.getState().currentViewMode).toBe('manager');
  });

  it('shows unselected guidance for dual-binding users without an explicit choice', () => {
    useDataScopeStore.setState({
      bindingTypes: ['owner', 'manager'],
      ownerPartyIds: ['owner-1'],
      managerPartyIds: ['manager-1'],
      isAdmin: false,
      initialized: true,
      isOwner: true,
      isManager: true,
      isDualBinding: true,
      isSingleOwner: false,
      isSingleManager: false,
      currentViewMode: null,
    });

    const { container } = renderWithProviders(<ViewModeSegment />);

    expect(screen.getByText('产权方口径')).toBeInTheDocument();
    expect(screen.getByText('运营方口径')).toBeInTheDocument();
    expect(screen.getByText(/请选择.*口径/)).toBeInTheDocument();
    const radios = container.querySelectorAll<HTMLInputElement>('input[type="radio"]');
    expect(radios.length).toBeGreaterThan(0);
    for (const radio of radios) {
      expect(radio.checked).toBe(false);
    }
  });
});
