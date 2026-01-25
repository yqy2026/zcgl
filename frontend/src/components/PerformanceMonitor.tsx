import React, { useEffect, useState, useCallback } from 'react';
import { Card, Statistic, Progress, Alert, Button, Modal, Table, Tag, Row, Col } from 'antd';
import {
  DashboardOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';

interface PerformanceMetrics {
  fcp?: number;
  lcp?: number;
  fid?: number;
  cls?: number;
  pageLoadTime?: number;
  apiResponseTime?: number;
  componentLoadTime?: number;
  memoryUsage?: number;
  connectionType?: string;
  effectiveType?: string;
  downlink?: number;
  rtt?: number;
}

interface ComponentMetrics {
  name: string;
  loadTime: number;
  status: 'success' | 'failed' | 'loading';
  retries: number;
}

const PerformanceMonitor: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({});
  const [componentMetrics, setComponentMetrics] = useState<ComponentMetrics[]>([]);
  const [isVisible, setIsVisible] = useState(false);
  const [isMonitoring, setIsMonitoring] = useState(false);

  const collectWebVitals = useCallback(() => {
    const fcpEntry = performance.getEntriesByName('first-contentful-paint')[0] as PerformanceEntry;
    if (fcpEntry != null) {
      setMetrics(prev => ({ ...prev, fcp: fcpEntry.startTime }));
    }

    if ('PerformanceObserver' in window) {
      const lcpObserver = new PerformanceObserver(list => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1] as PerformanceEntry;
        setMetrics(prev => ({ ...prev, lcp: lastEntry.startTime }));
      });
      lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });

      const fidObserver = new PerformanceObserver(list => {
        const entries = list.getEntries();
        entries.forEach(entry => {
          const inputEntry = entry as PerformanceEventTiming;
          setMetrics(prev => ({ ...prev, fid: inputEntry.processingStart - inputEntry.startTime }));
        });
      });
      fidObserver.observe({ entryTypes: ['first-input'] });

      let clsValue = 0;
      const clsObserver = new PerformanceObserver(list => {
        const entries = list.getEntries();
        entries.forEach(entry => {
          const layoutShiftEntry = entry as PerformanceEntry & {
            value: number;
            hadRecentInput: boolean;
          };
          if (!layoutShiftEntry.hadRecentInput) {
            clsValue += layoutShiftEntry.value;
          }
        });
        setMetrics(prev => ({ ...prev, cls: clsValue }));
      });
      clsObserver.observe({ entryTypes: ['layout-shift'] });
    }
  }, []);

  interface NetworkConnection {
    type: string;
    effectiveType: string;
    downlink: number;
    rtt: number;
  }

  interface MemoryInfo {
    usedJSHeapSize: number;
    jsHeapSizeLimit: number;
  }

