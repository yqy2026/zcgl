import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useContractList } from '../useContractList';
import { rentContractService } from '@/services/rentContractService';
import { assetService } from '@/services/assetService';
import { ownershipService } from '@/services/ownershipService';
import { Modal } from 'antd';

// Mock dependencies
vi.mock('@/services/rentContractService', () => ({
  rentContractService: {
    getContracts: vi.fn(),
    getRentStatistics: vi.fn(),
    deleteContract: vi.fn(),
    terminateContract: vi.fn(),
    generateMonthlyLedger: vi.fn(),
  },
}));

vi.mock('@/services/assetService', () => ({
  assetService: {
    getAssets: vi.fn(),
  },
}));

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    getOwnershipOptions: vi.fn(),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock Antd Modal
vi.mock('antd', () => ({
  Modal: {
    confirm: vi.fn(),
  },
}));

describe('useContractList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useContractList());

    expect(result.current.state.loading).toBe(false);
    expect(result.current.state.pagination.current).toBe(1);
    expect(result.current.assets).toEqual([]);
    expect(result.current.ownerships).toEqual([]);
  });

  it('should load data on mount', async () => {
    // Setup mocks
    const mockContracts = { items: [{ id: '1' }], total: 1, pages: 1 };
    const mockStats = { total_records: 1 };
    const mockAssets = { items: [{ id: 'a1' }] };
    const mockOwnerships = [{ id: 'o1' }];

    vi.mocked(rentContractService.getContracts).mockResolvedValue(mockContracts);
    vi.mocked(rentContractService.getRentStatistics).mockResolvedValue(mockStats);
    vi.mocked(assetService.getAssets).mockResolvedValue(mockAssets);
    vi.mocked(ownershipService.getOwnershipOptions).mockResolvedValue(mockOwnerships);

    const { result } = renderHook(() => useContractList());

    // Wait for effects
    await waitFor(() => {
      expect(rentContractService.getContracts).toHaveBeenCalled();
    });

    expect(result.current.state.contracts).toEqual(mockContracts.items);
    expect(result.current.assets).toEqual(mockAssets.items);
    expect(result.current.ownerships).toEqual(mockOwnerships);
    expect(result.current.statistics).toEqual(mockStats);
  });

  it('should handle search', async () => {
    const { result } = renderHook(() => useContractList());

    act(() => {
      result.current.handleSearch({ keyword: 'test' });
    });

    expect(result.current.state.filters).toEqual({ keyword: 'test' });
    expect(result.current.state.pagination.current).toBe(1);

    await waitFor(() => {
      expect(rentContractService.getContracts).toHaveBeenCalledWith(
        expect.objectContaining({ keyword: 'test', page: 1 })
      );
    });
  });

  it('should handle pagination change', async () => {
    const { result } = renderHook(() => useContractList());

    act(() => {
      result.current.handleTableChange({ current: 2, pageSize: 20 });
    });

    await waitFor(() => {
      expect(rentContractService.getContracts).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2, pageSize: 20 })
      );
    });
  });

  it('should handle delete confirmation', async () => {
    const { result } = renderHook(() => useContractList());

    // Setup Modal.confirm mock to trigger onOk immediately
    vi.mocked(Modal.confirm).mockImplementation(({ onOk }: { onOk?: () => void }) => {
      onOk?.();
    });
    vi.mocked(rentContractService.deleteContract).mockResolvedValue({});

    await act(async () => {
      await result.current.handleDelete('123');
    });

    expect(Modal.confirm).toHaveBeenCalled();
    expect(rentContractService.deleteContract).toHaveBeenCalledWith('123');
    // Should reload data after delete
    expect(rentContractService.getContracts).toHaveBeenCalledTimes(2); // Initial load + reload
  });
});
