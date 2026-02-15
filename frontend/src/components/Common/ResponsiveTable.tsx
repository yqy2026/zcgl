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
  cardTitle?: React.ReactNode;
  /**
   * Mobile breakpoint in pixels
   * @default 768
   */
  mobileBreakpoint?: number;
  /**
   * Accessible label for mobile card view
   * @default 移动端卡片列表
   */
  mobileListAriaLabel?: string;
  /**
   * Empty description for mobile card view
   * @default 暂无数据
   */
  emptyDescription?: React.ReactNode;
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
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return '-';
};

export function ResponsiveTable<T extends object>({
  cardTitle,
  mobileBreakpoint = 768,
  mobileListAriaLabel = '移动端卡片列表',
  emptyDescription = '暂无数据',
  renderCard,
  cardFields,
  dataSource,
  columns,
  rowKey,
  className,
  ...rest
}: ResponsiveTableProps<T>) {
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth < mobileBreakpoint : false
  );
  const totalCount = dataSource?.length ?? 0;
  const hasData = Array.isArray(dataSource) && dataSource.length > 0;
  const mobileSectionClassName = [styles.mobileSection, className]
    .filter((currentClassName): currentClassName is string => {
      return currentClassName != null && currentClassName !== '';
    })
    .join(' ');
  const showCardTitle = cardTitle != null;

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < mobileBreakpoint);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [mobileBreakpoint]);

  const getRecordKey = (record: T, index: number): React.Key => {
    if (typeof rowKey === 'function') {
      return rowKey(record, index);
    }
    if (rowKey == null) {
      return index;
    }
    return (getRecordValue(record, String(rowKey)) as React.Key | undefined) ?? index;
  };

  const renderMobileHeader = () => {
    if (showCardTitle !== true) {
      return null;
    }
    return (
      <div className={styles.mobileHeader}>
        <span className={styles.mobileTitle}>{cardTitle}</span>
        <span className={styles.mobileMeta}>共 {totalCount} 条</span>
      </div>
    );
  };

  const renderEmptyState = () => (
    <div className={styles.emptyState}>
      <Empty description={emptyDescription} />
    </div>
  );

  // If mobile and custom card render is provided
  if (isMobile === true && renderCard != null) {
    return (
      <section className={mobileSectionClassName} aria-label={mobileListAriaLabel}>
        {renderMobileHeader()}
        {hasData ? (
          <div className={styles.cardList} role="list">
            {dataSource.map((record, index) => {
              const key = getRecordKey(record, index);
              return (
                <div key={key} className={styles.cardListItem} role="listitem">
                  {renderCard(record, index)}
                </div>
              );
            })}
          </div>
        ) : (
          renderEmptyState()
        )}
      </section>
    );
  }

  // If mobile and card fields are provided, auto-generate cards
  if (isMobile === true && cardFields != null && columns != null) {
    return (
      <section className={mobileSectionClassName} aria-label={mobileListAriaLabel}>
        {renderMobileHeader()}
        {hasData ? (
          <div className={styles.cardList} role="list">
            {dataSource.map((record, index) => {
              const key = getRecordKey(record, index);

              return (
                <Card key={key} className={styles.mobileCard} role="listitem">
                  {cardFields.map(fieldConfig => {
                    const fieldKey =
                      typeof fieldConfig === 'string' ? fieldConfig : fieldConfig.key;
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
                          {render != null ? render(value, record) : getDisplayValue(value)}
                        </div>
                      </div>
                    );
                  })}
                </Card>
              );
            })}
          </div>
        ) : (
          renderEmptyState()
        )}
      </section>
    );
  }

  // Desktop view - standard table
  return (
    <Table<T>
      dataSource={dataSource}
      columns={columns}
      rowKey={rowKey}
      pagination={false}
      className={className}
      {...rest}
    />
  );
}

export default ResponsiveTable;
