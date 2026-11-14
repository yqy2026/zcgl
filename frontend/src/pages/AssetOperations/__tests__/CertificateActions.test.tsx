import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CertificateLink, CertificateControls } from '../CertificateActions';
import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import { archiveDocumentService } from '@/services/archiveDocumentService';
import type { AssetUnitCertificate } from '@/services/assetOperationsService';
import type { ReactNode } from 'react';

const permissions = vi.hoisted(() => ({ write: true, archive: true }));
vi.mock('@/components/System/CapabilityGuard', () => ({
  default: ({ children, action }: { children: ReactNode; action: 'write' | 'archive' }) =>
    permissions[action] ? children : null,
}));
vi.mock('@/services/assetOperationsService', async original => ({
  ...(await original<typeof import('@/services/assetOperationsService')>()),
  assetOperationsService: {
    listCertificateOptions: vi.fn(),
    linkCertificate: vi.fn(),
    unlinkCertificate: vi.fn(),
  },
}));
vi.mock('@/services/archiveDocumentService', () => ({
  archiveDocumentService: { list: vi.fn(), download: vi.fn(), upload: vi.fn(), replace: vi.fn() },
}));
const certificate: AssetUnitCertificate = {
  id: 'cert',
  certificate_number: '证照甲',
  certificate_type: 'real_estate',
  property_address: '地址甲',
  registration_date: null,
  building_area: null,
  land_area: null,
  land_use_term_start: null,
  land_use_term_end: null,
};
function show(element: ReactNode): void {
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false, refetchOnMount: false, staleTime: 300000 },
            mutations: { retry: 1, retryDelay: 0 },
          },
        })
      }
    >
      {element}
    </QueryClientProvider>
  );
}
beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  permissions.write = true;
  permissions.archive = true;
  vi.mocked(assetOperationsService.listCertificateOptions).mockResolvedValue({
    items: [certificate],
    total: 1,
  });
  vi.mocked(assetOperationsService.linkCertificate).mockResolvedValue();
  vi.mocked(assetOperationsService.unlinkCertificate).mockResolvedValue();
});

it('refreshes a warm archive cache when the drawer is reopened', async () => {
  vi.mocked(archiveDocumentService.list).mockResolvedValue([]);
  show(<CertificateControls unitId="unit" certificate={certificate} />);
  await userEvent.click(screen.getByRole('button', { name: '查看档案' }));
  await screen.findByText('此证照暂无已归档文件。');
  await userEvent.click(screen.getByRole('button', { name: /close/i }));
  await waitFor(() => expect(screen.queryByLabelText('选择归档文件')).toBeNull());
  await userEvent.click(screen.getByRole('button', { name: '查看档案' }));
  await waitFor(() => expect(archiveDocumentService.list).toHaveBeenCalledTimes(2));
});

it('does not retry failed uploads even when global mutation retries are enabled', async () => {
  vi.mocked(archiveDocumentService.list).mockResolvedValue([]);
  vi.mocked(archiveDocumentService.upload).mockRejectedValue(
    new AssetOperationsError('失败', 'ARCHIVE_DUPLICATE_CONTENT')
  );
  show(<CertificateControls unitId="unit" certificate={certificate} />);
  await userEvent.click(screen.getByRole('button', { name: '查看档案' }));
  await userEvent.upload(
    await screen.findByLabelText('选择归档文件'),
    new File(['scan'], '证照.pdf', { type: 'application/pdf' })
  );
  await userEvent.click(screen.getByRole('button', { name: '上传档案' }));
  await screen.findByText('此文件已归档，请选择内容不同的文件。');
  expect(archiveDocumentService.upload).toHaveBeenCalledTimes(1);
  await userEvent.click(screen.getByRole('button', { name: '重新加载档案' }));
  await waitFor(() => expect(archiveDocumentService.list).toHaveBeenCalledTimes(2));
});

it('reloads versions after a stale replacement without replaying the upload', async () => {
  const item = {
    id: 'old',
    attachment_id: 'file',
    document_type: 'property_certificate',
    target_type: 'property_certificate',
    target_id: 'cert',
    file_name: '原.pdf',
    content_type: 'application/pdf',
    file_size: 10,
    document_version: 1,
    replaces_document_id: null,
    uploaded_at: '2026-11-01T10:00:00',
    is_current: true,
  };
  vi.mocked(archiveDocumentService.list)
    .mockResolvedValueOnce([item])
    .mockResolvedValue([{ ...item, is_current: false }]);
  vi.mocked(archiveDocumentService.replace).mockRejectedValue(
    new AssetOperationsError('过期', 'ARCHIVE_VERSION_STALE')
  );
  show(<CertificateControls unitId="unit" certificate={certificate} />);
  await userEvent.click(screen.getByRole('button', { name: '查看档案' }));
  await userEvent.upload(
    await screen.findByLabelText('选择替换文件'),
    new File(['next'], '新.pdf', { type: 'application/pdf' })
  );
  await userEvent.click(screen.getByRole('button', { name: '保存替换版本' }));
  await screen.findByText('历史版本');
  expect(screen.queryByLabelText('选择替换文件')).toBeNull();
  expect(archiveDocumentService.replace).toHaveBeenCalledTimes(1);
});

