import React from 'react';
import { Empty, Spin } from 'antd';

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
  if (loading === true) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (hasData === false) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Empty description="暂无数据" />
      </div>
    );
  }

  return <>{children}</>;
};

export default React.memo(ChartContainer);
