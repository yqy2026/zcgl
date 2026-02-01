import { useCallback } from 'react';
import { useListData } from '@/hooks/useListData';
import type { ListResponse } from '@/hooks/useListData';
import { paginateArray } from '@/utils/pagination';

interface UseArrayListDataOptions<T, TFilters extends object> {
  items: T[];
  initialFilters: TFilters;
  initialPage?: number;
  initialPageSize?: number;
  onError?: (error: unknown) => void;
  filterFn?: (items: T[], filters: TFilters) => T[];
}

export const useArrayListData = <T, TFilters extends object>(
  options: UseArrayListDataOptions<T, TFilters>
) => {
  const {
    items,
    initialFilters,
    initialPage,
    initialPageSize,
    onError,
    filterFn,
  } = options;

  const fetcher = useCallback(
    async ({ page, pageSize, ...filters }: { page: number; pageSize: number } & TFilters) => {
      const nextFilters = filters as TFilters;
      const filteredItems = filterFn ? filterFn(items, nextFilters) : items;
      return paginateArray(filteredItems, page, pageSize) as ListResponse<T>;
    },
    [filterFn, items]
  );

  return useListData<T, TFilters>({
    fetcher,
    initialFilters,
    initialPage,
    initialPageSize,
    onError,
  });
};
