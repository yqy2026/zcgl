import { expect, test, type APIResponse, type Page } from '@playwright/test';
import * as XLSX from 'xlsx';
import {
  ensureAuthenticated,
  loginWithCredentialRetry,
  resolveAdminCredentialCandidates,
  resolveCsrfHeaders,
} from '../helpers/auth';

const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const PDF_MIME = 'application/pdf';
const MINIMAL_PDF_BUFFER = Buffer.from(
  [
    '%PDF-1.4',
    '1 0 obj',
    '<< /Type /Catalog /Pages 2 0 R >>',
    'endobj',
    '2 0 obj',
    '<< /Type /Pages /Count 0 >>',
    'endobj',
    'trailer',
    '<< /Root 1 0 R >>',
    '%%EOF',
  ].join('\n')
);

const assertApiSuccess = async (response: APIResponse, action: string): Promise<void> => {
  if (response.ok()) {
    return;
  }

  const snippet = await response.text().catch(() => '');
  throw new Error(`${action} failed: status=${response.status()} body=${snippet.slice(0, 300)}`);
};

const createOwnershipForImport = async (page: Page): Promise<string> => {
  const csrfHeaders = await resolveCsrfHeaders(page);
  const suffix = Date.now();

  const response = await page.request.post('/api/v1/ownerships', {
    headers: csrfHeaders,
    data: {
      name: `E2E导入权属方-${suffix}`,
      short_name: `E2E-${suffix}`,
    },
  });
  await assertApiSuccess(response, 'create ownership');

  const payload = (await response.json()) as { id?: string };
  if (payload.id == null || payload.id === '') {
    throw new Error('create ownership returned empty id');
  }
  return payload.id;
};

const ensureAuthenticatedStable = async (page: Page): Promise<void> => {
  try {
    await ensureAuthenticated(page);
    return;
  } catch {
    const candidates = resolveAdminCredentialCandidates();
    for (const credential of candidates) {
      const success = await loginWithCredentialRetry(page, credential, 3);
      if (success) {
        return;
      }
    }
  }

  throw new Error('failed to authenticate in import-success spec');
};

const buildExcelBuffer = (ownershipId: string, contractNumber: string): Buffer => {
  const workbook = XLSX.utils.book_new();

  const contractRows = [
    {
      合同编号: contractNumber,
      权属方ID: ownershipId,
      承租方名称: `E2E租户-${contractNumber}`,
      签订日期: '2026-01-01',
      租期开始日期: '2026-01-01',
      租期结束日期: '2026-12-31',
      基础月租金: 1000,
      合同类型: '下游租赁',
      付款周期: '月付',
      合同状态: '执行中',
    },
  ];

  const termRows = [
    {
      合同编号: contractNumber,
      条款开始日期: '2026-01-01',
      条款结束日期: '2026-12-31',
      月租金: 1000,
    },
  ];

  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(contractRows), 'contracts');
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(termRows), 'terms');

  return XLSX.write(workbook, { bookType: 'xlsx', type: 'buffer' }) as Buffer;
};

test.describe('@rental-import-success 导入成功路径', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticatedStable(page);
  });

  test('excel import should return structured outcome for minimal workbook', async ({ page }) => {
    await page.goto('/rental/contracts');
    await expect(page).toHaveURL(/\/rental\/contracts/);

    const ownershipId = await createOwnershipForImport(page);
    const contractNumber = `E2E-EXCEL-${Date.now()}`;
    const workbookBuffer = buildExcelBuffer(ownershipId, contractNumber);

    await page.getByRole('button', { name: '导入Excel' }).first().click();
    const importModal = page.getByRole('dialog', { name: /导入Excel文件/i });
    await expect(importModal).toBeVisible();

    const uploadInput = importModal.locator('input[type="file"]').first();
    const importResponsePromise = page.waitForResponse(response => {
      return (
        response.request().method() === 'POST' &&
        response.url().includes('/api/v1/rental-contracts/excel/import')
      );
    });

    await uploadInput.setInputFiles({
      name: `rent_contract_${contractNumber}.xlsx`,
      mimeType: XLSX_MIME,
      buffer: workbookBuffer,
    });

    const importResponse = await importResponsePromise;
    expect(importResponse.status()).toBe(200);
    const importPayload = (await importResponse.json()) as {
      success?: boolean;
      imported_contracts?: number;
      errors?: unknown[];
      warnings?: unknown[];
    };
    expect(typeof importPayload.success).toBe('boolean');
    expect(typeof importPayload.imported_contracts).toBe('number');
    expect(Array.isArray(importPayload.errors)).toBe(true);
    expect(Array.isArray(importPayload.warnings)).toBe(true);
    if (importPayload.success === true) {
      expect(importPayload.imported_contracts ?? 0).toBeGreaterThanOrEqual(1);
    } else {
      expect((importPayload.errors ?? []).length).toBeGreaterThan(0);
    }

    await expect(importModal.getByRole('button', { name: /选择Excel文件/i }).first()).toBeVisible({
      timeout: 30_000,
    });
  });

  test('pdf import should accept minimal valid pdf file', async ({ page }) => {
    await page.goto('/rental/contracts/pdf-import');
    await expect(page).toHaveURL(/\/rental\/contracts\/pdf-import/);
    await expect(page.getByRole('heading', { name: /PDF合同智能导入/i })).toBeVisible();

    const uploadResponsePromise = page.waitForResponse(response => {
      return (
        response.request().method() === 'POST' && response.url().includes('/api/v1/pdf-import/upload')
      );
    });

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `contract-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const uploadResponse = await uploadResponsePromise;
    expect(uploadResponse.status()).toBe(200);
    const uploadPayload = (await uploadResponse.json()) as {
      success?: boolean;
      session_id?: string;
    };
    expect(uploadPayload.success).toBe(true);
    expect(uploadPayload.session_id != null && uploadPayload.session_id !== '').toBe(true);
  });
});
