import * as XLSX from 'xlsx';
import type { PartyCreatePayload } from '@/services/partyService';
import type { PartyType } from '@/types/party';

const HEADER_ALIASES: Record<string, keyof PartyCreatePayload> = {
  party_type: 'party_type',
  主体类型: 'party_type',
  name: 'name',
  主体名称: 'name',
  identifier_type: 'identifier_type',
  统一标识类型: 'identifier_type',
  identifier_value: 'identifier_value',
  统一标识值: 'identifier_value',
  external_ref: 'external_ref',
  外部引用: 'external_ref',
};

const PARTY_TYPE_ALIASES: Record<string, PartyType> = {
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
    if (resolvedKey === 'identifier_type') {
      mapped.identifier_type = normalizedValue as PartyCreatePayload['identifier_type'];
      continue;
    }
    if (resolvedKey === 'identifier_value') {
      mapped.identifier_value = normalizedValue;
      continue;
    }
    if (resolvedKey === 'external_ref') {
      mapped.external_ref = normalizedValue;
      continue;
    }
  }

  if (mapped.party_type == null || mapped.name == null) {
    throw new Error('导入文件缺少必填列：主体类型/主体名称');
  }
  if ((mapped.identifier_type == null) !== (mapped.identifier_value == null)) {
    throw new Error('统一标识类型和统一标识值必须同时填写');
  }

  return {
    party_type: mapped.party_type,
    name: mapped.name,
    identifier_type: mapped.identifier_type ?? null,
    identifier_value: mapped.identifier_value ?? null,
    external_ref: mapped.external_ref ?? null,
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
