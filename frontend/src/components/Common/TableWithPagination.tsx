import React from 'react';
import { Table } from 'antd';
import type { TableProps } from 'antd/es/table';

export interface PaginationState {
  current: number;
  pageSize: number;
  total: number;
}

export interface TableWithPaginationProps<T> extends Omit<TableProps<T>, 'pagination' | 'onChange'> {
  paginationState: PaginationState;
  onPageChange: (pagination: { current?: number; pageSize?: number }) => void;
  paginationProps?: Omit<
    NonNullable<TableProps<T>['pagination']>,
    'current' | 'pageSize' | 'total'
  >;
  onChange?: TableProps<T>['onChange'];
}

export const TableWithPagination = <T extends object,>(
  props: TableWithPaginationProps<T>
) => {
  const { paginationState, onPageChange, paginationProps, onChange, ...rest } = props;

  const handleChange: TableProps<T>['onChange'] = (pagination, filters, sorter, extra) => {
    onPageChange({ current: pagination.current, pageSize: pagination.pageSize });
    if (onChange != null) {
      onChange(pagination, filters, sorter, extra);
    }
  };

  return (
    <Table
      {...rest}
      pagination={{
        current: paginationState.current,
        pageSize: paginationState.pageSize,
        total: paginationState.total,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
        ...paginationProps,
      }}
      onChange={handleChange}
    />
  );
};
