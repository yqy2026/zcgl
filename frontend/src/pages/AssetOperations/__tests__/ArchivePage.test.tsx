import { expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ArchivePage, { categoryValue } from '@/pages/AssetOperations/ArchivePage';

vi.mock('@/components/System/CapabilityGuard', () => ({
  default: ({ children }: { children: React.ReactNode }) => children,
}));
import { archiveMatrixService } from '@/services/archiveMatrixService';
import { AssetOperationsError } from '@/services/assetOperationsService';
vi.mock('@/services/archiveMatrixService', () => ({
  archiveMatrixService: { completion: vi.fn(), matrix: vi.fn() },
}));
const category = {
  document_type: 'property_certificate',
  label: '产权证',
  supported: true,
  required: 0,
  existing: 0,
  missing: 0,
  completion_rate: null,
};
beforeEach(() => {
  vi.clearAllMocks();
});
function show() {
  render(
    <MemoryRouter>
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <ArchivePage />
      </QueryClientProvider>
    </MemoryRouter>
  );
}
it('does not turn zero denominators or unsupported registries into completion', () => {
  expect(categoryValue(category)).toBe('不适用');
  expect(categoryValue({ ...category, supported: false, required: null, existing: null })).toBe(
    '登记清单待接入'
  );
});
it('shows shared-object summary and explicit unlinked properties with empty matrix', async () => {
  vi.mocked(archiveMatrixService.completion).mockResolvedValue({
    as_of: '2026-11-03',
    categories: [category],
    unlinked_unit_count: 3,
  });
  vi.mocked(archiveMatrixService.matrix).mockResolvedValue({
    as_of: '2026-11-03',
    items: [],
    total: 0,
  });
  show();
  expect(await screen.findByText(/尚未关联产权证的物业：3/)).toBeTruthy();
  expect(screen.getByText('当前范围没有符合条件的在管物业。')).toBeTruthy();
  expect(screen.queryByText('100.0%')).toBeNull();
});
it('shows scope recovery instead of cached counts when a request is forbidden', async () => {
  vi.mocked(archiveMatrixService.completion).mockRejectedValue(
    new AssetOperationsError('拒绝', 'PARTY_SCOPE_MISSING')
  );
  vi.mocked(archiveMatrixService.matrix).mockResolvedValue({
    as_of: '2026-11-03',
    items: [],
    total: 0,
  });
  show();
  expect(await screen.findByText('访问范围或权限已变化，请联系管理员后重新加载。')).toBeTruthy();
  expect(screen.queryByText('档案完成情况')).toBeNull();
});

it('restores project, search and pagination from the shared URL', async () => {
  vi.mocked(archiveMatrixService.completion).mockResolvedValue({
    as_of: '2026-11-03',
    categories: [category],
    unlinked_unit_count: 0,
  });
  vi.mocked(archiveMatrixService.matrix).mockResolvedValue({
    as_of: '2026-11-03',
    items: [],
    total: 60,
  });
  render(
    <MemoryRouter initialEntries={['/asset-operations/archive?project_id=p1&q=园区&page=2']}>
      <QueryClientProvider client={new QueryClient()}>
        <ArchivePage />
      </QueryClientProvider>
    </MemoryRouter>
  );
  await screen.findByText('档案完成情况');
  expect(archiveMatrixService.matrix).toHaveBeenCalledWith({
    project_id: 'p1',
    q: '园区',
    offset: 20,
    limit: 20,
  });
});

it('restores a historical as_of from the URL and offers returning to today', async () => {
  vi.mocked(archiveMatrixService.completion).mockResolvedValue({
    as_of: '2026-09-15',
    categories: [category],
    unlinked_unit_count: 0,
  });
  vi.mocked(archiveMatrixService.matrix).mockResolvedValue({
    as_of: '2026-09-15',
    items: [],
    total: 0,
  });
  const user = (await import('@testing-library/user-event')).default.setup();
  render(
    <MemoryRouter initialEntries={['/asset-operations/archive?as_of=2026-09-15']}>
      <QueryClientProvider client={new QueryClient()}>
        <ArchivePage />
      </QueryClientProvider>
    </MemoryRouter>
  );
  await screen.findByText('档案完成情况');
  expect(archiveMatrixService.completion).toHaveBeenCalledWith({
    as_of: '2026-09-15',
  });
  expect(screen.getByText('截至 2026-09-15（历史时点）（北京时间）')).toBeTruthy();
  const input = screen.getByLabelText('统计日期') as HTMLInputElement;
  expect(input.value).toBe('2026-09-15');
  await user.click(screen.getByRole('button', { name: '回到今天' }));
  await waitFor(() => expect(archiveMatrixService.completion).toHaveBeenLastCalledWith({}));
});
