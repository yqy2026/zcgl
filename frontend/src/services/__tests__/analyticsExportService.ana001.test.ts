import { describe, it, expect, vi, beforeEach } from 'vitest';
import { analyticsExportService } from '../analyticsExportService';
import type { AnalyticsExportData } from '../analyticsExportService';

// Mock xlsx
vi.mock('xlsx', () => ({
  utils: {
    book_new: vi.fn(() => ({ Sheets: {}, SheetNames: [] })),
    aoa_to_sheet: vi.fn(() => ({})),
    book_append_sheet: vi.fn((wb, _sheet, name) => {
      wb.Sheets[name] = {};
      wb.SheetNames.push(name);
    }),
  },
  writeFile: vi.fn(),
}));

const makeExportData = (overrides?: Partial<AnalyticsExportData['summary']>): AnalyticsExportData => ({
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
    metrics_version: 'req-ana-001-v1',
    ...overrides,
  },
  property_nature_distribution: [],
  ownership_status_distribution: [],
  usage_status_distribution: [],
  business_category_distribution: [],
});

describe('analyticsExportService ANA-001 fields', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('exportToExcel', () => {
    it('should include ANA-001 fields in summary sheet data', async () => {
      const XLSX = await import('xlsx');
      const data = makeExportData();

      await analyticsExportService.exportToExcel(data);

      // aoa_to_sheet is called for each sheet; first call is summary
      const aoaCalls = vi.mocked(XLSX.utils.aoa_to_sheet).mock.calls;
      const summaryRows = aoaCalls[0][0] as unknown[][];

      // Find ANA-001 rows
      const rowLabels = summaryRows.map(r => r[0]);
      expect(rowLabels).toContain('总收入（经营口径）');
      expect(rowLabels).toContain('自营租金收入');
      expect(rowLabels).toContain('代理服务费收入');
      expect(rowLabels).toContain('客户主体数');
      expect(rowLabels).toContain('客户合同数');
      expect(rowLabels).toContain('口径版本');
    });

    it('should export metrics_version value', async () => {
      const XLSX = await import('xlsx');
      const data = makeExportData();

      await analyticsExportService.exportToExcel(data);

      const aoaCalls = vi.mocked(XLSX.utils.aoa_to_sheet).mock.calls;
      const summaryRows = aoaCalls[0][0] as unknown[][];

      const versionRow = summaryRows.find(r => r[0] === '口径版本');
      expect(versionRow?.[1]).toBe('req-ana-001-v1');
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
      expect(blobContent).toContain('req-ana-001-v1');

      globalThis.Blob = OrigBlob;
      createElementSpy.mockRestore();
      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
    });
  });

  describe('edge: fields default to zero when absent', () => {
    it('should handle undefined ANA-001 fields gracefully', async () => {
      const XLSX = await import('xlsx');
      const data = makeExportData({
        total_income: undefined as unknown as number,
        self_operated_rent_income: undefined as unknown as number,
        agency_service_income: undefined as unknown as number,
        customer_entity_count: undefined as unknown as number,
        customer_contract_count: undefined as unknown as number,
        metrics_version: undefined as unknown as string,
      });

      // Should not throw
      await expect(analyticsExportService.exportToExcel(data)).resolves.not.toThrow();

      const aoaCalls = vi.mocked(XLSX.utils.aoa_to_sheet).mock.calls;
      const summaryRows = aoaCalls[0][0] as unknown[][];
      const incomeRow = summaryRows.find(r => r[0] === '总收入（经营口径）');
      expect(incomeRow?.[1]).toBe('0.00');
    });
  });
});
