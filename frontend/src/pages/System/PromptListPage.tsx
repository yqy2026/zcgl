/**
 * LLM Prompt 管理列表页面
 * 提供 Prompt 模板的列表展示、筛选、激活、版本管理等功能
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Table,
  Card,
  Button,
  Space,
  Tag,
  Select,
  Modal,
  Tooltip,
  Row,
  Col,
  Statistic,
  Typography,
  message,
  type TableProps,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  RocketOutlined,
  HistoryOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import {
  PromptTemplate,
  PromptStatus,
  DocType,
  LLMProvider,
  PromptQueryParams,
  PromptStatistics,
} from '@/types/llmPrompt';
import { llmPromptService } from '@/services/llmPromptService';
import { createLogger } from '@/utils/logger';
import { COLORS } from '@/styles/colorMap';
import PromptEditor from '@/components/System/PromptEditor';

const logger = createLogger('PromptListPage');
const { Title } = Typography;
const { Option } = Select;

interface PageState {
  loading: boolean;
  prompts: PromptTemplate[];
  pagination: {
    current: number;
    pageSize: number;
    total: number;
  };
  filters: PromptQueryParams;
  statistics: PromptStatistics | null;
  editorVisible: boolean;
  editorMode: 'create' | 'edit';
  selectedPrompt: PromptTemplate | null;
}

const PromptListPage: React.FC = () => {
  const [state, setState] = useState<PageState>({
    loading: false,
    prompts: [],
    pagination: {
      current: 1,
      pageSize: 10,
      total: 0,
    },
    filters: {},
    statistics: null,
    editorVisible: false,
    editorMode: 'create',
    selectedPrompt: null,
  });

  // 加载 Prompt 列表
  const loadPrompts = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true }));
    try {
      const response = await llmPromptService.getPrompts({
        page: state.pagination.current,
        pageSize: state.pagination.pageSize,
        ...state.filters,
      });

      const prompts = Array.isArray(response.items) ? response.items : [];

      setState(prev => ({
        ...prev,
        loading: false,
        prompts: prompts,
        pagination: {
          ...prev.pagination,
          total: response.total,
        },
      }));
    } catch (error) {
      logger.error('加载 Prompt 列表失败', error);
      message.error('加载 Prompt 列表失败');
      setState(prev => ({ ...prev, loading: false }));
    }
  }, [state.pagination.current, state.pagination.pageSize, state.filters]);

  // 加载统计数据
  const loadStatistics = useCallback(async () => {
    try {
      const stats = await llmPromptService.getStatistics();
      setState(prev => ({ ...prev, statistics: stats }));
    } catch (error) {
      logger.error('加载统计数据失败', error);
    }
  }, []);

  useEffect(() => {
    loadPrompts();
    loadStatistics();
  }, [loadPrompts, loadStatistics]);

  // 激活 Prompt
  const handleActivate = async (id: string, name: string) => {
    try {
      await llmPromptService.activatePrompt(id);
      message.success(`Prompt "${name}" 已激活`);
      loadPrompts();
    } catch (error) {
      logger.error(`激活 Prompt 失败: ${id}`, error);
      message.error('激活失败');
    }
  };

  // 查看版本历史
  const handleViewVersions = async (prompt: PromptTemplate) => {
    try {
      const versions = await llmPromptService.getPromptVersions(prompt.id);

      Modal.info({
        title: `版本历史 - ${prompt.name}`,
        width: 800,
        content: (
          <div style={{ marginTop: 16 }}>
            {versions.length === 0 ? (
              <p>暂无版本记录</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <th style={{ padding: '8px', textAlign: 'left' }}>版本</th>
                    <th style={{ padding: '8px', textAlign: 'left' }}>变更说明</th>
                    <th style={{ padding: '8px', textAlign: 'left' }}>创建时间</th>
                    <th style={{ padding: '8px', textAlign: 'left' }}>自动生成</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map(version => (
                    <tr key={version.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '8px' }}>
                        <Tag color="blue">{version.version}</Tag>
                      </td>
                      <td style={{ padding: '8px' }}>{version.change_description || '-'}</td>
                      <td style={{ padding: '8px' }}>
                        {dayjs(version.created_at).format('YYYY-MM-DD HH:mm')}
                      </td>
                      <td style={{ padding: '8px' }}>
                        {version.auto_generated ? <Tag color="purple">自动</Tag> : <Tag>手动</Tag>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ),
      });
    } catch (error) {
      logger.error(`获取版本历史失败: ${prompt.id}`, error);
      message.error('获取版本历史失败');
    }
  };

  // 打开新建编辑器
  const handleCreate = () => {
    setState(prev => ({
      ...prev,
      editorVisible: true,
      editorMode: 'create',
      selectedPrompt: null,
    }));
  };

  // 打开编辑编辑器
  const handleEdit = (prompt: PromptTemplate) => {
    setState(prev => ({
      ...prev,
      editorVisible: true,
      editorMode: 'edit',
      selectedPrompt: prompt,
    }));
  };

  // 关闭编辑器
  const handleEditorCancel = () => {
    setState(prev => ({
      ...prev,
      editorVisible: false,
      selectedPrompt: null,
    }));
  };

  // 编辑器成功回调
  const handleEditorSuccess = () => {
    setState(prev => ({
      ...prev,
      editorVisible: false,
      selectedPrompt: null,
    }));
    loadPrompts();
    loadStatistics();
  };

  // 表格列定义
  const columns: ColumnsType<PromptTemplate> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text: string, record: PromptTemplate) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#999' }}>v{record.version}</div>
        </div>
      ),
    },
    {
      title: '文档类型',
      dataIndex: 'doc_type',
      key: 'doc_type',
      width: 120,
      render: (docType: DocType) => {
        const config: Record<DocType, { text: string; color: string }> = {
          [DocType.CONTRACT]: { text: '租赁合同', color: 'blue' },
          [DocType.PROPERTY_CERT]: { text: '产权证', color: 'green' },
        };
        const { text, color } = config[docType] ?? { text: docType, color: 'default' };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '提供商',
      dataIndex: 'provider',
      key: 'provider',
      width: 100,
      render: (provider: LLMProvider) => {
        const config: Record<LLMProvider, { text: string; color: string }> = {
          [LLMProvider.QWEN]: { text: 'Qwen', color: 'cyan' },
          [LLMProvider.HUNYUAN]: { text: '混元', color: 'purple' },
          [LLMProvider.DEEPSEEK]: { text: 'DeepSeek', color: 'orange' },
          [LLMProvider.GLM]: { text: '智谱', color: 'geekblue' },
        };
        const { text, color } = config[provider] ?? { text: provider, color: 'default' };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: PromptStatus) => {
        const config: Record<PromptStatus, { text: string; color: string; icon: React.ReactNode }> =
          {
            [PromptStatus.ACTIVE]: {
              text: '活跃',
              color: 'success',
              icon: <CheckCircleOutlined />,
            },
            [PromptStatus.DRAFT]: { text: '草稿', color: 'default', icon: null },
            [PromptStatus.ARCHIVED]: { text: '已归档', color: 'default', icon: null },
          };
        const { text, color, icon } = config[status] ?? {
          text: status,
          color: 'default',
          icon: null,
        };
        return (
          <Tag icon={icon} color={color}>
            {text}
          </Tag>
        );
      },
    },
    {
      title: '平均准确率',
      dataIndex: 'avg_accuracy',
      key: 'avg_accuracy',
      width: 120,
      render: (value: number) => (
        <div>
          <div
            style={{
              fontWeight: value >= 90 ? 'bold' : 'normal',
              color: value >= 90 ? COLORS.success : value >= 70 ? COLORS.warning : COLORS.error,
            }}
          >
            {(value * 100).toFixed(1)}%
          </div>
        </div>
      ),
    },
    {
      title: '平均置信度',
      dataIndex: 'avg_confidence',
      key: 'avg_confidence',
      width: 120,
      render: (value: number) => (
        <div>
          <div
            style={{
              color: value >= 0.8 ? COLORS.success : value >= 0.6 ? COLORS.warning : COLORS.error,
            }}
          >
            {(value * 100).toFixed(1)}%
          </div>
        </div>
      ),
    },
    {
      title: '使用次数',
      dataIndex: 'total_usage',
      key: 'total_usage',
      width: 100,
      render: (value: number) => <span>{value}</span>,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 120,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right' as const,
      render: (_: any, record: PromptTemplate) => (
        <Space size="small">
          {record.status !== PromptStatus.ACTIVE && (
            <Tooltip title="激活">
              <Button
                type="text"
                icon={<RocketOutlined />}
                onClick={() => handleActivate(record.id, record.name)}
              />
            </Tooltip>
          )}
          <Tooltip title="版本历史">
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => handleViewVersions(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 处理表格变化
  const handleTableChange: TableProps<PromptTemplate>['onChange'] = pagination => {
    setState(prev => ({
      ...prev,
      pagination: {
        ...prev.pagination,
        current: pagination.current ?? 1,
        pageSize: pagination.pageSize ?? 10,
      },
    }));
  };

  // 处理筛选变化
  const handleFilterChange = (key: keyof PromptQueryParams, value: any) => {
    setState(prev => ({
      ...prev,
      filters: {
        ...prev.filters,
        [key]: value,
      },
      pagination: {
        ...prev.pagination,
        current: 1,
      },
    }));
  };

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 统计卡片 */}
      {state.statistics != null && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总 Prompt 数"
                value={state.statistics.total_prompts}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="活跃 Prompt"
                value={
                  state.statistics.status_distribution.find(
                    (s: { status: PromptStatus; count: number }) => s.status === PromptStatus.ACTIVE
                  )?.count ?? 0
                }
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: COLORS.success }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均准确率"
                value={(state.statistics.overall_avg_accuracy * 100).toFixed(1)}
                suffix="%"
                valueStyle={{
                  color:
                    state.statistics.overall_avg_accuracy >= 0.85 ? COLORS.success : COLORS.warning,
                }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均置信度"
                value={(state.statistics.overall_avg_confidence * 100).toFixed(1)}
                suffix="%"
                valueStyle={{
                  color:
                    state.statistics.overall_avg_confidence >= 0.8
                      ? COLORS.success
                      : COLORS.warning,
                }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 主卡片 */}
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              LLM Prompt 管理
            </Title>
            <Button icon={<ReloadOutlined />} onClick={loadPrompts}>
              刷新
            </Button>
          </Space>
        }
        extra={
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建 Prompt
            </Button>
          </Space>
        }
      >
        {/* 筛选器 */}
        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            placeholder="文档类型"
            allowClear
            style={{ width: 150 }}
            value={state.filters.doc_type}
            onChange={value => handleFilterChange('doc_type', value)}
          >
            <Option value={DocType.CONTRACT}>租赁合同</Option>
            <Option value={DocType.PROPERTY_CERT}>产权证</Option>
          </Select>

          <Select
            placeholder="提供商"
            allowClear
            style={{ width: 150 }}
            value={state.filters.provider}
            onChange={value => handleFilterChange('provider', value)}
          >
            <Option value={LLMProvider.QWEN}>Qwen</Option>
            <Option value={LLMProvider.HUNYUAN}>混元</Option>
            <Option value={LLMProvider.DEEPSEEK}>DeepSeek</Option>
            <Option value={LLMProvider.GLM}>智谱</Option>
          </Select>

          <Select
            placeholder="状态"
            allowClear
            style={{ width: 120 }}
            value={state.filters.status}
            onChange={value => handleFilterChange('status', value)}
          >
            <Option value={PromptStatus.ACTIVE}>活跃</Option>
            <Option value={PromptStatus.DRAFT}>草稿</Option>
            <Option value={PromptStatus.ARCHIVED}>已归档</Option>
          </Select>
        </Space>

        {/* 表格 */}
        <Table
          columns={columns}
          dataSource={state.prompts}
          rowKey="id"
          loading={state.loading}
          pagination={state.pagination}
          onChange={handleTableChange}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* Prompt 编辑器 */}
      <PromptEditor
        visible={state.editorVisible}
        prompt={state.selectedPrompt}
        mode={state.editorMode}
        onSuccess={handleEditorSuccess}
        onCancel={handleEditorCancel}
      />
    </div>
  );
};

export default PromptListPage;
