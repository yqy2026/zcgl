import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Card,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  TreeSelect,
  InputNumber,
  Popconfirm,
  Tag,
  Row,
  Col,
  Statistic,
  Tree,
  Tabs,
  Badge,
} from 'antd';
import { COLORS } from '@/styles/colorMap';
import { MessageManager } from '@/utils/messageManager';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  PartitionOutlined,
  TeamOutlined,
  BankOutlined,
  ApartmentOutlined,
  SettingOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { DataNode } from 'antd/es/tree';
import {
  Organization,
  OrganizationStatistics,
  OrganizationHistory,
  OrganizationTree,
} from '@/types/organization';
import { organizationService } from '@/services/organizationService';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { useQuery } from '@tanstack/react-query';
import { useArrayListData } from '@/hooks/useArrayListData';
import { useDictionary } from '@/hooks/useDictionary';
// 组织表单数据类型
interface OrganizationFormData {
  name: string;
  code: string;
  type: string;
  parent_id?: string;
  description?: string;
  status: string;
  sort_order?: number;
}

const { Option } = Select;
const { Search } = Input;

interface OrganizationFilters {
  keyword: string;
}

interface OrganizationListQueryResult {
  items: Organization[];
  total: number;
}

const OrganizationPage: React.FC = () => {
  const [filters, setFilters] = useState<OrganizationFilters>({
    keyword: '',
  });
  const [paginationState, setPaginationState] = useState({
    current: 1,
    pageSize: 10,
  });
  const [modalVisible, setModalVisible] = useState(false);
  const [historyModalVisible, setHistoryModalVisible] = useState(false);
  const [editingOrganization, setEditingOrganization] = useState<Organization | null>(null);
  const [selectedOrganization, setSelectedOrganization] = useState<Organization | null>(null);
  const [organizationHistory, setOrganizationHistory] = useState<OrganizationHistory[]>([]);
  const [activeTab, setActiveTab] = useState('list');

  const [form] = Form.useForm();

  const { options: organizationTypeOptions, isLoading: isTypeOptionsLoading } =
    useDictionary('organization_type');
  const { options: organizationStatusOptions, isLoading: isStatusOptionsLoading } =
    useDictionary('organization_status');

  const typeIconMap = useMemo(
    () => ({
      company: <BankOutlined />,
      department: <TeamOutlined />,
      group: <ApartmentOutlined />,
      division: <PartitionOutlined />,
      team: <TeamOutlined />,
      branch: <BankOutlined />,
      office: <SettingOutlined />,
    }),
    []
  );

  const typeLabelMap = useMemo(() => {
    const map = new Map<string, string>();
    organizationTypeOptions.forEach(option => {
      map.set(option.value, option.label);
    });
    return map;
  }, [organizationTypeOptions]);

  const statusLabelMap = useMemo(() => {
    const map = new Map<string, string>();
    organizationStatusOptions.forEach(option => {
      map.set(option.value, option.label);
    });
    return map;
  }, [organizationStatusOptions]);

  const statusColorMap = useMemo(() => {
    const map = new Map<string, string>();
    organizationStatusOptions.forEach(option => {
      const rawColor = option.color;
      if (typeof rawColor === 'string' && rawColor.trim() !== '') {
        map.set(option.value, rawColor);
      }
    });

    if (!map.has('active')) {
      map.set('active', 'green');
    }
    if (!map.has('inactive')) {
      map.set('inactive', 'red');
    }
    if (!map.has('suspended')) {
      map.set('suspended', 'orange');
    }

    return map;
  }, [organizationStatusOptions]);

  const convertTreeToDataNodes = (treeNodes: OrganizationTree[]): DataNode[] => {
    return treeNodes.map(node => ({
      key: node.id,
      title: (
        <span>
          {getTypeIcon(node.type)} {node.name} ({node.code})
          <Tag color={getStatusColor(node.status)} style={{ marginLeft: 8 }}>
            {getStatusLabel(node.status)}
          </Tag>
        </span>
      ),
      children:
        node.children != null && node.children.length > 0
          ? convertTreeToDataNodes(node.children)
          : [],
    }));
  };

  const getTypeIcon = (type: string) => {
    return typeIconMap[type as keyof typeof typeIconMap] ?? <TeamOutlined />;
  };

  const getTypeLabel = (type: string) => {
    return typeLabelMap.get(type) ?? type;
  };

  const getStatusColor = (status: string) => {
    return statusColorMap.get(status) ?? 'default';
  };

  const getStatusLabel = (status: string) => {
    return statusLabelMap.get(status) ?? status;
  };

  const fetchOrganizationList = useCallback(async (): Promise<OrganizationListQueryResult> => {
    const trimmedKeyword = filters.keyword.trim();
    const data =
      trimmedKeyword !== ''
        ? await organizationService.searchOrganizations(trimmedKeyword, {
            page: paginationState.current,
            page_size: paginationState.pageSize,
          })
        : await organizationService.getOrganizations({
            page: paginationState.current,
            page_size: paginationState.pageSize,
          });
    return { items: data, total: data.length };
  }, [filters.keyword, paginationState.current, paginationState.pageSize]);

  const {
    data: organizationsResponse,
    error: organizationsError,
    isLoading: isOrganizationsLoading,
    isFetching: isOrganizationsFetching,
    refetch: refetchOrganizations,
  } = useQuery<OrganizationListQueryResult>({
    queryKey: ['organization-list', paginationState.current, paginationState.pageSize, filters],
    queryFn: fetchOrganizationList,
    retry: 1,
  });

  const {
    data: organizationTree = [],
    error: organizationTreeError,
    refetch: refetchOrganizationTree,
  } = useQuery<DataNode[]>({
    queryKey: ['organization-tree'],
    queryFn: async () => {
      const data = await organizationService.getOrganizationTree();
      return convertTreeToDataNodes(data);
    },
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const {
    data: statistics = null,
    error: statisticsError,
    refetch: refetchStatistics,
  } = useQuery<OrganizationStatistics>({
    queryKey: ['organization-statistics'],
    queryFn: () => organizationService.getStatistics(),
    staleTime: 60 * 1000,
    retry: 1,
  });

  useEffect(() => {
    if (organizationsError != null) {
      MessageManager.error('加载组织列表失败');
    }
  }, [organizationsError]);

  useEffect(() => {
    if (organizationTreeError != null) {
      MessageManager.error('加载组织树失败');
    }
  }, [organizationTreeError]);

  useEffect(() => {
    if (statisticsError != null) {
      MessageManager.error('加载统计信息失败');
    }
  }, [statisticsError]);

  const organizations = organizationsResponse?.items ?? [];
  const loading = isOrganizationsLoading || isOrganizationsFetching;
  const pagination = useMemo(
    () => ({
      current: paginationState.current,
      pageSize: paginationState.pageSize,
      total: organizationsResponse?.total ?? 0,
    }),
    [organizationsResponse?.total, paginationState.current, paginationState.pageSize]
  );

  const refreshOrganizations = useCallback(() => {
    void refetchOrganizations();
    void refetchOrganizationTree();
    void refetchStatistics();
  }, [refetchOrganizationTree, refetchOrganizations, refetchStatistics]);

  const handleSearch = useCallback((keyword: string) => {
    setFilters({ keyword });
    setPaginationState(prev => ({ ...prev, current: 1 }));
  }, []);

  const handlePageChange = useCallback((next: { current?: number; pageSize?: number }) => {
    setPaginationState(prev => ({
      current: next.current ?? prev.current,
      pageSize: next.pageSize ?? prev.pageSize,
    }));
  }, []);

  const handleRefresh = useCallback(() => {
    refreshOrganizations();
  }, [refreshOrganizations]);

  const handleCreate = () => {
    setEditingOrganization(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (organization: Organization) => {
    setEditingOrganization(organization);
    form.setFieldsValue({
      ...organization,
      parent_id: organization.parent_id ?? undefined,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await organizationService.deleteOrganization(id);
      MessageManager.success('删除成功');
      void handleRefresh();
    } catch {
      MessageManager.error('删除失败');
    }
  };

  const handleViewHistory = async (organization: Organization) => {
    setSelectedOrganization(organization);
    try {
      const history = await organizationService.getOrganizationHistory(organization.id);
      setOrganizationHistory(history);
      setHistoryModalVisible(true);
    } catch {
      MessageManager.error('加载历史记录失败');
    }
  };

  const {
    data: historyPageItems,
    pagination: historyPagination,
    loadList: loadHistoryList,
    updatePagination: updateHistoryPagination,
  } = useArrayListData<OrganizationHistory, Record<string, never>>({
    items: organizationHistory,
    initialFilters: {},
    initialPageSize: 10,
  });

  useEffect(() => {
    void loadHistoryList({ page: 1 });
  }, [loadHistoryList, organizationHistory]);

  const handleSubmit = async (values: OrganizationFormData) => {
    try {
      if (editingOrganization) {
        await organizationService.updateOrganization(editingOrganization.id, values);
        MessageManager.success('更新成功');
      } else {
        await organizationService.createOrganization(values);
        MessageManager.success('创建成功');
      }
      setModalVisible(false);
      void handleRefresh();
    } catch {
      MessageManager.error(editingOrganization ? '更新失败' : '创建失败');
    }
  };

  const columns: ColumnsType<Organization> = [
    {
      title: '组织名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          {getTypeIcon(record.type)}
          <span>{text}</span>
          <Tag color="blue">{record.code}</Tag>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: type => getTypeLabel(type),
    },
    {
      title: '层级',
      dataIndex: 'level',
      key: 'level',
      render: level => <Badge count={level} color="blue" />,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: status => <Tag color={getStatusColor(status)}>{getStatusLabel(status)}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: date => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Button type="link" icon={<HistoryOutlined />} onClick={() => handleViewHistory(record)}>
            历史
          </Button>
          <Popconfirm
            title="确定要删除这个组织吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const historyColumns: ColumnsType<OrganizationHistory> = [
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      render: action => {
        const actionMap: { [key: string]: { label: string; color: string } } = {
          create: { label: '创建', color: 'green' },
          update: { label: '更新', color: 'blue' },
          delete: { label: '删除', color: 'red' },
        };
        const config = actionMap[action] ?? { label: action ?? '未知', color: 'default' };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '字段名称',
      dataIndex: 'field_name',
      key: 'field_name',
      render: field => field ?? '-',
    },
    {
      title: '原值',
      dataIndex: 'old_value',
      key: 'old_value',
      render: value => value ?? '-',
    },
    {
      title: '新值',
      dataIndex: 'new_value',
      key: 'new_value',
      render: value => value ?? '-',
    },
    {
      title: '操作人',
      dataIndex: 'created_by',
      key: 'created_by',
      render: user => user ?? '系统',
    },
    {
      title: '操作时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: date => new Date(date).toLocaleString(),
    },
  ];

  const tabItems = [
    {
      key: 'list',
      label: '列表视图',
      children: (
        <>
          <div style={{ marginBottom: 16 }}>
            <Row justify="space-between">
              <Col>
                <Space>
                  <Search
                    placeholder="搜索组织名称、编码或描述"
                    allowClear
                    style={{ width: 300 }}
                    onSearch={handleSearch}
                    value={filters.keyword}
                    onChange={event => handleSearch(event.target.value)}
                  />
                  <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
                    刷新
                  </Button>
                </Space>
              </Col>
              <Col>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                  新建组织
                </Button>
              </Col>
            </Row>
          </div>

          <TableWithPagination
            columns={columns}
            dataSource={organizations}
            rowKey="id"
            loading={loading}
            paginationState={pagination}
            onPageChange={handlePageChange}
            paginationProps={{
              showTotal: (total: number) => `共 ${total} 条记录`,
            }}
          />
        </>
      ),
    },
    {
      key: 'tree',
      label: '树形视图',
      children: (
        <>
          <div style={{ marginBottom: 16 }}>
            <Button icon={<ReloadOutlined />} onClick={() => void refetchOrganizationTree()}>
              刷新树形结构
            </Button>
          </div>

          <Tree
            treeData={organizationTree}
            showLine={{ showLeafIcon: false }}
            defaultExpandAll
            style={{ background: COLORS.bgSecondary, padding: 16, borderRadius: 6 }}
          />
        </>
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
              <Statistic title="总组织数" value={statistics.total} prefix={<ApartmentOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="活跃组织"
                value={statistics.active}
                prefix={<TeamOutlined />}
                styles={{ content: { color: COLORS.success } }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="停用组织"
                value={statistics.inactive}
                prefix={<SettingOutlined />}
                styles={{ content: { color: COLORS.error } }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="组织类型"
                value={Object.keys(statistics.by_type).length}
                prefix={<PartitionOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>

      {/* 创建/编辑模态框 */}
      <Modal
        title={editingOrganization ? '编辑组织' : '新建组织'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={800}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="组织名称"
                rules={[{ required: true, message: '请输入组织名称' }]}
              >
                <Input placeholder="请输入组织名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="code"
                label="组织编码"
                rules={[
                  { required: true, message: '请输入组织编码' },
                  {
                    pattern: /^[A-Z0-9_-]+$/,
                    message: '编码只能包含大写字母、数字、下划线和连字符',
                  },
                ]}
              >
                <Input placeholder="请输入组织编码" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="type"
                label="组织类型"
                rules={[{ required: true, message: '请选择组织类型' }]}
              >
                <Select
                  placeholder="请选择组织类型"
                  loading={isTypeOptionsLoading === true}
                >
                  {organizationTypeOptions.map(type => (
                    <Option key={type.value} value={type.value}>
                      {getTypeIcon(type.value)} {type.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="status"
                label="状态"
                rules={[{ required: true, message: '请选择状态' }]}
              >
                <Select
                  placeholder="请选择状态"
                  loading={isStatusOptionsLoading === true}
                >
                  {organizationStatusOptions.map(status => (
                    <Option key={status.value} value={status.value}>
                      <Tag color={getStatusColor(status.value)}>{status.label}</Tag>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sort_order" label="排序">
                <InputNumber min={0} placeholder="排序号" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="parent_id" label="上级组织">
            <TreeSelect
              placeholder="请选择上级组织"
              allowClear
              treeData={organizationTree}
              treeDefaultExpandAll
            />
          </Form.Item>

          <Form.Item name="description" label="组织描述">
            <Input.TextArea rows={3} placeholder="请输入组织描述" />
          </Form.Item>

          {editingOrganization != null && (
            <Card size="small" title="系统字段" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item label="组织路径" style={{ marginBottom: 12 }}>
                    <Input value={editingOrganization.path ?? '-'} disabled />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="创建人" style={{ marginBottom: 0 }}>
                    <Input value={editingOrganization.created_by ?? '-'} disabled />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="更新人" style={{ marginBottom: 0 }}>
                    <Input value={editingOrganization.updated_by ?? '-'} disabled />
                  </Form.Item>
                </Col>
              </Row>
            </Card>
          )}

          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                {editingOrganization ? '更新' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 历史记录模态框 */}
      <Modal
        title={`组织历史记录 - ${selectedOrganization?.name}`}
        open={historyModalVisible}
        onCancel={() => setHistoryModalVisible(false)}
        footer={null}
        width={1000}
      >
        <TableWithPagination
          columns={historyColumns}
          dataSource={historyPageItems}
          rowKey="id"
          paginationState={historyPagination}
          onPageChange={updateHistoryPagination}
          paginationProps={{
            showSizeChanger: true,
            showTotal: (total: number) => `共 ${total} 条记录`,
          }}
        />
      </Modal>
    </div>
  );
};

export default OrganizationPage;
