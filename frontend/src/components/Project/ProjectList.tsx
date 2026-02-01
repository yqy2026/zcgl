/**
 * 项目列表组件 - 精简版本
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Space,
  Tag,
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

import { projectService } from '@/services/projectService';
import { ownershipService } from '@/services/ownershipService';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { ListToolbar } from '@/components/Common/ListToolbar';
import { useListData } from '@/hooks/useListData';
import type {
  Project,
  ProjectStatisticsResponse,
} from '@/types/project';
import type { Ownership } from '@/types/ownership';
import { ProjectForm } from '@/components/Forms';
import ProjectDetail from './ProjectDetail';
// import OwnershipSelect from '@/components/Ownership/OwnershipSelect';

// 项目查询参数接口
interface ProjectQueryParams {
  page: number;
  page_size: number;
  keyword?: string;
  is_active?: boolean;
  ownership_id?: string;
}

interface ProjectFilters {
  keyword: string;
  isActive: boolean | null;
  ownershipId: string;
}

const { Search } = Input;
const { Option } = Select;
const { confirm } = Modal;

interface ProjectListProps {
  onSelectProject?: (project: Project) => void;
  mode?: 'list' | 'select';
}

const ProjectList: React.FC<ProjectListProps> = ({ onSelectProject, mode = 'list' }) => {
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isDetailVisible, setIsDetailVisible] = useState(false);
  const [ownerships, setOwnerships] = useState<Ownership[]>([]);
  const [ownershipsLoading, setOwnershipsLoading] = useState(false);

  const fetchProjectList = useCallback(
    async ({
      page,
      pageSize,
      keyword,
      isActive,
      ownershipId,
    }: {
      page: number;
      pageSize: number;
    } & ProjectFilters) => {
      const params: ProjectQueryParams = {
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

      const trimmedOwnership = ownershipId.trim();
      if (trimmedOwnership !== '') {
        params.ownership_id = trimmedOwnership;
      }

      return await projectService.getProjects(params);
    },
    []
  );

  const {
    data: projects,
    loading,
    pagination,
    filters,
    loadList,
    applyFilters,
    resetFilters: resetListFilters,
    updatePagination,
  } = useListData<Project, ProjectFilters>({
    fetcher: fetchProjectList,
    initialFilters: {
      keyword: '',
      isActive: null,
      ownershipId: '',
    },
    initialPageSize: 10,
    onError: error => {
      // eslint-disable-next-line no-console
      console.error('获取项目列表失败:', error);
      const err = error as Error & { response?: { status?: number; data?: unknown } };
      // eslint-disable-next-line no-console
      console.error('Error details:', {
        message: err.message,
        status: err.response?.status,
        data: err.response?.data,
      });
      MessageManager.error(`获取项目列表失败: ${err.message ?? '未知错误'}`);
    },
  });

  const statistics = useMemo<ProjectStatisticsResponse>(() => {
    const totalCount = projects.length;
    const activeCount = projects.filter(project => project.is_active === true).length;
    return {
      total_count: totalCount,
      active_count: activeCount,
      inactive_count: totalCount - activeCount,
    };
  }, [projects]);

  // 获取权属方列表（使用下拉选项API，更高效）
  const fetchOwnerships = useCallback(async () => {
    setOwnershipsLoading(true);
    try {
      const response = await ownershipService.getOwnershipOptions(true);
      setOwnerships(response);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('获取权属方列表失败:', error);
    } finally {
      setOwnershipsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadList();
    void fetchOwnerships();
  }, [fetchOwnerships, loadList]);

  // 删除项目
  const handleDelete = (project: Project) => {
    confirm({
      title: '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: `确定要删除项目 "${project.name}" 吗？`,
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await projectService.deleteProject(project.id);
          MessageManager.success('项目删除成功');
          void loadList();
        } catch (error) {
          // eslint-disable-next-line no-console
          console.error('删除项目失败:', error);
          MessageManager.error('删除项目失败');
        }
      },
    });
  };

  // 切换项目状态
  const handleToggleStatus = async (project: Project) => {
    try {
      await projectService.toggleProjectStatus(project.id);
      MessageManager.success('项目状态切换成功');
      void loadList();
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('切换项目状态失败:', error);
      MessageManager.error('切换项目状态失败');
    }
  };

  // 查看项目详情
  const handleView = (project: Project) => {
    setSelectedProject(project);
    setIsDetailVisible(true);
  };

  // 编辑项目
  const handleEdit = (project: Project) => {
    setEditingProject(project);
    setIsModalVisible(true);
  };

  // 创建项目
  const handleCreate = () => {
    setEditingProject(null);
    setIsModalVisible(true);
  };

  // 选择项目（在选择模式下）
  const handleSelect = (project: Project) => {
    if (mode === 'select' && onSelectProject) {
      onSelectProject(project);
    }
  };

  // 表格列定义
  const columns: ColumnsType<Project> = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Project) => (
        <Button
          type="link"
          onClick={() => handleView(record)}
          style={{ padding: 0, textAlign: 'left' }}
        >
          {text}
        </Button>
      ),
    },
    {
      title: '项目编码',
      dataIndex: 'code',
      key: 'code',
      width: 120,
    },
    {
      title: '权属方',
      dataIndex: 'ownership_entity',
      key: 'ownership_entity',
      width: 150,
      render: (text: string, record: Project) => {
        // 如果有直接权属方字段，显示它
        if (text != null && text !== '') {
          return <Tag color="blue">{text}</Tag>;
        }

        // 如果有权属方关系，显示主要权属方
        if (record.ownership_relations != null && record.ownership_relations.length > 0) {
          const activeRelations = record.ownership_relations.filter(rel => rel.is_active === true);
          if (activeRelations.length > 0) {
            return (
              <div>
                {activeRelations.slice(0, 2).map((rel, _index) => (
                  <Tag key={rel.id} color="blue" style={{ marginRight: 4 }}>
                    {rel.ownership_name ?? '权属方已关联'}
                  </Tag>
                ))}
                {activeRelations.length > 2 && (
                  <Tag color="gray">+{activeRelations.length - 2}</Tag>
                )}
              </div>
            );
          }
        }

        return '-';
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 200,
      render: (text: string) => text ?? '-',
    },
    {
      title: '关联资产',
      dataIndex: 'asset_count',
      key: 'asset_count',
      width: 100,
      render: (count: number) => count ?? 0,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (isActive: boolean, _record: Project) => (
        <Badge status={isActive ? 'success' : 'error'} text={isActive ? '启用' : '禁用'} />
      ),
    },
    {
      title: '数据状态',
      dataIndex: 'data_status',
      key: 'data_status',
      width: 100,
      render: (text: string) => {
        let color = 'default';
        switch (text) {
          case '正常':
            color = 'green';
            break;
          case '禁用':
            color = 'red';
            break;
          case '删除':
            color = 'default';
            break;
        }
        return <Tag color={color}>{text ?? '-'}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record: Project) => (
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

  const handleKeywordChange = useCallback(
    (value: string) => {
      applyFilters({
        keyword: value,
        isActive: filters.isActive,
        ownershipId: filters.ownershipId,
      });
    },
    [applyFilters, filters.isActive, filters.ownershipId]
  );

  const handleStatusChange = useCallback(
    (value: boolean | undefined) => {
      applyFilters({
        keyword: filters.keyword,
        isActive: value === undefined ? null : value,
        ownershipId: filters.ownershipId,
      });
    },
    [applyFilters, filters.keyword, filters.ownershipId]
  );

  const handleOwnershipChange = useCallback(
    (value: string | undefined) => {
      applyFilters({
        keyword: filters.keyword,
        isActive: filters.isActive,
        ownershipId: value ?? '',
      });
    },
    [applyFilters, filters.isActive, filters.keyword]
  );

  return (
    <div className="project-list">
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总项目数"
              value={statistics?.total_count ?? 0}
              prefix={<span style={{ color: '#1890ff' }}>📊</span>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="启用项目"
              value={statistics?.active_count ?? 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<span style={{ color: '#52c41a' }}>✅</span>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="禁用项目"
              value={statistics?.inactive_count ?? 0}
              valueStyle={{ color: '#cf1322' }}
              prefix={<span style={{ color: '#ff4d4f' }}>❌</span>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总关联资产"
              value={projects.reduce((sum, project) => sum + (project.asset_count ?? 0), 0)}
              prefix={<span style={{ color: '#722ed1' }}>🏢</span>}
            />
          </Card>
        </Col>
      </Row>

      {/* 搜索和操作栏 */}
      <ListToolbar
        items={[
          {
            key: 'search',
            col: { xs: 24, sm: 12, md: 8, lg: 6 },
            content: (
              <Search
                placeholder="搜索项目名称、编码"
                allowClear
                enterButton={<SearchOutlined />}
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
            key: 'ownership',
            col: { xs: 24, sm: 12, md: 6, lg: 4 },
            content: (
              <Select
                placeholder="权属方"
                allowClear
                style={{ width: '100%' }}
                value={filters.ownershipId === '' ? undefined : filters.ownershipId}
                onChange={handleOwnershipChange}
                loading={ownershipsLoading}
                showSearch
                filterOption={(input, option) =>
                  String(option?.children || '')
                    .toLowerCase()
                    .includes(input.toLowerCase())
                }
              >
                {ownerships.map(ownership => (
                  <Option key={ownership.id} value={ownership.id}>
                    {ownership.name}
                  </Option>
                ))}
              </Select>
            ),
          },
          {
            key: 'reset',
            col: { xs: 24, sm: 12, md: 6, lg: 4 },
            content: (
              <Space>
                <Button
                  onClick={() => {
                    resetListFilters();
                  }}
                >
                  重置
                </Button>
              </Space>
            ),
          },
          {
            key: 'actions',
            col: { xs: 24, sm: 12, md: 6, lg: 4 },
            content: (
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                  新建项目
                </Button>
                <Button icon={<ReloadOutlined />} onClick={() => void loadList()}>
                  刷新
                </Button>
              </Space>
            ),
          },
        ]}
      />

      {/* 项目表格 */}
      <Card>
        <TableWithPagination
          columns={columns}
          dataSource={projects}
          rowKey="id"
          loading={loading}
          paginationState={pagination}
          onPageChange={updatePagination}
          paginationProps={{
            showTotal: (total: number, range: [number, number]) =>
              `第 ${range[0]}-${range[1]} 条/共 ${total} 条`,
          }}
          scroll={{ x: 800 }}
        />
      </Card>

      {/* 项目表单弹窗 */}
      <Modal
        title={editingProject ? '编辑项目' : '新建项目'}
        open={isModalVisible}
        onCancel={() => {
          setIsModalVisible(false);
          setEditingProject(null);
        }}
        footer={null}
        width={600}
        destroyOnHidden
      >
        <ProjectForm
          project={editingProject}
          onSuccess={() => {
            setIsModalVisible(false);
            setEditingProject(null);
            void loadList();
          }}
          onCancel={() => {
            setIsModalVisible(false);
            setEditingProject(null);
          }}
        />
      </Modal>

      {/* 项目详情弹窗 */}
      <Modal
        title="项目详情"
        open={isDetailVisible}
        onCancel={() => {
          setIsDetailVisible(false);
          setSelectedProject(null);
        }}
        footer={null}
        width={800}
        destroyOnHidden
      >
        {selectedProject && (
          <ProjectDetail
            project={selectedProject}
            onEdit={() => {
              setIsDetailVisible(false);
              setEditingProject(selectedProject);
              setIsModalVisible(true);
            }}
          />
        )}
      </Modal>
    </div>
  );
};

export default ProjectList;
