import { describe, expect, it } from 'vitest';
import ExcelJS from 'exceljs';
import { parsePartyImportWorkbook } from '../partyImport';

describe('partyImport', () => {
  it('parses the first worksheet into party payloads', async () => {
    const workbook = new ExcelJS.Workbook();
    const worksheet = workbook.addWorksheet('Parties');
    worksheet.addRows([
      ['主体类型', '主体名称', '统一标识类型', '统一标识值', '外部引用', '状态'],
      [
        '法人主体',
        '导入主体',
        'unified_social_credit_code',
        '91440101231229726P',
        'EXT-001',
        'active',
      ],
    ]);
    const bytes = await workbook.xlsx.writeBuffer();
    const file = new File([bytes], 'party-import.xlsx');

    const result = await parsePartyImportWorkbook(file);

    expect(result).toEqual([
      {
        party_type: 'legal_entity',
        name: '导入主体',
        identifier_type: 'unified_social_credit_code',
        identifier_value: '91440101231229726P',
        external_ref: 'EXT-001',
      },
    ]);
  });

  it('parses date cells as Excel serial numbers (sheet_to_json semantics)', async () => {
    const workbook = new ExcelJS.Workbook();
    const worksheet = workbook.addWorksheet('Parties');
    worksheet.addRows([
      ['主体类型', '主体名称', '统一标识类型', '统一标识值'],
      ['法人主体', '日期主体', 'unified_social_credit_code', new Date(Date.UTC(2026, 5, 1))],
    ]);
    const bytes = await workbook.xlsx.writeBuffer();
    const file = new File([bytes], 'party-date-import.xlsx');

    const result = await parsePartyImportWorkbook(file);

    // 与旧 XLSX.sheet_to_json 一致：日期单元格产出序列号，而非 JS Date 的字符串形式
    const expectedSerial = Math.floor(new Date(Date.UTC(2026, 5, 1)).getTime() / 86400000) + 25569;
    expect(result[0].identifier_value).toBe(String(expectedSerial));
  });
});
