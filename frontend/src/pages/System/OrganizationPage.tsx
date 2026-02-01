import React, { useState, useEffect, useCallback } from 'react';
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
  Tooltip,
  Row,
  Col,
  Statistic,
  Tree,
  Tabs,
  Divider,
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
import { useListData } from '@/hooks/useListData';
import { useArrayListData } from '@/hooks/useArrayListData';
// 组织表单数据类型
interface OrganizationFormData {
  name: string;
  code: string;
  type: 'company' | 'department' | 'group' | 'division' | 'team' | 'branch' | 'office';
  parent_id?: string;
  description?: string;
  status: 'active' | 'inactive' | 'suspended';
  sort_order?: number;
}

const { Option } = Select;
const { TabPane } = Tabs;
const { Search } = Input;

interface OrganizationFilters {
  keyword: string;
}

const OrganizationPage: React.FC = () => {
  const [organizationTree, setOrganizationTree] = useState<DataNode[]>([]);
  const [statistics, setStatistics] = useState<OrganizationStatistics | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [historyModalVisible, setHistoryModalVisible] = useState(false);
  const [editingOrganization, setEditingOrganization] = useState<Organization | null>(null);
  const [selectedOrganization, setSelectedOrganization] = useState<Organization | null>(null);
  const [organizationHistory, setOrganizationHistory] = useState<OrganizationHistory[]>([]);
  const [activeTab, setActiveTab] = useState('list');

  const [form] = Form.useForm();

  // 组织类型选项
  const organizationTypes = [
    { value: 'company', label: '公司', icon: <BankOutlined /> },
    { value: 'department', label: '部门', icon: <TeamOutlined /> },
    { value: 'group', label: '集团', icon: <ApartmentOutlined /> },
    { value: 'division', label: '事业部', icon: <PartitionOutlined /> },
    { value: 'team', label: '团队', icon: <TeamOutlined /> },
    { value: 'branch', label: '分公司', icon: <BankOutlined /> },
    { value: 'office', label: '办事处', icon: <SettingOutlined /> },
  ];

  // 状态选项
  const statusOptions = [
    { value: 'active', label: '活跃', color: 'green' },
    { value: 'inactive', label: '停用', color: 'red' },
    { value: 'suspended', label: '暂停', color: 'orange' },
  ];

  const fetchOrganizationList = useCallback(
    async ({
      page,
      pageSize,
      keyword,
    }: {
      page: number;
      pageSize: number;
    } & OrganizationFilters) => {
      const trimmedKeyword = keyword.trim();
      const data =
        trimmedKeyword !== ''
          ? await organizationService.searchOrganizations(trimmedKeyword, {
              page,
              page_size: pageSize,
            })
          : await organizationService.getOrganizations({ page, page_size: pageSize });
      return { items: data, total: data.length };
    },
    []
  );

  const handleLoadError = useCallback(() => {
    MessageManager.error('加载组织列表失败');
  }, []);

  const {
    data: organizations,
    loading,
    pagination,
    filters,
    loadList,
    applyFilters,
    updatePagination,
  } = useListData<Organization, OrganizationFilters>({
    fetcher: fetchOrganizationList,
    initialFilters: {
      keyword: '',
    },
    initialPageSize: 10,
    onError: handleLoadError,
  });

  const loadOrganizationTree = useCallback(async () => {
    try {
      const data = await organizationService.getOrganizationTree();
      setOrganizationTree(convertTreeToDataNodes(data));
    } catch {
      MessageManager.error('加载组织树失败');
    }
  }, []);

  const loadStatistics = useCallback(async () => {
    try {
      const data = await organizationService.getStatistics();
      setStatistics(data);
    } catch {
      MessageManager.error('加载统计信息失败');
    }
  }, []);

  useEffect(() => {
    void loadList();
    void loadOrganizationTree();
    void loadStatistics();
  }, [loadList, loadOrganizationTree, loadStatistics]);

  const _convertToTreeData = (organizations: Organization[]): DataNode[] => {
    return organizations.map(org => ({
      key: org.id,
      title: (
        <span>
          {getTypeIcon(org.type)} {org.name} ({org.code})
          <Tag color={getStatusColor(org.status)} style={{ marginLeft: 8 }}>
            {getStatusLabel(org.status)}
          </Tag>
        </span>
      ),
      children:
        org.children != null && org.children.length > 0 ? _convertToTreeData(org.children) : [],
    }));
  };

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
    const typeConfig = organizationTypes.find(t => t.value === type);
    return typeConfig?.icon || <TeamOutlined />;
  };

  const getStatusColor = (status: string) => {
    const statusConfig = statusOptions.find(s => s.value === status);
    return statusConfig?.color ?? 'default';
  };

  const getStatusLabel = (status: string) => {
    const statusConfig = statusOptions.find(s => s.value === status);
    return statusConfig?.label ?? status;
  };

  const handleSearch = useCallback(
    (keyword: string) => {
      applyFilters({
        keyword,
      });
    },
    [applyFilters]
  );

  const handleRefresh = useCallback(() => {
    void loadList();
    void loadOrganizationTree();
    void loadStatistics();
  }, [loadList, loadOrganizationTree, loadStatistics]);

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
      render: type => {
        const typeConfig = organizationTypes.find(t => t.value === type);
        return typeConfig?.label ?? type;
      },
    },
    {
      title: '层级',
      dataIndex: 'level',
      key: 'level',
      render: level => <Badge count={level} color="blue" />,
    },
    {
      title: '负责人',
      dataIndex: 'leader_name',
      key: 'leader_name',
      render: (name, record) =>
        name != null ? (
          <Tooltip
            title={`电话: ${record.leader_phone ?? '未设置'} | 邮箱: ${record.leader_email ?? '未设置'}`}
          >
            <span>{name}</span>
          </Tooltip>
        ) : (
          '-'
        ),
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
                valueStyle={{ color: COLORS.success }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="停用组织"
                value={statistics.inactive}
                prefix={<SettingOutlined />}
                valueStyle={{ color: COLORS.error }}
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
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="列表视图" key="list">
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
              onPageChange={updatePagination}
              paginationProps={{
                showTotal: (total: number) => `共 ${total} 条记录`,
              }}
            />
          </TabPane>

          <TabPane tab="树形视图" key="tree">
            <div style={{ marginBottom: 16 }}>
              <Button icon={<ReloadOutlined />} onClick={loadOrganizationTree}>
                刷新树形结构
              </Button>
            </div>

            <Tree
              treeData={organizationTree}
              showLine={{ showLeafIcon: false }}
              defaultExpandAll
              style={{ background: COLORS.bgSecondary, padding: 16, borderRadius: 6 }}
            />
          </TabPane>
        </Tabs>
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
                <Select placeholder="请选择组织类型">
                  {organizationTypes.map(type => (
                    <Option key={type.value} value={type.value}>
                      {type.icon} {type.label}
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
                <Select placeholder="请选择状态">
                  {statusOptions.map(status => (
                    <Option key={status.value} value={status.value}>
                      <Tag color={status.color}>{status.label}</Tag>
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

          <Divider titlePlacement="start">负责人信息</Divider>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="leader_name" label="负责人姓名">
                <Input placeholder="请输入负责人姓名" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="leader_phone" label="负责人电话">
                <Input placeholder="请输入负责人电话" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="leader_email"
                label="负责人邮箱"
                rules={[{ type: 'email', message: '请输入正确的邮箱格式' }]}
              >
                <Input placeholder="请输入负责人邮箱" />
              </Form.Item>
            </Col>
          </Row>

          <Divider titlePlacement="start">联系信息</Divider>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="phone" label="组织电话">
                <Input placeholder="请输入组织电话" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="email"
                label="组织邮箱"
                rules={[{ type: 'email', message: '请输入正确的邮箱格式' }]}
              >
                <Input placeholder="请输入组织邮箱" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="address" label="组织地址">
                <Input placeholder="请输入组织地址" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="组织描述">
            <Input.TextArea rows={3} placeholder="请输入组织描述" />
          </Form.Item>

          <Form.Item name="functions" label="主要职能">
            <Input.TextArea rows={3} placeholder="请输入主要职能" />
          </Form.Item>

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
