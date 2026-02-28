import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { Form } from 'antd';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import AssetBasicInfoSection from '../AssetBasicInfoSection';

vi.mock('@/components/Common/PartySelector', () => ({
  default: ({ filterMode }: { filterMode?: string }) => (
    <div data-testid="party-selector" data-filter-mode={filterMode ?? ''} />
  ),
}));

vi.mock('@/components/Ownership/OwnershipSelect', () => ({
  default: () => <div data-testid="legacy-ownership-select" />,
}));

vi.mock('@/components/Project/ProjectSelect', () => ({
  default: () => <div data-testid="project-select" />,
}));

vi.mock('@/components/Dictionary', () => ({
  DictionarySelect: () => <div data-testid="dictionary-select" />,
}));

describe('AssetBasicInfoSection', () => {
  it('uses PartySelector for owner_party_id instead of legacy OwnershipSelect', () => {
    renderWithProviders(
      <Form>
        <AssetBasicInfoSection />
      </Form>
    );

    expect(screen.getByText('权属主体')).toBeInTheDocument();
    expect(screen.getByTestId('party-selector')).toHaveAttribute('data-filter-mode', 'owner');
    expect(screen.queryByTestId('legacy-ownership-select')).not.toBeInTheDocument();
  });
});
