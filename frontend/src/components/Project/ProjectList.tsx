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

import { projectService } from '@/services/projectService';
import { ownershipService } from '@/services/ownershipService';
import type { Project, ProjectListResponse, ProjectStatisticsResponse } from '@/types/project';
import type { Ownership } from '@/types/ownership';
import ProjectForm from './ProjectForm';
import ProjectDetail from './ProjectDetail';
// import OwnershipSelect from '@/components/Ownership/OwnershipSelect';

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
  const [statsLoading, setStatsLoading] = useState(false);
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
      const params: any = {
        page: pagination.current,
        size: pagination.pageSize
      };

      if (searchKeyword) {
        params.keyword = searchKeyword;
      }

      if (isActiveFilter !== null) {
        params.is_active = isActiveFilter;
      }

      if (ownershipFilter) {
        params.ownership_id = ownershipFilter;
      }

      const response: ProjectListResponse = await projectService.getProjects(params);
      setProjects(response.items);
      setPagination(prev => ({
        ...prev,
        total: response.total
      }));
    } catch (error) {
      console.error('获取项目列表失败:', error);
      message.error('获取项目列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取统计信息
  const fetchStatistics = async () => {
    setStatsLoading(true);
    try {
      const response: ProjectStatisticsResponse = await projectService.getProjectStatistics();
      setStatistics(response);
    } catch (error) {
      console.error('获取统计信息失败:', error);
    } finally {
      setStatsLoading(false);
    }
  };

  // 获取权属方列表（使用下拉选项API，更高效）
  const fetchOwnerships = async () => {
    setOwnershipsLoading(true);
    try {
      const response = await ownershipService.getOwnershipOptions(true);
      setOwnerships(response);
    } catch (error) {
      console.error('获取权属方列表失败:', error);
    } finally {
      setOwnershipsLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchStatistics();
    fetchOwnerships();
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
          message.success('项目删除成功');
          fetchProjects();
          fetchStatistics();
        } catch (error) {
          console.error('删除项目失败:', error);
          message.error('删除项目失败');
        }
      }
    });
  };

  // 切换项目状态
  const handleToggleStatus = async (project: Project) => {
    try {
      await projectService.toggleProjectStatus(project.id);
      message.success('项目状态切换成功');
      fetchProjects();
      fetchStatistics();
    } catch (error) {
      console.error('切换项目状态失败:', error);
      message.error('切换项目状态失败');
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
        if (text) {
          return <Tag color="blue">{text}</Tag>;
        }

        // 如果有权属方关系，显示主要权属方
        if (record.ownership_relations && record.ownership_relations.length > 0) {
          const activeRelations = record.ownership_relations.filter(rel => rel.is_active);
          if (activeRelations.length > 0) {
            return (
              <div>
                {activeRelations.slice(0, 2).map((rel, index) => (
                  <Tag key={rel.id} color="blue" style={{ marginRight: 4 }}>
                    {rel.ownership_name || record.ownership_entity || '权属方已关联'}
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
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (isActive: boolean, record: Project) => (
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
        return <Tag color={color}>{text}</Tag>;
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
              value={statistics?.total_count || 0}
              loading={statsLoading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="启用项目"
              value={statistics?.active_count || 0}
              valueStyle={{ color: '#3f8600' }}
              loading={statsLoading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="禁用项目"
              value={statistics?.inactive_count || 0}
              valueStyle={{ color: '#cf1322' }}
              loading={statsLoading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总关联资产"
              value={projects.reduce((sum, project) => sum + (project.asset_count || 0), 0)}
              loading={statsLoading}
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
                (option?.children as string)?.toLowerCase().includes(input.toLowerCase())
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
        destroyOnClose
      >
        <ProjectForm
          project={editingProject}
          onSuccess={() => {
            setIsModalVisible(false);
            setEditingProject(null);
            fetchProjects();
            fetchStatistics();
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
        destroyOnClose
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