import React, { useEffect, useState } from 'react';
import {
  Card,
  Timeline,
  Tag,
  Button,
  Space,
  Spin,
  Alert,
  Modal,
  Descriptions,
  Empty,
  Select,
  DatePicker,
  Row,
  Col,
  Pagination,
} from 'antd';
import {
  HistoryOutlined,
  EyeOutlined,
  FilterOutlined,
  ReloadOutlined,
  UserOutlined,
  CalendarOutlined,
  EditOutlined,
  PlusOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import dayjs, { Dayjs } from 'dayjs';

import { assetService } from '@/services/assetService';
import type { AssetHistory } from '@/types/asset';
import { formatDate } from '@/utils/format';
import { COLORS } from '@/styles/colorMap';

const { Option } = Select;
const { RangePicker } = DatePicker;

interface AssetHistoryProps {
  assetId: string;
}

interface AssetHistoryFilters {
  changeType?: string;
  dateRange?: [dayjs.Dayjs, dayjs.Dayjs] | null;
}

interface AssetHistoryListResult {
  items: AssetHistory[];
  total: number;
  pages?: number;
}

const AssetHistory: React.FC<AssetHistoryProps> = ({ assetId }) => {
  const [filters, setFilters] = useState<AssetHistoryFilters>({
    changeType: undefined,
    dateRange: null,
  });
  const [paginationState, setPaginationState] = useState({
    current: 1,
    pageSize: 20,
  });
  const [selectedHistory, setSelectedHistory] = useState<AssetHistory | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);

  const fetchHistory = async (): Promise<AssetHistoryListResult> => {
    const { changeType, dateRange } = filters;
    void dateRange;
    const response = await assetService.getAssetHistory(
      assetId,
      paginationState.current,
      paginationState.pageSize,
      changeType
    );
    return {
      items: response.data?.items ?? [],
      total: response.data?.pagination?.total ?? 0,
      pages: response.data?.pagination?.total_pages,
    };
  };

  const {
    data: historyResponse,
    error: historyError,
    isLoading: isHistoryLoading,
    isFetching: isHistoryFetching,
    refetch: refetchHistory,
  } = useQuery<AssetHistoryListResult>({
    queryKey: [
      'asset-history-list',
      assetId,
      paginationState.current,
      paginationState.pageSize,
      filters.changeType ?? null,
      filters.dateRange?.[0]?.format('YYYY-MM-DD') ?? null,
      filters.dateRange?.[1]?.format('YYYY-MM-DD') ?? null,
    ],
    queryFn: fetchHistory,
    enabled: assetId !== '',
    retry: 1,
  });

  const historyRows = historyResponse?.items ?? [];
  const pagination = {
    current: paginationState.current,
    pageSize: paginationState.pageSize,
    total: historyResponse?.total ?? 0,
  };
  const isLoading = isHistoryLoading || isHistoryFetching;

  // 获取历史详情
  const { isLoading: detailLoading } = useQuery({
    queryKey: ['history-detail', selectedHistory?.id],
    queryFn: () => assetService.getHistoryDetail(selectedHistory!.id),
    enabled: !!selectedHistory,
  });

  // 处理查看详情
  const handleViewDetail = (history: AssetHistory) => {
    setSelectedHistory(history);
    setDetailVisible(true);
  };

  // 处理筛选重置
  const handleResetFilter = () => {
    setFilters({
      changeType: undefined,
      dateRange: null,
    });
    setPaginationState(prev => ({ ...prev, current: 1 }));
  };

  useEffect(() => {
    if (assetId) {
      setFilters({
        changeType: undefined,
        dateRange: null,
      });
      setPaginationState(prev => ({ ...prev, current: 1 }));
    }
  }, [assetId]);

  // 获取变更类型图标和颜色
  const getChangeTypeConfig = (type?: string) => {
    switch (type) {
      case 'create':
        return {
          icon: <PlusOutlined />,
          color: 'green',
          text: '创建',
        };
      case 'update':
        return {
          icon: <EditOutlined />,
          color: 'blue',
          text: '更新',
        };
      case 'delete':
        return {
          icon: <DeleteOutlined />,
          color: 'red',
          text: '删除',
        };
      default:
        return {
          icon: <EditOutlined />,
          color: 'default',
          text: type ?? '未知',
        };
    }
  };

  // 渲染字段变更详情
  const renderFieldChanges = (
    oldValues: Record<string, unknown>,
    newValues: Record<string, unknown>
  ) => {
    const changes = [];

    // 合并所有变更的字段
    const allFields = new Set([...Object.keys(oldValues ?? {}), ...Object.keys(newValues ?? {})]);

    for (const field of allFields) {
      const oldValue = oldValues?.[field];
      const newValue = newValues?.[field];

      if (oldValue !== newValue) {
        changes.push({
          field,
          oldValue: oldValue ?? '-',
          newValue: newValue ?? '-',
        });
      }
    }

    return changes.map(change => (
      <Descriptions.Item key={change.field} label={change.field} span={3}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: COLORS.error, textDecoration: 'line-through' }}>
            {String(change.oldValue)}
          </span>
          <span>→</span>
          <span style={{ color: COLORS.success, fontWeight: 'bold' }}>
            {String(change.newValue)}
          </span>
        </div>
      </Descriptions.Item>
    ));
  };

  if (historyError != null) {
    return (
      <Alert
        title="加载失败"
        description="无法加载变更历史，请稍后重试"
        type="error"
        showIcon
        action={<Button onClick={() => void refetchHistory()}>重新加载</Button>}
      />
    );
  }

  return (
    <div>
      {/* 筛选器 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col xs={24} sm={8} md={6}>
            <Select
              placeholder="变更类型"
              value={filters.changeType}
              onChange={value => {
                setFilters(prev => ({ ...prev, changeType: value }));
                setPaginationState(prev => ({ ...prev, current: 1 }));
              }}
              allowClear
              style={{ width: '100%' }}
            >
              <Option value="create">创建</Option>
              <Option value="update">更新</Option>
              <Option value="delete">删除</Option>
            </Select>
          </Col>

          <Col xs={24} sm={10} md={8}>
            <RangePicker
              value={filters.dateRange ?? null}
              onChange={dates => {
                const nextRange =
                  dates !== undefined && dates !== null && dates[0] && dates[1]
                    ? ([dates[0], dates[1]] as [Dayjs, Dayjs])
                    : null;
                setFilters(prev => ({ ...prev, dateRange: nextRange }));
                setPaginationState(prev => ({ ...prev, current: 1 }));
              }}
              placeholder={['开始日期', '结束日期']}
              style={{ width: '100%' }}
            />
          </Col>

          <Col xs={24} sm={6} md={4}>
            <Space>
              <Button icon={<FilterOutlined />} onClick={handleResetFilter}>
                重置
              </Button>
              <Button icon={<ReloadOutlined />} onClick={() => void refetchHistory()} loading={isLoading}>
                刷新
              </Button>
            </Space>
          </Col>

          <Col xs={24} sm={24} md={6} style={{ textAlign: 'right' }}>
            <span style={{ color: '#8c8c8c', fontSize: '14px' }}>共 {pagination.total} 条记录</span>
          </Col>
        </Row>
      </Card>

      {/* 历史记录时间线 */}
      <Card
        title={
          <span>
            <HistoryOutlined style={{ marginRight: 8 }} />
            变更历史
          </span>
        }
      >
        <Spin spinning={isLoading}>
          {historyRows.length > 0 ? (
            <>
              <Timeline>
                {historyRows.map(history => {
                  const config = getChangeTypeConfig(history.change_type);

                  return (
                    <Timeline.Item key={history.id} dot={config.icon} color={config.color}>
                      <div style={{ paddingBottom: 16 }}>
                        {/* 变更标题 */}
                        <div style={{ marginBottom: 8 }}>
                          <Space>
                            <Tag color={config.color}>{config.text}</Tag>
                            <span style={{ fontWeight: 'bold' }}>
                              {history.changed_fields?.join(', ') ?? '无字段变更'}
                            </span>
                          </Space>
                        </div>

                        {/* 变更信息 */}
                        <div style={{ marginBottom: 8, color: '#8c8c8c', fontSize: '14px' }}>
                          <Space split={<span>•</span>}>
                            <span>
                              <UserOutlined style={{ marginRight: 4 }} />
                              {history.operator ?? '未知用户'}
                            </span>
                            <span>
                              <CalendarOutlined style={{ marginRight: 4 }} />
                              {formatDate(history.operation_time, 'datetime')}
                            </span>
                          </Space>
                        </div>

                        {/* 变更原因 */}
                        {history.change_reason != null && (
                          <div style={{ marginBottom: 8, color: '#595959' }}>
                            原因：{history.change_reason}
                          </div>
                        )}

                        {/* 操作按钮 */}
                        <div>
                          <Button
                            type="link"
                            size="small"
                            icon={<EyeOutlined />}
                            onClick={() => handleViewDetail(history)}
                            style={{ padding: 0 }}
                          >
                            查看详情
                          </Button>
                        </div>
                      </div>
                    </Timeline.Item>
                  );
                })}
              </Timeline>

              {/* 分页 */}
              {pagination.total > pagination.pageSize && (
                <div style={{ textAlign: 'center', marginTop: 24 }}>
                  <Pagination
                    current={pagination.current}
                    pageSize={pagination.pageSize}
                    total={pagination.total}
                    showSizeChanger
                    showQuickJumper
                    showTotal={(total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`}
                    onChange={(newPage, newPageSize) => {
                      setPaginationState(prev => ({
                        current: newPage,
                        pageSize: newPageSize ?? prev.pageSize,
                      }));
                    }}
                  />
                </div>
              )}
            </>
          ) : (
            <Empty description="暂无变更历史" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Spin>
      </Card>

      {/* 详情对话框 */}
      <Modal
        title={
          selectedHistory && (
            <span>变更详情 - {getChangeTypeConfig(selectedHistory.change_type).text}</span>
          )
        }
        open={detailVisible}
        onCancel={() => {
          setDetailVisible(false);
          setSelectedHistory(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {selectedHistory && (
          <Spin spinning={detailLoading}>
            <Descriptions bordered column={1} labelStyle={{ width: '120px' }}>
              <Descriptions.Item label="变更类型">
                <Tag color={getChangeTypeConfig(selectedHistory.change_type).color}>
                  {getChangeTypeConfig(selectedHistory.change_type).text}
                </Tag>
              </Descriptions.Item>

              <Descriptions.Item label="变更字段">
                {selectedHistory.changed_fields?.join(', ') ?? '无字段变更'}
              </Descriptions.Item>

              <Descriptions.Item label="操作人">
                {selectedHistory.operator ?? '未知用户'}
              </Descriptions.Item>

              <Descriptions.Item label="变更时间">
                {formatDate(selectedHistory.operation_time, 'datetime')}
              </Descriptions.Item>

              {selectedHistory.change_reason != null && (
                <Descriptions.Item label="变更原因">
                  {selectedHistory.change_reason}
                </Descriptions.Item>
              )}
            </Descriptions>

            {/* 字段变更详情 */}
            {selectedHistory.change_type === 'update' &&
              selectedHistory.old_values &&
              selectedHistory.new_values && (
                <div style={{ marginTop: 24 }}>
                  <h4>字段变更详情</h4>
                  <Descriptions bordered column={1} labelStyle={{ width: '120px' }}>
                    {renderFieldChanges(selectedHistory.old_values, selectedHistory.new_values)}
                  </Descriptions>
                </div>
              )}

            {/* 创建时的数据 */}
            {selectedHistory.change_type === 'create' && selectedHistory.new_values && (
              <div style={{ marginTop: 24 }}>
                <h4>创建时的数据</h4>
                <Descriptions bordered column={2} labelStyle={{ width: '120px' }}>
                  {Object.entries(selectedHistory.new_values).map(([key, value]) => (
                    <Descriptions.Item key={key} label={key}>
                      {String(value)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </div>
            )}
          </Spin>
        )}
      </Modal>
    </div>
  );
};

export default AssetHistory;
