import React from 'react';
import { Empty, Spin } from 'antd';
import styles from './ChartContainer.module.css';

interface ChartContainerProps {
  loading?: boolean;
  height: number;
  hasData: boolean;
  children: React.ReactNode;
}

const ChartContainer: React.FC<ChartContainerProps> = ({
  loading = false,
  height,
  hasData,
  children,
}) => {
  const containerStyle = {
    ['--chart-height' as string]: `${height}px`,
  } as React.CSSProperties;

  if (loading === true) {
    return (
      <div
        className={styles.stateContainer}
        style={containerStyle}
        role="status"
        aria-live="polite"
      >
        <Spin size="large" />
      </div>
    );
  }

  if (hasData === false) {
    return (
      <div className={styles.stateContainer} style={containerStyle}>
        <Empty description="暂无数据" />
      </div>
    );
  }

  return <>{children}</>;
};

export default React.memo(ChartContainer);
