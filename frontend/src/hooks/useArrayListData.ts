import { useCallback, useEffect, useRef, useState } from 'react';
import { paginateArray } from '@/utils/pagination';

interface UseArrayListDataOptions<T, TFilters extends object> {
  items: T[];
  initialFilters: TFilters;
  initialPage?: number;
  initialPageSize?: number;
  onError?: (error: unknown) => void;
  filterFn?: (items: T[], filters: TFilters) => T[];
}

interface ListResponse<T> {
  items?: T[];
  total?: number;
  pages?: number;
}

interface ListPagination {
  current: number;
  pageSize: number;
  total: number;
  pages?: number;
}

interface LoadListOptions<TFilters> {
  page?: number;
  pageSize?: number;
  filters?: Partial<TFilters>;
  replaceFilters?: boolean;
}

export const useArrayListData = <T, TFilters extends object>(
  options: UseArrayListDataOptions<T, TFilters>
) => {
  const {
    items,
    initialFilters,
    initialPage = 1,
    initialPageSize = 10,
    onError,
    filterFn,
  } = options;

  const initialFiltersRef = useRef(initialFilters);
  const [filters, setFilters] = useState<TFilters>(initialFilters);
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [pagination, setPagination] = useState<ListPagination>({
    current: initialPage,
    pageSize: initialPageSize,
    total: 0,
  });

  const filtersRef = useRef(filters);
  const paginationRef = useRef(pagination);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    filtersRef.current = filters;
  }, [filters]);

  useEffect(() => {
    paginationRef.current = pagination;
  }, [pagination]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const fetcher = useCallback(
    async ({ page, pageSize, ...nextFilters }: { page: number; pageSize: number } & TFilters) => {
      const resolvedFilters = nextFilters as TFilters;
      const filteredItems = filterFn != null ? filterFn(items, resolvedFilters) : items;
      return paginateArray(filteredItems, page, pageSize) as ListResponse<T>;
    },
    [filterFn, items]
  );

  const loadList = useCallback(
    async (loadOptions?: LoadListOptions<TFilters>) => {
      setLoading(true);
      setError(null);
      try {
        const optionsValue = loadOptions ?? {};
        const currentPagination = paginationRef.current;
        const currentFilters = filtersRef.current;
        const page = optionsValue.page ?? currentPagination.current;
        const pageSize = optionsValue.pageSize ?? currentPagination.pageSize;
        const nextFilters = optionsValue.replaceFilters
          ? ((optionsValue.filters ?? currentFilters) as TFilters)
          : { ...currentFilters, ...(optionsValue.filters ?? {}) };
        const response = await fetcher({ page, pageSize, ...nextFilters });

        if (response == null) {
          throw new Error('List response is empty');
        }

        const listItems = Array.isArray(response.items) ? response.items : [];
        setData(listItems);
        setPagination(prev => ({
          ...prev,
          current: page,
          pageSize,
          total: response.total ?? 0,
          pages: response.pages ?? prev.pages,
        }));

        if (optionsValue.filters != null) {
          setFilters(nextFilters);
        }
      } catch (nextError) {
        setData([]);
        setError(nextError);
        if (onErrorRef.current != null) {
          onErrorRef.current(nextError);
        }
      } finally {
        setLoading(false);
      }
    },
    [fetcher]
  );

  const applyFilters = useCallback(
    (nextFilters: TFilters) => {
      setFilters(nextFilters);
      setPagination(prev => ({ ...prev, current: 1 }));
      void loadList({ page: 1, filters: nextFilters, replaceFilters: true });
    },
    [loadList]
  );

  const resetFilters = useCallback(() => {
    const nextFilters = initialFiltersRef.current;
    setFilters(nextFilters);
    setPagination(prev => ({ ...prev, current: 1 }));
    void loadList({ page: 1, filters: nextFilters, replaceFilters: true });
  }, [loadList]);

  const updatePagination = useCallback(
    (next: { current?: number; pageSize?: number }) => {
      const current = next.current ?? pagination.current;
      const pageSize = next.pageSize ?? pagination.pageSize;
      setPagination(prev => ({ ...prev, current, pageSize }));
      void loadList({ page: current, pageSize });
    },
    [loadList, pagination.current, pagination.pageSize]
  );

  return {
    data,
    loading,
    error,
    pagination,
    filters,
    loadList,
    applyFilters,
    resetFilters,
    updatePagination,
  };
};
