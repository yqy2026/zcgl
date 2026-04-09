import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import OrganizationBindingDrawer from '../OrganizationBindingDrawer';
import { userService } from '@/services/systemService';

vi.mock('@/services/systemService', () => ({
  userService: {
    getUsers: vi.fn(),
  },
}));

vi.mock('@/pages/System/UserManagement/components/UserPartyBindingModal', () => ({
  default: ({ open, user }: { open: boolean; user: { full_name: string } | null }) =>
    open ? <div data-testid="user-party-binding-modal">{user?.full_name}</div> : null,
}));

describe('OrganizationBindingDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(userService.getUsers).mockResolvedValue({
      items: [
        {
          id: 'user-1',
          username: 'alice',
          email: 'alice@example.com',
          full_name: 'Alice',
          phone: '13800138000',
          status: 'active',
          roles: ['executive'],
          role_ids: ['role-1'],
          organization_name: '事业部A',
          last_login: null,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
          is_locked: false,
          login_attempts: 0,
        },
      ],
      total: 1,
      page: 1,
      page_size: 200,
      pages: 1,
    });
  });

  it('loads organization users and opens the binding modal from the organization context', async () => {
    renderWithProviders(
      <OrganizationBindingDrawer
        open
        organization={{
          id: 'org-1',
          name: '事业部A',
          code: 'DIV001',
          level: 1,
          sort_order: 0,
          type: 'division',
          status: 'active',
          is_deleted: false,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        }}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(userService.getUsers).toHaveBeenCalledWith({
        default_organization_id: 'org-1',
        page_size: 200,
      });
    });

    expect(await screen.findByText('Alice')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /管理 Alice 主体绑定/i }));

    expect(await screen.findByTestId('user-party-binding-modal')).toHaveTextContent('Alice');
  });
});
