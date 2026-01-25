import { useQuery } from '@tanstack/react-query';
import { dictionaryService, DictionaryOption } from '@/services/dictionary';

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
  const { data, isLoading, error } = useQuery({
    queryKey: ['dictionary', dictType],
    queryFn: async () => {
      // Use the unified getOptions method which handles caching and fallback logic
      const result = await dictionaryService.getOptions(dictType);
      return result.data;
    },
    // Cache for 30 minutes since dictionary data changes infrequently
    staleTime: 30 * 60 * 1000,
    // Keep in cache for 1 hour
    cacheTime: 60 * 60 * 1000,
    // Don't refetch on window focus to avoid unnecessary requests
    refetchOnWindowFocus: false,
  });

  // Helper function to get label from value
  const getLabel = (value: string | number | undefined | null): string => {
    if (value === undefined || value === null || !data) return '-';
    const option = data.find(opt => opt.value === String(value));
    return option ? option.label : String(value);
  };

  return {
    options: data || [],
    loading: isLoading,
    error: error as Error | null,
    getLabel,
  };
};
