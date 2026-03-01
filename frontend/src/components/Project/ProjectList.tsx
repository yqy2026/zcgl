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
  BarChartOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  BankOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

import { projectService } from '@/services/projectService';
import { partyService } from '@/services/partyService';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { ListToolbar } from '@/components/Common/ListToolbar';
import { useQuery } from '@tanstack/react-query';
import { getIconButtonProps } from '@/utils/accessibility';
import type { Project, ProjectListResponse, ProjectStatisticsResponse } from '@/types/project';
import type { Party } from '@/types/party';
import { ProjectForm } from '@/components/Forms';
import ProjectDetail from './ProjectDetail';
import styles from './ProjectList.module.css';
// import OwnershipSelect from '@/components/Ownership/OwnershipSelect';

interface LegacyOwnershipRelation {
  id?: string;
  party_id?: string;
  is_active?: boolean;
}

interface ProjectWithAssetsFallback extends Project {
  assets?: unknown[];
}

const resolveLegacyOwnershipRelations = (project: Project): LegacyOwnershipRelation[] => {
  const legacyRelations = (
    project as Project & {
      ownership_relations?: LegacyOwnershipRelation[];
    }
  ).ownership_relations;

  return Array.isArray(legacyRelations) ? legacyRelations : [];
};

const isRelationActive = (
  project: Project,
  relation: { id?: string; party_id: string; is_active?: boolean }
): boolean => {
  if (relation.is_active === true) {
    return true;
  }

  if (relation.is_active === false) {
    return false;
  }

  const legacyRelations = resolveLegacyOwnershipRelations(project);
  if (legacyRelations.length === 0) {
    return false;
  }

  const relationId = relation.id?.trim();
  if (relationId != null && relationId !== '') {
    const matchedById = legacyRelations.find(legacyRelation => legacyRelation.id === relationId);
    if (matchedById != null) {
      return matchedById.is_active === true;
    }
  }

  const partyId = relation.party_id.trim();
  if (partyId !== '') {
    const matchedByPartyId = legacyRelations.find(
      legacyRelation => legacyRelation.party_id === partyId
    );
    if (matchedByPartyId != null) {
      return matchedByPartyId.is_active === true;
    }
  }

  return false;
};

const getProjectAssetCount = (project: Project): number => {
  if (typeof project.asset_count === 'number' && Number.isFinite(project.asset_count)) {
    return project.asset_count;
  }

  const fallbackAssets = (project as ProjectWithAssetsFallback).assets;
  if (Array.isArray(fallbackAssets)) {
    return fallbackAssets.length;
  }

  return 0;
};

const isPendingBindingProject = (project: Project): boolean => getProjectAssetCount(project) === 0;

// 项目查询参数接口
interface ProjectQueryParams {
  page: number;
  page_size: number;
  keyword?: string;
  is_active?: boolean;
  owner_party_id?: string;
}

interface ProjectFilters {
  keyword: string;
  isActive: boolean | null;
  ownerPartyId: string;
}

const { Search } = Input;
const { Option } = Select;
const { confirm } = Modal;

interface ProjectListProps {
  onSelectProject?: (project: Project) => void;
  mode?: 'list' | 'select';
}

