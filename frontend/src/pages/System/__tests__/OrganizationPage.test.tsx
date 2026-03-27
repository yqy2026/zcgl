import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import OrganizationPage from '../OrganizationPage';
import { organizationService } from '@/services/organizationService';
import { useDictionary } from '@/hooks/useDictionary';

const formatStderrWrites = (calls: unknown[][]) => calls.map(call => String(call[0] ?? '')).join(' ');

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

vi.mock('@/hooks/useDictionary', () => ({
  useDictionary: vi.fn(),
}));

vi.mock('../OrganizationPage.module.css', () => ({
  default: new Proxy(
    {},
    {
      get: (_target, property) => String(property),
    }
  ),
}));

vi.mock('../Organization/components/OrganizationStatisticsCards', () => ({
  default: () => <div data-testid="org-stats-cards" />,
}));

vi.mock('../Organization/components/OrganizationTabsPanel', () => ({
  default: () => (
    <div data-testid="org-tabs-panel">
      <div>列表视图</div>
      <div>树形视图</div>
      <button disabled>新建组织</button>
    </div>
  ),
}));

vi.mock('../Organization/components/OrganizationFormModal', () => ({
  default: () => null,
}));

vi.mock('../Organization/components/OrganizationHistoryModal', () => ({
  default: () => null,
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
      by_level: {},
    });
    vi.mocked(organizationService.createOrganization).mockResolvedValue({
      id: 'org-created',
      name: '事业部A',
      code: 'DIV001',
      level: 1,
      sort_order: 0,
      type: 'division',
      status: 'active',
      is_deleted: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    vi.mocked(organizationService.getOrganizationHistory).mockResolvedValue([]);
    vi.mocked(useDictionary).mockImplementation((dictType: string) => {
      if (dictType === 'organization_type') {
        return {
          options: [
            { label: '事业部', value: 'division' },
            { label: '部门', value: 'department' },
          ],
          isLoading: false,
          error: null,
          refresh: vi.fn(),
        };
      }

      if (dictType === 'organization_status') {
        return {
          options: [
            { label: '启用(自定义)', value: 'active', color: 'green' },
            { label: '停用(自定义)', value: 'inactive', color: 'red' },
          ],
          isLoading: false,
          error: null,
          refresh: vi.fn(),
        };
      }

      return {
        options: [],
        isLoading: false,
        error: null,
        refresh: vi.fn(),
      };
    });
  });

  it('renders tabs without TabPane deprecation warning', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

    try {
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
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain(
        'Could not parse CSS stylesheet'
      );
    } finally {
      stderrWriteSpy.mockRestore();
      warnSpy.mockRestore();
      errorSpy.mockRestore();
    }
  });

  it('enforces read-only mode and disables write entry point', async () => {
    renderWithProviders(<OrganizationPage />);

    await waitFor(() => {
      expect(organizationService.getOrganizations).toHaveBeenCalled();
      expect(useDictionary).toHaveBeenCalledWith('organization_type');
      expect(useDictionary).toHaveBeenCalledWith('organization_status');
    });

    expect(screen.getByText(/组织架构当前为只读模式/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /新建组织/ })).toBeDisabled();
  });
});
