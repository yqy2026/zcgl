import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { DICTIONARY_CONFIGS } from '@/services/dictionary/config';
import { dictionaryManagerService, type EnumFieldType } from '@/services/dictionary/manager';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

const enumType = (overrides: Partial<EnumFieldType> = {}): EnumFieldType => ({
  id: 'type-1',
  name: '使用状态',
  code: 'usage_status',
  is_system: true,
  is_multiple: false,
  is_hierarchical: false,
  status: 'active',
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: '2026-01-01T00:00:00.000Z',
  ...overrides,
});

describe('dictionaryManagerService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getEnumFieldTypes 应支持字符串数组映射与失败回退', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      success: true,
      data: ['usage_status'],
    } as never);
    const mapped = await dictionaryManagerService.getEnumFieldTypes();
    expect(mapped[0]?.id).toBe('enum-type-0');
    expect(mapped[0]?.code).toBe('usage_status');

    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('network'));
    const fallback = await dictionaryManagerService.getEnumFieldTypes();
    expect(fallback.length).toBeGreaterThan(0);
    expect(fallback.some(item => item.code === 'usage_status')).toBe(true);
  });

  it('getEnumFieldValues 应处理空 type、映射数据与 fallback', async () => {
    const empty = await dictionaryManagerService.getEnumFieldValues('');
    expect(empty).toEqual([]);

    vi.mocked(apiClient.get).mockResolvedValueOnce({
      success: true,
      data: [enumType()],
    } as never);
    await dictionaryManagerService.getEnumFieldTypes();

    vi.mocked(apiClient.get).mockResolvedValueOnce({
      success: true,
      data: [
        {
          id: 'v-1',
          enum_type_id: '',
          label: '标签',
          value: 'value-1',
          is_active: false,
          is_default: true,
          sort_order: 3,
        },
      ],
    } as never);

    const values = await dictionaryManagerService.getEnumFieldValues('usage_status');
    expect(values[0]?.id).toBe('v-1');
    expect(values[0]?.enum_type_id).toBe('type-1');
    expect(values[0]?.is_active).toBe(false);
    expect(values[0]?.is_default).toBe(true);
    expect(apiClient.get).toHaveBeenLastCalledWith('/enum-fields/types/type-1/values', expect.any(Object));

    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('down'));
    const fallback = await dictionaryManagerService.getEnumFieldValues('usage_status');
    expect(fallback.length).toBeGreaterThan(0);
    expect(fallback[0]?.id).toContain('fallback-usage_status');
  });

  it('getEnumFieldData 应在值为空时使用 enum_values 备用数据', async () => {
    const type = enumType({
      enum_values: [
        {
          id: 'value-1',
          enum_type_id: 'type-1',
          label: 'L1',
          value: 'V1',
          level: 1,
          sort_order: 1,
          is_active: true,
          is_default: true,
          created_at: '2026-01-01',
          updated_at: '2026-01-01',
        },
      ],
    });

    const typesSpy = vi.spyOn(dictionaryManagerService, 'getEnumFieldTypes').mockResolvedValue([type]);
    const valuesSpy = vi.spyOn(dictionaryManagerService, 'getEnumFieldValues').mockResolvedValue([]);

    const data = await dictionaryManagerService.getEnumFieldData();
    expect(data[0]?.values[0]?.id).toBe('value-1');

    valuesSpy.mockRestore();
    typesSpy.mockRestore();
  });

  it('类型和值 CRUD 方法应返回预期结果', async () => {
    const invalidCreate = await dictionaryManagerService.createEnumFieldType({
      name: 'bad',
      code: 'INVALID_CODE',
    });
    expect(invalidCreate).toBeNull();

    vi.mocked(apiClient.post).mockResolvedValueOnce({
      success: true,
      data: enumType({ id: 'type-created', code: 'custom_type' }),
    } as never);
    const created = await dictionaryManagerService.createEnumFieldType({
      name: '自定义',
      code: 'custom_type',
    });
    expect(created?.id).toBe('type-created');

    const invalidUpdate = await dictionaryManagerService.updateEnumFieldType('type-1', {
      code: 'INVALID',
    });
    expect(invalidUpdate).toBeNull();

    vi.mocked(apiClient.put).mockResolvedValueOnce({
      success: true,
      data: enumType({ name: '已更新' }),
    } as never);
    const updated = await dictionaryManagerService.updateEnumFieldType('type-1', { name: '已更新' });
    expect(updated?.name).toBe('已更新');

    vi.mocked(apiClient.delete).mockResolvedValueOnce({
      success: true,
      data: { success: true, message: 'ok' },
    } as never);
    const deleted = await dictionaryManagerService.deleteEnumFieldType('type-1');
    expect(deleted).toBe(true);

    vi.mocked(apiClient.post).mockResolvedValueOnce({
      success: true,
      data: {
        id: 'v1',
        enum_type_id: 'type-1',
        label: 'L',
        value: 'V',
        level: 1,
        sort_order: 1,
        is_active: true,
        is_default: false,
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
    } as never);
    const added = await dictionaryManagerService.addEnumFieldValue('type-1', { label: 'L', value: 'V' });
    expect(added?.id).toBe('v1');

    vi.mocked(apiClient.put).mockResolvedValueOnce({
      success: true,
      data: {
        id: 'v1',
        enum_type_id: 'type-1',
        label: 'L2',
        value: 'V2',
        level: 1,
        sort_order: 1,
        is_active: true,
        is_default: false,
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
    } as never);
    const valueUpdated = await dictionaryManagerService.updateEnumFieldValue('type-1', 'v1', {
      label: 'L2',
      value: 'V2',
    });
    expect(valueUpdated?.label).toBe('L2');

    vi.mocked(apiClient.delete).mockResolvedValueOnce({
      success: true,
      data: { success: true, message: 'ok' },
    } as never);
    const valueDeleted = await dictionaryManagerService.deleteEnumFieldValue('type-1', 'v1');
    expect(valueDeleted).toBe(true);
  });

  it('getEnumFieldUsageStats 应返回统计结构并在异常时兜底', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      success: true,
      data: [
        { table_name: 'assets', field_name: 'usage_status', is_active: true },
        { table_name: 'assets', field_name: 'usage_status', is_active: false },
        { table_name: 'contracts', field_name: 'contract_status', is_active: true },
      ],
    } as never);
    const stats = await dictionaryManagerService.getEnumFieldUsageStats('');
    expect(stats.total_records).toBe(3);
    expect(stats.active_records).toBe(2);
    expect(stats.usage_by_field['assets.usage_status']).toBe(2);

    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('broken'));
    const fallback = await dictionaryManagerService.getEnumFieldUsageStats('');
    expect(fallback.total_records).toBe(0);
    expect(fallback.usage_by_field).toEqual({});
  });

  it('validateEnumTypeCode 应校验格式、长度与系统冲突', () => {
    const empty = dictionaryManagerService.validateEnumTypeCode('');
    expect(empty.valid).toBe(false);

    const invalid = dictionaryManagerService.validateEnumTypeCode('A-INVALID');
    expect(invalid.valid).toBe(false);

    const tooLong = dictionaryManagerService.validateEnumTypeCode('a'.repeat(51));
    expect(tooLong.valid).toBe(false);

    const conflicted = dictionaryManagerService.validateEnumTypeCode('usage_status');
    expect(conflicted.valid).toBe(false);

    const valid = dictionaryManagerService.validateEnumTypeCode('custom_code');
    expect(valid.valid).toBe(true);
  });

  it('导入导出应在成功时返回数据，在异常时抛错', async () => {
    const blob = new Blob(['abc'], { type: 'application/json' });
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      success: true,
      data: blob,
    } as never);
    const exported = await dictionaryManagerService.exportEnumFieldData('type-1');
    expect(exported).toBe(blob);

    vi.mocked(apiClient.get).mockResolvedValueOnce({
      success: false,
      error: 'fail',
    } as never);
    await expect(dictionaryManagerService.exportEnumFieldData('type-1')).rejects.toThrow('导出失败');

    vi.mocked(apiClient.post).mockResolvedValueOnce({
      success: true,
      data: { success: 2, errors: [] },
    } as never);
    const file = new File(['x'], 'enum.xlsx');
    const imported = await dictionaryManagerService.importEnumFieldData('type-1', file);
    expect(imported.success).toBe(2);

    vi.mocked(apiClient.post).mockResolvedValueOnce({
      success: false,
      error: 'import-fail',
    } as never);
    await expect(dictionaryManagerService.importEnumFieldData('type-1', file)).rejects.toThrow('导入失败');
  });

  it('批量操作方法应统计成功与失败数量', async () => {
    const addSpy = vi
      .spyOn(dictionaryManagerService, 'addEnumFieldValue')
      .mockResolvedValueOnce({
        id: 'v1',
        enum_type_id: 'type-1',
        label: 'L1',
        value: 'V1',
        level: 1,
        sort_order: 1,
        is_active: true,
        is_default: false,
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      })
      .mockRejectedValueOnce(new Error('bad'));

    const addResult = await dictionaryManagerService.batchAddEnumValues('type-1', [
      { label: 'L1', value: 'V1' },
      { label: 'L2', value: 'V2' },
    ]);
    expect(addResult.success).toBe(1);
    expect(addResult.failed).toBe(1);
    addSpy.mockRestore();

    const updateSpy = vi
      .spyOn(dictionaryManagerService, 'updateEnumFieldValue')
      .mockResolvedValueOnce({
        id: 'v1',
        enum_type_id: 'type-1',
        label: 'L1',
        value: 'V1',
        level: 1,
        sort_order: 1,
        is_active: true,
        is_default: false,
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      })
      .mockRejectedValueOnce(new Error('bad'));
    const updateResult = await dictionaryManagerService.batchUpdateEnumValues('type-1', [
      { valueId: 'v1', data: { label: 'U1' } },
      { valueId: 'v2', data: { label: 'U2' } },
    ]);
    expect(updateResult.success).toBe(1);
    expect(updateResult.failed).toBe(1);
    updateSpy.mockRestore();

    const deleteSpy = vi
      .spyOn(dictionaryManagerService, 'deleteEnumFieldValue')
      .mockResolvedValueOnce(true)
      .mockRejectedValueOnce(new Error('bad'));
    const deleteResult = await dictionaryManagerService.batchDeleteEnumValues('type-1', ['v1', 'v2']);
    expect(deleteResult.success).toBe(1);
    expect(deleteResult.failed).toBe(1);
    deleteSpy.mockRestore();
  });

  it('searchEnumTypes 应支持 API 查询和本地回退过滤', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      success: true,
      data: [enumType({ code: 'usage_status' })],
    } as never);
    const apiResult = await dictionaryManagerService.searchEnumTypes('usage');
    expect(apiResult.length).toBe(1);

    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('down'));
    const typesSpy = vi.spyOn(dictionaryManagerService, 'getEnumFieldTypes').mockResolvedValue([
      enumType({ code: 'usage_status', name: '使用状态', category: '资产状态' }),
      enumType({ id: 'type-2', code: 'tenant_type', name: '承租方类型', category: '租赁信息' }),
    ]);

    const local = await dictionaryManagerService.searchEnumTypes('状态', {
      category: '资产状态',
      is_system: true,
    });
    expect(local.length).toBe(1);
    expect(local[0]?.code).toBe('usage_status');

    typesSpy.mockRestore();
  });

  it('validateDictionaryData 应返回问题、警告与建议', async () => {
    const typesSpy = vi
      .spyOn(dictionaryManagerService, 'getEnumFieldTypes')
      .mockResolvedValueOnce([enumType({ code: 'usage_status' })])
      .mockResolvedValueOnce([]);

    const valuesSpy = vi.spyOn(dictionaryManagerService, 'getEnumFieldValues').mockResolvedValueOnce([
      {
        id: 'v1',
        enum_type_id: 'type-1',
        label: '重复',
        value: 'dup',
        level: 1,
        sort_order: 0,
        is_active: true,
        is_default: true,
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
      {
        id: 'v2',
        enum_type_id: 'type-1',
        label: '重复',
        value: 'dup',
        level: 1,
        sort_order: 0,
        is_active: true,
        is_default: true,
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
      {
        id: 'v3',
        enum_type_id: 'type-1',
        label: '',
        value: '',
        level: 1,
        sort_order: 0,
        is_active: true,
        is_default: false,
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
    ]);

    const validation = await dictionaryManagerService.validateDictionaryData('usage_status');
    expect(validation.isValid).toBe(false);
    expect(validation.issues.length).toBeGreaterThan(0);
    expect(validation.warnings.length).toBeGreaterThan(0);
    expect(validation.suggestions.length).toBeGreaterThan(0);

    const missingType = await dictionaryManagerService.validateDictionaryData('not_exists');
    expect(missingType.isValid).toBe(false);
    expect(missingType.issues[0]).toContain('字典类型不存在');

    valuesSpy.mockRestore();
    typesSpy.mockRestore();
  });

  it('备用类型数据应与配置保持一致', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('force fallback'));
    const list = await dictionaryManagerService.getEnumFieldTypes();
    expect(list.length).toBe(Object.keys(DICTIONARY_CONFIGS).length);
  });
});
