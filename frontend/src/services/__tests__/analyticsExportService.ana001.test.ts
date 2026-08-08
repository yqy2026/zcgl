import { describe, it, expect, vi, beforeEach } from 'vitest';
import ExcelJS from 'exceljs';
import { analyticsExportService } from '../analyticsExportService';
import type { AnalyticsExportData } from '../analyticsExportService';

const makeExportData = (
  overrides?: Partial<AnalyticsExportData['summary']>
): AnalyticsExportData => ({
  summary: {
    total_assets: 10,
    total_area: 5000,
    total_rentable_area: 4000,
    occupancy_rate: 80,
    total_annual_income: 200000,
    total_annual_expense: 50000,
    total_net_income: 150000,
    total_monthly_rent: 16000,
    total_income: 180000,
    self_operated_rent_income: 120000,
    agency_service_income: 60000,
    customer_entity_count: 15,
    customer_contract_count: 22,
    metrics_version: 'req-ana-001-v2',
    period_attribution_label: '按租金账期归属，流水发生日期仅用于查询、导出和审计',
    ...overrides,
  },
  property_nature_distribution: [],
  ownership_status_distribution: [],
  usage_status_distribution: [],
  business_category_distribution: [],
});

// 拦截导出下载，捕获写出的 .xlsx 字节，供重新加载断言
const captureExcelDownload = () => {
  const mockLink = {
    setAttribute: vi.fn(),
    click: vi.fn(),
    style: {} as CSSStyleDeclaration,
  } as unknown as HTMLAnchorElement;
  const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink);
  const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(n => n);
  const removeChildSpy = vi.spyOn(document.body, 'removeChild').mockImplementation(n => n);
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock');

  let capturedParts: BlobPart[] | null = null;
  const OrigBlob = globalThis.Blob;
  globalThis.Blob = class MockBlob extends OrigBlob {
    constructor(parts?: BlobPart[], options?: BlobPropertyBag) {
      super(parts, options);
      capturedParts = parts ?? null;
    }
  } as typeof Blob;

  return {
    loadWorkbook: async (): Promise<ExcelJS.Workbook> => {
      const workbook = new ExcelJS.Workbook();
      await workbook.xlsx.load((capturedParts ?? [])[0] as ArrayBuffer);
      return workbook;
    },
    restore: () => {
      globalThis.Blob = OrigBlob;
      createElementSpy.mockRestore();
      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
    },
  };
};

const findLabeledRow = (sheet: ExcelJS.Worksheet, label: string): ExcelJS.Row | undefined => {
  let matched: ExcelJS.Row | undefined;
  sheet.eachRow(row => {
    if (row.getCell(1).value === label) {
      matched = row;
    }
  });
  return matched;
};

describe('analyticsExportService ANA-001 fields', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('exportToExcel', () => {
    it('should include ANA-001 fields in summary sheet data', async () => {
      const data = makeExportData();
      const capture = captureExcelDownload();

      try {
        await analyticsExportService.exportToExcel(data);

        const workbook = await capture.loadWorkbook();
        const summary = workbook.getWorksheet('概览统计');
        expect(summary).toBeDefined();

        const labels: (string | number)[] = [];
        summary!.eachRow(row => {
          const value = row.getCell(1).value;
          if (value != null && typeof value !== 'object') {
            labels.push(value as string | number);
          }
        });
        expect(labels).toContain('总收入（经营口径）');
        expect(labels).toContain('自营租金收入');
        expect(labels).toContain('代理服务费收入');
        expect(labels).toContain('客户主体数');
        expect(labels).toContain('客户合同数');
        expect(labels).toContain('口径版本');
        expect(labels).toContain('账期归属口径');
      } finally {
        capture.restore();
      }
    });

    it('should export metrics_version value', async () => {
      const data = makeExportData();
      const capture = captureExcelDownload();

      try {
        await analyticsExportService.exportToExcel(data);

        const workbook = await capture.loadWorkbook();
        const summary = workbook.getWorksheet('概览统计');

        const versionRow = findLabeledRow(summary!, '口径版本');
        const attributionRow = findLabeledRow(summary!, '账期归属口径');
        expect(versionRow?.getCell(2).value).toBe('req-ana-001-v2');
        expect(attributionRow?.getCell(2).value).toBe(
          '按租金账期归属，流水发生日期仅用于查询、导出和审计'
        );
      } finally {
        capture.restore();
      }
    });
  });

  describe('exportToCSV', () => {
    it('should include ANA-001 section in CSV output', async () => {
      // Mock DOM APIs for download
      const mockLink = {
        setAttribute: vi.fn(),
        click: vi.fn(),
        style: {} as CSSStyleDeclaration,
      } as unknown as HTMLAnchorElement;
      const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink);
      const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(n => n);
      const removeChildSpy = vi.spyOn(document.body, 'removeChild').mockImplementation(n => n);
      vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock');

      let blobContent = '';
      const OrigBlob = globalThis.Blob;
      globalThis.Blob = class MockBlob extends OrigBlob {
        constructor(parts?: BlobPart[], options?: BlobPropertyBag) {
          super(parts, options);
          blobContent = (parts ?? []).map(p => (typeof p === 'string' ? p : '')).join('');
        }
      } as typeof Blob;

      const data = makeExportData();
      await analyticsExportService.exportToCSV(data);

      expect(blobContent).toContain('经营口径指标');
      expect(blobContent).toContain('总收入（经营口径）');
      expect(blobContent).toContain('自营租金收入');
      expect(blobContent).toContain('代理服务费收入');
      expect(blobContent).toContain('客户主体数');
      expect(blobContent).toContain('客户合同数');
      expect(blobContent).toContain('口径版本');
      expect(blobContent).toContain('req-ana-001-v2');
      expect(blobContent).toContain('账期归属口径');
      expect(blobContent).toContain('流水发生日期');

      globalThis.Blob = OrigBlob;
      createElementSpy.mockRestore();
      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
    });
  });

  describe('edge: fields default to zero when absent', () => {
    it('should handle undefined ANA-001 fields gracefully', async () => {
      const data = makeExportData({
        total_income: undefined as unknown as number,
        self_operated_rent_income: undefined as unknown as number,
        agency_service_income: undefined as unknown as number,
        customer_entity_count: undefined as unknown as number,
        customer_contract_count: undefined as unknown as number,
        metrics_version: undefined as unknown as string,
        period_attribution_label: undefined,
      });
      const capture = captureExcelDownload();

      try {
        // Should not throw
        await expect(analyticsExportService.exportToExcel(data)).resolves.not.toThrow();

        const workbook = await capture.loadWorkbook();
        const summary = workbook.getWorksheet('概览统计');

        const incomeRow = findLabeledRow(summary!, '总收入（经营口径）');
        expect(incomeRow?.getCell(2).value).toBe('0.00');
      } finally {
        capture.restore();
      }
    });
  });
});
