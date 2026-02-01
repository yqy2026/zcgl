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
import { useListData } from '@/hooks/useListData';

const { Option } = Select;
const { RangePicker } = DatePicker;

interface AssetHistoryProps {
  assetId: string;
}

interface AssetHistoryFilters {
  changeType?: string;
  dateRange?: [dayjs.Dayjs, dayjs.Dayjs] | null;
}

const AssetHistory: React.FC<AssetHistoryProps> = ({ assetId }) => {
  const [selectedHistory, setSelectedHistory] = useState<AssetHistory | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [loadError, setLoadError] = useState<Error | null>(null);

  const fetchHistory = async ({
    page,
    pageSize,
    changeType,
    dateRange,
  }: {
    page: number;
    pageSize: number;
  } & AssetHistoryFilters) => {
    void dateRange;
    const response = await assetService.getAssetHistory(assetId, page, pageSize, changeType);
    return {
      items: response.data?.items ?? [],
      total: response.data?.pagination?.total ?? 0,
      pages: response.data?.pagination?.total_pages,
    };
  };

  const {
    data: historyRows,
    loading: isLoading,
    pagination,
    filters,
    loadList,
    applyFilters,
    resetFilters,
    updatePagination,
  } = useListData<AssetHistory, AssetHistoryFilters>({
    fetcher: fetchHistory,
    initialFilters: {
      changeType: undefined,
      dateRange: null,
    },
    initialPageSize: 20,
    onError: error => {
      setLoadError(error instanceof Error ? error : new Error('无法加载变更历史'));
    },
  });

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
    setLoadError(null);
    resetFilters();
  };

  useEffect(() => {
    if (assetId) {
      setLoadError(null);
      resetFilters();
    }
  }, [assetId, resetFilters]);

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

  if (loadError) {
    return (
      <Alert
        message="加载失败"
        description="无法加载变更历史，请稍后重试"
        type="error"
        showIcon
        action={<Button onClick={() => void loadList()}>重新加载</Button>}
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
                setLoadError(null);
                applyFilters({ ...filters, changeType: value });
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
                    ? ([dates[0] as Dayjs, dates[1] as Dayjs] as [Dayjs, Dayjs])
                    : null;
                setLoadError(null);
                applyFilters({ ...filters, dateRange: nextRange });
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
              <Button icon={<ReloadOutlined />} onClick={() => void loadList()} loading={isLoading}>
                刷新
              </Button>
            </Space>
          </Col>

          <Col xs={24} sm={24} md={6} style={{ textAlign: 'right' }}>
            <span style={{ color: '#8c8c8c', fontSize: '14px' }}>
              共 {pagination.total} 条记录
            </span>
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
                              {history.changed_by ?? history.operator ?? '未知用户'}
                            </span>
                            <span>
                              <CalendarOutlined style={{ marginRight: 4 }} />
                              {formatDate(history.changed_at ?? history.operation_time, 'datetime')}
                            </span>
                          </Space>
                        </div>

                        {/* 变更原因 */}
                        {history.reason != null && (
                          <div style={{ marginBottom: 8, color: '#595959' }}>
                            原因：{history.reason}
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
                      updatePagination({ current: newPage, pageSize: newPageSize });
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
                {selectedHistory.changed_by ?? selectedHistory.operator ?? '未知用户'}
              </Descriptions.Item>

              <Descriptions.Item label="变更时间">
                {formatDate(
                  selectedHistory.changed_at ?? selectedHistory.operation_time,
                  'datetime'
                )}
              </Descriptions.Item>

              {(selectedHistory.reason != null || selectedHistory.description != null) && (
                <Descriptions.Item label="变更原因">
                  {selectedHistory.reason ?? selectedHistory.description}
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
