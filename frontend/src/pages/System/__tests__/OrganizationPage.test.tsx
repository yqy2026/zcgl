import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import OrganizationPage from '../OrganizationPage';
import { organizationService } from '@/services/organizationService';

vi.mock('@/services/organizationService', () => ({
  organizationService: {
    getOrganizations: vi.fn(),
    searchOrganizations: vi.fn(),
    getOrganizationTree: vi.fn(),
    getStatistics: vi.fn(),
    createOrganization: vi.fn(),
    updateOrganization: vi.fn(),
    deleteOrganization: vi.fn(),
    getOrganizationHistory: vi.fn(),
  },
}));

vi.mock('@/components/Common/TableWithPagination', () => ({
  TableWithPagination: ({ dataSource = [] }: { dataSource?: Array<Record<string, unknown>> }) => (
    <div data-testid="table-with-pagination">{dataSource.length}</div>
  ),
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

describe('OrganizationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(organizationService.getOrganizations).mockResolvedValue([]);
    vi.mocked(organizationService.searchOrganizations).mockResolvedValue([]);
    vi.mocked(organizationService.getOrganizationTree).mockResolvedValue([]);
    vi.mocked(organizationService.getStatistics).mockResolvedValue({
      total: 0,
      active: 0,
      inactive: 0,
      by_type: {},
    });
    vi.mocked(organizationService.getOrganizationHistory).mockResolvedValue([]);
  });

  it('renders tabs without TabPane deprecation warning', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    renderWithProviders(<OrganizationPage />);

    await waitFor(() => {
      expect(organizationService.getOrganizations).toHaveBeenCalled();
    });

    expect(screen.getByText('列表视图')).toBeInTheDocument();
    expect(screen.getByText('树形视图')).toBeInTheDocument();

    const warnOutput = warnSpy.mock.calls.flat().join(' ');
    const errorOutput = errorSpy.mock.calls.flat().join(' ');

    expect(warnOutput).not.toContain('Tabs.TabPane');
    expect(errorOutput).not.toContain('Tabs.TabPane');

    warnSpy.mockRestore();
    errorSpy.mockRestore();
  });
});
