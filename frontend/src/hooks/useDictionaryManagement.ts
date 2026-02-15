import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { dictionaryService } from '@/services/dictionary';
import type {
  CreateEnumFieldTypeRequest,
  CreateEnumFieldValueRequest,
  DictionaryOperationResult,
  DictionaryStats,
  EnumFieldType,
  EnumFieldValue,
  UpdateEnumFieldTypeRequest,
  UpdateEnumFieldValueRequest,
} from '@/services/dictionary';
import type { SystemDictionary } from '@/types/dictionary';

const STALE_TIME_MS = 60 * 1000;

const hasText = (value: string | null | undefined): value is string => {
  return value != null && value.trim() !== '';
};

export interface DictionaryStatisticsSummary {
  total_types: number;
  active_types: number;
  total_values: number;
  active_values: number;
  usage_count: number;
  categories: string[];
}

export const dictionaryManagementQueryKeys = {
  all: ['dictionary-management'] as const,
  enumFieldTypes: () => ['dictionary-management', 'enum-field-types'] as const,
  enumFieldData: () => ['dictionary-management', 'enum-field-data'] as const,
  enumFieldValuesByTypeCodePrefix: () =>
    ['dictionary-management', 'enum-field-values-by-type-code'] as const,
  enumFieldValuesByTypeCode: (typeCode: string) =>
    ['dictionary-management', 'enum-field-values-by-type-code', typeCode] as const,
  enumFieldValuesByTypeIdPrefix: () =>
    ['dictionary-management', 'enum-field-values-by-type-id'] as const,
  enumFieldValuesByTypeId: (typeId: string) =>
    ['dictionary-management', 'enum-field-values-by-type-id', typeId] as const,
  dictionaryStatistics: () => ['dictionary-management', 'dictionary-statistics'] as const,
};

const invalidateDictionaryManagementQueries = async (queryClient: QueryClient): Promise<void> => {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: dictionaryManagementQueryKeys.enumFieldTypes() }),
    queryClient.invalidateQueries({ queryKey: dictionaryManagementQueryKeys.enumFieldData() }),
    queryClient.invalidateQueries({
      queryKey: dictionaryManagementQueryKeys.enumFieldValuesByTypeCodePrefix(),
    }),
    queryClient.invalidateQueries({
      queryKey: dictionaryManagementQueryKeys.enumFieldValuesByTypeIdPrefix(),
    }),
    queryClient.invalidateQueries({
      queryKey: dictionaryManagementQueryKeys.dictionaryStatistics(),
    }),
  ]);
};

export const useEnumFieldTypesQuery = () => {
  return useQuery<EnumFieldType[]>({
    queryKey: dictionaryManagementQueryKeys.enumFieldTypes(),
    queryFn: async () => {
      return await dictionaryService.getEnumFieldTypes();
    },
    staleTime: STALE_TIME_MS,
  });
};

export const useEnumFieldDataQuery = () => {
  return useQuery({
    queryKey: dictionaryManagementQueryKeys.enumFieldData(),
    queryFn: async () => {
      return await dictionaryService.getEnumFieldData();
    },
    staleTime: STALE_TIME_MS,
  });
};

export const useEnumFieldValuesByTypeCodeQuery = (typeCode: string | undefined) => {
  const normalizedTypeCode = typeCode?.trim() ?? '';
  return useQuery<SystemDictionary[]>({
    queryKey: dictionaryManagementQueryKeys.enumFieldValuesByTypeCode(normalizedTypeCode),
    queryFn: async () => {
      if (normalizedTypeCode === '') {
        return [];
      }
      return await dictionaryService.getEnumFieldValuesByTypeCode(normalizedTypeCode);
    },
    enabled: normalizedTypeCode !== '',
    staleTime: STALE_TIME_MS,
  });
};

export const useEnumFieldValuesByTypeIdQuery = (typeId: string | null) => {
  const normalizedTypeId = typeId?.trim() ?? '';
  return useQuery<EnumFieldValue[]>({
    queryKey: dictionaryManagementQueryKeys.enumFieldValuesByTypeId(normalizedTypeId),
    queryFn: async () => {
      if (normalizedTypeId === '') {
        return [];
      }
      return await dictionaryService.getEnumFieldValues(normalizedTypeId);
    },
    enabled: normalizedTypeId !== '',
    staleTime: STALE_TIME_MS,
  });
};

