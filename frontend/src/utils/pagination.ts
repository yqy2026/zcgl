export interface PaginatedArrayResult<T> {
  items: T[];
  total: number;
  pages: number;
}

export const paginateArray = <T>(
  items: T[],
  page: number,
  pageSize: number
): PaginatedArrayResult<T> => {
  const total = items.length;
  const safePageSize = pageSize > 0 ? pageSize : total > 0 ? total : 1;
  const safePage = page > 0 ? page : 1;
  const start = (safePage - 1) * safePageSize;
  const end = start + safePageSize;
  const pagedItems = start >= total ? [] : items.slice(start, end);
  const pages = total === 0 ? 0 : Math.ceil(total / safePageSize);

  return {
    items: pagedItems,
    total,
    pages,
  };
};
