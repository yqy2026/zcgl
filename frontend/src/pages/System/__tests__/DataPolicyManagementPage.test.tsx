import {
  createTestQueryClient,
  fireEvent,
  renderWithProviders,
  screen,
  waitFor,
} from '@/test/utils/test-helpers';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DataPolicyManagementPage from '../DataPolicyManagementPage';
import { dataPolicyService } from '@/services/dataPolicyService';
import type { RoleDataPoliciesResponse } from '@/types/dataPolicy';

const formatConsoleMessages = (calls: unknown[][]) =>
  calls
    .flat()
    .map(value => String(value))
    .join(' ');

vi.mock('@/services/dataPolicyService', () => ({
  dataPolicyService: {
    getDataPolicyTemplates: vi.fn(),
    getRoleDataPolicies: vi.fn(),
    updateRoleDataPolicies: vi.fn(),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('DataPolicyManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(dataPolicyService.getDataPolicyTemplates).mockResolvedValue([
      {
        code: 'dual_party_viewer',
        name: '双主体查看',
        description: '只读查看',
      },
    ]);

    vi.mocked(dataPolicyService.getRoleDataPolicies).mockResolvedValue({
      role_id: 'role-1',
      policy_packages: ['dual_party_viewer'],
    });

    vi.mocked(dataPolicyService.updateRoleDataPolicies).mockResolvedValue({
      role_id: 'role-1',
      policy_packages: ['dual_party_viewer'],
    });
  });

  it('refetches role policies when loading the same role id repeatedly', async () => {
    renderWithProviders(<DataPolicyManagementPage />);

    const roleInput = await screen.findByPlaceholderText('请输入角色 ID（role_id）');
    fireEvent.change(roleInput, { target: { value: 'role-1' } });

    const loadButton = screen.getByRole('button', { name: '加载当前策略' });
    fireEvent.click(loadButton);

    await waitFor(() => {
      expect(dataPolicyService.getRoleDataPolicies).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(loadButton);

    await waitFor(() => {
      expect(dataPolicyService.getRoleDataPolicies).toHaveBeenCalledTimes(2);
    });
  });

  it('keeps save disabled until current role policies are loaded successfully', async () => {
    vi.mocked(dataPolicyService.getRoleDataPolicies).mockImplementation(
      () =>
        new Promise<RoleDataPoliciesResponse>(() => {
          // Keep request pending to assert loading-state behavior.
        })
    );

    renderWithProviders(<DataPolicyManagementPage />);

    const saveButton = screen.getByRole('button', { name: '保存配置' });
    const roleInput = await screen.findByPlaceholderText('请输入角色 ID（role_id）');
    fireEvent.change(roleInput, { target: { value: 'role-1' } });

    fireEvent.click(screen.getByRole('button', { name: '加载当前策略' }));

    await waitFor(() => {
      expect(dataPolicyService.getRoleDataPolicies).toHaveBeenCalledWith('role-1');
    });

    expect(saveButton).toBeDisabled();
  });

  it('keeps save disabled after loading role policies fails', async () => {
    vi.mocked(dataPolicyService.getRoleDataPolicies).mockRejectedValueOnce(new Error('加载失败'));

    renderWithProviders(<DataPolicyManagementPage />);

    const saveButton = screen.getByRole('button', { name: '保存配置' });
    const roleInput = await screen.findByPlaceholderText('请输入角色 ID（role_id）');
    fireEvent.change(roleInput, { target: { value: 'role-1' } });

    fireEvent.click(screen.getByRole('button', { name: '加载当前策略' }));

    await screen.findByText('加载失败');
    expect(saveButton).toBeDisabled();
  });

  it('does not emit antd deprecation warnings while rendering load failures', async () => {
    vi.mocked(dataPolicyService.getRoleDataPolicies).mockRejectedValueOnce(new Error('加载失败'));
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      renderWithProviders(<DataPolicyManagementPage />);

      const roleInput = await screen.findByPlaceholderText('请输入角色 ID（role_id）');
      fireEvent.change(roleInput, { target: { value: 'role-1' } });

      fireEvent.click(screen.getByRole('button', { name: '加载当前策略' }));

      await screen.findByText('加载失败');

      const messages = formatConsoleMessages(consoleErrorSpy.mock.calls);
      expect(messages).not.toContain('[antd: Space]');
      expect(messages).not.toContain('[antd: Alert]');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });

  it('writes mutation cache using the response role id after role switch', async () => {
    const queryClient = createTestQueryClient();

    vi.mocked(dataPolicyService.getRoleDataPolicies).mockImplementation(async roleId => ({
      role_id: roleId,
      policy_packages: roleId === 'role-1' ? ['dual_party_viewer'] : ['audit_viewer'],
    }));

    let resolveUpdate:
      | ((value: RoleDataPoliciesResponse | PromiseLike<RoleDataPoliciesResponse>) => void)
      | null = null;
    const pendingUpdate = new Promise<RoleDataPoliciesResponse>(resolve => {
      resolveUpdate = resolve;
    });
    vi.mocked(dataPolicyService.updateRoleDataPolicies).mockImplementation(() => pendingUpdate);

    renderWithProviders(<DataPolicyManagementPage />, { queryClient });

    const roleInput = await screen.findByPlaceholderText('请输入角色 ID（role_id）');
    const loadButton = screen.getByRole('button', { name: '加载当前策略' });
    const saveButton = screen.getByRole('button', { name: '保存配置' });

    fireEvent.change(roleInput, { target: { value: 'role-1' } });
    fireEvent.click(loadButton);

    await waitFor(() => {
      expect(queryClient.getQueryData(['role-data-policies', 'role-1'])).toEqual({
        role_id: 'role-1',
        policy_packages: ['dual_party_viewer'],
      });
    });

    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(dataPolicyService.updateRoleDataPolicies).toHaveBeenCalledWith('role-1', {
        policy_packages: ['dual_party_viewer'],
      });
    });

    fireEvent.change(roleInput, { target: { value: 'role-2' } });
    fireEvent.click(loadButton);

    await waitFor(() => {
      expect(queryClient.getQueryData(['role-data-policies', 'role-2'])).toEqual({
        role_id: 'role-2',
        policy_packages: ['audit_viewer'],
      });
    });

    resolveUpdate?.({
      role_id: 'role-1',
      policy_packages: ['dual_party_viewer'],
    });

    await waitFor(() => {
      expect(queryClient.getQueryData(['role-data-policies', 'role-2'])).toEqual({
        role_id: 'role-2',
        policy_packages: ['audit_viewer'],
      });
    });
  });
});
