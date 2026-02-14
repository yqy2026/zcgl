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
import PageContainer from '@/components/Common/PageContainer';
import { useQuery } from '@tanstack/react-query';
import { useArrayListData } from '@/hooks/useArrayListData';
import { useDictionary } from '@/hooks/useDictionary';
import styles from './OrganizationPage.module.css';
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

type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';

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
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
    neutral: styles.toneNeutral,
  };

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

  const getToneClassName = useCallback(
    (tone: Tone): string => {
      return toneClassMap[tone];
    },
    [toneClassMap]
  );

  const statusToneMap = useMemo(() => {
    const map = new Map<string, Tone>();
    organizationStatusOptions.forEach(option => {
      const rawColor = typeof option.color === 'string' ? option.color.toLowerCase() : '';
      if (rawColor.includes('green')) {
        map.set(option.value, 'success');
        return;
      }
      if (rawColor.includes('red')) {
        map.set(option.value, 'error');
        return;
      }
      if (rawColor.includes('orange') || rawColor.includes('yellow')) {
        map.set(option.value, 'warning');
        return;
      }
      if (rawColor.includes('blue')) {
        map.set(option.value, 'primary');
        return;
      }
      map.set(option.value, 'neutral');
    });
    if (!map.has('active')) {
      map.set('active', 'success');
    }
    if (!map.has('inactive')) {
      map.set('inactive', 'error');
    }
    if (!map.has('suspended')) {
      map.set('suspended', 'warning');
    }
    return map;
  }, [organizationStatusOptions]);

  const getStatusTone = useCallback(
    (status: string): Tone => {
      return statusToneMap.get(status) ?? 'neutral';
    },
    [statusToneMap]
  );

  const getStatusLabel = useCallback(
    (status: string): string => {
      return statusLabelMap.get(status) ?? status;
    },
    [statusLabelMap]
  );

  const getStatusTag = useCallback(
    (status: string, className?: string) => {
      const toneClassName = getToneClassName(getStatusTone(status));
      const extraClassName = className == null ? '' : ` ${className}`;
      return (
        <Tag className={`${styles.statusTag} ${toneClassName}${extraClassName}`}>
          {getStatusLabel(status)}
        </Tag>
      );
    },
    [getStatusLabel, getStatusTone, getToneClassName]
  );

  const convertTreeToDataNodes = (treeNodes: OrganizationTree[]): DataNode[] => {
    return treeNodes.map(node => ({
      key: node.id,
      title: (
        <span className={styles.treeNodeLabel}>
          <span className={styles.treeNodeTitle}>
            {getTypeIcon(node.type)} {node.name} ({node.code})
          </span>
          {getStatusTag(node.status, styles.treeStatusTag)}
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
    isFetching: isOrganizationTreeFetching,
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
  const activeFilterCount = useMemo(() => {
    if (filters.keyword.trim() !== '') {
      return 1;
    }
    return 0;
  }, [filters.keyword]);

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
        <Space className={styles.nameCell}>
          {getTypeIcon(record.type)}
          <span className={styles.primaryText}>{text}</span>
          <Tag className={`${styles.codeTag} ${styles.tonePrimary}`}>{record.code}</Tag>
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
      render: status => getStatusTag(status),
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
        <Space size={4} className={styles.tableActionGroup}>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            className={styles.tableActionButton}
            aria-label={`编辑组织 ${record.name}`}
          >
            编辑
          </Button>
          <Button
            type="text"
            icon={<HistoryOutlined />}
            onClick={() => handleViewHistory(record)}
            className={styles.tableActionButton}
            aria-label={`查看组织 ${record.name} 历史`}
          >
            历史
          </Button>
          <Popconfirm
            title="确定要删除这个组织吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              className={styles.tableActionButton}
              aria-label={`删除组织 ${record.name}`}
            >
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
        const actionMap: { [key: string]: { label: string; tone: Tone } } = {
          create: { label: '创建', tone: 'success' },
          update: { label: '更新', tone: 'primary' },
          delete: { label: '删除', tone: 'error' },
        };
        const config = actionMap[action] ?? { label: action ?? '未知', tone: 'neutral' };
        return (
          <Tag className={`${styles.statusTag} ${styles.historyActionTag} ${getToneClassName(config.tone)}`}>
            {config.label}
          </Tag>
        );
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
          <div className={styles.toolbarSection}>
            <div className={styles.filterSummary} aria-live="polite">
              <span className={styles.secondaryText}>共 {pagination.total} 条组织记录</span>
              <span className={styles.secondaryText}>
                {activeFilterCount > 0 ? `已启用 ${activeFilterCount} 项筛选` : '未启用筛选条件'}
              </span>
            </div>
            <Row justify="space-between" gutter={[12, 12]}>
              <Col>
                <Space className={styles.toolbarActions} wrap>
                  <Search
                    placeholder="搜索组织名称、编码或描述"
                    allowClear
                    className={styles.searchInput}
                    onSearch={handleSearch}
                    value={filters.keyword}
                    onChange={event => handleSearch(event.target.value)}
                  />
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={handleRefresh}
                    loading={loading}
                    disabled={loading}
                    className={styles.actionButton}
                    aria-label="刷新组织列表"
                  >
                    刷新
                  </Button>
                </Space>
              </Col>
              <Col>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreate}
                  className={styles.actionButton}
                  aria-label="新建组织"
                >
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
          <div className={styles.toolbarSection}>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void refetchOrganizationTree()}
              loading={isOrganizationTreeFetching}
              disabled={isOrganizationTreeFetching}
              className={styles.actionButton}
              aria-label="刷新组织树结构"
            >
              刷新树形结构
            </Button>
          </div>

          <Tree
            treeData={organizationTree}
            showLine={{ showLeafIcon: false }}
            defaultExpandAll
            className={styles.treePanel}
          />
        </>
      ),
    },
  ];

  return (
    <PageContainer className={styles.pageShell} title="组织管理" subTitle="维护组织结构、层级关系与组织历史记录">
      {/* 统计卡片 */}
      {statistics != null && (
        <Row gutter={16} className={styles.statsRow}>
          <Col xs={24} sm={12} md={6}>
            <Card className={styles.statsCard}>
              <Statistic title="总组织数" value={statistics.total} prefix={<ApartmentOutlined />} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={`${styles.statsCard} ${styles.toneSuccess}`}>
              <Statistic title="活跃组织" value={statistics.active} prefix={<TeamOutlined />} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={`${styles.statsCard} ${styles.toneError}`}>
              <Statistic title="停用组织" value={statistics.inactive} prefix={<SettingOutlined />} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={styles.statsCard}>
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
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} className={styles.tabs} />
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
            <Col xs={24} sm={12}>
              <Form.Item
                name="name"
                label="组织名称"
                rules={[{ required: true, message: '请输入组织名称' }]}
              >
                <Input placeholder="请输入组织名称" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
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
            <Col xs={24} sm={12} md={8}>
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
            <Col xs={24} sm={12} md={8}>
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
                      {getStatusTag(status.value)}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item name="sort_order" label="排序">
                <InputNumber min={0} placeholder="排序号" className={styles.fullWidthControl} />
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
            <Card size="small" title="系统字段" className={styles.systemFieldsCard}>
              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item label="组织路径" className={styles.compactFieldItem}>
                    <Input value={editingOrganization.path ?? '-'} disabled />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="创建人" className={styles.compactFieldLastItem}>
                    <Input value={editingOrganization.created_by ?? '-'} disabled />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="更新人" className={styles.compactFieldLastItem}>
                    <Input value={editingOrganization.updated_by ?? '-'} disabled />
                  </Form.Item>
                </Col>
              </Row>
            </Card>
          )}

          <Form.Item className={styles.formActions}>
            <Space size={8} className={styles.formActionGroup}>
              <Button
                onClick={() => setModalVisible(false)}
                className={`${styles.actionButton} ${styles.modalActionButton}`}
              >
                取消
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                className={`${styles.actionButton} ${styles.modalActionButton}`}
              >
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
    </PageContainer>
  );
};

export default OrganizationPage;
