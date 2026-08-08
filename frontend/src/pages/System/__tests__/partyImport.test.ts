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
});
