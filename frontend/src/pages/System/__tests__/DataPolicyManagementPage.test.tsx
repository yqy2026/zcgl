import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DataPolicyManagementPage from '../DataPolicyManagementPage';
import { dataPolicyService } from '@/services/dataPolicyService';

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
});
