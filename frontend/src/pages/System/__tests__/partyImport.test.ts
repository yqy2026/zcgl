import { describe, expect, it } from 'vitest';
import * as XLSX from 'xlsx';
import { parsePartyImportWorkbook } from '../partyImport';

describe('partyImport', () => {
  it('parses the first worksheet into party payloads', async () => {
    const workbook = XLSX.utils.book_new();
    const worksheet = XLSX.utils.json_to_sheet([
      {
        主体类型: '法人主体',
        主体名称: '导入主体',
        统一标识类型: 'unified_social_credit_code',
        统一标识值: '91440101231229726P',
        外部引用: 'EXT-001',
        状态: 'active',
      },
    ]);
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Parties');
    const bytes = XLSX.write(workbook, { type: 'array', bookType: 'xlsx' });
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
