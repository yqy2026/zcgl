/**
 * ContractDetailPage 页面级测试
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ContractDetailPage from '../ContractDetailPage';
import { ContractStatus } from '@/types/rentContract';

// Mock rentContractService
vi.mock('@/services/rentContractService', () => ({
  rentContractService: {
    getContract: vi.fn(),
    getContractDepositLedger: vi.fn(),
    getServiceFeeLedgers: vi.fn(),
  },
}));

// Mock ContractDetailInfo component
vi.mock('@/components/Rental/ContractDetailInfo', () => ({
  default: ({ contract }: { contract: { tenant_name: string } }) => (
    <div data-testid="contract-detail-info">
      Contract Info: {contract.tenant_name}
    </div>
  ),
}));

// Mock ContractTerminateModal component
vi.mock('@/components/Rental/ContractTerminateModal', () => ({
  default: ({ visible }: { visible: boolean }) => (
    visible ? <div data-testid="terminate-modal">Terminate Modal</div> : null
  ),
}));

import { rentContractService } from '@/services/rentContractService';

// 创建测试用 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

// 渲染辅助函数
const renderWithProviders = (contractId: string) => {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/rental/contracts/${contractId}`]}>
        <Routes>
          <Route path="/rental/contracts/:id" element={<ContractDetailPage />} />
          <Route path="/rental/contracts" element={<div>Contract List</div>} />
          <Route path="/rental/contracts/:id/edit" element={<div>Edit Contract</div>} />
          <Route path="/rental/contracts/:id/renew" element={<div>Renew Contract</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('ContractDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(rentContractService.getContractDepositLedger).mockResolvedValue([]);
    vi.mocked(rentContractService.getServiceFeeLedgers).mockResolvedValue([]);
  });

  describe('加载状态', () => {
    it('显示加载中状态', async () => {
      vi.mocked(rentContractService.getContract).mockImplementation(
        () => new Promise(() => {})
      );

      renderWithProviders('contract_123');

      expect(screen.getByText('加载合同详情中...')).toBeInTheDocument();
    });
  });

  describe('成功加载', () => {
    it('显示合同详情', async () => {
      const mockContract = {
        id: 'contract_123',
        contract_number: 'HT-2026-001',
        tenant_name: '测试租户公司',
        contract_status: ContractStatus.ACTIVE,
      };

      vi.mocked(rentContractService.getContract).mockResolvedValue(mockContract);

      renderWithProviders('contract_123');

      await waitFor(() => {
        expect(screen.getByText('HT-2026-001 - 测试租户公司')).toBeInTheDocument();
      });

      expect(screen.getByTestId('contract-detail-info')).toBeInTheDocument();
      expect(screen.getByText('返回列表')).toBeInTheDocument();
      expect(screen.getByText('编辑合同')).toBeInTheDocument();
    });

    it('活跃合同显示续签和终止按钮', async () => {
      const mockContract = {
        id: 'contract_active',
        contract_number: 'HT-2026-002',
        tenant_name: '活跃租户',
        contract_status: ContractStatus.ACTIVE,
      };

      vi.mocked(rentContractService.getContract).mockResolvedValue(mockContract);

      renderWithProviders('contract_active');

      await waitFor(() => {
        expect(screen.getByText('续签合同')).toBeInTheDocument();
        expect(screen.getByText('终止合同')).toBeInTheDocument();
      });
    });

    it('非活跃合同不显示续签和终止按钮', async () => {
      const mockContract = {
        id: 'contract_expired',
        contract_number: 'HT-2025-001',
        tenant_name: '过期租户',
        contract_status: ContractStatus.EXPIRED,
      };

      vi.mocked(rentContractService.getContract).mockResolvedValue(mockContract);

      renderWithProviders('contract_expired');

      await waitFor(() => {
        expect(screen.getByText('HT-2025-001 - 过期租户')).toBeInTheDocument();
      });

      expect(screen.queryByText('续签合同')).not.toBeInTheDocument();
      expect(screen.queryByText('终止合同')).not.toBeInTheDocument();
    });
  });

  describe('错误处理', () => {
    it('显示错误信息', async () => {
      vi.mocked(rentContractService.getContract).mockRejectedValue(
        new Error('网络错误')
      );

      renderWithProviders('contract_error');

      await waitFor(() => {
        expect(screen.getByText('数据加载失败')).toBeInTheDocument();
        expect(screen.getByText(/网络错误/)).toBeInTheDocument();
      });
    });

    it('合同不存在时显示警告', async () => {
      vi.mocked(rentContractService.getContract).mockResolvedValue(null);

      renderWithProviders('contract_not_found');

      await waitFor(() => {
        expect(screen.getByText('合同不存在')).toBeInTheDocument();
        expect(screen.getByText('未找到指定的合同信息')).toBeInTheDocument();
      });
    });
  });

  describe('导航功能', () => {
    it('点击返回列表按钮导航到合同列表', async () => {
      const mockContract = {
        id: 'contract_nav',
        contract_number: 'HT-NAV',
        tenant_name: '导航测试',
        contract_status: ContractStatus.ACTIVE,
      };

      vi.mocked(rentContractService.getContract).mockResolvedValue(mockContract);

      renderWithProviders('contract_nav');

      await waitFor(() => {
        expect(screen.getByText('HT-NAV - 导航测试')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('返回列表'));

      await waitFor(() => {
        expect(screen.getByText('Contract List')).toBeInTheDocument();
      });
    });

    it('点击编辑合同按钮导航到编辑页', async () => {
      const mockContract = {
        id: 'contract_edit',
        contract_number: 'HT-EDIT',
        tenant_name: '编辑测试',
        contract_status: ContractStatus.ACTIVE,
      };

      vi.mocked(rentContractService.getContract).mockResolvedValue(mockContract);

      renderWithProviders('contract_edit');

      await waitFor(() => {
        expect(screen.getByText('HT-EDIT - 编辑测试')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('编辑合同'));

      await waitFor(() => {
        expect(screen.getByText('Edit Contract')).toBeInTheDocument();
      });
    });

    it('点击续签合同按钮导航到续签页', async () => {
      const mockContract = {
        id: 'contract_renew',
        contract_number: 'HT-RENEW',
        tenant_name: '续签测试',
        contract_status: ContractStatus.ACTIVE,
      };

      vi.mocked(rentContractService.getContract).mockResolvedValue(mockContract);

      renderWithProviders('contract_renew');

      await waitFor(() => {
        expect(screen.getByText('续签合同')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('续签合同'));

      await waitFor(() => {
        expect(screen.getByText('Renew Contract')).toBeInTheDocument();
      });
    });
  });

  describe('终止合同模态框', () => {
    it('点击终止合同按钮显示模态框', async () => {
      const mockContract = {
        id: 'contract_terminate',
        contract_number: 'HT-TERM',
        tenant_name: '终止测试',
        contract_status: ContractStatus.ACTIVE,
      };

      vi.mocked(rentContractService.getContract).mockResolvedValue(mockContract);

      renderWithProviders('contract_terminate');

      await waitFor(() => {
        expect(screen.getByText('终止合同')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('终止合同'));

      await waitFor(() => {
        expect(screen.getByTestId('terminate-modal')).toBeInTheDocument();
      });
    });
  });
});
