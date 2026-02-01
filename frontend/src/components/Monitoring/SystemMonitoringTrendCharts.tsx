import React, { useMemo } from 'react';
import { Card, Row, Col } from 'antd';
import { Line } from '@ant-design/plots';

import {
  type ApplicationMetrics,
  type ChartDataPoint,
  type SystemMetrics,
} from './systemMonitoringTypes';

interface SystemMonitoringTrendChartsProps {
  systemMetrics: SystemMetrics[];
  applicationMetrics: ApplicationMetrics[];
}

const SystemMonitoringTrendCharts: React.FC<SystemMonitoringTrendChartsProps> = ({
  systemMetrics,
  applicationMetrics,
}) => {
  const cpuChartData = useMemo(
    () =>
      systemMetrics.map(item => ({
        time: new Date(item.timestamp).toLocaleTimeString(),
        value: item.cpu_percent,
      })),
    [systemMetrics]
  );

  const cpuChartConfig = useMemo(
    () => ({
      data: cpuChartData,
      xField: 'time',
      yField: 'value',
      smooth: true,
      color: '#1890ff',
      annotations: [
        {
          type: 'line',
          start: ['min', 80],
          end: ['max', 80],
          style: { stroke: '#ff4d4f', lineDash: [2, 2] },
        },
      ],
      tooltip: {
        formatter: (datum: ChartDataPoint) => ({
          name: 'CPU使用率',
          value: `${datum.value}%`,
        }),
      },
    }),
    [cpuChartData]
  );

  const memoryChartData = useMemo(
    () =>
      systemMetrics.map(item => ({
        time: new Date(item.timestamp).toLocaleTimeString(),
        value: item.memory_percent,
      })),
    [systemMetrics]
  );

  const memoryChartConfig = useMemo(
    () => ({
      data: memoryChartData,
      xField: 'time',
      yField: 'value',
      smooth: true,
      color: '#52c41a',
      annotations: [
        {
          type: 'line',
          start: ['min', 85],
          end: ['max', 85],
          style: { stroke: '#ff4d4f', lineDash: [2, 2] },
        },
      ],
      tooltip: {
        formatter: (datum: ChartDataPoint) => ({
          name: '内存使用率',
          value: `${datum.value}%`,
        }),
      },
    }),
    [memoryChartData]
  );

  const responseTimeChartData = useMemo(
    () =>
      applicationMetrics.map(item => ({
        time: new Date(item.timestamp).toLocaleTimeString(),
        value: item.average_response_time,
      })),
    [applicationMetrics]
  );

  const responseTimeChartConfig = useMemo(
    () => ({
      data: responseTimeChartData,
      xField: 'time',
      yField: 'value',
      smooth: true,
      color: '#faad14',
      annotations: [
        {
          type: 'line',
          start: ['min', 1000],
          end: ['max', 1000],
          style: { stroke: '#ff4d4f', lineDash: [2, 2] },
        },
      ],
      tooltip: {
        formatter: (datum: ChartDataPoint) => ({
          name: '响应时间',
          value: `${datum.value}ms`,
        }),
      },
    }),
    [responseTimeChartData]
  );

  return (
    <Row gutter={[16, 16]}>
      <Col span={8}>
        <Card title="CPU使用率趋势" size="small">
          <Line {...cpuChartConfig} height={200} />
        </Card>
      </Col>
      <Col span={8}>
        <Card title="内存使用率趋势" size="small">
          <Line {...memoryChartConfig} height={200} />
        </Card>
      </Col>
      <Col span={8}>
        <Card title="响应时间趋势" size="small">
          <Line {...responseTimeChartConfig} height={200} />
        </Card>
      </Col>
    </Row>
  );
};

export default React.memo(SystemMonitoringTrendCharts);
