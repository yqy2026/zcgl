/**
 * 权属方列表组件
 */

import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Tooltip,
  Modal,
  message,
  Card,
  Row,
  Col,
  Statistic,
  Badge,
  Input,
  Select,
  Switch,
  Pagination
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  SearchOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

import { ownershipService } from '@/services/ownershipService';
import type { Ownership, OwnershipListResponse, OwnershipStatisticsResponse } from '@/types/ownership';
import OwnershipForm from './OwnershipForm';
import OwnershipDetail from './OwnershipDetail';

const { Search } = Input;
const { Option } = Select;
const { confirm } = Modal;

interface OwnershipListProps {
  onSelectOwnership?: (ownership: Ownership) => void;
  mode?: 'list' | 'select';
}

const OwnershipList: React.FC<OwnershipListProps> = ({
  onSelectOwnership,
  mode = 'list'
}) => {
  const [ownerships, setOwnerships] = useState<Ownership[]>([]);
  const [loading, setLoading] = useState(false);
  const [statistics, setStatistics] = useState<OwnershipStatisticsResponse | null>(null);
  const [total, setTotal] = useState(0);
  const [current, setCurrent] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // 搜索和筛选状态
  const [keyword, setKeyword] = useState('');
  const [isActive, setIsActive] = useState<boolean | undefined>(undefined);

  // 模态框状态
  const [formVisible, setFormVisible] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [editingOwnership, setEditingOwnership] = useState<Ownership | null>(null);
  const [viewingOwnership, setViewingOwnership] = useState<Ownership | null>(null);

  // 加载权属方列表
  const loadOwnerships = async () => {
    setLoading(true);
    try {
      const response: OwnershipListResponse = await ownershipService.getOwnerships({
        keyword,
        is_active: isActive,
        page: current,
        size: pageSize
      });
      setOwnerships(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('加载权属方列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 加载统计信息
  const loadStatistics = async () => {
    try {
      const stats = await ownershipService.getOwnershipStatistics();
      setStatistics(stats);
    } catch (error) {
      console.error('加载统计信息失败:', error);
    }
  };


  useEffect(() => {
    loadOwnerships();
    loadStatistics();
  }, [current, pageSize]);

  useEffect(() => {
    setCurrent(1);
    loadOwnerships();
  }, [keyword, isActive]);

  // 刷新列表
  const handleRefresh = () => {
    loadOwnerships();
    loadStatistics();
  };

  // 搜索
  const handleSearch = () => {
    setCurrent(1);
    loadOwnerships();
  };

  // 重置筛选
  const handleReset = () => {
    setKeyword('');
    setIsActive(undefined);
    setCurrent(1);
  };

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
          message.success('删除成功');
          loadOwnerships();
          loadStatistics();
        } catch (error: any) {
          message.error(error.message || '删除失败');
        }
      }
    });
  };

  // 切换状态
  const handleToggleStatus = async (record: Ownership) => {
    try {
      await ownershipService.toggleOwnershipStatus(record.id);
      message.success(`${record.is_active ? '禁用' : '启用'}成功`);
      loadOwnerships();
      loadStatistics();
    } catch (error) {
      message.error('操作失败');
    }
  };

  // 表单提交成功
  const handleFormSuccess = () => {
    setFormVisible(false);
    loadOwnerships();
    loadStatistics();
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
        <Button
          type="link"
          onClick={() => handleView(record)}
          style={{ padding: 0 }}
        >
          {text}
        </Button>
      )
    },
    {
      title: '权属方编码',
      dataIndex: 'code',
      key: 'code',
      width: 120,
      render: (text: string) => text || '-'
    },
    {
      title: '权属方简称',
      dataIndex: 'short_name',
      key: 'short_name',
      width: 150,
      render: (text: string) => text || '-'
    },
    {
      title: '关联资产',
      dataIndex: 'asset_count',
      key: 'asset_count',
      width: 100,
      render: (count: number) => count || 0
    },
    {
      title: '关联项目',
      dataIndex: 'project_count',
      key: 'project_count',
      width: 100,
      render: (count: number) => count || 0
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Badge
          status={active ? 'success' : 'error'}
          text={active ? '启用' : '禁用'}
        />
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record: Ownership) => (
        <Space size="small">
          {mode === 'select' && (
            <Button
              type="primary"
              size="small"
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
                  icon={<EyeOutlined />}
                  onClick={() => handleView(record)}
                />
              </Tooltip>
              <Tooltip title="编辑">
                <Button
                  type="text"
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(record)}
                />
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
      )
    }
  ];

  return (
    <div className="ownership-list">
      {/* 统计卡片 */}
      {statistics && mode === 'list' && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="总数量"
                value={statistics.total_count}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="启用数量"
                value={statistics.active_count}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="禁用数量"
                value={statistics.inactive_count}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="关联资产"
                value={ownerships.reduce((sum, ownership) => sum + (ownership.asset_count || 0), 0)}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 搜索和操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} md={8} lg={6}>
            <Search
              placeholder="搜索权属方名称、简称等"
              allowClear
              enterButton={<SearchOutlined />}
              style={{ width: '100%' }}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onSearch={handleSearch}
            />
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Select
              placeholder="状态"
              allowClear
              style={{ width: '100%' }}
              value={isActive === undefined ? undefined : isActive}
              onChange={setIsActive}
            >
              <Option value={true}>启用</Option>
              <Option value={false}>禁用</Option>
            </Select>
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Space>
              <Button onClick={handleReset}>重置</Button>
            </Space>
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreate}
              >
                新建权属方
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={loading}
              >
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 权属方表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={ownerships}
          rowKey="id"
          loading={loading}
          pagination={{
            current,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条/共 ${total} 条`,
            onChange: (page, size) => {
              setCurrent(page);
              setPageSize(size || 10);
            }
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
        destroyOnClose
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
        destroyOnClose
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