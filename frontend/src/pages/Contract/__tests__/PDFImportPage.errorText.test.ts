import { describe, expect, it } from 'vitest';

import { errorText, isPdfFile, relationTypeOptionsForRevenueMode } from '../PDFImportPage';

describe('errorText', () => {
  it('preserves an API client error message carried by a plain object', () => {
    expect(errorText({ message: 'contract context is invalid' })).toBe(
      'contract context is invalid'
    );
  });
});

describe('relationTypeOptionsForRevenueMode', () => {
  it('only exposes contract roles compatible with the selected revenue mode', () => {
    expect(relationTypeOptionsForRevenueMode('lease').map(option => option.value)).toEqual([
      '\u4e0a\u6e38',
      '\u4e0b\u6e38',
    ]);
    expect(relationTypeOptionsForRevenueMode('agency').map(option => option.value)).toEqual([
      '\u59d4\u6258',
      '\u76f4\u79df',
    ]);
  });
});

describe('isPdfFile', () => {
  it('allows PDFs by MIME type or filename and rejects other files before upload', () => {
    expect(isPdfFile({ name: 'contract', type: 'application/pdf' })).toBe(true);
    expect(isPdfFile({ name: 'contract.pdf', type: '' })).toBe(true);
    expect(isPdfFile({ name: 'contract.txt', type: 'text/plain' })).toBe(false);
  });
});
