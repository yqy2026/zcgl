import React from 'react';
import { Table, Pagination } from 'antd';
import type { TableProps } from 'antd/es/table';
import { ResponsiveTable } from '@/components/Common/ResponsiveTable';
import styles from './TableWithPagination.module.css';

export interface PaginationState {
  current: number;
  pageSize: number;
  total: number;
}

export interface TableWithPaginationProps<T> extends Omit<
  TableProps<T>,
  'pagination' | 'onChange'
> {
  paginationState: PaginationState;
  onPageChange: (pagination: { current?: number; pageSize?: number }) => void;
  paginationProps?: Omit<
    NonNullable<TableProps<T>['pagination']>,
    'current' | 'pageSize' | 'total'
  >;
  onChange?: TableProps<T>['onChange'];
  /**
   * Enable responsive card view on mobile
   * @default true
   */
  responsive?: boolean;
  /**
   * Custom card title for mobile view
   */
  cardTitle?: string;
  /**
   * Custom card renderer for mobile view
   */
  renderCard?: (record: T, index: number) => React.ReactNode;
  /**
   * Fields to display in card view
   */
  cardFields?: Array<Extract<keyof T, string> | { key: string; label: string; render?: (value: unknown, record: T) => React.ReactNode }>;
}

export const TableWithPagination = <T extends object>(props: TableWithPaginationProps<T>) => {
  const {
    paginationState,
    onPageChange,
    paginationProps,
    onChange,
    responsive = true,
    cardTitle,
    renderCard,
    cardFields,
    className,
    ...rest
  } = props;

  const handleChange: TableProps<T>['onChange'] = (pagination, filters, sorter, extra) => {
    onPageChange({ current: pagination.current, pageSize: pagination.pageSize });
    if (onChange != null) {
      onChange(pagination, filters, sorter, extra);
    }
  };

  const handlePageChange = (page: number, pageSize: number) => {
    onPageChange({ current: page, pageSize });
  };
  const tableScroll = rest.scroll ?? { x: 'max-content' };
  const mergedTableClassName = [styles.tableRoot, className]
    .filter((tableClassName): tableClassName is string => {
      return tableClassName != null && tableClassName !== '';
    })
    .join(' ');

  return (
    <div className={styles.wrapper}>
      {responsive ? (
        <ResponsiveTable
          {...rest}
          className={mergedTableClassName}
          cardTitle={cardTitle}
          renderCard={renderCard}
          cardFields={cardFields}
          dataSource={rest.dataSource}
          columns={rest.columns}
          rowKey={rest.rowKey}
          onChange={handleChange}
          scroll={tableScroll}
        />
      ) : (
        <Table
          {...rest}
          className={mergedTableClassName}
          dataSource={rest.dataSource}
          columns={rest.columns}
          rowKey={rest.rowKey}
          onChange={handleChange}
          scroll={tableScroll}
        />
      )}

      {/* Pagination */}
      <div className={styles.paginationContainer}>
        <Pagination
          current={paginationState.current}
          pageSize={paginationState.pageSize}
          total={paginationState.total}
          showSizeChanger
          showQuickJumper
          showTotal={(total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`}
          onChange={handlePageChange}
          {...paginationProps}
          responsive
        />
      </div>
    </div>
  );
};
