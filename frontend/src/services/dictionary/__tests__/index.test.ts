import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { baseDictionaryService } from '@/services/dictionary/base';
import { DictionaryService } from '@/services/dictionary/index';

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

describe('DictionaryService', () => {
  let service: DictionaryService;

  beforeEach(() => {
    vi.clearAllMocks();
    service = new DictionaryService();
  });

  it('getTypes 应返回所有 code，并在异常时兜底为空数组', async () => {
    const types = await service.getTypes();
    expect(types.length).toBeGreaterThan(0);

    const spy = vi
      .spyOn(baseDictionaryService, 'getAvailableTypes')
      .mockImplementationOnce(() => {
        throw new Error('broken');
      });
    const fallback = await service.getTypes();
    expect(fallback).toEqual([]);
    spy.mockRestore();
  });

  it('quickCreate 应覆盖已存在、创建成功、创建失败场景', async () => {
    const existed = await service.quickCreate('usage_status', { options: [] });
    expect(existed.success).toBe(true);
    expect(existed.message).toContain('已存在');

    const createSpy = vi
      .spyOn(service, 'createEnumFieldType')
      .mockResolvedValueOnce({
        id: 'new-type',
        name: 'new_type',
        code: 'new_type',
        is_system: false,
        is_multiple: false,
        is_hierarchical: false,
        status: 'active',
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      })
      .mockResolvedValueOnce(null);

    const created = await service.quickCreate('new_type', { options: [] });
    expect(created.success).toBe(true);
    const failed = await service.quickCreate('new_type_2', { options: [] });
    expect(failed.success).toBe(false);

    createSpy.mockRestore();
  });

  it('deleteType 与 addValue 应返回对应操作结果', async () => {
    const typesSpy = vi.spyOn(service, 'getEnumFieldTypes').mockResolvedValue([
      {
        id: 't1',
        name: '使用状态',
        code: 'usage_status',
        is_system: true,
        is_multiple: false,
        is_hierarchical: false,
        status: 'active',
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
    ]);

    const deleteSpy = vi.spyOn(service, 'deleteEnumFieldType').mockResolvedValue(true);
    const addSpy = vi.spyOn(service, 'addEnumFieldValue').mockResolvedValue({
      id: 'v1',
      enum_type_id: 't1',
      label: '出租',
      value: 'rented',
      level: 1,
      sort_order: 1,
      is_active: true,
      is_default: false,
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
    });

    const deleted = await service.deleteType('usage_status');
    expect(deleted.success).toBe(true);
    const added = await service.addValue('usage_status', { label: '出租', value: 'rented' });
    expect(added.success).toBe(true);

    const missing = await service.deleteType('not_exists');
    expect(missing.success).toBe(false);

    addSpy.mockRestore();
    deleteSpy.mockRestore();
    typesSpy.mockRestore();
  });

  it('getDictionaryStats 应生成统计并在异常时返回默认值', async () => {
    const typesSpy = vi.spyOn(service, 'getEnumFieldTypes').mockResolvedValue([
      {
        id: 't1',
        name: '使用状态',
        code: 'usage_status',
        is_system: true,
        is_multiple: false,
        is_hierarchical: false,
        status: 'active',
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
    ]);
    const usageSpy = vi.spyOn(service, 'getEnumFieldUsageStats').mockResolvedValue({
      total_records: 3,
      active_records: 2,
      usage_by_field: {},
      last_updated: '2026-01-01',
      popular_values: [],
    });
    const valuesSpy = vi.spyOn(service, 'getEnumFieldValues').mockResolvedValue([
      {
        id: 'v1',
        enum_type_id: 't1',
        label: '出租',
        value: 'rented',
        level: 1,
        sort_order: 1,
        is_active: true,
        is_default: false,
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
    ]);

    const stats = await service.getDictionaryStats();
    expect(stats.totalTypes).toBe(1);
    expect(stats.totalValues).toBe(1);
    expect(stats.performanceMetrics.errorRate).toBe(0);

    typesSpy.mockRejectedValueOnce(new Error('boom'));
    const fallback = await service.getDictionaryStats();
    expect(fallback.totalTypes).toBe(0);
    expect(fallback.performanceMetrics.errorRate).toBe(1);

    valuesSpy.mockRestore();
    usageSpy.mockRestore();
    typesSpy.mockRestore();
  });

  it('getSystemDictionaries 与 getEnumFieldValuesByTypeCode 应支持 API 与 fallback', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      success: true,
      data: [{ id: 'd1', dict_type: 'usage_status', dict_label: '出租', dict_value: 'rented' }],
    } as never);
    const apiData = await service.getSystemDictionaries('usage_status');
    expect(apiData.length).toBe(1);

    const fallbackSpy = vi.spyOn(service, 'getEnumFieldValuesByTypeCode').mockResolvedValueOnce([
      {
        id: 'd2',
        dict_type: 'usage_status',
        dict_code: 'rented',
        dict_label: '出租',
        dict_value: 'rented',
        sort_order: 1,
        is_active: true,
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
    ]);
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('down'));
    const fallback = await service.getSystemDictionaries('usage_status');
    expect(fallback[0]?.id).toBe('d2');

    const typesSpy = vi.spyOn(service, 'getEnumFieldTypes').mockResolvedValue([
      {
        id: 't1',
        name: '使用状态',
        code: 'usage_status',
        is_system: true,
        is_multiple: false,
        is_hierarchical: false,
        status: 'active',
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
    ]);
    const valuesSpy = vi.spyOn(service, 'getEnumFieldValues').mockResolvedValue([
      {
        id: 'v1',
        enum_type_id: 't1',
        label: '出租',
        value: 'rented',
        code: 'rented',
        level: 1,
        sort_order: 1,
        is_active: true,
        is_default: false,
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
    ]);
    const mapped = await service.getEnumFieldValuesByTypeCode('usage_status');
    expect(mapped[0]?.dict_code).toBe('rented');

    typesSpy.mockRejectedValueOnce(new Error('boom'));
    const empty = await service.getEnumFieldValuesByTypeCode('usage_status');
    expect(empty).toEqual([]);

    valuesSpy.mockRestore();
    typesSpy.mockRestore();
    fallbackSpy.mockRestore();
  });

  it('create/update/deleteEnumValue 应处理成功和未找到场景', async () => {
    const addSpy = vi.spyOn(service, 'addEnumFieldValue').mockResolvedValue({
      id: 'v1',
      enum_type_id: 't1',
      label: '出租',
      value: 'rented',
      level: 1,
      sort_order: 1,
      is_active: true,
      is_default: false,
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
    });
    const created = await service.createEnumValue('t1', { label: '出租', value: 'rented' });
    expect(created.success).toBe(true);

    addSpy.mockResolvedValueOnce(null);
    const createFail = await service.createEnumValue('t1', { label: '失败', value: 'fail' });
    expect(createFail.success).toBe(false);

    const enumDataSpy = vi.spyOn(service, 'getEnumFieldData').mockResolvedValue([
      {
        type: {
          id: 't1',
          name: '使用状态',
          code: 'usage_status',
          is_system: true,
          is_multiple: false,
          is_hierarchical: false,
          status: 'active',
          created_at: '2026-01-01',
          updated_at: '2026-01-01',
        },
        values: [
          {
            id: 'v1',
            enum_type_id: 't1',
            label: '出租',
            value: 'rented',
            level: 1,
            sort_order: 1,
            is_active: true,
            is_default: false,
            created_at: '2026-01-01',
            updated_at: '2026-01-01',
          },
        ],
      },
    ]);
    const updateSpy = vi.spyOn(service, 'updateEnumFieldValue').mockResolvedValue({
      id: 'v1',
      enum_type_id: 't1',
      label: '出租中',
      value: 'rented',
      level: 1,
      sort_order: 1,
      is_active: true,
      is_default: false,
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
    });
    const deleteSpy = vi.spyOn(service, 'deleteEnumFieldValue').mockResolvedValue(true);

    const updated = await service.updateEnumValue('v1', { label: '出租中' });
    expect(updated.success).toBe(true);
    const deleted = await service.deleteEnumValue('v1');
    expect(deleted.success).toBe(true);

    enumDataSpy.mockResolvedValueOnce([]);
    const updateMissing = await service.updateEnumValue('v404', { label: 'x' });
    expect(updateMissing.success).toBe(false);
    const deleteMissing = await service.deleteEnumValue('v404');
    expect(deleteMissing.success).toBe(false);

    deleteSpy.mockRestore();
    updateSpy.mockRestore();
    enumDataSpy.mockRestore();
    addSpy.mockRestore();
  });

  it('toggleEnumValueActive、batchOperation、healthCheck 应返回对应状态', async () => {
    const enumDataSpy = vi.spyOn(service, 'getEnumFieldData').mockResolvedValue([
      {
        type: {
          id: 't1',
          name: '使用状态',
          code: 'usage_status',
          is_system: true,
          is_multiple: false,
          is_hierarchical: false,
          status: 'active',
          created_at: '2026-01-01',
          updated_at: '2026-01-01',
        },
        values: [
          {
            id: 'v1',
            enum_type_id: 't1',
            label: '出租',
            value: 'rented',
            code: 'rented',
            description: '',
            level: 1,
            sort_order: 1,
            is_active: true,
            is_default: false,
            created_at: '2026-01-01',
            updated_at: '2026-01-01',
          },
        ],
      },
    ]);
    const updateSpy = vi.spyOn(service, 'updateEnumValue').mockResolvedValue({
      success: true,
      message: 'ok',
      operationType: 'updateEnumValue',
      timestamp: '2026-01-01',
    });

    const toggled = await service.toggleEnumValueActive('v1', false);
    expect(toggled.success).toBe(true);

    enumDataSpy.mockResolvedValueOnce([]);
    const notFound = await service.toggleEnumValueActive('v404', true);
    expect(notFound.success).toBe(false);

    const createSpy = vi.spyOn(service, 'createEnumValue').mockResolvedValue({
      success: true,
      message: 'created',
      operationType: 'createEnumValue',
      timestamp: '2026-01-01',
    });
    const deleteSpy = vi.spyOn(service, 'deleteEnumValue').mockResolvedValue({
      success: true,
      message: 'deleted',
      operationType: 'deleteEnumValue',
      timestamp: '2026-01-01',
    });

    const batchCreate = await service.batchOperation('create', [
      { typeId: 't1', data: { label: 'A', value: 'a' } },
      { data: { label: 'B', value: 'b' } },
    ]);
    expect(batchCreate.success).toBe(1);
    expect(batchCreate.failed).toBe(1);

    const batchDelete = await service.batchOperation('delete', [
      { valueId: 'v1', data: {} },
      { data: {} },
    ]);
    expect(batchDelete.success).toBe(1);
    expect(batchDelete.failed).toBe(1);

    const healthyTypeSpy = vi.spyOn(service, 'getEnumFieldTypes').mockResolvedValue([]);
    const healthy = await service.healthCheck();
    expect(healthy.status).toBe('healthy');

    healthyTypeSpy.mockRejectedValueOnce(new Error('down'));
    const degraded = await service.healthCheck();
    expect(degraded.status).toBe('degraded');

    const statsSpy = vi
      .spyOn(baseDictionaryService, 'getStats')
      .mockImplementationOnce(() => {
        throw new Error('down');
      });
    const unhealthy = await service.healthCheck();
    expect(unhealthy.status).toBe('unhealthy');

    statsSpy.mockRestore();
    healthyTypeSpy.mockRestore();
    deleteSpy.mockRestore();
    createSpy.mockRestore();
    updateSpy.mockRestore();
    enumDataSpy.mockRestore();
  });
});
