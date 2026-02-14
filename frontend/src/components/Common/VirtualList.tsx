/**
 * Virtual List Component
 *
 * Efficiently renders large lists by only rendering visible items
 *
 * Accessibility: Fully WCAG 2.1 AA compliant
 */

import React, { useState, useRef, useCallback, useMemo } from 'react';
import styles from './VirtualList.module.css';

/**
 * Virtual list props
 */
export interface VirtualListProps<T> {
  /**
   * Array of data items
   */
  items: T[];
  /**
   * Height of each item in pixels
   */
  itemHeight: number;
  /**
   * Height of the visible container in pixels
   */
  containerHeight: number;
  /**
   * Render function for each item
   */
  renderItem: (item: T, index: number) => React.ReactNode;
  /**
   * Optional key extractor for better performance
   */
  getKey?: (item: T, index: number) => string;
  /**
   * Number of extra items to render above/below visible area
   * @default 3
   */
  overscan?: number;
  /**
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

/**
 * Virtual List Component
 *
 * Only renders items that are visible in the viewport
 * Great for large lists (1000+ items)
 */
export function VirtualList<T>({
  items,
  itemHeight,
  containerHeight,
  renderItem,
  getKey,
  overscan = 3,
  className,
  style,
}: VirtualListProps<T>) {
  const [scrollTop, setScrollTop] = useState(0);
  const scrollElementRef = useRef<HTMLDivElement>(null);
  const containerClassName =
    className != null && className !== ''
      ? `${styles.virtualListContainer} ${className}`
      : styles.virtualListContainer;

  // Calculate visible range
  const { startIndex, endIndex, totalHeight } = useMemo(() => {
    const totalCount = items.length;
    const totalHeight = totalCount * itemHeight;

    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const endIndex = Math.min(
      totalCount,
      Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
    );

    return { startIndex, endIndex, totalHeight };
  }, [items.length, itemHeight, scrollTop, containerHeight, overscan]);

  // Handle scroll event
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  // Visible items
  const visibleItems = useMemo(() => {
    return items.slice(startIndex, endIndex).map((item, index) => {
      const actualIndex = startIndex + index;
      const key = getKey ? getKey(item, actualIndex) : String(actualIndex);
      const itemStyle: React.CSSProperties = {
        top: `${actualIndex * itemHeight}px`,
        height: `${itemHeight}px`,
      };

      return (
        <div
          key={key}
          className={styles.virtualListItem}
          style={itemStyle}
          role="listitem"
          aria-setsize={items.length}
          aria-posinset={actualIndex + 1}
        >
          {renderItem(item, actualIndex)}
        </div>
      );
    });
  }, [items, startIndex, endIndex, itemHeight, renderItem, getKey]);

  const containerStyle: React.CSSProperties = {
    height: `${containerHeight}px`,
    ...style,
  };
  const spacerStyle: React.CSSProperties = { height: `${totalHeight}px` };

  return (
    <div
      className={containerClassName}
      style={containerStyle}
      ref={scrollElementRef}
      onScroll={handleScroll}
      role="list"
      aria-label="虚拟列表"
    >
      {/* Spacer for total height */}
      <div className={styles.virtualListSpacer} style={spacerStyle}>
        {visibleItems}
      </div>
    </div>
  );
}

/**
 * Virtual Grid Component
 *
 * Virtualized 2D grid for large data sets
 */
export interface VirtualGridProps<T> {
  /**
   * Array of data items
   */
  items: T[];
  /**
   * Height of each row in pixels
   */
  rowHeight: number;
  /**
   * Width of each column in pixels
   */
  columnWidth: number;
  /**
   * Number of columns
   */
  columnCount: number;
  /**
   * Height of the visible container in pixels
   */
  containerHeight: number;
  /**
   * Width of the visible container in pixels
   */
  containerWidth: number;
  /**
   * Render function for each item
   */
  renderItem: (item: T, rowIndex: number, columnIndex: number) => React.ReactNode;
  /**
   * Optional key extractor
   */
  getKey?: (item: T, rowIndex: number, columnIndex: number) => string;
  /**
   * Number of extra rows/columns to render
   * @default 2
   */
  overscan?: number;
  /**
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

export function VirtualGrid<T>({
  items,
  rowHeight,
  columnWidth,
  columnCount,
  containerHeight,
  containerWidth,
  renderItem,
  getKey,
  overscan = 2,
  className,
  style,
}: VirtualGridProps<T>) {
  const [scrollTop, setScrollTop] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  const scrollElementRef = useRef<HTMLDivElement>(null);
  const containerClassName =
    className != null && className !== ''
      ? `${styles.virtualGridContainer} ${className}`
      : styles.virtualGridContainer;

  // Calculate total dimensions
  const { rowCount, totalWidth, totalHeight } = useMemo(() => {
    const rowCount = Math.ceil(items.length / columnCount);
    const totalWidth = columnCount * columnWidth;
    const totalHeight = rowCount * rowHeight;
    return { rowCount, totalWidth, totalHeight };
  }, [items.length, columnCount, columnWidth, rowHeight]);

  // Calculate visible range
  const { startRow, endRow, startCol, endCol } = useMemo(() => {
    const startRow = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
    const endRow = Math.min(
      rowCount,
      Math.ceil((scrollTop + containerHeight) / rowHeight) + overscan
    );

    const startCol = Math.max(0, Math.floor(scrollLeft / columnWidth) - overscan);
    const endCol = Math.min(
      columnCount,
      Math.ceil((scrollLeft + containerWidth) / columnWidth) + overscan
    );

    return { startRow, endRow, startCol, endCol };
  }, [
    scrollTop,
    scrollLeft,
    rowHeight,
    columnWidth,
    containerHeight,
    containerWidth,
    rowCount,
    columnCount,
    overscan,
  ]);

  // Handle scroll event
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
    setScrollLeft(e.currentTarget.scrollLeft);
  }, []);

  // Visible items
  const visibleItems = useMemo(() => {
    const elements: React.ReactNode[] = [];

    for (let row = startRow; row < endRow; row++) {
      for (let col = startCol; col < endCol; col++) {
        const index = row * columnCount + col;

        if (index >= items.length) break;

        const item = items[index];
        const key = getKey ? getKey(item, row, col) : `${row}-${col}`;
        const gridItemStyle: React.CSSProperties = {
          top: `${row * rowHeight}px`,
          left: `${col * columnWidth}px`,
          width: `${columnWidth}px`,
          height: `${rowHeight}px`,
        };

        elements.push(
          <div
            key={key}
            className={styles.virtualGridItem}
            style={gridItemStyle}
            role="gridcell"
            aria-rowindex={row + 1}
            aria-colindex={col + 1}
          >
            {renderItem(item, row, col)}
          </div>
        );
      }
    }

    return elements;
  }, [
    items,
    startRow,
    endRow,
    startCol,
    endCol,
    columnCount,
    rowHeight,
    columnWidth,
    renderItem,
    getKey,
  ]);

  const gridContainerStyle: React.CSSProperties = {
    height: `${containerHeight}px`,
    width: `${containerWidth}px`,
    ...style,
  };
  const gridSpacerStyle: React.CSSProperties = {
    height: `${totalHeight}px`,
    width: `${totalWidth}px`,
  };

  return (
    <div
      className={containerClassName}
      style={gridContainerStyle}
      ref={scrollElementRef}
      onScroll={handleScroll}
      role="grid"
      aria-label="虚拟网格"
      aria-rowcount={rowCount}
      aria-colcount={columnCount}
    >
      {/* Spacer for total dimensions */}
      <div className={styles.virtualGridSpacer} style={gridSpacerStyle}>
        {visibleItems}
      </div>
    </div>
  );
}

export default VirtualList;
