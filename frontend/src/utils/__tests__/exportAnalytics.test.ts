import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { exportAnalytics } from '../exportAnalytics';

const formatStderrWrites = (calls: unknown[][]) => calls.map(call => String(call[0] ?? '')).join(' ');

const mockData = {
  area_summary: {
    total_assets: 12,
    total_area: 1234.56,
    total_rentable_area: 987.65,
    occupancy_rate: 88.8,
  },
  financial_summary: {
    estimated_annual_income: 1200000.5,
    total_monthly_rent: 100000.25,
    total_deposit: 300000.75,
  },
  property_nature_distribution: [{ name: '商业', count: 6, percentage: 50 }],
  ownership_status_distribution: [{ status: '已确权', count: 8, percentage: 66.67 }],
  usage_status_distribution: [{ status: '在用', count: 9, percentage: 75 }],
  occupancy_distribution: [{ range: '80-100%', count: 7, percentage: 58.33 }],
  business_category_distribution: [{ category: '零售', occupancy_rate: 90.12, count: 4 }],
  occupancy_trend: [
    {
      date: '2026-02-01',
      occupancy_rate: 87.12,
      total_rented_area: 860.4,
      total_rentable_area: 987.65,
    },
  ],
};

describe('exportAnalytics', () => {
  const realCreateObjectURL = URL.createObjectURL;
  const realRevokeObjectURL = URL.revokeObjectURL;
  const realCreateElement = document.createElement.bind(document);

  const readBlobText = async (blob: Blob): Promise<string> => {
    if (typeof (blob as Blob & { text?: () => Promise<string> }).text === 'function') {
      return (blob as Blob & { text: () => Promise<string> }).text();
    }

    return new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result ?? ''));
      reader.onerror = () => reject(reader.error ?? new Error('Failed to read blob text'));
      reader.readAsText(blob);
    });
  };

  const stubDownloadLinkClick = () => {
    const clickSpy = vi.fn();
    vi.spyOn(document, 'createElement').mockImplementation(((tagName: string) => {
      const element = realCreateElement(tagName);

      if (tagName.toLowerCase() === 'a') {
        (element as HTMLAnchorElement).click = clickSpy;
      }

      return element;
    }) as typeof document.createElement);

    return clickSpy;
  };

  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    URL.createObjectURL = realCreateObjectURL;
    URL.revokeObjectURL = realRevokeObjectURL;
  });

  it('exports CSV for excel format with BOM and expected sections', async () => {
    const appendSpy = vi.spyOn(document.body, 'appendChild');
    const removeSpy = vi.spyOn(document.body, 'removeChild');
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);
    const clickSpy = stubDownloadLinkClick();

    try {
      await exportAnalytics(mockData, 'excel');

      const createUrlMock = vi.mocked(URL.createObjectURL);
      expect(createUrlMock).toHaveBeenCalledTimes(1);
      const blob = createUrlMock.mock.calls[0]?.[0] as Blob;
      const text = await readBlobText(blob);

      expect(text).toContain('资产分析报告');
      expect(text).toContain('面积概览');
      expect(text).toContain('财务概览');
      expect(text).toContain('物业性质分布');
      expect(text).toContain('出租率趋势');

      const link = appendSpy.mock.calls[0]?.[0] as HTMLAnchorElement;
      expect(link.tagName).toBe('A');
      expect(link.getAttribute('href')).toBe('blob:mock-url');
      expect(link.getAttribute('download')).toMatch(/^analytics_\d+\.csv$/);

      expect(clickSpy).toHaveBeenCalledTimes(1);
      expect(removeSpy).toHaveBeenCalledWith(link);
      expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain(
        'navigation to another Document'
      );
    } finally {
      stderrWriteSpy.mockRestore();
    }
  });

  it('exports CSV for csv format', async () => {
    const appendSpy = vi.spyOn(document.body, 'appendChild');
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);
    const clickSpy = stubDownloadLinkClick();

    try {
      await exportAnalytics(mockData, 'csv');

      const link = appendSpy.mock.calls[0]?.[0] as HTMLAnchorElement;
      expect(link.getAttribute('download')).toMatch(/^analytics_\d+\.csv$/);
      expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
      expect(clickSpy).toHaveBeenCalledTimes(1);
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain(
        'navigation to another Document'
      );
    } finally {
      stderrWriteSpy.mockRestore();
    }
  });

  it('exports text fallback and warns for pdf format', async () => {
    const appendSpy = vi.spyOn(document.body, 'appendChild');
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);
    const clickSpy = stubDownloadLinkClick();

    try {
      await exportAnalytics(mockData, 'pdf');

      const link = appendSpy.mock.calls[0]?.[0] as HTMLAnchorElement;
      expect(link.getAttribute('download')).toMatch(/^analytics_\d+\.txt$/);

      const blob = vi.mocked(URL.createObjectURL).mock.calls[0]?.[0] as Blob;
      const text = await readBlobText(blob);
      expect(text).toContain('资产分析报告');
      expect(text).toContain('财务概览');

      expect(warnSpy).toHaveBeenCalledWith(
        'PDF export requires external library (jsPDF). Exported as text file instead.'
      );
      expect(infoSpy).toHaveBeenCalledWith('To enable PDF export, install jsPDF: pnpm add jspdf');
      expect(clickSpy).toHaveBeenCalledTimes(1);
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain(
        'navigation to another Document'
      );
    } finally {
      stderrWriteSpy.mockRestore();
    }
  });
});
