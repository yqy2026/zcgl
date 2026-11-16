import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';

import ImportPage from '../ImportPage';
import { importService, ImportError } from '@/services/importService';

vi.mock('@/services/importService', async importOriginal => {
  const actual = await importOriginal<typeof import('@/services/importService')>();
  return {
    ...actual,
    importService: {
      downloadCreateTemplate: vi.fn(),
      stageScanFiles: vi.fn(),
      uploadBatch: vi.fn(),
      getBatch: vi.fn(),
      listChanges: vi.fn(),
      updateSelection: vi.fn(),
      commitPreview: vi.fn(),
      commit: vi.fn(),
      revertPreview: vi.fn(),
      revert: vi.fn(),
    },
  };
});

const mocked = vi.mocked(importService);

function renderPage(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ImportPage />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  for (const key of Object.keys(mocked) as Array<keyof typeof mocked>) {
    const value = mocked[key];
    if (typeof value === 'function' && 'mockReset' in value) {
      (value as unknown as ReturnType<typeof vi.fn>).mockReset();
    }
  }
});

afterEach(() => {
  cleanup();
});

describe('ImportPage', () => {
  it('renders the staged workflow steps and mode switch', async () => {
    renderPage();
    expect(screen.getByText('第一步 暂存已签扫描件')).toBeTruthy();
    expect(screen.getByText('第二步 上传工作簿')).toBeTruthy();
    expect(screen.getByText('新增导入')).toBeTruthy();

    await userEvent.click(screen.getByText('更新导入'));
    expect(screen.getByRole('button', { name: /更新导入/ })).toBeTruthy();
  });

  it('shows batch status and blocks commit while errors exist', async () => {
    mocked.uploadBatch.mockResolvedValue({
      id: 'b1',
      mode: 'create',
      status: 'invalid',
      template_version: '2026-11-15',
      row_count: 4,
      valid_count: 3,
      error_count: 1,
      warning_count: 0,
      proposal_hash: null,
      version: 1,
      committed_at: null,
      reverted_at: null,
    });
    mocked.listChanges.mockResolvedValue({
      items: [
        {
          id: 'c1',
          sheet_name: '物业单元',
          row_number: 3,
          target_type: 'asset_unit',
          target_key: 'U-1',
          field_name: 'PARTY_NAME_NOT_FOUND_ERROR',
          old_value: null,
          new_value: null,
          selected: true,
          severity: 'error',
          effect_summary: '主体全称未匹配到已审核启用主体（不自动创建）',
        },
      ],
      total: 1,
    });

    renderPage();
    const fileInput = document.querySelector(
      'input[type="file"][accept=".xlsx"]'
    ) as HTMLInputElement | null;
    expect(fileInput).not.toBeNull();
    const file = new File(['stub'], 'import.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    await userEvent.upload(fileInput as HTMLInputElement, file);

    await waitFor(() => {
      expect(screen.getByText('校验未通过')).toBeTruthy();
    });
    await waitFor(() => {
      expect(screen.getByText(/主体全称未匹配到已审核启用主体/)).toBeTruthy();
    });
    expect(screen.queryByRole('button', { name: /预览并整批提交/ })).toBeNull();
    expect(screen.getByText('存在错误行，修正工作簿后重新上传')).toBeTruthy();
  });

  it('surfaces business error text from ImportError codes', async () => {
    mocked.uploadBatch.mockRejectedValue(
      new ImportError(
        '批次上传失败: 工作簿无法解析：表头、工作表或模板版本不符',
        'IMPORT_FILE_INVALID'
      )
    );
    renderPage();
    const fileInput = document.querySelector(
      'input[type="file"][accept=".xlsx"]'
    ) as HTMLInputElement | null;
    const file = new File(['stub'], 'bad.xlsx');
    await userEvent.upload(fileInput as HTMLInputElement, file);
    await waitFor(() => {
      expect(screen.getByText(/表头、工作表或模板版本不符/)).toBeTruthy();
    });
  });

  it('exposes stable blocker descriptions for the revert preview', async () => {
    const { describeBlocker } = await import('../ImportPage');
    expect(describeBlocker('rent_payment')).toContain('租金实收');
    expect(describeBlocker('unknown_kind')).toContain('unknown_kind');
  });
});
