import * as XLSX from 'xlsx';
import type { PartyCreatePayload } from '@/services/partyService';
import type { PartyType } from '@/types/party';

const HEADER_ALIASES: Record<string, keyof PartyCreatePayload> = {
  party_type: 'party_type',
  主体类型: 'party_type',
  name: 'name',
  主体名称: 'name',
  code: 'code',
  主体编码: 'code',
  external_ref: 'external_ref',
  外部引用: 'external_ref',
  status: 'status',
  状态: 'status',
};

const PARTY_TYPE_ALIASES: Record<string, PartyType> = {
  organization: 'organization',
  组织: 'organization',
  legal_entity: 'legal_entity',
  法人主体: 'legal_entity',
  individual: 'individual',
  自然人: 'individual',
};

const normalizeHeader = (value: unknown): string => String(value ?? '').trim();

const normalizePartyType = (value: unknown): PartyType => {
  const normalized = String(value ?? '').trim();
  const resolved = PARTY_TYPE_ALIASES[normalized];
  if (resolved == null) {
    throw new Error(`不支持的主体类型: ${normalized}`);
  }
  return resolved;
};

const normalizeRow = (row: Record<string, unknown>): PartyCreatePayload => {
  const mapped: Partial<PartyCreatePayload> = {};

  for (const [rawKey, rawValue] of Object.entries(row)) {
    const resolvedKey = HEADER_ALIASES[normalizeHeader(rawKey)];
    if (resolvedKey == null) {
      continue;
    }
    if (resolvedKey === 'party_type') {
      mapped.party_type = normalizePartyType(rawValue);
      continue;
    }

    const normalizedValue = String(rawValue ?? '').trim();
    if (normalizedValue === '') {
      continue;
    }
    if (resolvedKey === 'name') {
      mapped.name = normalizedValue;
      continue;
    }
    if (resolvedKey === 'code') {
      mapped.code = normalizedValue;
      continue;
    }
    if (resolvedKey === 'external_ref') {
      mapped.external_ref = normalizedValue;
      continue;
    }
    if (resolvedKey === 'status') {
      mapped.status = normalizedValue;
    }
  }

  if (mapped.party_type == null || mapped.name == null || mapped.code == null) {
    throw new Error('导入文件缺少必填列：主体类型/主体名称/主体编码');
  }

  return {
    party_type: mapped.party_type,
    name: mapped.name,
    code: mapped.code,
    external_ref: mapped.external_ref ?? null,
    status: mapped.status ?? 'active',
  };
};

export const parsePartyImportWorkbook = async (file: File): Promise<PartyCreatePayload[]> => {
  const buffer =
    typeof file.arrayBuffer === 'function'
      ? await file.arrayBuffer()
      : await new Promise<ArrayBuffer>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            if (reader.result instanceof ArrayBuffer) {
              resolve(reader.result);
              return;
            }
            reject(new Error('无法读取导入文件'));
          };
          reader.onerror = () => {
            reject(reader.error ?? new Error('无法读取导入文件'));
          };
          reader.readAsArrayBuffer(file);
        });
  const workbook = XLSX.read(buffer, { type: 'array' });
  const firstSheetName = workbook.SheetNames[0];
  if (firstSheetName == null) {
    throw new Error('导入文件不包含工作表');
  }

  const worksheet = workbook.Sheets[firstSheetName];
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(worksheet, {
    defval: '',
  });

  if (rows.length === 0) {
    throw new Error('导入文件为空');
  }

  return rows.map(normalizeRow);
};
