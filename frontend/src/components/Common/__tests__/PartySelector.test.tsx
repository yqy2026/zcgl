import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  fireEvent,
  renderWithProviders,
  screen,
  userEvent,
  waitFor,
} from '@/test/utils/test-helpers';
import { partyService } from '@/services/partyService';
import type { Party, PartyType } from '@/types/party';
import PartySelector, { createDefaultPartyFetcher } from '../PartySelector';

vi.mock('@/services/partyService', () => ({
  partyService: {
    searchParties: vi.fn(),
    createParty: vi.fn(),
  },
}));

describe('PartySelector', () => {
  const buildParties = (prefix: string, count: number, partyType: PartyType): Party[] => {
    return Array.from({ length: count }, (_, index) => {
      const suffix = `${index + 1}`;
      return {
        id: `${prefix}-${suffix}`,
        party_type: partyType,
        name: `${prefix.toUpperCase()}-${suffix}`,
        code: `${prefix.toUpperCase()}-CODE-${suffix}`,
        status: 'active',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      };
    });
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(partyService.searchParties).mockResolvedValue({
      items: [
        {
          id: 'party-1',
          party_type: 'organization',
          name: '测试主体A',
          code: 'PTY-A',
          status: 'active',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      skip: 0,
      limit: 20,
      isTruncated: false,
    });
    vi.mocked(partyService.createParty).mockResolvedValue({
      id: 'party-created',
      party_type: 'organization',
      name: '新建主体',
      code: 'NEW-001',
      status: 'active',
      review_status: 'draft',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });
  });

  it('uses default fetcher and returns party_id + party_name on select', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    renderWithProviders(<PartySelector onChange={handleChange} />);

    await waitFor(() => {
      expect(partyService.searchParties).toHaveBeenCalledWith('', { limit: 20 });
    });

    const selector = screen.getByRole('combobox');
    fireEvent.mouseDown(selector);
    await user.click(await screen.findByText('测试主体A [PTY-A]'));

    expect(handleChange).toHaveBeenCalledWith(
      'party-1',
      expect.objectContaining({
        party_id: 'party-1',
        party_name: '测试主体A',
      })
    );
  });

  it('shows empty-state message when no party data is available', async () => {
    vi.mocked(partyService.searchParties).mockResolvedValue({
      items: [],
      skip: 0,
      limit: 20,
      isTruncated: false,
    });

    renderWithProviders(<PartySelector />);

    expect(await screen.findByRole('status')).toHaveTextContent('请先创建主体数据');
  });

  it('shows 403 message when party.read is denied', async () => {
    vi.mocked(partyService.searchParties).mockRejectedValue(new Error('403 PERMISSION_DENIED'));

    renderWithProviders(<PartySelector />);

    expect(await screen.findByRole('status')).toHaveTextContent(
      '当前账号无 party.read 权限，请联系管理员'
    );
  });

  it('supports custom fetcher and filter mode', async () => {
    const fetcher = vi.fn().mockResolvedValue([]);

    renderWithProviders(<PartySelector filterMode="tenant" fetcher={fetcher} />);

    await waitFor(() => {
      expect(fetcher).toHaveBeenCalledWith('', 'tenant');
    });
  });

  it('defaults to owner-scoped search when route perspective is owner', async () => {
    vi.mocked(partyService.searchParties)
      .mockResolvedValueOnce({ items: [], skip: 0, limit: 20, isTruncated: false })
      .mockResolvedValueOnce({ items: [], skip: 0, limit: 20, isTruncated: false });

    renderWithProviders(<PartySelector />, { route: '/owner/assets' });

    await waitFor(() => {
      expect(partyService.searchParties).toHaveBeenCalledWith('', {
        limit: 20,
        party_type: 'organization',
      });
      expect(partyService.searchParties).toHaveBeenCalledWith('', {
        limit: 20,
        party_type: 'legal_entity',
      });
    });
  });

  it('defaults to manager-scoped search when route perspective is manager', async () => {
    vi.mocked(partyService.searchParties)
      .mockResolvedValueOnce({ items: [], skip: 0, limit: 20, isTruncated: false })
      .mockResolvedValueOnce({ items: [], skip: 0, limit: 20, isTruncated: false });

    renderWithProviders(<PartySelector />, { route: '/manager/assets' });

    await waitFor(() => {
      expect(partyService.searchParties).toHaveBeenCalledWith('', {
        limit: 20,
        party_type: 'organization',
      });
      expect(partyService.searchParties).toHaveBeenCalledWith('', {
        limit: 20,
        party_type: 'legal_entity',
      });
    });
  });

  it('defaults to unscoped search on non-perspective routes', async () => {
    renderWithProviders(<PartySelector />, { route: '/dashboard' });

    await waitFor(() => {
      expect(partyService.searchParties).toHaveBeenCalledWith('', { limit: 20 });
    });
  });

  it('keeps explicit filterMode over route-derived default', async () => {
    renderWithProviders(<PartySelector filterMode="tenant" />, { route: '/owner/assets' });

    await waitFor(() => {
      expect(partyService.searchParties).toHaveBeenCalledWith('', { limit: 20 });
    });
  });

  it('applies owner filter mode in default fetcher with role-aligned party_type queries', async () => {
    vi.mocked(partyService.searchParties)
      .mockResolvedValueOnce({
        items: [
          {
            id: 'party-org-1',
            party_type: 'organization',
            name: '组织主体',
            code: 'ORG-1',
            status: 'active',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
          },
        ],
        skip: 0,
        limit: 20,
        isTruncated: false,
      })
      .mockResolvedValueOnce({
        items: [
          {
            id: 'party-legal-1',
            party_type: 'legal_entity',
            name: '法人主体',
            code: 'LEGAL-1',
            status: 'active',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
          },
        ],
        skip: 0,
        limit: 20,
        isTruncated: false,
      });

    renderWithProviders(<PartySelector filterMode="owner" />);

    await waitFor(() => {
      expect(partyService.searchParties).toHaveBeenCalledWith('', {
        limit: 20,
        party_type: 'organization',
      });
      expect(partyService.searchParties).toHaveBeenCalledWith('', {
        limit: 20,
        party_type: 'legal_entity',
      });
    });
  });

  it('applies manager filter mode in default fetcher with role-aligned party_type queries', async () => {
    const searchParties = vi
      .fn()
      .mockResolvedValueOnce({ items: [], skip: 0, limit: 20, isTruncated: false })
      .mockResolvedValueOnce({ items: [], skip: 0, limit: 20, isTruncated: false });
    const fetcher = createDefaultPartyFetcher(searchParties);

    await fetcher('', 'manager');

    expect(searchParties).toHaveBeenCalledWith('', {
      limit: 20,
      party_type: 'organization',
    });
    expect(searchParties).toHaveBeenCalledWith('', {
      limit: 20,
      party_type: 'legal_entity',
    });
  });

  it('caps merged owner/manager results to default limit to avoid oversized dropdown payload', async () => {
    const searchParties = vi
      .fn()
      .mockResolvedValueOnce({
        items: buildParties('org', 20, 'organization'),
        skip: 0,
        limit: 20,
        isTruncated: false,
      })
      .mockResolvedValueOnce({
        items: buildParties('legal', 20, 'legal_entity'),
        skip: 0,
        limit: 20,
        isTruncated: false,
      });
    const fetcher = createDefaultPartyFetcher(searchParties);

    const parties = await fetcher('', 'owner');

    expect(parties).toHaveLength(20);
    expect(parties.every(item => item.party_type === 'organization')).toBe(true);
  });

  it('recognizes forbidden status by structured error object without PERMISSION_DENIED text', async () => {
    vi.mocked(partyService.searchParties).mockRejectedValue({
      statusCode: 403,
      code: 'HTTP_403',
      message: '访问被拒绝',
    });

    renderWithProviders(<PartySelector />);

    expect(await screen.findByRole('status')).toHaveTextContent(
      '当前账号无 party.read 权限，请联系管理员'
    );
  });

  it('recognizes forbidden status from axios-like response.status object', async () => {
    vi.mocked(partyService.searchParties).mockRejectedValue({
      response: {
        status: 403,
        data: {
          message: '没有权限',
        },
      },
    });

    renderWithProviders(<PartySelector />);

    expect(await screen.findByRole('status')).toHaveTextContent(
      '当前账号无 party.read 权限，请联系管理员'
    );
  });

  it('supports quick-create and selects the created party', async () => {
    vi.mocked(partyService.searchParties).mockResolvedValue({
      items: [],
      skip: 0,
      limit: 20,
      isTruncated: false,
    });
    const handleChange = vi.fn();
    const user = userEvent.setup();

    renderWithProviders(<PartySelector allowQuickCreate onChange={handleChange} />);

    expect(await screen.findByRole('button', { name: '快速新建主体' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '快速新建主体' }));
    await user.type(screen.getByLabelText('快速新建主体名称'), '新建主体');
    await user.type(screen.getByLabelText('快速新建主体编码'), 'NEW-001');
    await user.click(screen.getByRole('button', { name: '创建主体' }));

    await waitFor(() => {
      expect(partyService.createParty).toHaveBeenCalledWith(
        expect.objectContaining({
          name: '新建主体',
          code: 'NEW-001',
        })
      );
    });

    expect(handleChange).toHaveBeenCalledWith(
      'party-created',
      expect.objectContaining({
        party_id: 'party-created',
        party_name: '新建主体',
      })
    );
  });
});
