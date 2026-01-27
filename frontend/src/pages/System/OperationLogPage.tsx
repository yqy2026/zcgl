import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
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

const { Text } = Typography;
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
import { COLORS } from '@/styles/colorMap';

const { RangePicker } = DatePicker;
const { Search } = Input;
const { Option } = Select;
import { logService, type OperationLog, type LogStatistics } from '../../services/systemService';

const OperationLogPage: React.FC = () => {
  const [logs, setLogs] = useState<OperationLog[]>([]);
  const [statistics, setStatistics] = useState<LogStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<OperationLog | null>(null);
  const [_searchText, _setSearchText] = useState('');
  const [_moduleFilter, _setModuleFilter] = useState<string>('');
  const [_actionFilter, _setActionFilter] = useState<string>('');
  const [_statusFilter, _setStatusFilter] = useState<string>('');
  const [_dateRange, _setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  // 操作类型选项
  const actionOptions = [
    { value: 'create', label: '创建', color: 'green', icon: <PlusOutlined /> },
    { value: 'update', label: '更新', color: 'blue', icon: <EditOutlined /> },
    { value: 'delete', label: '删除', color: 'red', icon: <DeleteOutlined /> },
    { value: 'view', label: '查看', color: 'default', icon: <EyeOutlined /> },
    { value: 'login', label: '登录', color: 'green', icon: <LoginOutlined /> },
    { value: 'logout', label: '登出', color: 'orange', icon: <LogoutOutlined /> },
    { value: 'export', label: '导出', color: 'purple', icon: <FileTextOutlined /> },
    { value: 'import', label: '导入', color: 'purple', icon: <FileTextOutlined /> },
    { value: 'security', label: '安全操作', color: 'red', icon: <SecurityScanOutlined /> },
  ];

  // 模块选项
  const moduleOptions = [
    { value: 'dashboard', label: '数据看板' },
    { value: 'assets', label: '资产管理' },
    { value: 'rental', label: '租赁管理' },
    { value: 'ownership', label: '权属方管理' },
    { value: 'project', label: '项目管理' },
    { value: 'system', label: '系统管理' },
    { value: 'auth', label: '认证授权' },
  ];

  // 状态选项
  const statusOptions = [
    { value: 'success', label: '成功', color: 'green' },
    { value: 'error', label: '失败', color: 'red' },
    { value: 'warning', label: '警告', color: 'orange' },
  ];

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
    return (
      <pre
        style={{
          background: COLORS.bgTertiary,
          padding: '8px',
          borderRadius: '4px',
          fontSize: '12px',
          margin: 0,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {formatted}
      </pre>
    );
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async (options?: {
    page?: number;
    pageSize?: number;
    searchText?: string;
    module?: string;
    action?: string;
    status?: string;
    dateRange?: [dayjs.Dayjs, dayjs.Dayjs] | null;
  }) => {
    setLoading(true);
    try {
      const page = options?.page ?? pagination.current;
      const pageSize = options?.pageSize ?? pagination.pageSize;
      const searchText = options?.searchText ?? _searchText;
      const moduleFilter = options?.module ?? _moduleFilter;
      const actionFilter = options?.action ?? _actionFilter;
      const statusFilter = options?.status ?? _statusFilter;
      const dateRange = options?.dateRange ?? _dateRange;

      const params = {
        page,
        page_size: pageSize,
        module: moduleFilter || undefined,
        action: actionFilter || undefined,
        start_date: dateRange?.[0].format('YYYY-MM-DD'),
        end_date: dateRange?.[1].format('YYYY-MM-DD'),
        search: searchText || undefined,
        response_status: statusFilter || undefined,
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

      setLogs(normalizedItems);
      setPagination({
        current: result?.page ?? page,
        pageSize: result?.page_size ?? pageSize,
        total: result?.total ?? normalizedItems.length,
      });

      const responseTimes = normalizedItems
        .map(log => log.response_time)
        .filter((time): time is number => typeof time === 'number');
      const avgResponseTime =
        responseTimes.length > 0
          ? Math.round(responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length)
          : 0;

      setStatistics({
        total: result?.total ?? normalizedItems.length,
        today: normalizedItems.filter(log => dayjs(log.created_at).isSame(dayjs(), 'day')).length,
        this_week: normalizedItems.filter(log => dayjs(log.created_at).isSame(dayjs(), 'week'))
          .length,
        this_month: normalizedItems.filter(log => dayjs(log.created_at).isSame(dayjs(), 'month'))
          .length,
        by_action: {},
        by_module: {},
        error_count: normalizedItems.filter(log => (log.response_status ?? 0) >= 400).length,
        avg_response_time: avgResponseTime,
      });
    } catch {
      MessageManager.error('加载操作日志失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    _setSearchText(value);
    loadLogs({ page: 1, searchText: value });
  };

  const handleViewDetail = (log: OperationLog) => {
    setSelectedLog(log);
    setDetailDrawerVisible(true);
  };

  const getActionTag = (action: string) => {
    const actionConfig = actionOptions.find(a => a.value === action);
    return (
      <Tag color={actionConfig?.color ?? 'default'} icon={actionConfig?.icon}>
        {actionConfig?.label ?? action}
      </Tag>
    );
  };

  const getStatusTag = (status?: number | null) => {
    if (status == null) {
      return <Tag>未知</Tag>;
    }
    if (status >= 200 && status < 300) {
      return <Tag color="green">成功</Tag>;
    } else if (status >= 400 && status < 500) {
      return <Tag color="orange">客户端错误</Tag>;
    } else if (status >= 500) {
      return <Tag color="red">服务器错误</Tag>;
    }
    return <Tag>未知</Tag>;
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
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <div style={{ fontWeight: 500 }}>{record.user_name ?? record.username ?? '-'}</div>
          <div style={{ fontSize: '12px', color: COLORS.textSecondary }}>
            @{record.username ?? '-'}
          </div>
        </Space>
      ),
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: action => getActionTag(action),
    },
    {
      title: '模块',
      dataIndex: 'module_name',
      key: 'module',
      width: 120,
      render: module => <Tag color="blue">{module ?? '-'}</Tag>,
    },
    {
      title: '资源',
      key: 'resource',
      width: 150,
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.resource_name ?? '-'}</div>
          <div style={{ fontSize: '12px', color: COLORS.textSecondary }}>
            {record.resource_type || '-'}
          </div>
        </div>
      ),
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 120,
      render: ip => (
        <Tooltip title={ip ?? ''}>
          <span>{ip ?? ''}</span>
        </Tooltip>
      ),
    },
    {
      title: '响应状态',
      dataIndex: 'response_status',
      key: 'response_status',
      width: 100,
      render: status => getStatusTag(status),
    },
    {
      title: '响应时间',
      dataIndex: 'response_time',
      key: 'response_time',
      width: 100,
      render: time =>
        typeof time === 'number' ? (
          <span
            style={{
              color: time > 1000 ? COLORS.error : time > 500 ? COLORS.warning : COLORS.success,
            }}
          >
            {time}ms
          </span>
        ) : (
          '-'
        ),
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 80,
      render: (_, record) => (
        <Tooltip title="查看详情">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          />
        </Tooltip>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* 统计卡片 */}
      {statistics && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="今日操作"
                value={statistics.today}
                prefix={<FileTextOutlined />}
                valueStyle={{ color: COLORS.success }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="本周操作"
                value={statistics.this_week}
                prefix={<SettingOutlined />}
                valueStyle={{ color: COLORS.primary }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="错误数量"
                value={statistics.error_count}
                prefix={<ExclamationCircleOutlined />}
                valueStyle={{ color: COLORS.error }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均响应时间"
                value={statistics.avg_response_time}
                suffix="ms"
                prefix={<SettingOutlined />}
                valueStyle={{
                  color:
                    statistics.avg_response_time > 1000
                      ? COLORS.error
                      : statistics.avg_response_time > 500
                        ? COLORS.warning
                        : COLORS.success,
                }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        <div style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={6}>
              <Search
                placeholder="搜索用户名、资源或操作"
                allowClear
                onSearch={handleSearch}
                prefix={<SearchOutlined />}
              />
            </Col>
            <Col xs={24} sm={12} md={4}>
              <Select
                placeholder="模块筛选"
                allowClear
                style={{ width: '100%' }}
                onChange={value => {
                  _setModuleFilter(value ?? '');
                  loadLogs({ page: 1, module: value ?? '' });
                }}
              >
                {moduleOptions.map(module => (
                  <Option key={module.value} value={module.value}>
                    {module.label}
                  </Option>
                ))}
              </Select>
            </Col>
            <Col xs={24} sm={12} md={4}>
              <Select
                placeholder="操作筛选"
                allowClear
                style={{ width: '100%' }}
                onChange={value => {
                  _setActionFilter(value ?? '');
                  loadLogs({ page: 1, action: value ?? '' });
                }}
              >
                {actionOptions.map(action => (
                  <Option key={action.value} value={action.value}>
                    {action.label}
                  </Option>
                ))}
              </Select>
            </Col>
            <Col xs={24} sm={12} md={4}>
              <Select
                placeholder="状态筛选"
                allowClear
                style={{ width: '100%' }}
                onChange={value => {
                  _setStatusFilter(value ?? '');
                  loadLogs({ page: 1, status: value ?? '' });
                }}
              >
                {statusOptions.map(status => (
                  <Option key={status.value} value={status.value}>
                    {status.label}
                  </Option>
                ))}
              </Select>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <RangePicker
                style={{ width: '100%' }}
                onChange={dates => {
                  if (dates && dates[0] && dates[1]) {
                    _setDateRange([dates[0], dates[1]]);
                    loadLogs({ page: 1, dateRange: [dates[0], dates[1]] });
                  } else {
                    _setDateRange(null);
                    loadLogs({ page: 1, dateRange: null });
                  }
                }}
                placeholder={['开始日期', '结束日期']}
              />
            </Col>
            <Col xs={24} sm={12} md={4}>
              <Button icon={<ReloadOutlined />} onClick={() => loadLogs()} loading={loading}>
                刷新
              </Button>
            </Col>
          </Row>
        </div>

        <Table
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
          onChange={paginationState => {
            const current = paginationState.current ?? 1;
            const pageSize = paginationState.pageSize ?? 20;
            setPagination(prev => ({
              ...prev,
              current,
              pageSize,
            }));
            loadLogs({ page: current, pageSize });
          }}
          pagination={{
            current: pagination.current,
            total: pagination.total,
            pageSize: pagination.pageSize,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`,
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
        width={800}
      >
        {selectedLog && (
          <div>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="操作时间">
                {dayjs(selectedLog.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="用户信息">
                <Space>
                  <UserOutlined />
                  <span>
                    {selectedLog.user_name ?? selectedLog.username ?? '-'} (@
                    {selectedLog.username ?? '-'})
                  </span>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="操作类型">
                {getActionTag(selectedLog.action)}
              </Descriptions.Item>
              <Descriptions.Item label="所属模块">
                <Tag color="blue">{selectedLog.module_name ?? selectedLog.module ?? '-'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="资源信息">
                {selectedLog.resource_name != null ? (
                  <div>
                    <div>{selectedLog.resource_name}</div>
                    <div style={{ fontSize: '12px', color: COLORS.textSecondary }}>
                      {selectedLog.resource_type} (ID: {selectedLog.resource_id})
                    </div>
                  </div>
                ) : (
                  '-'
                )}
              </Descriptions.Item>
              <Descriptions.Item label="请求信息">
                <div>
                  <div>
                    {selectedLog.request_method != null ? (
                      <Tag color="purple">{selectedLog.request_method}</Tag>
                    ) : (
                      '-'
                    )}
                    {selectedLog.request_url != null ? (
                      <code style={{ background: COLORS.bgTertiary, padding: '2px 4px' }}>
                        {selectedLog.request_url}
                      </code>
                    ) : (
                      '-'
                    )}
                  </div>
                  <div style={{ marginTop: 8, fontSize: '12px', color: COLORS.textSecondary }}>
                    IP: {selectedLog.ip_address ?? '-'}
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
                <div>
                  <div>状态: {getStatusTag(selectedLog.response_status)}</div>
                  <div>
                    耗时:{' '}
                    {typeof selectedLog.response_time === 'number' ? (
                      <span
                        style={{
                          color:
                            selectedLog.response_time > 1000
                              ? COLORS.error
                              : selectedLog.response_time > 500
                                ? COLORS.warning
                                : COLORS.success,
                        }}
                      >
                        {selectedLog.response_time}ms
                      </span>
                    ) : (
                      '-'
                    )}
                  </div>
                </div>
              </Descriptions.Item>
              {selectedLog.error_message != null && (
                <Descriptions.Item label="错误信息">
                  <div
                    style={{
                      color: COLORS.error,
                      background: 'var(--color-error-light)',
                      padding: '8px',
                      borderRadius: '4px',
                    }}
                  >
                    {selectedLog.error_message}
                  </div>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="用户代理">
                <div
                  style={{ fontSize: '12px', color: COLORS.textSecondary, wordBreak: 'break-all' }}
                >
                  {selectedLog.user_agent ?? '-'}
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
                  <div
                    style={{
                      background: COLORS.bgTertiary,
                      padding: '12px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      overflow: 'auto',
                      maxHeight: '300px',
                    }}
                  >
                    {Object.entries(selectedLog.details).map(([key, value]) => (
                      <div key={key} style={{ marginBottom: 4 }}>
                        <Text strong style={{ marginRight: 8 }}>
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
    </div>
  );
};

export default OperationLogPage;
