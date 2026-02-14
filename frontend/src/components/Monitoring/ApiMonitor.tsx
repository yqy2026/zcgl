/**
 * API监控组件
 * 显示API健康状态和实时监控信息
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, Row, Col, Statistic, Alert, Tag, Progress, Button } from 'antd';
import {
  CloudServerOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { createLogger } from '@/utils/logger';
import { apiHealthCheck } from '@/services/apiHealthCheck';
import { useArrayListData } from '@/hooks/useArrayListData';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { COLORS } from '@/styles/colorMap';
import styles from './ApiMonitor.module.css';

const componentLogger = createLogger('ApiMonitor');

interface ApiStatus {
  endpoint: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  responseTime?: number;
  error?: string;
  lastChecked: Date;
}

const HEALTHY_STATISTIC_STYLE = {
  content: { color: COLORS.success },
};

const UNHEALTHY_STATISTIC_STYLE = {
  content: { color: COLORS.error },
};

const UNKNOWN_STATISTIC_STYLE = {
  content: { color: COLORS.warning },
};

const ApiMonitor: React.FC = () => {
  const [summary, setSummary] = useState({
    total: 0,
    healthy: 0,
    unhealthy: 0,
    unknown: 0,
    healthPercentage: 0,
  });
  const [apiStatusSource, setApiStatusSource] = useState<ApiStatus[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleLoadError = useCallback((error: unknown) => {
    componentLogger.error('Failed to load API status:', error as Error);
  }, []);

  const {
    data: apiStatus,
    loading: listLoading,
    pagination,
    loadList,
    updatePagination,
  } = useArrayListData<ApiStatus, Record<string, never>>({
    items: apiStatusSource,
    initialFilters: {},
    initialPageSize: 10,
    onError: handleLoadError,
  });

  const refreshStatus = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // Check all critical endpoints
      await apiHealthCheck.checkCriticalEndpoints();

      // Get results and convert to array
      const statusArray = Array.from(apiHealthCheck.getResults().values());
      setApiStatusSource(statusArray);

      // Calculate summary
      const healthSummary = apiHealthCheck.getHealthSummary();
      setSummary(healthSummary);
    } catch (error) {
      handleLoadError(error);
    } finally {
      setIsRefreshing(false);
    }
  }, [handleLoadError]);

  useEffect(() => {
    void refreshStatus();
    // 每30秒自动刷新一次
    const interval = setInterval(() => {
      void refreshStatus();
    }, 30000);
    return () => clearInterval(interval);
  }, [refreshStatus]);

  useEffect(() => {
    void loadList({ page: 1 });
  }, [apiStatusSource, loadList]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'green';
      case 'unhealthy':
        return 'red';
      case 'unknown':
        return 'orange';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleOutlined className={styles.statusIconHealthy} />;
      case 'unhealthy':
        return <ExclamationCircleOutlined className={styles.statusIconUnhealthy} />;
      case 'unknown':
        return <CloudServerOutlined className={styles.statusIconUnknown} />;
      default:
        return <CloudServerOutlined />;
    }
  };

  const formatResponseTime = (time?: number) => {
    if (time == null) return '-';
    if (time < 1000) return `${time}ms`;
    return `${(time / 1000).toFixed(2)}s`;
  };

  const getResponseTimeClass = (time?: number) => {
    if ((time ?? 0) > 3000) {
      return styles.responseTimeSlow;
    }
    if ((time ?? 0) > 1000) {
      return styles.responseTimeMedium;
    }
    return styles.responseTimeFast;
  };

  const columns = [
    {
      title: '端点',
      dataIndex: 'endpoint',
      key: 'endpoint',
      width: 200,
      render: (text: string) => <code className={styles.endpointCode}>{text}</code>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: '响应时间',
      dataIndex: 'responseTime',
      key: 'responseTime',
      width: 120,
      render: (time?: number) => (
        <span className={getResponseTimeClass(time)}>
          {formatResponseTime(time)}
        </span>
      ),
    },
    {
      title: '错误信息',
      dataIndex: 'error',
      key: 'error',
      ellipsis: true,
      render: (error?: string) =>
        error != null && error !== '' ? <span className={styles.errorText}>{error}</span> : '-',
    },
    {
      title: '最后检查',
      dataIndex: 'lastChecked',
      key: 'lastChecked',
      width: 150,
      render: (date: Date) => new Date(date).toLocaleTimeString(),
    },
  ];

  const getHealthStatusColor = (percentage: number) => {
    if (percentage >= 80) return COLORS.success;
    if (percentage >= 60) return COLORS.warning;
    return COLORS.error;
  };

  const loading = useMemo(() => isRefreshing || listLoading, [isRefreshing, listLoading]);

  return (
    <div className={styles.monitorContainer}>
      <div className={styles.monitorHeader}>
        <h2>API健康监控</h2>
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          loading={loading}
          onClick={() => void refreshStatus()}
        >
          刷新状态
        </Button>
      </div>

      {/* 总体状态概览 */}
      <Row gutter={16} className={styles.overviewRow}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总体健康度"
              value={summary.healthPercentage}
              precision={1}
              suffix="%"
              styles={{ content: { color: getHealthStatusColor(summary.healthPercentage) } }}
              prefix={<CloudServerOutlined />}
            />
            <Progress
              percent={summary.healthPercentage}
              strokeColor={getHealthStatusColor(summary.healthPercentage)}
              showInfo={false}
              size="small"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="健康端点"
              value={summary.healthy}
              styles={HEALTHY_STATISTIC_STYLE}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="异常端点"
              value={summary.unhealthy}
              styles={UNHEALTHY_STATISTIC_STYLE}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="未知状态"
              value={summary.unknown}
              styles={UNKNOWN_STATISTIC_STYLE}
              prefix={<CloudServerOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 健康状态警告 */}
      {summary.healthPercentage < 80 && (
        <Alert
          title="API健康状况需要关注"
          description={`当前API健康度为${summary.healthPercentage.toFixed(1)}%，低于80%的健康阈值。建议检查异常端点并采取相应措施。`}
          type="warning"
          showIcon
          className={styles.alertSpacing}
        />
      )}

      {summary.healthPercentage < 60 && (
        <Alert
          title="API健康状况严重"
          description={`当前API健康度仅为${summary.healthPercentage.toFixed(1)}%，系统可能存在严重问题。建议立即检查所有API端点状态。`}
          type="error"
          showIcon
          className={styles.alertSpacing}
        />
      )}

      {/* 详细状态表格 */}
      <Card title="端点详细状态" size="small">
        <TableWithPagination
          columns={columns}
          dataSource={apiStatus}
          rowKey="endpoint"
          loading={loading}
          paginationState={pagination}
          onPageChange={updatePagination}
          paginationProps={{
            showTotal: (total: number) => `共 ${total} 个端点`,
          }}
          size="small"
        />
      </Card>

      {/* 监控说明 */}
      <Card title="监控说明" size="small" className={styles.guideCard}>
        <div className={styles.guideText}>
          <p>
            <strong>监控范围：</strong>系统关键API端点
          </p>
          <p>
            <strong>检查频率：</strong>每30秒自动刷新一次
          </p>
          <p>
            <strong>健康标准：</strong>
          </p>
          <ul className={styles.guideList}>
            <li>
              <span className={styles.statusHealthy}>绿色</span>：响应正常（2xx状态码，响应时间&lt;3秒）
            </li>
            <li>
              <span className={styles.statusUnhealthy}>红色</span>：端点不可用（404、500等错误）
            </li>
            <li>
              <span className={styles.statusUnknown}>橙色</span>：状态未知（检查失败或超时）
            </li>
          </ul>
          <p>
            <strong>建议：</strong>当健康度低于80%时需要关注，低于60%时需要立即处理。
          </p>
        </div>
      </Card>
    </div>
  );
};

export default ApiMonitor;