type NavigatorWithConnection = Navigator & { connection?: NetworkConnection };
type PerformanceWithMemory = Performance & { memory?: MemoryInfo };

  const collectNetworkInfo = useCallback(() => {
    if ('connection' in navigator) {
      const connection = (navigator as NavigatorWithConnection).connection;
      if (connection !== undefined && connection !== null) {
        setMetrics(prev => ({
          ...prev,
          connectionType: connection.type,
          effectiveType: connection.effectiveType,
          downlink: connection.downlink,
          rtt: connection.rtt,
        }));
      }
    }
  }, []);

  const collectMemoryInfo = useCallback(() => {
    if ('memory' in performance) {
      const memory = (performance as PerformanceWithMemory).memory;
      if (memory != null && memory.jsHeapSizeLimit > 0) {
        setMetrics(prev => ({
          ...prev,
          memoryUsage: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100,
        }));
      }
    }
  }, []);

  const collectComponentMetrics = useCallback(() => {
    const mockComponentMetrics: ComponentMetrics[] = [
      { name: 'DashboardPage', loadTime: 1200, status: 'success', retries: 0 },
      { name: 'AssetListPage', loadTime: 800, status: 'success', retries: 1 },
      { name: 'AssetDetailPage', loadTime: 600, status: 'success', retries: 0 },
    ];
    setComponentMetrics(mockComponentMetrics);
  }, []);

  const startMonitoring = useCallback(() => {
    setIsMonitoring(true);
    collectWebVitals();
    collectNetworkInfo();
    collectMemoryInfo();
    collectComponentMetrics();

    const interval = setInterval(() => {
      collectMemoryInfo();
      collectComponentMetrics();
    }, 5000);

    return () => clearInterval(interval);
  }, [collectWebVitals, collectNetworkInfo, collectMemoryInfo, collectComponentMetrics]);

  useEffect(() => {
    if (isMonitoring !== undefined && isMonitoring !== null) {
      const cleanup = startMonitoring();
      return cleanup;
    }
  }, [isMonitoring, startMonitoring]);

  const getPerformanceScore = (metric: number, thresholds: [number, number]) => {
    if (metric <= thresholds[0]) return { score: 'good', color: 'green' };
    if (metric <= thresholds[1]) return { score: 'needs-improvement', color: 'orange' };
    return { score: 'poor', color: 'red' };
  };

  const getPerformanceAdvice = () => {
    const advice = [];

    if (metrics.lcp != null && metrics.lcp > 2500) {
      advice.push('LCP过高，建议优化图片加载和关键资源');
    }

    if (metrics.fid != null && metrics.fid > 100) {
      advice.push('FID过高，建议减少JavaScript执行时间');
    }

    if (metrics.cls != null && metrics.cls > 0.1) {
      advice.push('CLS过高，建议为图片和广告预留空间');
    }

    if (metrics.memoryUsage != null && metrics.memoryUsage > 80) {
      advice.push('内存使用率过高，建议检查内存泄漏');
    }

    return advice;
  };

  const componentColumns = [
    {
      title: '组件名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '加载时间',
      dataIndex: 'loadTime',
      key: 'loadTime',
      render: (time: number) => `${time}ms`,
      sorter: (a: ComponentMetrics, b: ComponentMetrics) => a.loadTime - b.loadTime,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap = {
          success: 'green',
          failed: 'red',
          loading: 'blue',
        };
        return <Tag color={colorMap[status as keyof typeof colorMap]}>{status}</Tag>;
      },
    },
    {
      title: '重试次数',
      dataIndex: 'retries',
      key: 'retries',
    },
  ];

  return (
    <>
      <Button
        type="primary"
        icon={<ThunderboltOutlined />}
        onClick={() => setIsVisible(true)}
        style={{ position: 'fixed', bottom: 20, right: 20, zIndex: 1000 }}
      >
        性能监控
      </Button>

      <Modal
        title={
          <span>
            <DashboardOutlined /> 性能监控面板
          </span>
        }
        open={isVisible}
        onCancel={() => setIsVisible(false)}
        footer={null}
        width={800}
      >
        {!isMonitoring && (
          <Alert
            message="性能监控未启动"
            description="点击开始监控按钮开始收集性能数据"
            type="info"
            action={
              <Button type="primary" onClick={startMonitoring}>
                开始监控
              </Button>
            }
          />
        )}

        <div style={{ marginTop: 16 }}>
          <Card title="Web Vitals" size="small">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="FCP"
                  value={metrics.fcp ? metrics.fcp.toFixed(0) : '-'}
                  suffix="ms"
                  valueStyle={{ color: getPerformanceScore(metrics.fcp || 0, [1800, 3000]).color }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="LCP"
                  value={metrics.lcp ? metrics.lcp.toFixed(0) : '-'}
                  suffix="ms"
                  valueStyle={{ color: getPerformanceScore(metrics.lcp || 0, [2500, 4000]).color }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="FID"
                  value={metrics.fid ? metrics.fid.toFixed(0) : '-'}
                  suffix="ms"
                  valueStyle={{ color: getPerformanceScore(metrics.fid || 0, [100, 300]).color }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="CLS"
                  value={metrics.cls ? metrics.cls.toFixed(3) : '-'}
                  valueStyle={{ color: getPerformanceScore(metrics.cls || 0, [0.1, 0.25]).color }}
                />
              </Col>
            </Row>
          </Card>

          <Card title="系统资源" size="small" style={{ marginTop: 16 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic title="内存使用率" value={metrics.memoryUsage?.toFixed(1)} suffix="%" />
                {metrics.memoryUsage != null && (
                  <Progress percent={metrics.memoryUsage} size="small" />
                )}
              </Col>
              <Col span={8}>
                <Statistic title="网络类型" value={metrics.connectionType || '-'} />
              </Col>
              <Col span={8}>
                <Statistic title="下载速度" value={metrics.downlink || '-'} suffix="Mbps" />
              </Col>
            </Row>
          </Card>

          <Card title="组件性能" size="small" style={{ marginTop: 16 }}>
            <Table
              columns={componentColumns}
              dataSource={componentMetrics}
              pagination={false}
              size="small"
            />
          </Card>

          <Card title="性能建议" size="small" style={{ marginTop: 16 }}>
            {getPerformanceAdvice().length > 0 ? (
              getPerformanceAdvice().map((advice, index) => (
                <Alert
                  key={index}
                  message={advice}
                  type="warning"
                  showIcon
                  icon={<WarningOutlined />}
                  style={{ marginBottom: 8 }}
                />
              ))
            ) : (
              <Alert message="性能表现良好" type="success" showIcon />
            )}
          </Card>

          <Card title="操作" size="small" style={{ marginTop: 16 }}>
            <Button
              icon={<ClockCircleOutlined />}
              onClick={() => {
                collectWebVitals();
                collectNetworkInfo();
                collectMemoryInfo();
                collectComponentMetrics();
              }}
            >
              刷新数据
            </Button>
          </Card>
        </div>
      </Modal>
    </>
  );
};

export default PerformanceMonitor;
