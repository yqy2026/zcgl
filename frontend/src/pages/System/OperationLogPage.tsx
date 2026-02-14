import React, { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Card,
  Button,
  Space,
  Select,
  DatePicker,
  Input,
  Tag,
  Tooltip,
  Row,
  Col,
  Statistic,
  Descriptions,
  Drawer,
  Typography,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  ReloadOutlined,
  SearchOutlined,
  EyeOutlined,
  UserOutlined,
  SettingOutlined,
  EditOutlined,
  DeleteOutlined,
  LoginOutlined,
  LogoutOutlined,
  SecurityScanOutlined,
  FileTextOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { ListToolbar } from '@/components/Common/ListToolbar';
import PageContainer from '@/components/Common/PageContainer';
import { useQuery } from '@tanstack/react-query';
import { logService, type OperationLog, type LogStatistics } from '@/services/systemService';
import styles from './OperationLogPage.module.css';

const { Text } = Typography;
const { RangePicker } = DatePicker;
const { Search } = Input;
const { Option } = Select;

type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';
type ResponseTimeTone = 'neutral' | 'success' | 'warning' | 'error';

interface ActionMeta {
  value: string;
  label: string;
  tone: Tone;
  icon: ReactNode;
}

interface ModuleMeta {
  value: string;
  label: string;
  tone: Tone;
}

interface StatusFilterOption {
  value: string;
  label: string;
}

const ACTION_OPTIONS: ActionMeta[] = [
  { value: 'create', label: '创建', tone: 'success', icon: <PlusOutlined /> },
  { value: 'update', label: '更新', tone: 'primary', icon: <EditOutlined /> },
  { value: 'delete', label: '删除', tone: 'error', icon: <DeleteOutlined /> },
  { value: 'view', label: '查看', tone: 'primary', icon: <EyeOutlined /> },
  { value: 'login', label: '登录', tone: 'success', icon: <LoginOutlined /> },
  { value: 'logout', label: '登出', tone: 'warning', icon: <LogoutOutlined /> },
  { value: 'export', label: '导出', tone: 'warning', icon: <FileTextOutlined /> },
  { value: 'import', label: '导入', tone: 'primary', icon: <FileTextOutlined /> },
  { value: 'security', label: '安全操作', tone: 'error', icon: <SecurityScanOutlined /> },
];

const ACTION_META_MAP = ACTION_OPTIONS.reduce<Record<string, ActionMeta>>((accumulator, option) => {
  accumulator[option.value] = option;
  return accumulator;
}, {});

const MODULE_OPTIONS: ModuleMeta[] = [
  { value: 'dashboard', label: '数据看板', tone: 'primary' },
  { value: 'assets', label: '资产管理', tone: 'success' },
  { value: 'rental', label: '租赁管理', tone: 'warning' },
  { value: 'ownership', label: '权属方管理', tone: 'primary' },
  { value: 'project', label: '项目管理', tone: 'success' },
  { value: 'system', label: '系统管理', tone: 'error' },
  { value: 'auth', label: '认证授权', tone: 'warning' },
];

const MODULE_META_MAP = MODULE_OPTIONS.reduce<Record<string, ModuleMeta>>((accumulator, option) => {
  accumulator[option.value] = option;
  return accumulator;
}, {});

const STATUS_OPTIONS: StatusFilterOption[] = [
  { value: 'success', label: '成功' },
  { value: 'error', label: '失败' },
  { value: 'warning', label: '警告' },
];

const REQUEST_METHOD_TONE_MAP: Record<string, Tone> = {
  GET: 'success',
  POST: 'primary',
  PUT: 'warning',
  PATCH: 'warning',
  DELETE: 'error',
};

const TONE_CLASS_MAP: Record<Tone, string> = {
  primary: styles.tonePrimary,
  success: styles.toneSuccess,
  warning: styles.toneWarning,
  error: styles.toneError,
  neutral: styles.toneNeutral,
};

const getToneClassName = (tone: Tone): string => {
  return TONE_CLASS_MAP[tone];
};

const getResponseTimeTone = (time?: number | null): ResponseTimeTone => {
  if (typeof time !== 'number') {
    return 'neutral';
  }
  if (time > 1000) {
    return 'error';
  }
  if (time > 500) {
    return 'warning';
  }
  return 'success';
};

const getResponseTimeLabel = (time?: number | null): string => {
  if (typeof time !== 'number') {
    return '';
  }
  if (time > 1000) {
    return '慢';
  }
  if (time > 500) {
    return '中';
  }
  return '快';
};

const getStatusMeta = (status?: number | null): { label: string; tone: Tone } => {
  if (status == null) {
    return { label: '未知', tone: 'neutral' };
  }
  if (status >= 200 && status < 300) {
    return { label: '成功', tone: 'success' };
  }
  if (status >= 400 && status < 500) {
    return { label: '客户端错误', tone: 'warning' };
  }
  if (status >= 500) {
    return { label: '服务器错误', tone: 'error' };
  }
  return { label: '未知', tone: 'neutral' };
};

const OperationLogPage: React.FC = () => {
  interface LogFilters {
    searchText: string;
    module: string;
    action: string;
    status: string;
    dateRange: [dayjs.Dayjs, dayjs.Dayjs] | null;
  }

  interface LogListQueryResult {
    items: OperationLog[];
    total: number;
    pages?: number;
  }

  const [filters, setFilters] = useState<LogFilters>({
    searchText: '',
    module: '',
    action: '',
    status: '',
    dateRange: null,
  });
  const [paginationState, setPaginationState] = useState({
    current: 1,
    pageSize: 20,
  });
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<OperationLog | null>(null);

  type LogJsonValue = string | Record<string, unknown> | unknown[] | null | undefined;

  const parseJsonValue = (value: LogJsonValue): LogJsonValue => {
    if (typeof value !== 'string') {
      return value;
    }
    const trimmed = value.trim();
    if (trimmed === '') {
      return value;
    }
    try {
      const parsed = JSON.parse(trimmed) as unknown;
      if (parsed == null) {
        return value;
      }
      if (Array.isArray(parsed) || typeof parsed === 'object') {
        return parsed as Record<string, unknown> | unknown[];
      }
      return value;
    } catch {
      return value;
    }
  };

  const formatJson = (value: unknown) => {
    if (value == null) {
      return '-';
    }
    if (typeof value === 'string') {
      const parsed = parseJsonValue(value);
      if (parsed !== value) {
        return JSON.stringify(parsed, null, 2);
      }
      return value;
    }
    return JSON.stringify(value, null, 2);
  };

  const renderJsonBlock = (value: unknown) => {
    const formatted = formatJson(value);
    if (formatted === '-') {
      return '-';
    }
    return <pre className={styles.jsonBlock}>{formatted}</pre>;
  };

  const fetchLogs = useCallback(async (): Promise<LogListQueryResult> => {
    const trimmedSearch = filters.searchText.trim();
    const params = {
      page: paginationState.current,
      page_size: paginationState.pageSize,
      module: filters.module === '' ? undefined : filters.module,
      action: filters.action === '' ? undefined : filters.action,
      start_date:
        filters.dateRange != null && filters.dateRange[0] != null
          ? filters.dateRange[0].format('YYYY-MM-DD')
          : undefined,
      end_date:
        filters.dateRange != null && filters.dateRange[1] != null
          ? filters.dateRange[1].format('YYYY-MM-DD')
          : undefined,
      search: trimmedSearch === '' ? undefined : trimmedSearch,
      response_status: filters.status === '' ? undefined : filters.status,
    };

    const result = await logService.getLogs(params);
    const items = Array.isArray(result?.items) ? result.items : [];
    const normalizedItems = items.map(item => ({
      ...item,
      request_params: parseJsonValue(item.request_params),
      request_body: parseJsonValue(item.request_body),
      details: parseJsonValue(item.details),
      user_name: item.user_name ?? item.username ?? '-',
      module_name: item.module_name ?? item.module,
      action_name: item.action_name ?? item.action,
    }));

    return {
      items: normalizedItems,
      total: result?.total ?? normalizedItems.length,
      pages: result?.pages,
    };
  }, [
    filters.action,
    filters.dateRange,
    filters.module,
    filters.searchText,
    filters.status,
    paginationState.current,
    paginationState.pageSize,
  ]);

  const {
    data: logsResponse,
    error: logsError,
    isLoading: isLogsLoading,
    isFetching: isLogsFetching,
    refetch: refetchLogs,
  } = useQuery<LogListQueryResult>({
    queryKey: ['operation-log-list', paginationState.current, paginationState.pageSize, filters],
    queryFn: fetchLogs,
    retry: 1,
  });

  useEffect(() => {
    if (logsError != null) {
      MessageManager.error('加载操作日志失败');
    }
  }, [logsError]);

  const logs = logsResponse?.items ?? [];
  const loading = isLogsLoading || isLogsFetching;
  const pagination = useMemo(
    () => ({
      current: paginationState.current,
      pageSize: paginationState.pageSize,
      total: logsResponse?.total ?? 0,
    }),
    [logsResponse?.total, paginationState.current, paginationState.pageSize]
  );
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.module !== '') {
      count += 1;
    }
    if (filters.action !== '') {
      count += 1;
    }
    if (filters.status !== '') {
      count += 1;
    }
    if (filters.dateRange != null) {
      count += 1;
    }
    if (filters.searchText.trim() !== '') {
      count += 1;
    }
    return count;
  }, [filters.action, filters.dateRange, filters.module, filters.searchText, filters.status]);

  const refreshLogs = useCallback(() => {
    void refetchLogs();
  }, [refetchLogs]);

  const updateFilters = useCallback((nextFilters: Partial<LogFilters>) => {
    setFilters(prev => ({ ...prev, ...nextFilters }));
    setPaginationState(prev => ({ ...prev, current: 1 }));
  }, []);

  const handleSearch = useCallback(
    (value: string) => {
      updateFilters({ searchText: value });
    },
    [updateFilters]
  );

  const handleModuleChange = useCallback(
    (value: string | undefined) => {
      updateFilters({ module: value ?? '' });
    },
    [updateFilters]
  );

  const handleActionChange = useCallback(
    (value: string | undefined) => {
      updateFilters({ action: value ?? '' });
    },
    [updateFilters]
  );

  const handleStatusChange = useCallback(
    (value: string | undefined) => {
      updateFilters({ status: value ?? '' });
    },
    [updateFilters]
  );

  const handleDateRangeChange = useCallback(
    (dates: [dayjs.Dayjs, dayjs.Dayjs] | null) => {
      updateFilters({ dateRange: dates });
    },
    [updateFilters]
  );

  const handlePageChange = useCallback((next: { current?: number; pageSize?: number }) => {
    setPaginationState(prev => ({
      current: next.current ?? prev.current,
      pageSize: next.pageSize ?? prev.pageSize,
    }));
  }, []);

  const statistics = useMemo<LogStatistics>(() => {
    const responseTimes = logs
      .map(log => log.response_time)
      .filter((time): time is number => typeof time === 'number');
    const avgResponseTime =
      responseTimes.length > 0
        ? Math.round(responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length)
        : 0;

    return {
      total: pagination.total,
      today: logs.filter(log => dayjs(log.created_at).isSame(dayjs(), 'day')).length,
      this_week: logs.filter(log => dayjs(log.created_at).isSame(dayjs(), 'week')).length,
      this_month: logs.filter(log => dayjs(log.created_at).isSame(dayjs(), 'month')).length,
      by_action: {},
      by_module: {},
      error_count: logs.filter(log => (log.response_status ?? 0) >= 400).length,
      avg_response_time: avgResponseTime,
    };
  }, [logs, pagination.total]);

  const handleViewDetail = (log: OperationLog) => {
    setSelectedLog(log);
    setDetailDrawerVisible(true);
  };

  const getActionTag = (action: string) => {
    const actionConfig = ACTION_META_MAP[action];
    const label = actionConfig?.label ?? (action.trim() === '' ? '未知操作' : action);
    const toneClassName = getToneClassName(actionConfig?.tone ?? 'neutral');
    const icon = actionConfig?.icon ?? <SettingOutlined />;
    return (
      <Tag className={`${styles.statusTag} ${styles.actionTag} ${toneClassName}`} icon={icon}>
        {label}
      </Tag>
    );
  };

  const getModuleTag = (module?: string | null, moduleName?: string | null) => {
    const moduleKey = module == null ? '' : module;
    const moduleMeta = MODULE_META_MAP[moduleKey];
    const derivedLabel = (() => {
      if (moduleName != null && moduleName.trim() !== '') {
        return moduleName;
      }
      if (moduleMeta != null) {
        return moduleMeta.label;
      }
      if (moduleKey !== '') {
        return moduleKey;
      }
      return '-';
    })();

    return (
      <Tag
        className={`${styles.statusTag} ${styles.moduleTag} ${getToneClassName(moduleMeta?.tone ?? 'neutral')}`}
      >
        {derivedLabel}
      </Tag>
    );
  };

  const getStatusTag = (status?: number | null) => {
    const meta = getStatusMeta(status);
    const statusCodeText = typeof status === 'number' ? ` ${status}` : '';
    return (
      <Tag className={`${styles.statusTag} ${getToneClassName(meta.tone)}`}>
        {meta.label}
        {statusCodeText}
      </Tag>
    );
  };

  const getRequestMethodTag = (requestMethod?: string | null) => {
    if (requestMethod == null || requestMethod.trim() === '') {
      return <Text type="secondary">-</Text>;
    }
    const normalizedMethod = requestMethod.toUpperCase();
    const methodTone = REQUEST_METHOD_TONE_MAP[normalizedMethod] ?? 'neutral';
    return (
      <Tag className={`${styles.statusTag} ${styles.methodTag} ${getToneClassName(methodTone)}`}>
        {normalizedMethod}
      </Tag>
    );
  };

  const columns: ColumnsType<OperationLog> = [
    {
      title: '操作时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: date => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '用户信息',
      key: 'user_info',
      width: 150,
      render: (_, record) => {
        const accountName =
          record.username != null && record.username.trim() !== '' ? record.username : '-';
        const displayName =
          record.user_name != null && record.user_name.trim() !== '' ? record.user_name : accountName;
        return (
          <Space direction="vertical" size={2} className={styles.userCell}>
            <div className={styles.primaryText}>{displayName}</div>
            <div className={styles.secondaryText}>
              {accountName === '-' ? '-' : `账号 @${accountName}`}
            </div>
          </Space>
        );
      },
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: action => getActionTag(typeof action === 'string' ? action : ''),
    },
    {
      title: '模块',
      key: 'module',
      width: 120,
      render: (_, record) => getModuleTag(record.module, record.module_name),
    },
    {
      title: '资源',
      key: 'resource',
      width: 150,
      render: (_, record) => (
        <div className={styles.resourceCell}>
          <div className={styles.primaryText}>{record.resource_name ?? '-'}</div>
          <div className={styles.secondaryText}>
            {record.resource_type != null && record.resource_type.trim() !== ''
              ? record.resource_type
              : '-'}
          </div>
        </div>
      ),
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 120,
      render: ip => {
        const ipAddress = typeof ip === 'string' && ip.trim() !== '' ? ip : '-';
        return (
          <Tooltip title={ipAddress}>
            <span className={styles.ipValue}>{ipAddress}</span>
          </Tooltip>
        );
      },
    },
    {
      title: '响应状态',
      dataIndex: 'response_status',
      key: 'response_status',
      width: 132,
      render: status => getStatusTag(status),
    },
    {
      title: '响应时间',
      dataIndex: 'response_time',
      key: 'response_time',
      width: 112,
      render: time => {
        if (typeof time !== 'number') {
          return '-';
        }
        const tone = getResponseTimeTone(time);
        const label = getResponseTimeLabel(time);
        return (
          <span className={`${styles.responseTime} ${getToneClassName(tone)}`}>
            <span className={styles.responseTimeValue}>{time}ms</span>
            <span className={styles.responseTimeLabel}>{label}</span>
          </span>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      fixed: 'right',
      width: 88,
      render: (_, record) => (
        <Tooltip title="查看详情">
          <Button
            type="text"
            className={styles.rowActionButton}
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
            aria-label={`查看操作日志 ${record.id} 详情`}
          />
        </Tooltip>
      ),
    },
  ];

  return (
    <PageContainer className={styles.pageShell} title="操作日志" subTitle="查看系统操作轨迹与安全审计记录">
      {/* 统计卡片 */}
      {statistics && (
        <Row gutter={[16, 16]} className={styles.statsRow}>
          <Col xs={24} sm={12} xl={6}>
            <Card className={`${styles.statsCard} ${styles.toneSuccess}`}>
              <Statistic
                title="今日操作"
                value={statistics.today}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card className={`${styles.statsCard} ${styles.tonePrimary}`}>
              <Statistic
                title="本周操作"
                value={statistics.this_week}
                prefix={<SettingOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card className={`${styles.statsCard} ${styles.toneError}`}>
              <Statistic
                title="错误数量"
                value={statistics.error_count}
                prefix={<ExclamationCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card
              className={`${styles.statsCard} ${getToneClassName(
                getResponseTimeTone(statistics.avg_response_time)
              )}`}
            >
              <Statistic
                title="平均响应时间"
                value={statistics.avg_response_time}
                suffix="ms"
                prefix={<SettingOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card className={styles.auditCard}>
        <div className={styles.filtersSection}>
          <div className={styles.filterSummary} aria-live="polite">
            <Text type="secondary">共 {pagination.total} 条记录</Text>
            <Text type="secondary">
              {activeFilterCount > 0 ? `已启用 ${activeFilterCount} 项筛选` : '未启用筛选条件'}
            </Text>
          </div>
          <ListToolbar
            variant="plain"
            gutter={[16, 16]}
            items={[
              {
                key: 'search',
                col: { xs: 24, sm: 12, md: 6 },
                content: (
                  <Search
                    placeholder="搜索用户名、资源或操作"
                    allowClear
                    className={styles.fullWidthControl}
                    onSearch={handleSearch}
                    value={filters.searchText}
                    onChange={event => handleSearch(event.target.value)}
                    prefix={<SearchOutlined />}
                  />
                ),
              },
              {
                key: 'module',
                col: { xs: 24, sm: 12, md: 4 },
                content: (
                  <Select
                    placeholder="模块筛选"
                    allowClear
                    className={styles.fullWidthControl}
                    value={filters.module === '' ? undefined : filters.module}
                    onChange={handleModuleChange}
                  >
                    {MODULE_OPTIONS.map(module => (
                      <Option key={module.value} value={module.value}>
                        {module.label}
                      </Option>
                    ))}
                  </Select>
                ),
              },
              {
                key: 'action',
                col: { xs: 24, sm: 12, md: 4 },
                content: (
                  <Select
                    placeholder="操作筛选"
                    allowClear
                    className={styles.fullWidthControl}
                    value={filters.action === '' ? undefined : filters.action}
                    onChange={handleActionChange}
                  >
                    {ACTION_OPTIONS.map(action => (
                      <Option key={action.value} value={action.value}>
                        {action.label}
                      </Option>
                    ))}
                  </Select>
                ),
              },
              {
                key: 'status',
                col: { xs: 24, sm: 12, md: 4 },
                content: (
                  <Select
                    placeholder="状态筛选"
                    allowClear
                    className={styles.fullWidthControl}
                    value={filters.status === '' ? undefined : filters.status}
                    onChange={handleStatusChange}
                  >
                    {STATUS_OPTIONS.map(status => (
                      <Option key={status.value} value={status.value}>
                        {status.label}
                      </Option>
                    ))}
                  </Select>
                ),
              },
              {
                key: 'range',
                col: { xs: 24, sm: 12, md: 6 },
                content: (
                  <RangePicker
                    className={styles.fullWidthControl}
                    value={filters.dateRange}
                    onChange={dates => {
                      if (dates != null && dates[0] != null && dates[1] != null) {
                        handleDateRangeChange([dates[0], dates[1]]);
                      } else {
                        handleDateRangeChange(null);
                      }
                    }}
                    placeholder={['开始日期', '结束日期']}
                  />
                ),
              },
              {
                key: 'refresh',
                col: { xs: 24, sm: 12, md: 4 },
                content: (
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={refreshLogs}
                    loading={loading}
                    disabled={loading}
                    className={styles.toolbarButton}
                    aria-label="刷新操作日志列表"
                  >
                    刷新
                  </Button>
                ),
              },
            ]}
          />
        </div>

        <TableWithPagination
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
          paginationState={pagination}
          onPageChange={handlePageChange}
          paginationProps={{
            showTotal: (total: number, range: [number, number]) =>
              `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`,
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 详情抽屉 */}
      <Drawer
        title="操作日志详情"
        placement="right"
        onClose={() => setDetailDrawerVisible(false)}
        open={detailDrawerVisible}
        size={800}
        className={styles.detailDrawer}
      >
        {selectedLog && (
          <div className={styles.detailContent}>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="操作时间">
                {dayjs(selectedLog.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="用户信息">
                <Space>
                  <UserOutlined />
                  <Space direction="vertical" size={0} className={styles.userCell}>
                    <span className={styles.primaryText}>
                      {selectedLog.user_name ?? selectedLog.username ?? '-'}
                    </span>
                    <span className={styles.secondaryText}>
                      {selectedLog.username != null && selectedLog.username.trim() !== ''
                        ? `账号 @${selectedLog.username}`
                        : '-'}
                    </span>
                  </Space>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="操作类型">
                {getActionTag(selectedLog.action)}
              </Descriptions.Item>
              <Descriptions.Item label="所属模块">
                {getModuleTag(selectedLog.module, selectedLog.module_name)}
              </Descriptions.Item>
              <Descriptions.Item label="资源信息">
                {selectedLog.resource_name != null && selectedLog.resource_name.trim() !== '' ? (
                  <div>
                    <div>{selectedLog.resource_name}</div>
                    <div className={styles.secondaryText}>
                      {selectedLog.resource_type} (ID: {selectedLog.resource_id})
                    </div>
                  </div>
                ) : (
                  '-'
                )}
              </Descriptions.Item>
              <Descriptions.Item label="请求信息">
                <div>
                  <div className={styles.requestMetaRow}>
                    {getRequestMethodTag(selectedLog.request_method)}
                    {selectedLog.request_url != null && selectedLog.request_url.trim() !== '' ? (
                      <code className={styles.requestUrl}>
                        {selectedLog.request_url}
                      </code>
                    ) : (
                      <Text type="secondary">-</Text>
                    )}
                  </div>
                  <div className={styles.ipText}>
                    IP:{' '}
                    {selectedLog.ip_address != null && selectedLog.ip_address.trim() !== ''
                      ? selectedLog.ip_address
                      : '-'}
                  </div>
                </div>
              </Descriptions.Item>
              <Descriptions.Item label="请求参数">
                {renderJsonBlock(selectedLog.request_params)}
              </Descriptions.Item>
              <Descriptions.Item label="请求体">
                {renderJsonBlock(selectedLog.request_body)}
              </Descriptions.Item>
              <Descriptions.Item label="响应信息">
                <div className={styles.responseMeta}>
                  <div className={styles.responseMetaRow}>
                    <Text strong>状态：</Text>
                    {getStatusTag(selectedLog.response_status)}
                  </div>
                  <div className={styles.responseMetaRow}>
                    <Text strong>耗时：</Text>
                    {typeof selectedLog.response_time === 'number' ? (
                      <span
                        className={`${styles.responseTime} ${getToneClassName(
                          getResponseTimeTone(selectedLog.response_time)
                        )}`}
                      >
                        <span className={styles.responseTimeValue}>{selectedLog.response_time}ms</span>
                        <span className={styles.responseTimeLabel}>
                          {getResponseTimeLabel(selectedLog.response_time)}
                        </span>
                      </span>
                    ) : (
                      '-'
                    )}
                  </div>
                </div>
              </Descriptions.Item>
              {selectedLog.error_message != null && (
                <Descriptions.Item label="错误信息">
                  <div className={styles.errorMessage}>
                    {selectedLog.error_message}
                  </div>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="用户代理">
                <div className={styles.userAgent}>
                  {selectedLog.user_agent != null && selectedLog.user_agent.trim() !== ''
                    ? selectedLog.user_agent
                    : '-'}
                </div>
              </Descriptions.Item>
              <Descriptions.Item label="详细信息">
                {selectedLog.details == null ? (
                  '-'
                ) : typeof selectedLog.details === 'string' ? (
                  <Text type="secondary">{selectedLog.details}</Text>
                ) : Array.isArray(selectedLog.details) ? (
                  renderJsonBlock(selectedLog.details)
                ) : (
                  <div className={styles.detailsObject}>
                    {Object.entries(selectedLog.details).map(([key, value]) => (
                      <div key={key} className={styles.detailsRow}>
                        <Text strong className={styles.detailKey}>
                          {key}:
                        </Text>
                        <Text type="secondary">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </Text>
                      </div>
                    ))}
                  </div>
                )}
              </Descriptions.Item>
            </Descriptions>
          </div>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default OperationLogPage;
