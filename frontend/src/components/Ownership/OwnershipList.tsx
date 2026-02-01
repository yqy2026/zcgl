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
import { useListData } from '@/hooks/useListData';
import type {
  Ownership,
  OwnershipListResponse,
  OwnershipStatisticsResponse,
} from '@/types/ownership';
import { OwnershipForm } from '@/components/Forms';
import OwnershipDetail from './OwnershipDetail';

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
  const [statistics, setStatistics] = useState<OwnershipStatisticsResponse | null>(null);

  // 模态框状态
  const [formVisible, setFormVisible] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [editingOwnership, setEditingOwnership] = useState<Ownership | null>(null);
  const [viewingOwnership, setViewingOwnership] = useState<Ownership | null>(null);

  const fetchOwnershipList = useCallback(
    async ({
      page,
      pageSize,
      keyword,
      isActive,
    }: {
      page: number;
      pageSize: number;
    } & OwnershipFilters): Promise<OwnershipListResponse> => {
      const params: {
        keyword?: string;
        is_active?: boolean;
        page: number;
        page_size: number;
      } = {
        page,
        page_size: pageSize,
      };

      const trimmedKeyword = keyword.trim();
      if (trimmedKeyword !== '') {
        params.keyword = trimmedKeyword;
      }

      if (isActive !== null) {
        params.is_active = isActive;
      }

      return await ownershipService.getOwnerships(params);
    },
    []
  );

  const {
    data: ownerships,
    loading,
    pagination,
    filters,
    loadList,
    applyFilters,
    resetFilters,
    updatePagination,
  } = useListData<Ownership, OwnershipFilters>({
    fetcher: fetchOwnershipList,
    initialFilters: {
      keyword: '',
      isActive: null,
    },
    initialPageSize: 10,
    onError: () => {
      MessageManager.error('加载权属方列表失败');
    },
  });

  const loadStatistics = useCallback(async () => {
    try {
      const stats = await ownershipService.getOwnershipStatistics();
      setStatistics(stats);
    } catch {
      componentLogger.warn('加载统计信息失败');
    }
  }, []);

  useEffect(() => {
    void loadList();
    void loadStatistics();
  }, [loadList, loadStatistics]);

  const handleRefresh = useCallback(() => {
    void loadList();
    void loadStatistics();
  }, [loadList, loadStatistics]);

  const handleKeywordChange = useCallback(
    (value: string) => {
      applyFilters({
        keyword: value,
        isActive: filters.isActive,
      });
    },
    [applyFilters, filters.isActive]
  );

  const handleStatusChange = useCallback(
    (value: boolean | undefined) => {
      applyFilters({
        keyword: filters.keyword,
        isActive: value === undefined ? null : value,
      });
    },
    [applyFilters, filters.keyword]
  );

  const handleReset = useCallback(() => {
    resetFilters();
  }, [resetFilters]);

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
          void loadList();
          void loadStatistics();
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
      void loadList();
      void loadStatistics();
    } catch {
      MessageManager.error('操作失败');
    }
  };

  // 表单提交成功
  const handleFormSuccess = () => {
    setFormVisible(false);
    void loadList();
    void loadStatistics();
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
        <Button type="link" onClick={() => handleView(record)} style={{ padding: 0 }}>
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
        <Space size="small">
          {mode === 'select' && (
            <Button type="primary" size="small" onClick={() => handleSelect(record)}>
              选择
            </Button>
          )}
          {mode === 'list' && (
            <>
              <Tooltip title="查看详情">
                <Button type="text" icon={<EyeOutlined />} onClick={() => handleView(record)} />
              </Tooltip>
              <Tooltip title="编辑">
                <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
              </Tooltip>
              <Tooltip title="删除">
                <Button
                  type="text"
                  danger
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
          />
        </Space>
      ),
    },
  ];

  return (
    <div className="ownership-list">
      {/* 统计卡片 */}
      {mode === 'list' && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="总数量"
                value={derivedStatistics.total_count}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="启用数量"
                value={derivedStatistics.active_count}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="禁用数量"
                value={derivedStatistics.inactive_count}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="关联资产"
                value={ownerships.reduce((sum, ownership) => sum + (ownership.asset_count ?? 0), 0)}
                valueStyle={{ color: '#722ed1' }}
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
                style={{ width: '100%' }}
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
                style={{ width: '100%' }}
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
              <Space>
                <Button onClick={handleReset}>重置</Button>
              </Space>
            ),
          },
          {
            key: 'actions',
            col: { xs: 24, sm: 12, md: 6, lg: 4 },
            content: (
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                  新建权属方
                </Button>
                <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
                  刷新
                </Button>
              </Space>
            ),
          },
        ]}
      />

      {/* 权属方表格 */}
      <Card>
        <TableWithPagination
          columns={columns}
          dataSource={ownerships}
          rowKey="id"
          loading={loading}
          paginationState={pagination}
          onPageChange={updatePagination}
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
