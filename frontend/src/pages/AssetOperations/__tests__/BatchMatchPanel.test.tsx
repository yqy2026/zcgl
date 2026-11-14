import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import BatchMatchPanel from '../BatchMatchPanel';
import { archiveDocumentService } from '@/services/archiveDocumentService';

vi.mock('@/services/archiveDocumentService', () => ({
  archiveDocumentService: {
    previewBatchMatch: vi.fn(),
    commitBatchMatch: vi.fn(),
  },
}));
vi.mock('@/components/System/CapabilityGuard', () => ({
  default: ({ children }: { children: React.ReactNode }) => children,
}));

function show() {
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })
      }
    >
      <BatchMatchPanel />
    </QueryClientProvider>
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const preview = {
  preview_token: 'token-1',
  expires_at: '2026-11-04T12:30:00Z',
  items: [
    {
      staging_id: 's1',
      file_name: '【五羊司合字[2024]214号】合同.png',
      file_size: 4,
      detected: {
        target_type: 'upstream_contract',
        target_id: 'u1',
        label: '五羊司合字[2024]214号 北京路物业',
      },
      ambiguous: [],
      already_archived: false,
    },
    {
      staging_id: 's2',
      file_name: '无编号扫描件.png',
      file_size: 4,
      detected: null,
      ambiguous: [],
      already_archived: false,
    },
  ],
};

it('previews filename matches and submits only selected targets', async () => {
  const user = userEvent.setup();
  vi.mocked(archiveDocumentService.previewBatchMatch).mockResolvedValue(preview);
  vi.mocked(archiveDocumentService.commitBatchMatch).mockResolvedValue({ items: [] });
  show();
  await user.upload(screen.getByLabelText('选择多份扫描件'), [
    new File(['a'], '【五羊司合字[2024]214号】合同.png'),
    new File(['b'], '无编号扫描件.png'),
  ]);
  expect(await screen.findByText('【五羊司合字[2024]214号】合同.png')).toBeVisible();
  expect(screen.getByText('识别：五羊司合字[2024]214号 北京路物业')).toBeVisible();
  expect(screen.getByText('未识别到合同编号')).toBeVisible();
  const submit = screen.getByRole('button', { name: /提交配对/ });
  expect(submit).toHaveTextContent('1 / 2');
  await user.click(submit);
  await waitFor(() =>
    expect(archiveDocumentService.commitBatchMatch).toHaveBeenCalledWith('token-1', [
      { staging_id: 's1', target_type: 'upstream_contract', target_id: 'u1' },
    ])
  );
  expect(await screen.findByText('已按所选目标归档，档案完成情况已更新。')).toBeVisible();
});

it('keeps the commit button disabled until a target is chosen', async () => {
  const ambiguous = {
    ...preview,
    items: [
      {
        staging_id: 's3',
        file_name: '重复编号.png',
        file_size: 4,
        detected: null,
        ambiguous: [
          {
            target_type: 'upstream_contract',
            target_id: 'u1',
            label: '候选一',
          },
          {
            target_type: 'terminal_contract',
            target_id: 't1',
            label: '候选二',
          },
        ],
        already_archived: false,
      },
    ],
  };
  const user = userEvent.setup();
  vi.mocked(archiveDocumentService.previewBatchMatch).mockResolvedValue(ambiguous);
  show();
  await user.upload(screen.getByLabelText('选择多份扫描件'), [new File(['a'], '重复编号.png')]);
  expect(await screen.findByText('编号命中多份合同，请选择')).toBeVisible();
  expect(screen.getByRole('button', { name: /提交配对/ })).toBeDisabled();
});

it('surfaces an expired preview without retrying', async () => {
  const user = userEvent.setup();
  vi.mocked(archiveDocumentService.previewBatchMatch).mockRejectedValue(
    new (await import('@/services/assetOperationsService')).AssetOperationsError(
      '预览已过期',
      'BATCH_PREVIEW_EXPIRED'
    )
  );
  show();
  await user.upload(screen.getByLabelText('选择多份扫描件'), [new File(['a'], '任意.png')]);
  expect(await screen.findByText('预览已过期（30 分钟），请重新选择文件。')).toBeVisible();
  expect(archiveDocumentService.previewBatchMatch).toHaveBeenCalledTimes(1);
});

it('keeps commit error codes actionable instead of the generic fallback', async () => {
  const user = userEvent.setup();
  const { AssetOperationsError } = await import('@/services/assetOperationsService');
  vi.mocked(archiveDocumentService.previewBatchMatch).mockResolvedValue(preview);
  vi.mocked(archiveDocumentService.commitBatchMatch).mockRejectedValue(
    new AssetOperationsError('失败', 'ARCHIVE_TARGET_ALREADY_HAS_FILE')
  );
  show();
  await user.upload(screen.getByLabelText('选择多份扫描件'), [
    new File(['a'], '【五羊司合字[2024]214号】合同.png'),
  ]);
  await screen.findByText('识别：五羊司合字[2024]214号 北京路物业');
  await user.click(screen.getByRole('button', { name: /提交配对/ }));
  expect(
    await screen.findByText('所选合同已有档案，请到合同详情改用替换，或重新选择目标。')
  ).toBeVisible();
});

it('keeps remaining files pairable after a partial commit', async () => {
  const user = userEvent.setup();
  vi.mocked(archiveDocumentService.previewBatchMatch).mockResolvedValue(preview);
  vi.mocked(archiveDocumentService.commitBatchMatch).mockResolvedValue({ items: [] });
  show();
  await user.upload(screen.getByLabelText('选择多份扫描件'), [
    new File(['a'], '【五羊司合字[2024]214号】合同.png'),
    new File(['b'], '无编号扫描件.png'),
  ]);
  expect(await screen.findByText('识别：五羊司合字[2024]214号 北京路物业')).toBeVisible();
  await user.click(screen.getByRole('button', { name: /提交配对/ }));
  expect(await screen.findByText('已按所选目标归档，档案完成情况已更新。')).toBeVisible();
  // The unmatched file survives for a later decision; the matched one is gone.
  expect(screen.getByText('无编号扫描件.png')).toBeVisible();
  expect(screen.queryByText('【五羊司合字[2024]214号】合同.png')).toBeNull();
});