it('does not grant archive uploads with write permission alone', async () => {
  permissions.archive = false;
  vi.mocked(archiveDocumentService.list).mockResolvedValue([]);
  show(<CertificateControls unitId="unit" certificate={certificate} />);
  await userEvent.click(screen.getByRole('button', { name: '查看档案' }));
  await screen.findByText('此证照暂无已归档文件。');
  expect(screen.queryByLabelText('选择归档文件')).toBeNull();
});

it('uploads a selected file and refreshes the document list', async () => {
  vi.mocked(archiveDocumentService.list).mockResolvedValue([]);
  vi.mocked(archiveDocumentService.upload).mockResolvedValue({ id: 'new' } as Awaited<
    ReturnType<typeof archiveDocumentService.upload>
  >);
  show(<CertificateControls unitId="unit" certificate={certificate} />);
  await userEvent.click(screen.getByRole('button', { name: '查看档案' }));
  const file = new File(['scan'], '证照.pdf', { type: 'application/pdf' });
  await userEvent.upload(await screen.findByLabelText('选择归档文件'), file);
  await userEvent.click(screen.getByRole('button', { name: '上传档案' }));
  expect(await screen.findByText('档案已保存。')).toBeTruthy();
  expect(archiveDocumentService.upload).toHaveBeenCalledWith('cert', file);
  expect(archiveDocumentService.list).toHaveBeenCalledTimes(2);
});
it('does not show maintenance controls to a read-only user', () => {
  permissions.write = false;
  show(<CertificateLink unitId="unit" />);
  expect(screen.queryByRole('button', { name: '关联产权证' })).toBeNull();
});
it('selects a real candidate and saves the chosen effective date', async () => {
  vi.mocked(assetOperationsService.listCertificateOptions).mockResolvedValue({
    items: [certificate, { ...certificate, id: 'second', certificate_number: '证照乙' }],
    total: 2,
  });
  show(<CertificateLink unitId="unit" />);
  await userEvent.click(screen.getByRole('button', { name: '关联产权证' }));
  const picker = await screen.findByRole('combobox', { name: '选择产权证', exact: true });
  if (!(picker instanceof HTMLSelectElement))
    throw new Error('Expected native certificate selector');
  expect(picker.labels?.[0]?.textContent?.trim()).toBe('选择产权证');
  expect(screen.getByLabelText('选择产权证', { exact: true })).toBe(picker);
  await userEvent.selectOptions(picker, 'cert');
  await userEvent.click(screen.getByRole('button', { name: '保存关联' }));
  expect(await screen.findByText(/已保存关联，自/)).toBeTruthy();
  expect(assetOperationsService.linkCertificate).toHaveBeenCalledWith(
    'unit',
    expect.objectContaining({ certificate_id: 'cert' })
  );
});
it('confirms an unlink arrangement without calling it deletion', async () => {
  show(<CertificateControls unitId="unit" certificate={certificate} />);
  await userEvent.click(screen.getByRole('button', { name: '解除关联' }));
  expect(assetOperationsService.unlinkCertificate).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button', { name: '确认解除关联' }));
  expect(await screen.findByText(/已保存解除安排，自/)).toBeTruthy();
});

it('removes an open unlink form when write permission is lost', async () => {
  const client = new QueryClient();
  const view = render(
    <QueryClientProvider client={client}>
      <CertificateControls unitId="unit" certificate={certificate} />
    </QueryClientProvider>
  );
  await userEvent.click(screen.getByRole('button', { name: '解除关联' }));
  expect(screen.getByLabelText('解除生效日')).toBeTruthy();
  permissions.write = false;
  view.rerender(
    <QueryClientProvider client={client}>
      <CertificateControls unitId="unit" certificate={certificate} />
    </QueryClientProvider>
  );
  expect(screen.queryByLabelText('解除生效日')).toBeNull();
});
it('shows historical versions and a download failure without success', async () => {
  vi.mocked(archiveDocumentService.list).mockResolvedValue([
    {
      id: 'doc',
      attachment_id: 'file',
      document_type: 'property_certificate',
      target_type: 'property_certificate',
      target_id: 'cert',
      file_name: '历史.pdf',
      content_type: 'application/pdf',
      file_size: 10,
      document_version: 1,
      replaces_document_id: null,
      uploaded_at: '2026-11-01T10:00:00',
      is_current: false,
    },
  ]);
  vi.mocked(archiveDocumentService.download).mockRejectedValue(new Error('denied'));
  show(<CertificateControls unitId="unit" certificate={certificate} />);
  await userEvent.click(screen.getByRole('button', { name: '查看档案' }));
  expect(await screen.findByText('历史版本')).toBeTruthy();
  expect(screen.queryByLabelText('选择替换文件')).toBeNull();
  await userEvent.click(screen.getByRole('button', { name: '下载 历史.pdf' }));
  expect(await screen.findByText('操作失败，请重新加载后重试。')).toBeTruthy();
});
