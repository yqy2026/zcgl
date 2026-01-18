/**
 * 项目列表组件 - 精简版本
 */

import React, { useState, useEffect } from 'react';
import {
  Table,
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
  Switch
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
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

import { projectService } from '@/services/projectService';
import { ownershipService } from '@/services/ownershipService';
import type { Project, ProjectStatisticsResponse } from '@/types/project';
import type { Ownership } from '@/types/ownership';
import { ProjectForm } from '@/components/Forms';
import ProjectDetail from './ProjectDetail';
// import OwnershipSelect from '@/components/Ownership/OwnershipSelect';

// 项目查询参数接口
interface ProjectQueryParams {
  page: number;
  size: number;
  keyword?: string;
  is_active?: boolean;
  ownership_id?: string;
}

const { Search } = Input;
const { Option } = Select;
const { confirm } = Modal;

interface ProjectListProps {
  onSelectProject?: (project: Project) => void;
  mode?: 'list' | 'select';
}

const ProjectList: React.FC<ProjectListProps> = ({
  onSelectProject,
  mode = 'list'
}) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [statistics, setStatistics] = useState<ProjectStatisticsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isDetailVisible, setIsDetailVisible] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [isActiveFilter, setIsActiveFilter] = useState<boolean | null>(null);
  const [ownershipFilter, setOwnershipFilter] = useState<string>('');
  const [ownerships, setOwnerships] = useState<Ownership[]>([]);
  const [ownershipsLoading, setOwnershipsLoading] = useState(false);

  // 分页状态
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });

  // 获取项目列表
  const fetchProjects = async () => {
    setLoading(true);
    try {
      const params: ProjectQueryParams = {
        page: pagination.current,
        size: pagination.pageSize
      };

      if (searchKeyword !== undefined && searchKeyword !== null) {
        params.keyword = searchKeyword;
      }

      if (isActiveFilter !== null) {
        params.is_active = isActiveFilter;
      }

      if (ownershipFilter !== undefined && ownershipFilter !== null) {
        params.ownership_id = ownershipFilter;
      }

      const response = await projectService.getProjects(params);
      // API response received

      // 处理后端响应格式: {items: [...], total: 58, page: 1, size: 10, pages: 6}
      if (response != null && 'items' in response) {
        // 标准响应格式：{items: [...], total: number, page: number, size: number}
        setProjects(response.items ?? []);
        setPagination(prev => ({
          ...prev,
          total: response.total ?? 0,
          current: response.page ?? prev.current,
          pageSize: response.size ?? prev.pageSize
        }));
      } else if (response != null && (response as any).data != null && (response as any).data.items != null) {
        // 嵌套响应格式：{data: {items: [...], total: number}}
        setProjects((response as any).data.items ?? []);
        setPagination(prev => ({
          ...prev,
          total: (response as any).data.total ?? (response as any).data.total_count ?? 0,
          current: (response as any).data.page ?? prev.current,
          pageSize: (response as any).data.size ?? prev.pageSize
        }));
      } else {
        // eslint-disable-next-line no-console
        console.error('Unexpected response format:', response ?? 'undefined response');
        setProjects([]);
        setPagination(prev => ({
          ...prev,
          total: 0
        }));
      }

      // 在项目数据加载后，基于实际数据计算统计信息
      const loadedProjects = response?.items ?? (response as any)?.data?.items ?? [];
      const activeCount = loadedProjects.filter(p => p.is_active === true).length;
      const inactiveCount = loadedProjects.length - activeCount;

      setStatistics({
        total_count: loadedProjects.length,
        active_count: activeCount,
        inactive_count: inactiveCount,
        type_distribution: {} as any, // 如需要可基于项目数据计算
        status_distribution: {} as any // 如需要可基于项目数据计算
      } as any);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('获取项目列表失败:', error);
      const err = error as any;
      // eslint-disable-next-line no-console
      console.error('Error details:', {
        message: err.message,
        status: err.response?.status,
        data: err.response?.data
      });
      MessageManager.error(`获取项目列表失败: ${err.message ?? '未知错误'}`);
    } finally {
      setLoading(false);
    }
  };

  // 获取统计信息 - 基于本地项目数据计算
  const _fetchStatistics = async () => {
    try {
      // 由于后端没有提供统计API，我们基于当前项目数据计算统计信息
      // 这里使用空数组，实际统计会在项目数据加载后计算
      setStatistics({
        total_count: 0,
        active_count: 0,
        inactive_count: 0,
        type_distribution: {} as any,
        status_distribution: {} as any
      } as any);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('获取统计信息失败:', error);
      setStatistics(null);
    }
  };

  // 获取权属方列表（使用下拉选项API，更高效）
  const fetchOwnerships = async () => {
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
  };

  useEffect(() => {
    const loadData = async () => {
      await Promise.all([
        fetchProjects(),
        fetchOwnerships()
      ]);
    };
    loadData();
  }, [pagination.current, pagination.pageSize, searchKeyword, isActiveFilter, ownershipFilter]);

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
          fetchProjects();
        } catch (error) {
          // eslint-disable-next-line no-console
          console.error('删除项目失败:', error);
          MessageManager.error('删除项目失败');
        }
      }
    });
  };

  // 切换项目状态
  const handleToggleStatus = async (project: Project) => {
    try {
      await projectService.toggleProjectStatus(project.id);
      MessageManager.success('项目状态切换成功');
      fetchProjects();
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
      )
    },
    {
      title: '项目编码',
      dataIndex: 'code',
      key: 'code',
      width: 120
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
                    {rel.ownership_name ?? (record as any).ownership_entity ?? '权属方已关联'}
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
      }
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 200,
      render: (text: string) => text ?? '-'
    },
    {
      title: '关联资产',
      dataIndex: 'asset_count',
      key: 'asset_count',
      width: 100,
      render: (count: number) => count ?? 0
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (isActive: boolean, _record: Project) => (
        <Badge
          status={isActive ? 'success' : 'error'}
          text={isActive ? '启用' : '禁用'}
        />
      )
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
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record: Project) => (
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
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} md={8} lg={6}>
            <Search
              placeholder="搜索项目名称、编码"
              allowClear
              enterButton={<SearchOutlined />}
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              onSearch={fetchProjects}
            />
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Select
              placeholder="状态"
              allowClear
              style={{ width: '100%' }}
              value={isActiveFilter === null ? undefined : isActiveFilter}
              onChange={(value) => setIsActiveFilter(value === undefined ? null : value)}
            >
              <Option value={true}>启用</Option>
              <Option value={false}>禁用</Option>
            </Select>
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Select
              placeholder="权属方"
              allowClear
              style={{ width: '100%' }}
              value={ownershipFilter || undefined}
              onChange={(value) => setOwnershipFilter(value || '')}
              loading={ownershipsLoading}
              showSearch
              filterOption={(input, option) =>
                String(option?.children || '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {ownerships.map(ownership => (
                <Option key={ownership.id} value={ownership.id}>
                  {ownership.name}
                </Option>
              ))}
            </Select>
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Space>
              <Button onClick={() => {
                setSearchKeyword('');
                setIsActiveFilter(null);
                setOwnershipFilter('');
              }}>
                重置
              </Button>
            </Space>
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreate}
              >
                新建项目
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchProjects}
              >
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 项目表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={projects}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条/共 ${total} 条`,
            onChange: (page, pageSize) => {
              setPagination(prev => ({
                ...prev,
                current: page,
                pageSize: pageSize || prev.pageSize
              }));
            }
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
            fetchProjects();
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
