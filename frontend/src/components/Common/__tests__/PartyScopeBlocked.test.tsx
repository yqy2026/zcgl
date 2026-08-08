import { describe, expect, it } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import type { UserPartyScopeView } from '@/services/systemService';
import PartyScopeBlocked from '../PartyScopeBlocked';

const invalidScope: UserPartyScopeView = {
  user_id: 'user-1',
  source: 'none',
  scope_mode: 'none',
  owner_party_ids: [],
  manager_party_ids: [],
  organization_id: null,
  source_organization_id: null,
  next_transition_at: null,
  error_code: 'PARTY_SCOPE_MISSING',
  issues: [
    {
      code: 'PARTY_SCOPE_MISSING',
      node_type: 'organization',
      safe_label: '组织链未配置代表主体',
      node_ref: null,
    },
  ],
};

const validScope: UserPartyScopeView = {
  user_id: 'user-1',
  source: 'explicit',
  scope_mode: 'owner',
  owner_party_ids: ['party-1'],
  manager_party_ids: [],
  organization_id: 'org-1',
  source_organization_id: null,
  next_transition_at: null,
  error_code: null,
  issues: [],
};

describe('PartyScopeBlocked', () => {
  it('renders a blocking state for an invalid Party scope', () => {
    renderWithProviders(<PartyScopeBlocked scope={invalidScope} />);

    expect(screen.getByText('主体范围未配置')).toBeInTheDocument();
    expect(screen.getByText(/PARTY_SCOPE_MISSING/)).toBeInTheDocument();
    expect(screen.getByText('组织链未配置代表主体')).toBeInTheDocument();
  });

  it('returns null for a valid Party scope', () => {
    const { container } = renderWithProviders(<PartyScopeBlocked scope={validScope} />);

    expect(container).toBeEmptyDOMElement();
  });
});