export const useDictionaryStatisticsQuery = () => {
  return useQuery<DictionaryStatisticsSummary>({
    queryKey: dictionaryManagementQueryKeys.dictionaryStatistics(),
    queryFn: async () => {
      const [stats, enumData] = await Promise.all([
        dictionaryService.getDictionaryStats(),
        dictionaryService.getEnumFieldData(),
      ]);
      const activeValues = enumData.reduce((totalCount, item) => {
        const activeCount = item.values.filter(value => value.is_active === true).length;
        return totalCount + activeCount;
      }, 0);

      return {
        total_types: stats.totalTypes,
        active_types: stats.activeTypes,
        total_values: stats.totalValues,
        active_values: activeValues,
        usage_count: 0,
        categories: [],
      };
    },
    staleTime: STALE_TIME_MS,
  });
};

export const useCreateEnumFieldTypeMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateEnumFieldTypeRequest) => {
      return await dictionaryService.createEnumFieldType(payload);
    },
    onSuccess: async () => {
      await invalidateDictionaryManagementQueries(queryClient);
    },
  });
};

export const useUpdateEnumFieldTypeMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { typeId: string; data: UpdateEnumFieldTypeRequest }) => {
      return await dictionaryService.updateEnumFieldType(payload.typeId, payload.data);
    },
    onSuccess: async () => {
      await invalidateDictionaryManagementQueries(queryClient);
    },
  });
};

export const useDeleteEnumFieldTypeMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (typeId: string) => {
      return await dictionaryService.deleteEnumFieldType(typeId);
    },
    onSuccess: async (_, typeId) => {
      await Promise.all([
        invalidateDictionaryManagementQueries(queryClient),
        hasText(typeId)
          ? queryClient.invalidateQueries({
              queryKey: dictionaryManagementQueryKeys.enumFieldValuesByTypeId(typeId),
            })
          : Promise.resolve(),
      ]);
    },
  });
};

export const useCreateEnumFieldValueMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { typeId: string; data: CreateEnumFieldValueRequest }) => {
      return await dictionaryService.addEnumFieldValue(payload.typeId, payload.data);
    },
    onSuccess: async (_, payload) => {
      await Promise.all([
        invalidateDictionaryManagementQueries(queryClient),
        hasText(payload.typeId)
          ? queryClient.invalidateQueries({
              queryKey: dictionaryManagementQueryKeys.enumFieldValuesByTypeId(payload.typeId),
            })
          : Promise.resolve(),
      ]);
    },
  });
};

export const useUpdateEnumFieldValueMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      typeId: string;
      valueId: string;
      data: UpdateEnumFieldValueRequest;
    }) => {
      return await dictionaryService.updateEnumFieldValue(
        payload.typeId,
        payload.valueId,
        payload.data
      );
    },
    onSuccess: async (_, payload) => {
      await Promise.all([
        invalidateDictionaryManagementQueries(queryClient),
        hasText(payload.typeId)
          ? queryClient.invalidateQueries({
              queryKey: dictionaryManagementQueryKeys.enumFieldValuesByTypeId(payload.typeId),
            })
          : Promise.resolve(),
      ]);
    },
  });
};

export const useCreateEnumValueMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { typeId: string; data: CreateEnumFieldValueRequest }) => {
      return await dictionaryService.createEnumValue(payload.typeId, payload.data);
    },
    onSuccess: async (_, payload) => {
      await Promise.all([
        invalidateDictionaryManagementQueries(queryClient),
        hasText(payload.typeId)
          ? queryClient.invalidateQueries({
              queryKey: dictionaryManagementQueryKeys.enumFieldValuesByTypeCodePrefix(),
            })
          : Promise.resolve(),
      ]);
    },
  });
};

export const useUpdateEnumValueMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { valueId: string; data: UpdateEnumFieldValueRequest }) => {
      return await dictionaryService.updateEnumValue(payload.valueId, payload.data);
    },
    onSuccess: async () => {
      await invalidateDictionaryManagementQueries(queryClient);
    },
  });
};

export const useDeleteEnumValueMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (valueId: string) => {
      return await dictionaryService.deleteEnumValue(valueId);
    },
    onSuccess: async () => {
      await invalidateDictionaryManagementQueries(queryClient);
    },
  });
};

export const useToggleEnumValueActiveMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { valueId: string; isActive: boolean }) => {
      return await dictionaryService.toggleEnumValueActive(payload.valueId, payload.isActive);
    },
    onSuccess: async () => {
      await invalidateDictionaryManagementQueries(queryClient);
    },
  });
};

export type {
  CreateEnumFieldTypeRequest,
  CreateEnumFieldValueRequest,
  DictionaryOperationResult,
  DictionaryStats,
  UpdateEnumFieldTypeRequest,
  UpdateEnumFieldValueRequest,
};
