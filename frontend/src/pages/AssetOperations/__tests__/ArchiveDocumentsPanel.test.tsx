import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import ArchiveDocumentsPanel from '../ArchiveDocumentsPanel';
import { archiveDocumentService } from '@/services/archiveDocumentService';
vi.mock('@/services/archiveDocumentService', () => ({
  archiveDocumentService: { list: vi.fn(), upload: vi.fn(), replace: vi.fn(), download: vi.fn() },
}));
vi.mock('@/components/System/CapabilityGuard', () => ({
  default: ({ children }: { children: React.ReactNode }) => children,
}));
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(archiveDocumentService.list).mockResolvedValue([]);
});
it('reads withdrawn supplement history without upload controls', async () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ArchiveDocumentsPanel targetId="supp" targetType="contract_supplement" readOnly />
    </QueryClientProvider>
  );
  await screen.findByText('此协议暂无已归档文件。');
  expect(archiveDocumentService.list).toHaveBeenCalledWith('supp', 'contract_supplement');
  expect(screen.queryByLabelText('选择归档文件')).toBeNull();
});
it('refreshes warm matrix and completion after a supplement upload', async () => {
  const completion = vi.fn().mockResolvedValue({}),
    matrix = vi.fn().mockResolvedValue({});
  function WarmQueries() {
    useQuery({ queryKey: ['archive-completion'], queryFn: completion });
    useQuery({ queryKey: ['archive-matrix'], queryFn: matrix });
    return null;
  }
  vi.mocked(archiveDocumentService.upload).mockResolvedValue({ id: 'doc' } as Awaited<
    ReturnType<typeof archiveDocumentService.upload>
  >);
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { staleTime: 300000, refetchOnMount: false },
            mutations: { retry: 1 },
          },
        })
      }
    >
      <WarmQueries />
      <ArchiveDocumentsPanel targetId="supp" targetType="contract_supplement" />
    </QueryClientProvider>
  );
  await screen.findByText('此协议暂无已归档文件。');
  await userEvent.upload(
    screen.getByLabelText('选择归档文件'),
    new File(['scan'], '协议.pdf', { type: 'application/pdf' })
  );
  await userEvent.click(screen.getByRole('button', { name: '上传档案' }));
  await screen.findByText('档案已保存。');
  expect(archiveDocumentService.upload).toHaveBeenCalledWith(
    'supp',
    expect.any(File),
    'contract_supplement'
  );
  await waitFor(() => {
    expect(completion).toHaveBeenCalledTimes(2);
    expect(matrix).toHaveBeenCalledTimes(2);
  });
});

it('refreshes handover eligibility after a reversal conflict without retrying', async () => {
  const { AssetOperationsError } = await import('@/services/assetOperationsService');
  const targets = vi.fn().mockResolvedValue([]);
  function WarmTargets() {
    useQuery({ queryKey: ['handover-targets', 'upstream', 'parent'], queryFn: targets });
    return null;
  }
  vi.mocked(archiveDocumentService.upload).mockRejectedValue(
    new AssetOperationsError('撤销', 'HANDOVER_EVENT_REVERSED')
  );
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { staleTime: 300000 }, mutations: { retry: 1 } },
        })
      }
    >
      <WarmTargets />
      <ArchiveDocumentsPanel targetId="event" targetType="contract_lifecycle_event" />
    </QueryClientProvider>
  );
  await screen.findByText('此次交接暂无已归档文件。');
  await userEvent.upload(
    screen.getByLabelText('选择归档文件'),
    new File(['scan'], '交接.pdf', { type: 'application/pdf' })
  );
  await userEvent.click(screen.getByRole('button', { name: '上传档案' }));
  await screen.findByText('此交接事件已撤销，仅可查看和下载历史档案。');
  await waitFor(() => expect(targets).toHaveBeenCalledTimes(2));
  expect(archiveDocumentService.upload).toHaveBeenCalledTimes(1);
});

it('shows the contract scan empty state for contract targets', async () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ArchiveDocumentsPanel targetId="c1" targetType="upstream_contract" />
    </QueryClientProvider>
  );
  await screen.findByText('此合同暂无已归档扫描件。');
  expect(archiveDocumentService.list).toHaveBeenCalledWith('c1', 'upstream_contract');
});
it('shows the fee stamp empty state without upload controls', async () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ArchiveDocumentsPanel targetId="st1" targetType="management_fee_statement" readOnly />
    </QueryClientProvider>
  );
  await screen.findByText('此对账单暂无盖章件。');
  expect(archiveDocumentService.list).toHaveBeenCalledWith('st1', 'management_fee_statement');
  expect(screen.queryByLabelText('选择归档文件')).toBeNull();
});
