import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import {
  renderWithProviders,
  screen,
  waitFor,
  userEvent,
  fireEvent,
} from '@/test/utils/test-helpers';
import OrganizationPage from '../OrganizationPage';
import { organizationService } from '@/services/organizationService';
import { useDictionary } from '@/hooks/useDictionary';

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

  it('loads enum options from dictionaries and submits enum values', async () => {
    const user = userEvent.setup();

    renderWithProviders(<OrganizationPage />);

    await waitFor(() => {
      expect(organizationService.getOrganizations).toHaveBeenCalled();
      expect(useDictionary).toHaveBeenCalledWith('organization_type');
      expect(useDictionary).toHaveBeenCalledWith('organization_status');
    });

    await user.click(screen.getByRole('button', { name: /新建组织/ }));

    await user.type(screen.getByPlaceholderText('请输入组织名称'), '事业部A');
    await user.type(screen.getByPlaceholderText('请输入组织编码'), 'DIV001');

    const typeLabel = screen
      .getAllByText('组织类型')
      .find(element => element.tagName.toLowerCase() === 'label');
    const typeSelect = typeLabel?.closest('.ant-form-item')?.querySelector('.ant-select');
    expect(typeSelect).toBeTruthy();
    fireEvent.mouseDown(typeSelect!);
    await user.click(screen.getByText('事业部'));

    const statusLabel = screen
      .getAllByText('状态')
      .find(element => element.tagName.toLowerCase() === 'label');
    const statusSelect = statusLabel?.closest('.ant-form-item')?.querySelector('.ant-select');
    expect(statusSelect).toBeTruthy();
    fireEvent.mouseDown(statusSelect!);
    await user.click(screen.getByText('启用(自定义)'));

    const formElement = document.querySelector('.ant-modal form');
    expect(formElement).toBeTruthy();
    fireEvent.submit(formElement!);

    await waitFor(() => {
      expect(organizationService.createOrganization).toHaveBeenCalledWith(
        expect.objectContaining({
          name: '事业部A',
          code: 'DIV001',
          type: 'division',
          status: 'active',
        })
      );
    });
  }, 30000);
});
