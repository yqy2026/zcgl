import { useQuery } from '@tanstack/react-query';
import { dictionaryService } from '@/services/dictionary';
import type { DictionaryOption, DictionaryServiceResult } from '@/services/dictionary';

// Define the hook return type
interface UseSystemDictionaryResult {
  options: DictionaryOption[];
  loading: boolean;
  error: Error | null;
  getLabel: (value: string | number | undefined | null) => string;
}

/**
 * Custom hook to fetch system dictionary options using React Query
 * @param dictType The dictionary type code (e.g., 'ownership_status')
 * @returns Object containing options, loading state, error state, and a helper to get labels
 */
export const useSystemDictionary = (dictType: string): UseSystemDictionaryResult => {
  const { data, isLoading, error } = useQuery<DictionaryServiceResult>({
    queryKey: ['dictionary', dictType],
    queryFn: async () => {
      // Use the unified getOptions method which handles caching and fallback logic
      const result: DictionaryServiceResult = await dictionaryService.getOptions(dictType);
      return result;
    },
    // Cache for 30 minutes since dictionary data changes infrequently
    staleTime: 30 * 60 * 1000,
    // Keep in cache for 1 hour
    gcTime: 60 * 60 * 1000,
    // Don't refetch on window focus to avoid unnecessary requests
    refetchOnWindowFocus: false,
    enabled: !!dictType,
  });

  const options = data?.success === true ? (data.data ?? []) : [];

  // Helper function to get label from value
  const getLabel = (value: string | number | undefined | null): string => {
    if (value === undefined || value === null || options.length === 0) return '-';
    const option = options.find(opt => opt.value === String(value));
    return option ? option.label : String(value);
  };

  const errorMessage =
    data?.success === true
      ? null
      : new Error(data?.error ?? error?.message ?? '字典数据获取失败');

  return {
    options,
    loading: isLoading,
    error: errorMessage,
    getLabel,
  };
};
