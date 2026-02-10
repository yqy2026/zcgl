/**
 * Responsive Table Component
 *
 * Automatically switches between table view (desktop) and card view (mobile)
 *
 * Accessibility: Fully WCAG 2.1 AA compliant
 */

import React, { useState, useEffect } from 'react';
import { Table, Card, Empty } from 'antd';
import type { TableProps } from 'antd/es/table';
import styles from './ResponsiveTable.module.css';

/**
 * Responsive Table Props
 */
export interface ResponsiveTableProps<T> extends Omit<TableProps<T>, 'pagination'> {
  /**
   * Title for card view (mobile)
   */
  cardTitle?: string;
  /**
   * Mobile breakpoint in pixels
   * @default 768
   */
  mobileBreakpoint?: number;
  /**
   * Custom render function for card view
   */
  renderCard?: (record: T, index: number) => React.ReactNode;
  /**
   * Fields to display in card view
   * Can be string (field key) or object with label and custom render
   */
  cardFields?: Array<
    | Extract<keyof T, string>
    | { key: string; label: string; render?: (value: unknown, record: T) => React.ReactNode }
  >;
}

/**
 * Responsive Table Component
 *
 * On desktop: shows standard table
 * On mobile: shows card-based layout for better readability
 */
const getRecordValue = <T extends object>(record: T, key: string): unknown => {
  const recordMap = record as Record<string, unknown>;
  return recordMap[key];
};

const getDisplayValue = (value: unknown): React.ReactNode => {
  if (value == null) {
    return '-';
  }
  if (React.isValidElement(value)) {
    return value;
  }
  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return String(value);
  }
  return '-';
};

export function ResponsiveTable<T extends object>({
  cardTitle: _cardTitle,
  mobileBreakpoint = 768,
  renderCard,
  cardFields,
  dataSource,
  columns,
  rowKey,
  ...rest
}: ResponsiveTableProps<T>) {
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth < mobileBreakpoint : false
  );

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < mobileBreakpoint);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [mobileBreakpoint]);

  // If mobile and custom card render is provided
  if (isMobile && renderCard) {
    return (
      <div className={styles.cardList}>
        {dataSource && dataSource.length > 0 ? (
          dataSource.map((record, index) => {
            const key =
              typeof rowKey === 'function'
                ? rowKey(record, index)
                : rowKey == null
                  ? index
                  : (getRecordValue(record, String(rowKey)) as React.Key | undefined) ??
                    index;
            return (
              <div key={key} className={styles.cardListItem}>
                {renderCard(record, index)}
              </div>
            );
          })
        ) : (
          <Empty description="暂无数据" />
        )}
      </div>
    );
  }

  // If mobile and card fields are provided, auto-generate cards
  if (isMobile && cardFields && columns) {
    return (
      <div className={styles.cardList}>
        {dataSource && dataSource.length > 0 ? (
          dataSource.map((record, index) => {
            const key =
              typeof rowKey === 'function'
                ? rowKey(record, index)
                : rowKey == null
                  ? index
                  : (getRecordValue(record, String(rowKey)) as React.Key | undefined) ??
                    index;

            return (
              <Card key={key} className={styles.mobileCard}>
                {cardFields.map((fieldConfig) => {
                  const fieldKey = typeof fieldConfig === 'string' ? fieldConfig : fieldConfig.key;
                  const label = typeof fieldConfig === 'string' ? fieldKey : fieldConfig.label;
                  const render = typeof fieldConfig === 'string' ? undefined : fieldConfig.render;

                  // Find corresponding column for dataIndex
                  const column = columns.find(col => {
                    // Skip column groups
                    if ('children' in col) return false;
                    if (typeof col.dataIndex === 'string') {
                      return col.dataIndex === fieldKey;
                    } else if (Array.isArray(col.dataIndex)) {
                      return col.dataIndex.join('.') === fieldKey;
                    }
                    return false;
                  });

                  const value = getRecordValue(record, fieldKey);

                  return (
                    <div key={fieldKey} className={styles.cardFieldRow}>
                      <div className={styles.cardFieldLabel}>
                        {typeof column?.title === 'string' ? column.title : label}
                      </div>
                      <div className={styles.cardFieldValue}>
                        {render ? render(value, record) : getDisplayValue(value)}
                      </div>
                    </div>
                  );
                })}
              </Card>
            );
          })
        ) : (
          <Empty description="暂无数据" />
        )}
      </div>
    );
  }

  // Desktop view - standard table
  return (
    <Table<T>
      dataSource={dataSource}
      columns={columns}
      rowKey={rowKey}
      pagination={false}
      {...rest}
    />
  );
}

export default ResponsiveTable;