const ProjectList: React.FC<ProjectListProps> = ({ onSelectProject, mode = 'list' }) => {
  const [filters, setFilters] = useState<ProjectFilters>({
    keyword: '',
    isActive: null,
    ownerPartyId: '',
  });
  const [ownerPartySearchKeyword, setOwnerPartySearchKeyword] = useState('');
  const [paginationState, setPaginationState] = useState({
    current: 1,
    pageSize: 10,
  });
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isDetailVisible, setIsDetailVisible] = useState(false);

  const fetchProjectList = useCallback(async () => {
    const params: ProjectQueryParams = {
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

    const trimmedOwnerPartyId = filters.ownerPartyId.trim();
    if (trimmedOwnerPartyId !== '') {
      params.owner_party_id = trimmedOwnerPartyId;
    }

    return await projectService.getProjects(params);
  }, [
    filters.isActive,
    filters.keyword,
    filters.ownerPartyId,
    paginationState.current,
    paginationState.pageSize,
  ]);

  const {
    data: projectsResponse,
    error: projectsError,
    isLoading: isProjectsLoading,
    isFetching: isProjectsFetching,
    refetch: refetchProjects,
  } = useQuery<ProjectListResponse>({
    queryKey: ['project-list', paginationState.current, paginationState.pageSize, filters],
    queryFn: fetchProjectList,
    retry: 1,
  });

  useEffect(() => {
    if (projectsError != null) {
      console.error('获取项目列表失败:', projectsError);
      const err = projectsError as Error & { response?: { status?: number; data?: unknown } };
      console.error('Error details:', {
        message: err.message,
        status: err.response?.status,
        data: err.response?.data,
      });
      MessageManager.error(`获取项目列表失败: ${err.message ?? '未知错误'}`);
    }
  }, [projectsError]);

  const projects = projectsResponse?.items ?? [];
  const loading = isProjectsLoading || isProjectsFetching;
  const pagination = useMemo(
    () => ({
      current: paginationState.current,
      pageSize: paginationState.pageSize,
      total: projectsResponse?.total ?? 0,
    }),
    [paginationState.current, paginationState.pageSize, projectsResponse?.total]
  );

  const statistics = useMemo<ProjectStatisticsResponse>(() => {
    const totalCount = projects.length;
    const activeCount = projects.filter(project => project.is_active === true).length;
    return {
      total_count: totalCount,
      active_count: activeCount,
      inactive_count: totalCount - activeCount,
    };
  }, [projects]);

  const {
    data: ownerParties = [],
    isLoading: isOwnerPartiesLoading,
    isFetching: isOwnerPartiesFetching,
  } = useQuery<Party[]>({
    queryKey: ['project-owner-party-options', ownerPartySearchKeyword],
    queryFn: async () =>
      (
        await partyService.searchParties(ownerPartySearchKeyword, {
          status: 'active',
          limit: 20,
        })
      ).items,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const ownerPartiesLoading = isOwnerPartiesLoading || isOwnerPartiesFetching;

  const refreshProjects = useCallback(() => {
    void refetchProjects();
  }, [refetchProjects]);

  const updateFilters = useCallback((nextFilters: Partial<ProjectFilters>) => {
    setFilters(prev => ({ ...prev, ...nextFilters }));
    setPaginationState(prev => ({ ...prev, current: 1 }));
  }, []);

  const resetListFilters = useCallback(() => {
    setFilters({
      keyword: '',
      isActive: null,
      ownerPartyId: '',
    });
    setOwnerPartySearchKeyword('');
    setPaginationState(prev => ({ ...prev, current: 1 }));
  }, []);

  const handlePageChange = useCallback((next: { current?: number; pageSize?: number }) => {
    setPaginationState(prev => ({
      current: next.current ?? prev.current,
      pageSize: next.pageSize ?? prev.pageSize,
    }));
  }, []);

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
          refreshProjects();
        } catch (error) {
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
      refreshProjects();
    } catch (error) {
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
        <Button type="link" onClick={() => handleView(record)} className={styles.projectNameButton}>
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
      title: '所有方主体',
      dataIndex: 'party_relations',
      key: 'owner_party',
      width: 150,
      render: (_relations: Project['party_relations'], record: Project) => {
        // 优先展示 active 的 party_relations
        if (record.party_relations != null && record.party_relations.length > 0) {
          const activeRelations = record.party_relations.filter(rel =>
            isRelationActive(record, rel)
          );
          if (activeRelations.length > 0) {
            return (
              <div>
                {activeRelations.slice(0, 2).map((rel, index) => (
                  <Tag
                    key={rel.id ?? `${rel.party_id}-${index}`}
                    color="blue"
                    className={styles.ownershipTag}
                  >
                    {rel.party_name ?? '主体已关联'}
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
      render: (_count: number, record: Project) => getProjectAssetCount(record),
    },
    {
      title: '面积统计',
      key: 'area_status',
      width: 100,
      render: (_value: unknown, record: Project) =>
        isPendingBindingProject(record) ? <Tag color="default">N/A</Tag> : '-',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (isActive: boolean, record: Project) => (
        <Space size="small">
          <Badge status={isActive ? 'success' : 'error'} text={isActive ? '启用' : '禁用'} />
          {isPendingBindingProject(record) && <Tag color="warning">待补绑定</Tag>}
        </Space>
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
                <Button
                  type="text"
                  icon={<EyeOutlined />}
                  onClick={() => handleView(record)}
                  {...getIconButtonProps('view', '项目')}
                />
              </Tooltip>
              <Tooltip title="编辑">
                <Button
                  type="text"
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(record)}
                  {...getIconButtonProps('edit', '项目')}
                />
              </Tooltip>
              <Tooltip title="删除">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleDelete(record)}
                  {...getIconButtonProps('delete', '项目')}
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
            aria-label={`${record.is_active ? '停用' : '启用'}项目 ${record.name}`}
          />
        </Space>
      ),
    },
  ];

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

  const handleOwnerPartyChange = useCallback(
    (value: string | undefined) => {
      updateFilters({ ownerPartyId: value ?? '' });
    },
    [updateFilters]
  );

  const handleOwnerPartySearch = useCallback((value: string) => {
    setOwnerPartySearchKeyword(value.trim());
  }, []);

  return (
    <div className="project-list">
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} className={styles.statisticsRow}>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.statsTotal}`}>
            <Statistic
              title="总项目数"
              value={statistics?.total_count ?? 0}
              prefix={
                <span className={styles.statPrefixPrimary} aria-hidden>
                  <BarChartOutlined />
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.statsActive}`}>
            <Statistic
              title="启用项目"
              value={statistics?.active_count ?? 0}
              prefix={
                <span className={styles.statPrefixSuccess} aria-hidden>
                  <CheckCircleOutlined />
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.statsInactive}`}>
            <Statistic
              title="禁用项目"
              value={statistics?.inactive_count ?? 0}
              prefix={
                <span className={styles.statPrefixError} aria-hidden>
                  <CloseCircleOutlined />
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.statsAssets}`}>
            <Statistic
              title="总关联资产"
              value={projects.reduce((sum, project) => sum + getProjectAssetCount(project), 0)}
              prefix={
                <span className={styles.statPrefixInfo} aria-hidden>
                  <BankOutlined />
                </span>
              }
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
                className={styles.fullWidthSelect}
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
                placeholder="所有方主体"
                allowClear
                className={styles.fullWidthSelect}
                value={filters.ownerPartyId === '' ? undefined : filters.ownerPartyId}
                onChange={handleOwnerPartyChange}
                onSearch={handleOwnerPartySearch}
                onClear={() => setOwnerPartySearchKeyword('')}
                loading={ownerPartiesLoading}
                showSearch
                filterOption={false}
              >
                {ownerParties.map(party => (
                  <Option key={party.id} value={party.id}>
                    {party.name}
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
                <Button icon={<ReloadOutlined />} onClick={refreshProjects}>
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
          onPageChange={handlePageChange}
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
            refreshProjects();
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
