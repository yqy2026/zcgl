import React, { useState, useEffect } from 'react'
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
  message
} from 'antd'
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
  PlusOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker
const { Search } = Input
const { Option } = Select
import { type OperationLog, type LogStatistics } from '../../services/systemService'

const OperationLogPage: React.FC = () => {
  const [logs, setLogs] = useState<OperationLog[]>([])
  const [statistics, setStatistics] = useState<LogStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false)
  const [selectedLog, setSelectedLog] = useState<OperationLog | null>(null)
  const [_searchText, _setSearchText] = useState('')
  const [_moduleFilter, _setModuleFilter] = useState<string>('')
  const [_actionFilter, _setActionFilter] = useState<string>('')
  const [_statusFilter, _setStatusFilter] = useState<string>('')
  const [_dateRange, _setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)

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
    { value: 'security', label: '安全操作', color: 'red', icon: <SecurityScanOutlined /> }
  ]

  // 模块选项
  const moduleOptions = [
    { value: 'dashboard', label: '数据看板' },
    { value: 'assets', label: '资产管理' },
    { value: 'rental', label: '租赁管理' },
    { value: 'ownership', label: '权属方管理' },
    { value: 'project', label: '项目管理' },
    { value: 'system', label: '系统管理' },
    { value: 'auth', label: '认证授权' }
  ]

  // 状态选项
  const statusOptions = [
    { value: 'success', label: '成功', color: 'green' },
    { value: 'error', label: '失败', color: 'red' },
    { value: 'warning', label: '警告', color: 'orange' }
  ]

  useEffect(() => {
    loadLogs()
    loadStatistics()
  }, [])

  const loadLogs = async () => {
    setLoading(true)
    try {
      // 模拟API调用
      const mockLogs: OperationLog[] = [
        {
          id: '1',
          user_id: '1',
          username: 'admin',
          user_name: '系统管理员',
          action: 'login',
          action_name: '用户登录',
          module: 'auth',
          module_name: '认证授权',
          resource_type: 'user',
          resource_id: '1',
          resource_name: '系统管理员',
          ip_address: '192.168.1.100',
          user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          request_method: 'POST',
          request_url: '/api/auth/login',
          response_status: 200,
          response_time: 120,
          error_message: null,
          details: { login_type: 'password', device: 'web' },
          created_at: dayjs().subtract(1, 'hour').toISOString()
        },
        {
          id: '2',
          user_id: '2',
          username: 'manager001',
          user_name: '张经理',
          action: 'create',
          action_name: '创建资产',
          module: 'assets',
          module_name: '资产管理',
          resource_type: 'asset',
          resource_id: 'asset123',
          resource_name: '测试资产',
          ip_address: '192.168.1.101',
          user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          request_method: 'POST',
          request_url: '/api/assets',
          response_status: 201,
          response_time: 250,
          error_message: null,
          details: { asset_name: '测试资产', asset_type: 'commercial' },
          created_at: dayjs().subtract(2, 'hours').toISOString()
        },
        {
          id: '3',
          user_id: '3',
          username: 'user001',
          user_name: '普通用户',
          action: 'view',
          action_name: '查看资产',
          module: 'assets',
          module_name: '资产管理',
          resource_type: 'asset',
          resource_id: 'asset456',
          resource_name: '示例资产',
          ip_address: '192.168.1.102',
          user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          request_method: 'GET',
          request_url: '/api/assets/asset456',
          response_status: 200,
          response_time: 80,
          error_message: null,
          details: { view_type: 'detail' },
          created_at: dayjs().subtract(3, 'hours').toISOString()
        }
      ]
      setLogs(mockLogs)
    } catch {
      message.error('加载操作日志失败')
    } finally {
      setLoading(false)
    }
  }

  const loadStatistics = async () => {
    try {
      // 模拟统计数据
      const mockStats: LogStatistics = {
        total: logs.length,
        today: logs.filter(log => dayjs(log.created_at).isSame(dayjs(), 'day')).length,
        this_week: logs.filter(log => dayjs(log.created_at).isSame(dayjs(), 'week')).length,
        this_month: logs.filter(log => dayjs(log.created_at).isSame(dayjs(), 'month')).length,
        by_action: {},
        by_module: {},
        error_count: logs.filter(log => log.response_status >= 400).length,
        avg_response_time: Math.round(logs.reduce((sum, log) => sum + log.response_time, 0) / logs.length) || 0
      }
      setStatistics(mockStats)
    } catch {
      message.error('加载统计信息失败')
    }
  }

  const handleSearch = (value: string) => {
    _setSearchText(value)
    // 这里可以添加搜索逻辑
  }

  const handleViewDetail = (log: OperationLog) => {
    setSelectedLog(log)
    setDetailDrawerVisible(true)
  }

  const getActionTag = (action: string) => {
    const actionConfig = actionOptions.find(a => a.value === action)
    return (
      <Tag color={actionConfig?.color || 'default'} icon={actionConfig?.icon}>
        {actionConfig?.label || action}
      </Tag>
    )
  }

  const getStatusTag = (status: number) => {
    if (status >= 200 && status < 300) {
      return <Tag color="green">成功</Tag>
    } else if (status >= 400 && status < 500) {
      return <Tag color="orange">客户端错误</Tag>
    } else if (status >= 500) {
      return <Tag color="red">服务器错误</Tag>
    }
    return <Tag>未知</Tag>
  }

  const columns: ColumnsType<OperationLog> = [
    {
      title: '操作时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm:ss')
    },
    {
      title: '用户信息',
      key: 'user_info',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <div style={{ fontWeight: 500 }}>{record.user_name}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            @{record.username}
          </div>
        </Space>
      )
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action) => getActionTag(action)
    },
    {
      title: '模块',
      dataIndex: 'module_name',
      key: 'module',
      width: 120,
      render: (module) => <Tag color="blue">{module}</Tag>
    },
    {
      title: '资源',
      key: 'resource',
      width: 150,
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.resource_name || '-'}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {record.resource_type || '-'}
          </div>
        </div>
      )
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 120,
      render: (ip) => (
        <Tooltip title={ip}>
          <span>{ip}</span>
        </Tooltip>
      )
    },
    {
      title: '响应状态',
      dataIndex: 'response_status',
      key: 'response_status',
      width: 100,
      render: (status) => getStatusTag(status)
    },
    {
      title: '响应时间',
      dataIndex: 'response_time',
      key: 'response_time',
      width: 100,
      render: (time) => (
        <span style={{ color: time > 1000 ? '#ff4d4f' : time > 500 ? '#fa8c16' : '#52c41a' }}>
          {time}ms
        </span>
      )
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
      )
    }
  ]

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
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="本周操作"
                value={statistics.this_week}
                prefix={<SettingOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="错误数量"
                value={statistics.error_count}
                prefix={<ExclamationCircleOutlined />}
                valueStyle={{ color: '#cf1322' }}
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
                  color: statistics.avg_response_time > 1000 ? '#cf1322' :
                    statistics.avg_response_time > 500 ? '#fa8c16' : '#3f8600'
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
                onChange={_setModuleFilter}
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
                onChange={_setActionFilter}
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
                onChange={_setStatusFilter}
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
                onChange={(dates) => {
                  if (dates && dates[0] && dates[1]) {
                    _setDateRange([dates[0], dates[1]])
                  } else {
                    _setDateRange(null)
                  }
                }}
                placeholder={['开始日期', '结束日期']}
              />
            </Col>
            <Col xs={24} sm={12} md={4}>
              <Button
                icon={<ReloadOutlined />}
                onClick={loadLogs}
                loading={loading}
              >
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
          pagination={{
            total: logs.length,
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`
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
                  <span>{selectedLog.user_name} (@{selectedLog.username})</span>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="操作类型">
                {getActionTag(selectedLog.action)}
              </Descriptions.Item>
              <Descriptions.Item label="所属模块">
                <Tag color="blue">{selectedLog.module_name}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="资源信息">
                {selectedLog.resource_name ? (
                  <div>
                    <div>{selectedLog.resource_name}</div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
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
                    <Tag color="purple">{selectedLog.request_method}</Tag>
                    <code style={{ background: '#f5f5f5', padding: '2px 4px' }}>
                      {selectedLog.request_url}
                    </code>
                  </div>
                  <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                    IP: {selectedLog.ip_address}
                  </div>
                </div>
              </Descriptions.Item>
              <Descriptions.Item label="响应信息">
                <div>
                  <div>状态: {getStatusTag(selectedLog.response_status)}</div>
                  <div>耗时: <span style={{
                    color: selectedLog.response_time > 1000 ? '#ff4d4f' :
                      selectedLog.response_time > 500 ? '#fa8c16' : '#52c41a'
                  }}>
                    {selectedLog.response_time}ms
                  </span></div>
                </div>
              </Descriptions.Item>
              {selectedLog.error_message && (
                <Descriptions.Item label="错误信息">
                  <div style={{ color: '#ff4d4f', background: '#fff2f0', padding: '8px', borderRadius: '4px' }}>
                    {selectedLog.error_message}
                  </div>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="用户代理">
                <div style={{ fontSize: '12px', color: '#666', wordBreak: 'break-all' }}>
                  {selectedLog.user_agent}
                </div>
              </Descriptions.Item>
              {selectedLog.details && (
                <Descriptions.Item label="详细信息">
                  <pre style={{
                    background: '#f5f5f5',
                    padding: '12px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    overflow: 'auto'
                  }}>
                    {JSON.stringify(selectedLog.details, null, 2)}
                  </pre>
                </Descriptions.Item>
              )}
            </Descriptions>
          </div>
        )}
      </Drawer>
    </div>
  )
}

export default OperationLogPage
