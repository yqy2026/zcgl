/**
 * 权属方列表组件
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createLogger } from '@/utils/logger';
import {
  Button,
  Space,
  Tooltip,
  Modal,
  Card,
  Row,
  Col,
  Statistic,
  Badge,
  Input,
  Select,
  Switch,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  SearchOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

import { ownershipService } from '@/services/ownershipService';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { ListToolbar } from '@/components/Common/ListToolbar';
import { useQuery } from '@tanstack/react-query';
import type {
  Ownership,
  OwnershipListResponse,
  OwnershipStatisticsResponse,
} from '@/types/ownership';
import { OwnershipForm } from '@/components/Forms';
import OwnershipDetail from './OwnershipDetail';
import styles from './OwnershipList.module.css';

const { Search } = Input;
const { Option } = Select;
const { confirm } = Modal;
const componentLogger = createLogger('OwnershipList');

interface OwnershipListProps {
  onSelectOwnership?: (ownership: Ownership) => void;
  mode?: 'list' | 'select';
}

interface OwnershipFilters {
  keyword: string;
  isActive: boolean | null;
}

const OwnershipList: React.FC<OwnershipListProps> = ({ onSelectOwnership, mode = 'list' }) => {
  const [filters, setFilters] = useState<OwnershipFilters>({
    keyword: '',
    isActive: null,
  });
  const [paginationState, setPaginationState] = useState({
    current: 1,
    pageSize: 10,
  });

  // 模态框状态
  const [formVisible, setFormVisible] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [editingOwnership, setEditingOwnership] = useState<Ownership | null>(null);
  const [viewingOwnership, setViewingOwnership] = useState<Ownership | null>(null);

  const fetchOwnershipList = useCallback(async (): Promise<OwnershipListResponse> => {
    const params: {
      keyword?: string;
      is_active?: boolean;
      page: number;
      page_size: number;
    } = {
      page: paginationState.current,
      page_size: paginationState.pageSize,
    };

    const trimmedKeyword = filters.keyword.trim();
    if (trimmedKeyword !== '') {
      params.keyword = trimmedKeyword;
    }

    if (filters.isActive !== null) {
      params.is_active = filters.isActive;
    }

    return await ownershipService.getOwnerships(params);
  }, [filters.isActive, filters.keyword, paginationState.current, paginationState.pageSize]);

  const {
    data: ownershipsResponse,
    error: ownershipsError,
    isLoading: isOwnershipsLoading,
    isFetching: isOwnershipsFetching,
    refetch: refetchOwnerships,
  } = useQuery<OwnershipListResponse>({
    queryKey: ['ownership-list', paginationState.current, paginationState.pageSize, filters],
    queryFn: fetchOwnershipList,
    retry: 1,
  });

  const {
    data: statistics = null,
    error: statisticsError,
    refetch: refetchStatistics,
  } = useQuery<OwnershipStatisticsResponse>({
    queryKey: ['ownership-statistics'],
    queryFn: () => ownershipService.getOwnershipStatistics(),
    staleTime: 60 * 1000,
    retry: 1,
  });

  useEffect(() => {
    if (ownershipsError != null) {
      MessageManager.error('加载权属方列表失败');
    }
  }, [ownershipsError]);

  useEffect(() => {
    if (statisticsError != null) {
      componentLogger.warn('加载统计信息失败');
    }
  }, [statisticsError]);

  const ownerships = ownershipsResponse?.items ?? [];
  const loading = isOwnershipsLoading || isOwnershipsFetching;
  const totalLinkedAssets = useMemo(
    () => ownerships.reduce((sum, ownership) => sum + (ownership.asset_count ?? 0), 0),
    [ownerships]
  );
  const pagination = useMemo(
    () => ({
      current: paginationState.current,
      pageSize: paginationState.pageSize,
      total: ownershipsResponse?.total ?? 0,
    }),
    [ownershipsResponse?.total, paginationState.current, paginationState.pageSize]
  );

  const refreshOwnershipsAndStatistics = useCallback(() => {
    void refetchOwnerships();
    void refetchStatistics();
  }, [refetchOwnerships, refetchStatistics]);

  const handleRefresh = useCallback(() => {
    refreshOwnershipsAndStatistics();
  }, [refreshOwnershipsAndStatistics]);

  const updateFilters = useCallback((nextFilters: Partial<OwnershipFilters>) => {
    setFilters(prev => ({ ...prev, ...nextFilters }));
    setPaginationState(prev => ({ ...prev, current: 1 }));
  }, []);

  const handleKeywordChange = useCallback(
    (value: string) => {
      updateFilters({ keyword: value });
    },
    [updateFilters]
  );

  const handleStatusChange = useCallback(
    (value: boolean | undefined) => {
      updateFilters({ isActive: value === undefined ? null : value });
    },
    [updateFilters]
  );

  const handleReset = useCallback(() => {
    setFilters({
      keyword: '',
      isActive: null,
    });
    setPaginationState(prev => ({ ...prev, current: 1 }));
  }, []);

  const handlePageChange = useCallback((next: { current?: number; pageSize?: number }) => {
    setPaginationState(prev => ({
      current: next.current ?? prev.current,
      pageSize: next.pageSize ?? prev.pageSize,
    }));
  }, []);

  const derivedStatistics = useMemo(() => {
    if (statistics != null) {
      return statistics;
    }
    const totalCount = ownerships.length;
    const activeCount = ownerships.filter(item => item.is_active === true).length;
    return {
      total_count: totalCount,
      active_count: activeCount,
      inactive_count: totalCount - activeCount,
    };
  }, [ownerships, statistics]);

  // 创建权属方
  const handleCreate = () => {
    setEditingOwnership(null);
    setFormVisible(true);
  };

  // 编辑权属方
  const handleEdit = (record: Ownership) => {
    setEditingOwnership(record);
    setFormVisible(true);
  };

  // 查看详情
  const handleView = (record: Ownership) => {
    setViewingOwnership(record);
    setDetailVisible(true);
  };

  // 删除权属方
  const handleDelete = (record: Ownership) => {
    confirm({
      title: '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: `确定要删除权属方"${record.name}"吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await ownershipService.deleteOwnership(record.id);
          MessageManager.success('删除成功');
          refreshOwnershipsAndStatistics();
        } catch (error: unknown) {
          MessageManager.error(error instanceof Error ? error.message : '删除失败');
        }
      },
    });
  };

  // 切换状态
  const handleToggleStatus = async (record: Ownership) => {
    try {
      await ownershipService.toggleOwnershipStatus(record.id);
      MessageManager.success(`${record.is_active ? '禁用' : '启用'}成功`);
      refreshOwnershipsAndStatistics();
    } catch {
      MessageManager.error('操作失败');
    }
  };

  // 表单提交成功
  const handleFormSuccess = () => {
    setFormVisible(false);
    refreshOwnershipsAndStatistics();
  };

  // 选中权属方（选择模式）
  const handleSelect = (record: Ownership) => {
    if (mode === 'select' && onSelectOwnership) {
      onSelectOwnership(record);
    }
  };

  // 表格列定义
  const columns: ColumnsType<Ownership> = [
    {
      title: '权属方全称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Ownership) => (
        <Button type="link" className={styles.linkButton} onClick={() => handleView(record)}>
          {text}
        </Button>
      ),
    },
    {
      title: '权属方编码',
      dataIndex: 'code',
      key: 'code',
      width: 120,
      render: (text: string) => text || '-',
    },
    {
      title: '权属方简称',
      dataIndex: 'short_name',
      key: 'short_name',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: '关联资产',
      dataIndex: 'asset_count',
      key: 'asset_count',
      width: 100,
      render: (count: number) => count ?? 0,
    },
    {
      title: '关联项目',
      dataIndex: 'project_count',
      key: 'project_count',
      width: 100,
      render: (count: number) => count ?? 0,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Badge status={active ? 'success' : 'error'} text={active ? '启用' : '禁用'} />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record: Ownership) => (
        <Space size="small" className={styles.actionGroup}>
          {mode === 'select' && (
            <Button
              type="primary"
              size="small"
              className={styles.selectActionButton}
              onClick={() => handleSelect(record)}
            >
              选择
            </Button>
          )}
          {mode === 'list' && (
            <>
              <Tooltip title="查看详情">
                <Button
                  type="text"
                  className={styles.iconActionButton}
                  icon={<EyeOutlined />}
                  onClick={() => handleView(record)}
                />
              </Tooltip>
              <Tooltip title="编辑">
                <Button
                  type="text"
                  className={styles.iconActionButton}
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(record)}
                />
              </Tooltip>
              <Tooltip title="删除">
                <Button
                  type="text"
                  danger
                  className={`${styles.iconActionButton} ${styles.deleteActionButton}`}
                  icon={<DeleteOutlined />}
                  onClick={() => handleDelete(record)}
                />
              </Tooltip>
            </>
          )}
          <Switch
            size="small"
            checked={record.is_active}
            onChange={() => handleToggleStatus(record)}
            checkedChildren="启用"
            unCheckedChildren="禁用"
            className={styles.statusSwitch}
            aria-label={`${record.is_active ? '停用' : '启用'}权属方 ${record.name}`}
          />
        </Space>
      ),
    },
  ];

  return (
    <div className={styles.ownershipList}>
      {/* 统计卡片 */}
      {mode === 'list' && (
        <Row gutter={[16, 16]} className={styles.statsRow}>
          <Col xs={24} sm={12} md={6}>
            <Card className={styles.statsCard}>
              <Statistic
                title="总数量"
                value={derivedStatistics.total_count}
                className={styles.statsTotal}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={styles.statsCard}>
              <Statistic
                title="启用数量"
                value={derivedStatistics.active_count}
                className={styles.statsActive}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={styles.statsCard}>
              <Statistic
                title="禁用数量"
                value={derivedStatistics.inactive_count}
                className={styles.statsInactive}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={styles.statsCard}>
              <Statistic
                title="关联资产"
                value={totalLinkedAssets}
                className={styles.statsAssets}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 搜索和操作栏 */}
      <ListToolbar
        items={[
          {
            key: 'search',
            col: { xs: 24, sm: 12, md: 8, lg: 6 },
            content: (
              <Search
                placeholder="搜索权属方名称、简称等"
                allowClear
                enterButton={<SearchOutlined />}
                className={styles.fullWidthControl}
                value={filters.keyword}
                onChange={e => handleKeywordChange(e.target.value)}
                onSearch={handleKeywordChange}
              />
            ),
          },
          {
            key: 'status',
            col: { xs: 24, sm: 12, md: 6, lg: 4 },
            content: (
              <Select
                placeholder="状态"
                allowClear
                className={styles.fullWidthControl}
                value={filters.isActive === null ? undefined : filters.isActive}
                onChange={handleStatusChange}
              >
                <Option value={true}>启用</Option>
                <Option value={false}>禁用</Option>
              </Select>
            ),
          },
          {
            key: 'reset',
            col: { xs: 24, sm: 12, md: 6, lg: 4 },
            content: (
              <Space className={styles.toolbarActionGroup}>
                <Button className={styles.toolbarButton} onClick={handleReset}>
                  重置
                </Button>
              </Space>
            ),
          },
          {
            key: 'actions',
            col: { xs: 24, sm: 12, md: 6, lg: 4 },
            content: (
              <Space className={styles.toolbarActionGroup}>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  className={styles.toolbarButton}
                  onClick={handleCreate}
                >
                  新建权属方
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  className={styles.toolbarButton}
                  onClick={handleRefresh}
                  loading={loading}
                >
                  刷新
                </Button>
              </Space>
            ),
          },
        ]}
      />

      {/* 权属方表格 */}
      <Card className={styles.tableCard}>
        <TableWithPagination
          columns={columns}
          dataSource={ownerships}
          rowKey="id"
          loading={loading}
          paginationState={pagination}
          onPageChange={handlePageChange}
          paginationProps={{
            showTotal: (total: number, range: [number, number]) =>
              `第 ${range[0]}-${range[1]} 条/共 ${total} 条`,
          }}
          scroll={{ x: 1000 }}
        />
      </Card>

      {/* 权属方表单弹窗 */}
      <Modal
        title={editingOwnership ? '编辑权属方' : '新建权属方'}
        open={formVisible}
        onCancel={() => {
          setFormVisible(false);
          setEditingOwnership(null);
        }}
        footer={null}
        width={600}
        destroyOnHidden
      >
        <OwnershipForm
          initialValues={editingOwnership}
          onSuccess={handleFormSuccess}
          onCancel={() => {
            setFormVisible(false);
            setEditingOwnership(null);
          }}
        />
      </Modal>

      {/* 权属方详情弹窗 */}
      <Modal
        title="权属方详情"
        open={detailVisible}
        onCancel={() => {
          setDetailVisible(false);
          setViewingOwnership(null);
        }}
        footer={null}
        width={800}
        destroyOnHidden
      >
        {viewingOwnership && (
          <OwnershipDetail
            ownership={viewingOwnership}
            onEdit={() => {
              setDetailVisible(false);
              handleEdit(viewingOwnership);
            }}
          />
        )}
      </Modal>
    </div>
  );
};

export default OwnershipList;
