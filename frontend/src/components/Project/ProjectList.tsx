/**
 * 项目列表组件 - 容器组件
 * 表格列定义见 ProjectTable.tsx，操作弹窗见 ProjectActions.tsx
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Space,
  Card,
  Row,
  Col,
  Statistic,
  Input,
  Select,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  BankOutlined,
} from '@ant-design/icons';

import { projectService } from '@/services/projectService';
import { partyService } from '@/services/partyService';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { ListToolbar } from '@/components/Common/ListToolbar';
import CurrentViewBanner from '@/components/System/CurrentViewBanner';
import { useView } from '@/contexts/ViewContext';
import { useQuery } from '@tanstack/react-query';
import type { Project, ProjectListResponse, ProjectStatisticsResponse } from '@/types/project';
import type { Party } from '@/types/party';
import { buildQueryScopeKey } from '@/utils/queryScope';
import styles from './ProjectList.module.css';

import { getProjectColumns, getProjectAssetCount } from './ProjectTable';
import { confirmDeleteProject, toggleProjectStatus, ProjectFormModal, ProjectDetailModal } from './ProjectActions';

// 项目查询参数接口
interface ProjectQueryParams {
  page: number;
  page_size: number;
  keyword?: string;
  status?: string;
  owner_party_id?: string;
}

interface ProjectFilters {
  keyword: string;
  status: string;
  ownerPartyId: string;
}

const { Search } = Input;
const { Option } = Select;

interface ProjectListProps {
  onSelectProject?: (project: Project) => void;
  mode?: 'list' | 'select';
}

const ProjectList: React.FC<ProjectListProps> = ({ onSelectProject, mode = 'list' }) => {
  const { currentView, isViewReady } = useView();
  const [filters, setFilters] = useState<ProjectFilters>({
    keyword: '',
    status: '',
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
  const queryScopeKey = buildQueryScopeKey(currentView);

  const fetchProjectList = useCallback(async () => {
    const params: ProjectQueryParams = {
      page: paginationState.current,
      page_size: paginationState.pageSize,
    };

    const trimmedKeyword = filters.keyword.trim();
    if (trimmedKeyword !== '') {
      params.keyword = trimmedKeyword;
    }

    if (filters.status !== '') {
      params.status = filters.status;
    }

    const trimmedOwnerPartyId = filters.ownerPartyId.trim();
    if (trimmedOwnerPartyId !== '') {
      params.owner_party_id = trimmedOwnerPartyId;
    }

    return await projectService.getProjects(params);
  }, [
    filters.keyword,
    filters.ownerPartyId,
    filters.status,
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
    queryKey: [
      'project-list',
      queryScopeKey,
      paginationState.current,
      paginationState.pageSize,
      filters,
    ],
    queryFn: fetchProjectList,
    retry: 1,
    enabled: isViewReady,
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
    const activeCount = projects.filter(project => project.status === 'active').length;
    return {
      total_projects: totalCount,
      active_projects: activeCount,
    };
  }, [projects]);

  const {
    data: ownerParties = [],
    isLoading: isOwnerPartiesLoading,
    isFetching: isOwnerPartiesFetching,
  } = useQuery<Party[]>({
    queryKey: ['project-owner-party-options', queryScopeKey, ownerPartySearchKeyword],
    queryFn: async () =>
      (
        await partyService.searchParties(ownerPartySearchKeyword, {
          status: 'active',
          limit: 20,
        })
      ).items,
    staleTime: 10 * 60 * 1000,
    retry: 1,
    enabled: isViewReady,
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
      status: '',
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

  // --- 操作回调 ---

  const handleDelete = useCallback(
    (project: Project) => {
      confirmDeleteProject(project, refreshProjects);
    },
    [refreshProjects]
  );

  const handleToggleStatus = useCallback(
    async (project: Project) => {
      await toggleProjectStatus(project, refreshProjects);
    },
    [refreshProjects]
  );

  const handleView = useCallback((project: Project) => {
    setSelectedProject(project);
    setIsDetailVisible(true);
  }, []);

  const handleEdit = useCallback((project: Project) => {
    setEditingProject(project);
    setIsModalVisible(true);
  }, []);

  const handleCreate = useCallback(() => {
    setEditingProject(null);
    setIsModalVisible(true);
  }, []);

  const handleSelect = useCallback(
    (project: Project) => {
      if (mode === 'select' && onSelectProject != null) {
        onSelectProject(project);
      }
    },
    [mode, onSelectProject]
  );

  // --- 表格列 ---

  const columns = useMemo(
    () =>
      getProjectColumns({
        onView: handleView,
        onEdit: handleEdit,
        onDelete: handleDelete,
        onSelect: handleSelect,
        onToggleStatus: handleToggleStatus,
        mode,
      }),
    [handleDelete, handleEdit, handleSelect, handleToggleStatus, handleView, mode]
  );

  // --- 筛选回调 ---

  const handleKeywordChange = useCallback(
    (value: string) => {
      updateFilters({ keyword: value });
    },
    [updateFilters]
  );

  const handleStatusChange = useCallback(
    (value: string | undefined) => {
      updateFilters({ status: value ?? '' });
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
      <CurrentViewBanner />

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} className={styles.statisticsRow}>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.statsTotal}`}>
            <Statistic
              title="总项目数"
              value={statistics.total_projects}
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
              value={statistics.active_projects}
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
              value={Math.max(0, statistics.total_projects - statistics.active_projects)}
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
                value={filters.status === '' ? undefined : filters.status}
                onChange={handleStatusChange}
              >
                <Option value="planning">规划中</Option>
                <Option value="active">进行中</Option>
                <Option value="paused">已暂停</Option>
                <Option value="completed">已完成</Option>
                <Option value="terminated">已终止</Option>
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
      <ProjectFormModal
        visible={isModalVisible}
        editingProject={editingProject}
        onClose={() => {
          setIsModalVisible(false);
          setEditingProject(null);
        }}
        onSuccess={() => {
          setIsModalVisible(false);
          setEditingProject(null);
          refreshProjects();
        }}
      />

      {/* 项目详情弹窗 */}
      <ProjectDetailModal
        visible={isDetailVisible}
        project={selectedProject}
        onClose={() => {
          setIsDetailVisible(false);
          setSelectedProject(null);
        }}
        onEdit={() => {
          setIsDetailVisible(false);
          setEditingProject(selectedProject);
          setIsModalVisible(true);
        }}
      />
    </div>
  );
};

export default ProjectList;
